# shard_alpha.py
# ShardAlphaActuationAdapter — Blackglass Variance Core
#
# When the Watchtower detects INTERDICT_DRIFT or INTERDICT_QUEUE,
# this adapter calls POST /interdict on the Shard Alpha API,
# passing the V(t) score and decision reason as a structured payload.
# The Shard then emits its own FSM event (current_state → INTERDICTED)
# to the VaultNode, making the full chain auditable.

import os
import logging
import requests

logger = logging.getLogger("actuation.shard_alpha")

SHARD_URL = os.getenv("SHARD_ALPHA_URL", "http://localhost:8001")
SHARD_TIMEOUT = float(os.getenv("SHARD_TIMEOUT_SEC", "5.0"))


class ShardAlphaActuationAdapter:
    """
    Actuation adapter that fires POST /interdict on Shard Alpha.
    Compatible with the watch_variance actuation_mode="shard_alpha" hook.
    """

    def __init__(self, base_url: str = SHARD_URL, timeout: float = SHARD_TIMEOUT):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def apply(self, mitigation_plan: dict) -> dict:
        """
        Called by the Watchtower when a mitigation is needed.
        mitigation_plan is the output of recommend_mitigation().
        """
        # Extract V(t) and queue depth from the trigger signals block
        trigger    = mitigation_plan.get("trigger", {})
        signals    = trigger.get("signals", [])

        drift = next(
            (s["value"] for s in signals if s.get("name") == "variance_detected"), 0.0
        )
        queue = next(
            (s["value"] for s in signals if s.get("name") == "queue_depth"), 0
        )

        # Derive the action label: prefer drift reason, fall back to queue
        if drift > 0.05:
            action = "INTERDICT_DRIFT"
        elif queue > 50:
            action = "INTERDICT_QUEUE"
        else:
            action = "INTERDICT"

        payload = {
            "source":         "variance_core",
            "variance_score": float(drift),
            "reason":         action,
        }

        logger.info(
            "[ACTUATION] Firing /interdict on Shard Alpha — reason=%s V(t)=%.4f queue=%d",
            action, drift, queue,
        )

        try:
            r = requests.post(
                f"{self.base_url}/interdict",
                json=payload,
                timeout=self.timeout,
            )
            result = r.json() if r.content else {}
            logger.info("[ACTUATION] Shard response %d: %s", r.status_code, result)
            return {
                "status":      "ok" if r.status_code == 200 else "error",
                "http_status": r.status_code,
                "shard_response": result,
                "payload_sent": payload,
            }
        except requests.exceptions.ConnectionError:
            msg = f"Shard Alpha unreachable at {self.base_url}"
            logger.error("[ACTUATION] %s", msg)
            return {"status": "error", "message": msg}
        except requests.exceptions.Timeout:
            msg = f"Shard Alpha timed out after {self.timeout}s"
            logger.error("[ACTUATION] %s", msg)
            return {"status": "error", "message": msg}
        except Exception as e:
            logger.error("[ACTUATION] Unexpected error: %s", e)
            return {"status": "error", "message": str(e)}
