# Technical Brief: Blackglass Watchtower

**System:** Reliability Control Loop (Variance-Based Interdiction)
**Version:** v0.2.0-watchtower-control-loop
**Status:** PROVEN (Evidence Integrity Contract Verified)

## 1. The Problem: Latency is Too Late
Traditional reliability engineering relies on **lagging indicators** (P99 latency, 5xx error rates). By the time these metrics breach thresholds, the cascade has often already begun.

> **Thesis:** Variance is the leading indicator of failure. "Shaky" systems fail before "slow" ones.

## 2. The Solution: Causal Drift Interdiction
Watchtower is a **closed-loop control system** that continuously monitors system variance (physics-based drift detection) and interdicts *before* hard failure boundaries are crossed.

### Core Loop
1.  **Simulate/Measure**: Ingests strict telemetry (Latency, Queue Depth).
2.  **Analyze**: Python-native logic calculates `variance_detected` (drift from stable baseline).
3.  **Decide**: If `drift > 0.15` (leading) OR `queue > 50` (lagging), trigger mitigation.
4.  **Interdict**: Emit structured `mitigation_plan.json` (Scaling, Throttling).

## 3. Evidence Integrity Contract
Watchtower is designed for **auditability**. Every cycle produces a verifiable evidence chain.

| Artifact | Source | Role | Contract |
| :--- | :--- | :--- | :--- |
| `analysis.json` | `src.tools.blackglass_analyze` | The Signal | Schema: `watchtower.analysis.v1` |
| `mitigation_plan.json` | `src.tools.recommend_mitigation` | The Action | Created iff `decision == MITIGATE` |
| `cycle_summary.json` | `src.tools.watch_variance` | The Truth | Always exists. Fail-closed. |

**Safety:** If analysis input is malformed, the system **fails closed** (No Interdiction) and logs an `ERROR` decision, preventing unverified automated actions.

## 4. Quick Verification (< 60s)
You can verify the system's logic and integrity contract on any machine (no heavy dependencies required):

```bash
# Run 2 deterministic cycles, writing evidence to a verifiable path
python -m src.agent watch --cycles 2 --output-dir runs/brief_verify

# Expected Output:
# [WATCH] Cycle 1/2...
#     -> [DETECTED] INTERDICT_DRIFT (Drift=0.8xxx, Queue=63)
# [WATCH] Cycle 2/2...
#     -> [DEBOUNCE] INTERDICT_DRIFT persists
```

## 5. Integration Posture
Watchtower is a **composable primitive**, not a monolith.

### Inputs (Telemetry)
- **Current:** Mock Generator / Simulation
- **Ready For:** Prometheus, Datadog, OpenTelemetry
- **Interface:** `TelemetryAdapter.get_window() -> { latency_series, queue_series }`

### Outputs (Actuation)
- **Current:** structured JSON (`mitigation_plan.json`)
- **Ready For:** Kubernetes HPA, KEDA, AWS AutoScaling
- **Interface:** `ActuationAdapter.apply(plan)`

---
*Blackglass Watchtower moves reliability from "Firefighting" to "Physics-Based Control".*
