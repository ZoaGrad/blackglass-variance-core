from .base import ActuationAdapter
from typing import Dict, Any

class NoopActuationAdapter(ActuationAdapter):
    def apply(self, mitigation_plan: Dict[str, Any]) -> Dict[str, Any]:
        # Purely logs the intent, takes no action
        actions = [a["action"] for a in mitigation_plan.get("recommended_actions", [])]
        return {
            "status": "noop",
            "actions_skipped": actions,
            "message": "Noop adapter active. No changes made."
        }
