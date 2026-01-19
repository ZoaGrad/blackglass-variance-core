import time
import functools
from dataclasses import dataclass
from typing import Callable, Any, Optional

@dataclass
class CircuitState:
    failure_count: int = 0
    entropy_score: float = 0.0
    last_failure_time: float = 0.0
    status: str = "CLOSED"  # CLOSED (Flowing), OPEN (Blocked), HALF-OPEN (Testing)

class ThermodynamicBreaker:
    def __init__(self, recovery_timeout: int = 30, variance_threshold: float = 2.0):
        self.state = CircuitState()
        self.recovery_timeout = recovery_timeout
        self.variance_threshold = variance_threshold  # Max allowed latency variance
        self.baseline_latency = 0.1 # Moving average

    def _update_thermodynamics(self, duration: float):
        """Calculates the 'Heat' (Entropy) of the call."""
        # Simple moving average for baseline
        self.baseline_latency = (self.baseline_latency * 0.9) + (duration * 0.1)
        
        # Variance: How far off were we?
        variance = duration / self.baseline_latency
        
        if variance > self.variance_threshold:
            self.state.entropy_score += variance
            print(f"[WATCHTOWER] Variance Spike Detected: {variance:.2f}x baseline.")
        else:
            # Cool down naturally
            self.state.entropy_score = max(0, self.state.entropy_score - 0.5)

    def __call__(self, func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # 1. INTERDICTION CHECK
            if self.state.status == "OPEN":
                if time.time() - self.state.last_failure_time > self.recovery_timeout:
                    print(f"[WATCHTOWER] Circuit HALF-OPEN. Probing system...")
                    self.state.status = "HALF-OPEN"
                else:
                    # PREDICTIVE INTERDICTION
                    print(f"[WATCHTOWER] INTERDICTED: Call blocked to prevent Hydrostatic Lock.")
                    return None

            # 2. EXECUTION
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                # 3. THERMODYNAMIC ANALYSIS
                self._update_thermodynamics(duration)
                
                # If Entropy gets too high, trip the breaker BEFORE the next crash
                if self.state.entropy_score > 10.0:
                    print(f"[WATCHTOWER] CRITICAL ENTROPY ({self.state.entropy_score:.1f}). TRIPPING CIRCUIT.")
                    self.state.status = "OPEN"
                    self.state.last_failure_time = time.time()
                
                if self.state.status == "HALF-OPEN":
                    print(f"[WATCHTOWER] Probe successful. Closing circuit.")
                    self.state.status = "CLOSED"
                    self.state.entropy_score = 0
                
                return result

            except Exception as e:
                self.state.failure_count += 1
                self.state.last_failure_time = time.time()
                self.state.status = "OPEN"
                print(f"[WATCHTOWER] HARD FAILURE. Circuit OPENED. Error: {e}")
                raise e

        return wrapper
