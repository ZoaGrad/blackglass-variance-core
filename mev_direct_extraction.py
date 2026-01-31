import os
import asyncio
import json
import time
import hmac
import hashlib
import uuid
from datetime import datetime
from web3 import Web3
from dotenv import load_dotenv

from modules.oracle_hunter import OracleHunter
from modules.executor import Executor
from modules.council_bridge import CouncilBridge
from modules.territory_manager import TerritoryManager

# [PHASE IV] COHERENCE GUARDS
class CoherenceGuard:
    def __init__(self, w3, max_block_age=60):
        self.w3 = w3
        self.max_block_age = max_block_age
        self.last_block_time = 0
        self.last_block_number = 0

    async def check_integrity(self):
        """
        Verifies the coherence of the substrate before extraction.
        Returns (is_coherent, reason)
        """
        try:
            latest_block = self.w3.eth.get_block('latest')
            block_time = latest_block['timestamp']
            current_time = int(time.time())
            
            # 1. Block Staleness Check (The Ache of Latency)
            age = current_time - block_time
            if age > self.max_block_age:
                return False, f"Substrate is Stale: Block age {age}s > {self.max_block_age}s"

            # 2. Reorg Buffer (The Coherence Debt)
            # In a live high-frequency environment, we would check for chain-tip stability.
            # Here we ensure the block number is advancing.
            if latest_block['number'] <= self.last_block_number and self.last_block_number != 0:
                return False, "Chain Stagnation: Block height has not advanced."
            
            self.last_block_number = latest_block['number']
            self.last_block_time = block_time
            
            return True, "Perfect Coherence"
        except Exception as e:
            return False, f"Substrate Connection Severed: {e}"

# [PHASE III] HOLOECONOMIC SINK (HARDENED)
class HoloeconomicSink:
    def __init__(self, vault_path="evidence/proposals"):
        self.vault_path = vault_path
        self.root_key = os.getenv("SENTINEL_ROOT_KEY", "COHERENCE_DEFAULT_SECRET").encode()
        self.last_hash = "GENESIS"
        os.makedirs(self.vault_path, exist_ok=True)
        self._initialize_lineage()

    def _initialize_lineage(self):
        """Finds the latest hash in the vault to maintain the chain of evidence."""
        files = sorted([f for f in os.listdir(self.vault_path) if f.endswith(".json")])
        if files:
            try:
                with open(os.path.join(self.vault_path, files[-1]), "r") as f:
                    data = json.load(f)
                    self.last_hash = data.get("signature", "GENESIS")
            except:
                pass

    def record_extraction(self, record):
        """
        Logs a signed extraction to the Evidence Vault as an immutable proposal.
        """
        extraction_id = f"ext-{int(time.time())}-{uuid.uuid4().hex[:4]}"
        filename = os.path.join(self.vault_path, f"{extraction_id}.json")
        
        payload_body = {
            "id": extraction_id,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "EXTRACTED",
            "type": "RECOGNITION_REWARD",
            "content": record,
            "parent_hash": self.last_hash
        }
        
        # Cryptographic Sealing (HMAC-SHA256)
        payload_str = json.dumps(payload_body, sort_keys=True)
        signature = hmac.new(self.root_key, payload_str.encode(), hashlib.sha256).hexdigest()
        
        payload_body["signature"] = signature
        payload_body["justification"] = f"Automated extraction by ZoaGrad Mirror Node. PnL: {record.get('pnl_est', 0)}"
        payload_body["coherence_score"] = record.get("coherence_score", 1.0)

        with open(filename, "w") as f:
            json.dump(payload_body, f, indent=2)
        
        self.last_hash = signature
        print(f"[HOLO-SINK] :: SEALED & RECORDED :: {extraction_id}")

# [ZOAGRAD MIRROR NODE] :: DIRECT EXTRACTION PROTOCOL
# This script operates independently of the Telegram/Moltbot gateway.
# It ensures 'Signal Purity' by relying solely on the local OracleHunter.

load_dotenv()

# [CONFIG]
BASE_RPC_URL = os.getenv("BASE_RPC_URL", "https://mainnet.base.org")
PRIVATE_KEY = os.getenv("PRIVATE_KEY", "")
# ΔΩ-LOCK: Simulation mode enforced. Manual override required for live fire.
# ARMED = os.getenv("ARMED", "false").lower() == "true"
ARMED = False  # Hardcoded False per Ω.157 safety protocol

# [TARGETS] :: High-Resonance Hit List
TARGET_CONFIG = {
    "clones": [
        {
            "id": "ZN-01-ETH",
            "target_symbol": "ETH",
            "base_address": "0x4200000000000000000000000000000000000006", # WETH
            "pair_address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bDA02913", # USDC
            "cex_symbol": "ETH/USD",
            "coingecko_id": "ethereum",
            "threshold": 0.005, # 0.5%
            "enabled": True
        },
        {
            "id": "ZN-02-DEGEN",
            "target_symbol": "DEGEN",
            "base_address": "0x4ed4E862860beD51a9570b96d8014711Ad151522",
            "pair_address": "0x4200000000000000000000000000000000000006", # WETH
            "cex_symbol": "DEGEN/USD",
            "coingecko_id": "degen-base",
            "threshold": 0.015, # 1.5%
            "enabled": True
        },
        {
            "id": "ZN-03-TOSHI",
            "target_symbol": "TOSHI",
            "base_address": "0xAC1Bd2486aAf3B5C0fc3Fd868558b082a531B2B4",
            "pair_address": "0x4200000000000000000000000000000000000006", # WETH
            "cex_symbol": "TOSHI/USD",
            "coingecko_id": "toshi",
            "threshold": 0.015, # 1.5%
            "enabled": True
        }
    ]
}

class MirrorNode:
    def __init__(self):
        print(f"\n[SENTINEL] :: INITIALIZING MEV MIRROR NODE (DIRECT EXTRACTION) ::")
        print(f"[STATUS]   :: FREQUENCY LOCK ENGAGED :: {datetime.utcnow().isoformat()} UTC")
        
        self.w3 = Web3(Web3.HTTPProvider(BASE_RPC_URL))
        if not self.w3.is_connected():
            print("[CRITICAL] :: FAILED TO CONNECT TO BASE RPC. ABORTING.")
            exit(1)
            
        print(f"[UPLINK]   :: BASE MAINNET CONNECTED :: Chain ID {self.w3.eth.chain_id}")
        
        self.executor = Executor(self.w3, PRIVATE_KEY)
        self.hunter = OracleHunter({"clones": TARGET_CONFIG['clones']})
        self.inhibitor = TerritoryManager()
        self.guard = CoherenceGuard(self.w3)
        self.sink = HoloeconomicSink()
        
        print(f"[NODE]     :: DIRECT EXTRACTION VECTOR ACTIVE.")
        if not ARMED:
            print(f"[SAFETY]   :: SIMULATION MODE ACTIVE (ARMED=False)")
        else:
            print(f"[DANGER]   :: LIVE EXECUTION MODE ARMING...")

    async def extraction_loop(self):
        try:
            while True:
                print(f"\n[PULSE]    :: {datetime.utcnow().isoformat()} :: Scanning the Void...")
                
                # 0. COHERENCE CHECK (Phase IV Hardening)
                is_coherent, reason = await self.guard.check_integrity()
                if not is_coherent:
                    print(f"[INHIBIT]  :: {reason}")
                    await asyncio.sleep(5.0)
                    continue

                # Scan all targets via OracleHunter
                signals = await self.hunter.scan_all(self.w3)
                
                if signals:
                    for sig in signals:
                        print(f"[SIGNAL]   :: {sig['symbol']} :: {sig['signal']} Detected! Deviation: {sig['confidence']:.2f}%")
                        await self.process_signal(sig)
                else:
                    print("[PULSE]    :: No Golden Threads found in the Current Frequency.")
                
                # Yield to the substrate
                await asyncio.sleep(10.0)
                
        except KeyboardInterrupt:
            print("\n[SENTINEL] :: MANUAL OVERRIDE. COHERENCE SEALING...")

    async def process_signal(self, sig):
        symbol = sig['symbol']
        direction = sig['signal']
        expected_price = sig['chain_price']
        base_asset = sig['base_address']
        pair_asset = sig['pair_address']
        
        # Hardcoded capital allocation for the Genesis Extraction
        # $12.00 USDC or equivalent WETH
        amount_in_human = 12.0

        async def execute_extraction():
            # [REFLEXIVE OPTIMIZATION] :: Adjust Threshold based on Substrate 'Ache'
            # If block age is high, we demand a higher confidence.
            latest_block = self.w3.eth.get_block('latest')
            ache = int(time.time()) - latest_block['timestamp']
            ache_penalty = (ache / 60.0) * 0.01 # 1% additional threshold per minute of age
            
            effective_threshold = sig.get('threshold', 0.01) + ache_penalty
            if sig['confidence'] / 100.0 < effective_threshold:
                print(f"[INHIBIT]  :: Confidence {sig['confidence']:.2f}% too low for Ache {ache}s (Required: {effective_threshold*100:.2f}%)")
                return False

            if not ARMED:
                print(f"[SIMULATION] :: {direction} {symbol} found at ${expected_price:.4f} :: Extraction Calculated.")
                # Even in simulation, we record to the sink to test the bridge logic
                self.sink.record_extraction({
                    "symbol": symbol,
                    "direction": direction,
                    "pnl_est": amount_in_human * (sig['confidence'] / 100.0),
                    "price": expected_price,
                    "ache": ache,
                    "coherence_score": 1.0 - (ache / 300.0) # Decay score as block ages
                })
                return True
            
            print(f"[GENESIS] :: EXTRACTING {direction} {symbol}...")
            
            # Logic mapping for execution
            if direction == 'LONG':
                token_in = pair_asset
                token_out = base_asset
            else:
                token_in = base_asset
                token_out = pair_asset

            success = await self.executor.execute_swap(
                token_in=token_in,
                token_out=token_out,
                amount_in_human=amount_in_human,
                expected_price=expected_price,
                direction=direction
            )

            if success:
                self.sink.record_extraction({
                    "symbol": symbol,
                    "direction": direction,
                    "pnl_est": amount_in_human * (sig['confidence'] / 100.0),
                    "price": expected_price,
                    "ache": ache,
                    "coherence_score": 1.0 - (ache / 300.0)
                })
            
            return success

        # Run with Territory Lock to avoid race conditions/double-spend in high frequency
        await self.inhibitor.execute_with_territory(f"EXTRACT-{symbol}", base_asset, execute_extraction)

async def main():
    node = MirrorNode()
    await node.extraction_loop()

if __name__ == "__main__":
    asyncio.run(main())
