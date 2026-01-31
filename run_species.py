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
import warnings
warnings.filterwarnings("ignore")
load_dotenv()
VAULT_PATH = "evidence/proposals"
LOG_PATH = "evidence/logs"
PRIVATE_KEY = os.getenv("PRIVATE_KEY", "")
ARMED = os.getenv("ARMED", "False").lower() == "true"

# [ADDRESSES]
WETH = "0x4200000000000000000000000000000000000006"
USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bDA02913"

GENESIS_CONFIG = {
    "swarm_id": "MONDAY_GENESIS_V1",
    "global_risk_limit": 0.05, 
    "clones": [
        {
            "id": "MC-03-ALPHA",
            "target_symbol": "ETH", 
            "base_address": "0x4200000000000000000000000000000000000006", # WETH
            "pair_address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bDA02913", # USDC
            "cex_symbol": "ETH/USD",
            "coingecko_id": "ethereum",
            "threshold": 0.005,
            "enabled": True
        },

        {
            "id": "MC-CLONE-C",
            "target_symbol": "DEGEN",
            "base_address": "0x4ed4E862860beD51a9570b96d8014711Ad151522", # DEGEN
            "pair_address": "0x4200000000000000000000000000000000000006", # WETH
            "cex_symbol": "DEGEN/USD",
            "coingecko_id": "degen-base",
            "threshold": 0.02,
            "enabled": True
        },
        {
            "id": "MC-CLONE-D",
            "target_symbol": "TOSHI",
            "base_address": "0xAC1Bd2486aAf3B5C0fc3Fd868558b082a531B2B4", # TOSHI
            "pair_address": "0x4200000000000000000000000000000000000006", # WETH
            "cex_symbol": "TOSHI/USD",
            "coingecko_id": "toshi",
            "threshold": 0.02,
            "enabled": True
        }
    ],
    "capital_per_clone": 12.00,
    "mutation_rate": 0.05
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
    # Force LIVE mode for Factory to ensure RPC connection (for Oracle Hunter)
    # Safety is guaranteed by ARMED=False flag later.
    os.environ["MODE"] = "LIVE" 
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
                    if 'error' in res:
                        print(f"   >>> ERROR DETAIL: {res['error']}")
                    
                    # [FORCE TEST] EXECUTION TRIGGER
                    # If the clone found an arb opportunity OR gas is cheap (Genesis Shot), we PULL THE TRIGGER.
                    if (res['action'] == 'HUNTING_ARBITRAGE' or res['action'] == 'HUNTING_GAS'):
                        print(f"[DEBUG] :: TRIGGER LOGIC ENTERED for {res['id']}")
                        signal_data = res.get('telemetry', {}).get('hunter_signal', {})
                        print(f"[DEBUG] :: SIGNAL DATA: {signal_data}")
                        
                        if signal_data:
                            direction = signal_data.get('signal') # SHORT or LONG
                            # SHORT -> Sell WETH for USDC
                            # LONG -> Buy WETH with USDC
                            
                            expected_price = signal_data.get('price', signal_data.get('chain_price', 0))
                            fee_tier = signal_data.get('fee', 3000)
                            
                            # [PHASE 24 SAFETY] Abort if expected_price is invalid
                            if expected_price is None or expected_price <= 0:
                                print(f"[SAFETY] :: ABORTING :: expected_price is {expected_price}. Cannot calculate min_out.")
                                continue

                            # Define Task for Territory Manager
                            async def fire_swap():
                                print(f"[DEBUG] :: FIRE_SWAP STARTED for {direction}")
                                if not ARMED:
                                    print(f"[SIMULATION] :: {direction} DETECTED :: Price {expected_price} :: WOULD EXECUTE")
                                    return True

                                # [SAFETY PROTOCOL] CHECK HOLDINGS BEFORE BUYING
                                # Prevents infinite loop if price stays low
                                if direction == 'LONG':
                                    try:
                                        # Check if we already own the target asset
                                        # For Genesis, we hardcode to check PEPE balance if targeting PEPE
                                        # Ideally, this should be dynamic based on pair
                                        token_address = GENESIS_CONFIG['clones'][1]['base_address'] if 'PEPE' in GENESIS_CONFIG['clones'][1]['target_symbol'] else None
                                        
                                        if token_address:
                                            balance = executor.get_token_balance(token_address)
                                            if balance > 1000: # Threshold to account for dust
                                                print(f"[INHIBIT] :: HOLDING DETECTED ({balance}) :: BUY ABORTED")
                                                return False
                                    except Exception as e:
                                        print(f"[SAFETY] :: BALANCE CHECK FAILED :: {e}")
                                        return False # Fail safe

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
                                    print(f"[GENESIS] :: ENGAGING TARGET :: BUYING PEPE...")
                                    # GENESIS SHOT: $10.00 USDC -> PEPE
                                    # Hardcoded safety limit for first test
                                    return await executor.execute_swap(
                                        token_in=USDC, 
                                        token_out=GENESIS_CONFIG['clones'][1]['base_address'], # PEPE
                                        amount_in_human=10.0, # $10.00 USDC exactly
                                        expected_price=expected_price,
                                        direction="BUY"
                                    )
                                return False

                            # RUN WITH TERRITORY LOCK (Inhibitor)
                            territory_id = res['id'] 
                            target_territory = res.get('telemetry', {}).get('base_address', 'GLOBAL')
                            await inhibitor.execute_with_territory(territory_id, target_territory, fire_swap)

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
            await asyncio.sleep(15.0) 

    except KeyboardInterrupt:
        print("\n[SENTINEL] :: MANUAL OVERRIDE. SHUTTING DOWN.")

if __name__ == "__main__":
    asyncio.run(main())
