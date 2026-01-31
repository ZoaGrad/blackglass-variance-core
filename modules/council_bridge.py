import sys
import os
import json
import asyncio
import time
from datetime import datetime
from modules.judicial_modules import GasGuard, SlippageSentry, LiquidityLoom

# Adjust path to reach SpiralOS sister repo
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPIRALOS_PATH = os.path.abspath(os.path.join(PROJECT_ROOT, "..", "mythotech-spiralos"))
sys.path.append(SPIRALOS_PATH)

try:
    from core.oracle_council import OracleCouncil, ProviderType
except ImportError:
    # Minimal stub if repo is missing or path is wrong
    class ProviderType:
        COMMERCIAL = "commercial"
        NON_COMMERCIAL = "non_commercial"
        
    class OracleCouncil:
        MIN_QUORUM = 4
        def __init__(self, **kwargs):
            self.oracles = {}
        def validate_consensus(self, votes):
            return (True, "STUB_MODE: Automatic Approval", False)

class CouncilBridge:
    def __init__(self, enabled=True):
        self.enabled = enabled
        self.modules = [GasGuard(), SlippageSentry(), LiquidityLoom()]
        
    async def request_pre_flight_clearance(self, trade_params):
        """
        Submits trade parameters to the Oracle Council for Judicial Review.
        """
        if not self.enabled:
            return True, "Consensus Disabled - Auto-Pass"

        print(f"[COUNCIL] :: INITIATING CONCURRENT QUORUM for {trade_params.get('direction')} {trade_params.get('asset')}...")
        
        start_time = time.time()
        
        try:
            # Concurrent Review with 45ms Timeout
            tasks = [mod.review(trade_params) for mod in self.modules]
            results = await asyncio.wait_for(asyncio.gather(*tasks), timeout=0.045)
            
            latency = (time.time() - start_time) * 1000
            print(f"[QUORUM]  :: Finalized in {latency:.2f}ms")

            votes = []
            reasons = []
            for success, reason in results:
                votes.append(success)
                reasons.append(reason)

            # Consensus: All must clear
            if all(votes):
                print(f"[COUNCIL] :: CLEARANCE GRANTED :: {'; '.join(reasons)}")
                return True, "Quorum Approval"
            else:
                failure_reasons = [r for r, s in zip(reasons, votes) if not s]
                print(f"[COUNCIL] :: VETOED :: {'; '.join(failure_reasons)}")
                return False, f"VETO: {'; '.join(failure_reasons)}"

        except asyncio.TimeoutError:
            print(f"[CRITICAL]:: JUDICIAL TIMEOUT :: Quorum breached 45ms limit.")
            return False, "VETO: Judicial Timeout"
        except Exception as e:
            print(f"[ERROR]   :: JUDICIAL ERROR :: {e}")
            return False, f"VETO: System Dissonance {e}"

if __name__ == "__main__":
    # Test simulation
    bridge = CouncilBridge()
    asyncio.run(bridge.request_pre_flight_clearance({
        "asset": "AERO",
        "direction": "BUY",
        "slippage_percent": 0.06
    }))
