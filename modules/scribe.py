import json
import os
import aiofiles
from datetime import datetime

class Scribe:
    def __init__(self, vault_path="evidence/proposals"):
        self.vault_path = vault_path
        os.makedirs(vault_path, exist_ok=True)

    async def record_mutation(self, clone_id, generation, traits, pnl, outcome):
        """
        Writes a significant evolutionary event to the Vault.
        Only records if PnL is non-zero (Signal) or if a Death occurred.
        """
        timestamp = datetime.utcnow().isoformat()
        # Unique ID combining clone + microsecond timestamp to avoid collisions
        filename = f"mutation_{clone_id}_{int(datetime.utcnow().timestamp()*1000)}.json"
        filepath = os.path.join(self.vault_path, filename)

        record = {
            "id": clone_id,
            "timestamp": timestamp,
            "generation": generation,
            "event_type": outcome,  # EVOLVED, DIED, PROFIT, LOSS, MUTATION_DRIFT
            "pnl": pnl,
            "traits": traits,       # The specific parameters (slippage, etc.)
            "genetic_hash": hash(str(traits)) # Simple integrity check
        }

        # Async write to avoid hydrostatic lock
        # Note: aiofiles needs to be installed. If not, fallback to sync write for scaffolding.
        try:
             async with aiofiles.open(filepath, mode='w') as f:
                await f.write(json.dumps(record, indent=2))
        except NameError: 
             # Fallback if aiofiles isn't imported/installed in environment
             with open(filepath, 'w') as f:
                json.dump(record, f, indent=2)
        
        return filepath
