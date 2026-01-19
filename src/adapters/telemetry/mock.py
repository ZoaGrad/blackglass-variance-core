from .base import TelemetryAdapter
from src.tools.blackglass_analyze import analyze_variance
from typing import Dict, Any

class MockTelemetryAdapter(TelemetryAdapter):
    def __init__(self, run_dir: str):
        self.run_dir = run_dir
        
    def get_window(self, duration_sec: int) -> Dict[str, Any]:
        # Reuse existing analyze_variance logic which handles simulation/mocking
        # This returns the *Analysis* schema, which effectively contains the telemetry summary we need
        # In a real impl, this would return raw series, but for now we bridge the existing tool.
        return analyze_variance(run_dir=self.run_dir, duration_sec=duration_sec)
