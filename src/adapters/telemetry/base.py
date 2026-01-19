from abc import ABC, abstractmethod
from typing import Dict, Any

class TelemetryAdapter(ABC):
    @abstractmethod
    def get_window(self, duration_sec: int) -> Dict[str, Any]:
        """
        Retrieves telemetry window for analysis.
        Must return dict with keys:
          - latency_ms: float (current/avg)
          - queue_depth: int
          - ... other raw signal data
        """
        pass
