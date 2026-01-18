# Demo Run — Proof of Life

This folder is a curated, deterministic example of the full Blackglass loop.

Chain:
1) `metrics.json` + `services/checkout.log` (artifacts)
2) `analysis.json` (engine output)
3) `mitigation_plan.json` (recommendation)

Scenario:
- Queue saturation begins at **13:58** (prediction window)
- Availability drops at **14:00** (failure event)
- Watchtower triggers **INTERDICT_QUEUE** before the drop

How to verify locally:
- Open `metrics.json` and find queue_depth > 50 at 13:58
- Open `analysis.json` for the prediction verdict
- Open `mitigation_plan.json` for the recommended interdiction response
