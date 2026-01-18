# Blackglass Output Contracts

This document defines the schema guarantees for artifacts produced by the Reliability Agent.

## 1. Analysis Report (`analysis.json`)
Produced by `analyze_variance`. Represents the "Physics" truth.

```json
{
  "status": "STABLE | DRIFTING | CRITICAL",
  "variance_detected": 0.002,   // Float: 0.0 - 1.0
  "variance_threshold": 0.05,
  "queue_depth": 12,            // Integer
  "queue_threshold": 50,
  "latency_ms": 45,             // Integer
  "verdict": "PASS | FAIL",
  "recommendation": "DEPLOY | REJECT",
  "active_signals": []          // List[str]
}
```

## 2. Mitigation Plan (`mitigation.json`)
Produced by `recommend_mitigation`. Represents the "Logic" decision.

```json
{
  "type": "mitigation",
  "trigger": {
    "status": "INTERDICT",
    "time": "ISO-8601 Timestamp",
    "signals": [
      {"name": "field_name", "value": 123, "threshold": 100}
    ]
  },
  "hypotheses": [
    {
      "label": "short_snake_case_name",
      "confidence": 0.0 - 1.0,
      "evidence": ["string log reference"]
    }
  ],
  "recommended_actions": [
    {
      "rank": 1,
      "action": "Human readable action",
      "rationale": "Why this action was chosen",
      "verification": ["observable metric change"],
      "risk": "low | medium | high"
    }
  ],
  "confidence": 0.0 - 1.0
}
```

## 3. Watchtower Log (`watchtower.log`)
Produced by `watch_variance`. Durable audit trail.

**Standard Cycle:**
```text
[TIMESTAMP] Cycle=N Status=OK Drift=0.000 Queue=0
```

**Interdiction:**
```text
[TIMESTAMP] Cycle=N Status=INTERDICT_TYPE Drift=x.xxx Queue=x
    -> RECOMMENDED: Action Summary String
```

**Debounced (Repeat):**
```text
[TIMESTAMP] Cycle=N Status=INTERDICT_TYPE Drift=x.xxx Queue=x
    -> REPEAT DETECTED (Cooldown Active - Cycle M)
```
