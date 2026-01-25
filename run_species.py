import os
import time
import asyncio
import json
from datetime import datetime
from dotenv import load_dotenv
from modules.scribe import Scribe
from modules.swarm_factory import SwarmFactory
from modules.auditor_core import Auditor
from modules.executor import Executor
from modules.territory_manager import TerritoryManager

# [INIT] Load Environment
load_dotenv()
VAULT_PATH = "evidence/proposals"
LOG_PATH = "evidence/logs"
PRIVATE_KEY = os.getenv("PRIVATE_KEY", "")

# [CONFIG] Genesis Parameters
GENESIS_CONFIG = {
    "swarm_id": "MONDAY_GENESIS_V1",
    "territories": {
        "MC-03-ALPHA": "DEGEN_USDC",
        "MC-CLONE-A": "PEPE_USDC",
        "MC-CLONE-B": "MOG_WETH",
        "MC-CLONE-C": "BASE_FEES",
        "MC-CLONE-D": "TOSHI_TYBG"
    },
    "capital_per_clone": 12.00,  # USD
    "mutation_rate": 0.05        # 5% drift allowed
}

async def main():
    print(f"\n[SENTINEL] :: BLACKGLASS VECTOR-BASTION SWARM ::")
    print(f"[TIME]     :: {datetime.utcnow().isoformat()} UTC")
    
    # 1. Auditor Check (The Hunger)
    auditor = Auditor(risk_tolerance="HIGH")
    if not auditor.check_vault_integrity(VAULT_PATH):
        print("[CRITICAL] VAULT COMPROMISED. ABORTING.")
        return

    # 1.5 Initialize Scribe (The Memory)
    scribe = Scribe(VAULT_PATH)

    # 2. Forge the Clones
    factory = SwarmFactory(GENESIS_CONFIG)
    clones = factory.ignite_clones()
    
    # 2.5 Arm the Executor (The Hand)
    # We use the factory's Web3 connection to ensure same RPC usage
    if hasattr(factory, 'w3'):
        executor = Executor(factory.w3, PRIVATE_KEY)
    elif len(clones) > 0:
        # Fallback if factory doesn't expose w3, grab from first clone
        executor = Executor(clones[0].w3, PRIVATE_KEY)
    
    # 2.6 Activate Inhibitor Chips (The Territorial Integrity)
    inhibitor = TerritoryManager()
    
    print(f"[SWARM]    :: {len(clones)} Phenotypes Active.")
    print(f"[STATUS]   :: CONNECTING TO BASE L2...")
    print(f"[INHIBIT]  :: TERRITORY LOCKS INITIALIZED.")

    # 3. The Infinite Loop (The Life)
    try:
        while True:
            # A. Heartbeat
            tasks = [clone.pulse() for clone in clones]
            results = await asyncio.gather(*tasks)
            
            # B. Log Adaptations (The Evidence)
            for res in results:
                if res['action'] != 'WAIT':
                    print(f"[{res['id']}] >> {res['action']} | PnL: {res['pnl']}")
                    
                    # [FORCE TEST] EXECUTION TRIGGER
                    # If the clone found an arb opportunity, we PULL THE TRIGGER.
                    if res['action'] == 'HUNTING_ARBITRAGE' and 'executor' in locals():
                        signal_data = res.get('telemetry', {}).get('hunter_signal', {})
                        if signal_data:
                            direction = signal_data.get('signal') # SHORT or LONG
                            # SHORT -> Sell WETH for USDC
                            # LONG -> Buy WETH with USDC
                            
                            expected_price = signal_data.get('price', 0)
                            
                            # Define Task for Territory Manager
                            async def fire_swap():
                                if direction == 'SHORT':
                                    print(f"[GENESIS] :: ENGAGING TARGET :: SELLING WETH...")
                                    return await executor.execute_swap(
                                        token_in=WETH, 
                                        token_out=USDC, 
                                        amount_in=amount, 
                                        expected_price=expected_price,
                                        direction="SELL"
                                    )
                                elif direction == 'LONG':
                                    print(f"[GENESIS] :: ENGAGING TARGET :: BUYING WETH...")
                                    # For BUY, we need USDC amount. Example: $0.30 (300,000 units)
                                    return await executor.execute_swap(
                                        token_in=USDC, 
                                        token_out=WETH, 
                                        amount_in=300000, 
                                        expected_price=1/expected_price if expected_price > 0 else 0,
                                        direction="BUY"
                                    )
                                return False

                            # RUN WITH TERRITORY LOCK (Inhibitor)
                            territory_id = res['id'] # Each clone owns its target territory
                            await inhibitor.execute_with_territory(territory_id, fire_swap())

                    # THE FIX: WRITE TO VAULT
                    # Only write significant events to save IO ops
                    if res['pnl'] != 0 or res['action'] in ['DIED', 'EVOLVED', 'MUTATION_DRIFT', 'HUNTING_ARBITRAGE']:
                        await scribe.record_mutation(
                            clone_id=res['id'],
                            generation=res.get('gen', 0), # Ensure Clones report generation
                            traits=res.get('traits', {}),
                            pnl=res['pnl'],
                            outcome=res['action']
                        )
            
            # C. Yield to Hardware (Hydrostatic Integrity)
            await asyncio.sleep(0.1) 

    except KeyboardInterrupt:
        print("\n[SENTINEL] :: MANUAL OVERRIDE. SHUTTING DOWN.")

if __name__ == "__main__":
    asyncio.run(main())
