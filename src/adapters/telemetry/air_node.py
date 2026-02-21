# A.I.R. Node Telemetry Adapter
# Blackglass Variance Core // Blackglass Continuum LLC
# CAGE: 17TJ5 | UEI: SVZVXPTM9AF4
#
# Polls the A.I.R. VaultNode /incidents endpoint and translates
# incident rate into a normalized variance signal compatible with
# the watchtower.analysis.v1 schema.
#
# Plug-in point: telemetry_mode="air_node" in watch_variance()

import datetime
import os
from typing import Optional

import requests

# Constitutional baseline: incidents per minute that maps to V(t) = 1.0
# At or above this rate, norm_incident_rate is capped at 1.0.
# 10 incidents/min = semantic collapse. Tune via AIR_INCIDENT_SATURATION env.
_DEFAULT_SATURATION_RATE: float = 10.0

# Observation window in seconds — incidents older than this are ignored.
# Matches watchtower duration_sec default. Tune via AIR_WINDOW_SEC env.
_DEFAULT_WINDOW_SEC: int = 300


class AirNodeTelemetryAdapter:
    """
    Telemetry adapter that derives V(t) from A.I.R. VaultNode incident rate.

    Returns the standard watchtower.analysis.v1 schema so it is a drop-in
    replacement for MockTelemetryAdapter or PrometheusTelemetryAdapter.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        window_sec: Optional[int] = None,
        saturation_rate: Optional[float] = None,
        timeout: float = 5.0,
    ):
        self.base_url = (
            base_url
            or os.getenv("AIR_NODE_URL", "http://localhost:8000")
        ).rstrip("/")
        self.window_sec = window_sec or int(
            os.getenv("AIR_WINDOW_SEC", str(_DEFAULT_WINDOW_SEC))
        )
        self.saturation_rate = saturation_rate or float(
            os.getenv("AIR_INCIDENT_SATURATION", str(_DEFAULT_SATURATION_RATE))
        )
        self.timeout = timeout

    # ------------------------------------------------------------------
    # Public interface (matches telemetry adapter contract)
    # ------------------------------------------------------------------

    def get_window(self, duration_sec: int = 30) -> dict:
        """
        Fetch incidents from A.I.R., filter to the observation window,
        compute incident rate, and return watchtower.analysis.v1 payload.

        duration_sec is accepted for interface compatibility but the
        adapter uses self.window_sec as the authoritative window.
        """
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        window_start = now_utc - datetime.timedelta(seconds=self.window_sec)
        timestamp_utc = now_utc.isoformat()

        try:
            resp = requests.get(
                f"{self.base_url}/incidents",
                timeout=self.timeout,
            )
            resp.raise_for_status()
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "message": f"A.I.R. VaultNode unreachable at {self.base_url}",
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "message": f"A.I.R. VaultNode timed out after {self.timeout}s",
            }
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "message": f"A.I.R. VaultNode HTTP error: {e}",
            }

        body = resp.json()
        all_incidents = body.get("incidents", [])

        # Filter to observation window
        recent = []
        for inc in all_incidents:
            created_raw = inc.get("created_at")
            if not created_raw:
                continue
            try:
                # Postgres returns ISO without timezone — treat as UTC
                created_at = datetime.datetime.fromisoformat(
                    created_raw.replace("Z", "+00:00")
                )
                if created_at.tzinfo is None:
                    created_at = created_at.replace(
                        tzinfo=datetime.timezone.utc
                    )
                if created_at >= window_start:
                    recent.append(inc)
            except ValueError:
                continue

        incident_count = len(recent)
        window_minutes = self.window_sec / 60.0
        incident_rate_per_min = incident_count / window_minutes if window_minutes > 0 else 0.0

        # Normalize: rate / saturation_rate, capped at 1.0
        norm_incident_rate = min(incident_rate_per_min / self.saturation_rate, 1.0)

        # Derive synthetic latency/queue signals from incident density
        # so the Mercy Protocol's latency check has a value to evaluate.
        # We do NOT fabricate infrastructure metrics — these are stubs
        # indicating "no infrastructure signal from this adapter."
        synthetic_latency_ms = 0.0
        synthetic_queue_depth = incident_count  # incidents are the queue

        return {
            "status": "ok",
            "schema_version": "watchtower.analysis.v1",
            "timestamp_utc": timestamp_utc,
            "variance_detected": round(norm_incident_rate, 4),
            "queue_depth": synthetic_queue_depth,
            "latency_ms": synthetic_latency_ms,
            "features": {
                "incident_count": incident_count,
                "incident_rate_per_min": round(incident_rate_per_min, 4),
                "norm_incident_rate": round(norm_incident_rate, 4),
                "window_sec": self.window_sec,
                "saturation_rate": self.saturation_rate,
                "source": "air_node",
            },
            "source": "air_node",
            "raw_artifacts": {
                "air_node_url": self.base_url,
                "total_incidents_fetched": len(all_incidents),
                "incidents_in_window": incident_count,
                "window_start_utc": window_start.isoformat(),
            },
        }
