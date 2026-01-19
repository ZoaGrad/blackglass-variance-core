from abc import ABC, abstractmethod
from typing import Dict, Any

class ActuationAdapter(ABC):
    @abstractmethod
    def apply(self, mitigation_plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Applies the mitigation plan.
        Returns a result dict describing the action taken.
        """
        pass
