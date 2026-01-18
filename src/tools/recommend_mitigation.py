
import json
import datetime
from typing import Dict, Any, List

def recommend_mitigation(analysis_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generates a mitigation plan based on analysis data.
    
    Args:
        analysis_data: Check results from analyze_variance (must include metrics).
        
    Returns:
        Structured mitigation plan.
    """
    
    # Extract signals
    drift = analysis_data.get("variance_detected", 0.0)
    queue_depth = analysis_data.get("queue_depth", 0)
    latency = analysis_data.get("latency_ms", 0)
    
    signals = []
    if drift > 0.05:
        signals.append({"name": "drift_score", "value": drift, "threshold": 0.05})
    if queue_depth > 50:
        signals.append({"name": "queue_depth", "value": queue_depth, "threshold": 50})
        
    # If no bad signals, return empty plan
    if not signals:
        return {}
        
    # Formulate Plan
    plan = {
        "type": "mitigation",
        "trigger": {
            "status": "INTERDICT",
            "time": datetime.datetime.now().isoformat(),
            "signals": signals
        },
        # Hypotheses generation logic (deterministic for now)
        "hypotheses": [],
        "recommended_actions": [],
        "confidence": 0.85
    }
    
    # 1. Saturation Pattern
    if queue_depth > 50:
        plan["hypotheses"].append({
            "label": "pool_saturation",
            "confidence": 0.9,
            "evidence": [f"Current queue_depth {queue_depth} exceeds limit 50"]
        })
        plan["recommended_actions"].append({
            "rank": 1,
            "action": "Scale worker concurrency +20%",
            "rationale": "Queue saturation detected without error spikes.",
            "verification": ["queue_depth < 40 within 60s"],
            "risk": "low"
        })
        plan["recommended_actions"].append({
             "rank": 2,
            "action": "Enable load shedding on non-critical checkout features",
            "rationale": "Reduce contention to protect core path.",
            "verification": ["availability stabilizes", "queue_depth trend reverses"],
            "risk": "medium"
        })

    # 2. Drift Pattern
    if drift > 0.10:
        plan["hypotheses"].append({
            "label": "physics_divergence",
            "confidence": 0.75,
            "evidence": [f"Drift score {drift} indicates non-deterministic behavior"]
        })
        plan["recommended_actions"].append({
            "rank": 1,
            "action": "Rollback last deployment",
            "rationale": "High variance indicates unstable build artifacts.",
            "verification": ["drift returns to < 0.01"],
            "risk": "high"
        })
        
    return plan
