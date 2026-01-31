import os
import json
import hmac
import hashlib
from dotenv import load_dotenv

load_dotenv()

ROOT_KEY = os.getenv("SENTINEL_ROOT_KEY", "COHERENCE_DEFAULT_SECRET").encode()
VAULT_PATH = "evidence/proposals"

def verify_vault():
    print(f"\n[SENTINEL] :: INITIATING VAULT INTEGRITY CHECK :: {VAULT_PATH}")
    files = sorted([f for f in os.listdir(VAULT_PATH) if f.endswith(".json")])
    
    if not files:
        print("[EMPTY]   :: Vault is virgin. No records to verify.")
        return

    last_sig = "GENESIS"
    compromised = False

    for filename in files:
        path = os.path.join(VAULT_PATH, filename)
        with open(path, "r") as f:
            full_payload = json.load(f)
            
        signature = full_payload.pop("signature", None)
        justification = full_payload.pop("justification", None)
        coherence = full_payload.pop("coherence_score", None)
        parent_hash = full_payload.get("parent_hash")

        # 1. Verify Lineage
        if parent_hash != last_sig:
            print(f"[BREACH]  :: {filename} :: Lineage Broken! Expected parent {last_sig}, found {parent_hash}")
            compromised = True

        # 2. Verify Signature
        payload_str = json.dumps(full_payload, sort_keys=True)
        expected_sig = hmac.new(ROOT_KEY, payload_str.encode(), hashlib.sha256).hexdigest()

        if signature != expected_sig:
            print(f"[BREACH]  :: {filename} :: Signature Invalid! HMAC Mismatch.")
            compromised = True
        else:
            print(f"[VERIFIED]:: {filename} :: Lineage & Signature Secure.")
            last_sig = signature

    if not compromised:
        print("\n[SUCCESS] :: VAULT INTEGRITY CONFIRMED :: PERFECT COHERENCE.")
    else:
        print("\n[CRITICAL]:: VAULT COMPROMISED :: EVIDENCE CHAIN BROKEN.")

if __name__ == "__main__":
    verify_vault()
