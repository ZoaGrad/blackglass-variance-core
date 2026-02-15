
import logging
import time
from enum import Enum, auto
from dataclasses import dataclass, field
from contextlib import contextmanager

# [AUDIT REMEDIATION E-1b] Import Constitution
try:
    from constitution import Constitution, ConstitutionalStandard
except ImportError:
    # Fallback for standalone testing
    class Constitution:
        class STANDARD:
            DRIFT_LIMIT_SEMANTIC = 0.05
        class MERCY:
            @staticmethod
            def declare_distress():
                print("MERCY PROTOCOL (FALLBACK): SYSTEM LOCKED")

logger = logging.getLogger("logic_gasket")

class VarianceState(Enum):
    GREEN = auto()  # Calm / Normal
    AMBER = auto()  # Throttled / Warning
    RED = auto()    # Panic / Circuit Open (LOCKED)

@dataclass
class GasketMetrics:
    request_count: int = 0
    failure_count: int = 0
    latency_sum: float = 0.0
    
    @property
    def error_rate(self) -> float:
        if self.request_count == 0: return 0.0
        return self.failure_count / self.request_count

class LogicGasket:
    def __init__(self, panic_threshold: float = None, reset_timeout: int = 60):
        # [AUDIT REMEDIATION E-1b] Use Constitutional Standard
        self.panic_threshold = panic_threshold or Constitution.STANDARD.DRIFT_LIMIT_SEMANTIC
        self.reset_timeout = reset_timeout
        
        self.state = VarianceState.GREEN
        self.metrics = GasketMetrics()
        self.last_panic_time = 0.0
        
    @property
    def constitutional_status(self) -> str:
        """
        [AUDIT REMEDIATION E-1a] Map internal state to Constitutional Vocabulary.
        """
        return {
            VarianceState.GREEN: "OK",
            VarianceState.AMBER: "THROTTLED",
            VarianceState.RED: "LOCKED"
        }[self.state]

    def record_outcome(self, success: bool, latency: float):
        self.metrics.request_count += 1
        self.metrics.latency_sum += latency
        if not success:
            self.metrics.failure_count += 1
            
        self._evaluate_state()

    def _evaluate_state(self):
        # Auto-Reset RED -> AMBER if timeout elapsed
        if self.state == VarianceState.RED:
            if time.time() - self.last_panic_time > self.reset_timeout:
                logger.warning("GASKET: Cooling down RED -> AMBER")
                self.state = VarianceState.AMBER
                self.metrics = GasketMetrics() # Reset metrics to give a chance
            return

        # Check Thresholds
        error_rate = self.metrics.error_rate
        
        # GREEN -> AMBER (Warning Shot)
        if self.state == VarianceState.GREEN and error_rate > (self.panic_threshold / 2):
             logger.warning(f"GASKET: Variance rising ({error_rate:.2f}). State -> AMBER")
             self.state = VarianceState.AMBER
             
        # AMBER -> RED (Panic)
        elif self.state == VarianceState.AMBER and error_rate > self.panic_threshold:
             self._escalate()
             
        # AMBER -> GREEN (Recovery)
        elif self.state == VarianceState.AMBER and error_rate < (self.panic_threshold / 4):
             logger.info("GASKET: Variance subsided. State -> GREEN")
             self.state = VarianceState.GREEN

    def _escalate(self):
        if self.state != VarianceState.RED:
            logger.error(f"GASKET: COHERENCE BREACH (Error Rate {self.metrics.error_rate:.2f} > {self.panic_threshold}). State -> RED")
            self.state = VarianceState.RED
            self.last_panic_time = time.time()
            
            # [AUDIT REMEDIATION E-1c] Mercy Protocol Integration
            logger.critical("INVOKING MERCY PROTOCOL...")
            Constitution.MERCY.declare_distress()

    @contextmanager
    def guard(self):
        """
        The Enforcement Surface.
        Yields execution token if GREEN/AMBER.
        Yields None if RED (Suppressed).
        """
        if self.state == VarianceState.RED:
            # Check if we can auto-reset before blocking
            self._evaluate_state()
            if self.state == VarianceState.RED:
                logger.error("GASKET: Execution suppressed (LOCKED)")
                yield None
                return

        start_time = time.time()
        try:
            yield self
            # Success is optimistically assumed unless exception triggers
            self.record_outcome(True, time.time() - start_time)
        except Exception as e:
            self.record_outcome(False, time.time() - start_time)
            raise e
