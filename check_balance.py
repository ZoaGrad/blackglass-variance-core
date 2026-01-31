import os
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

# CONFIG
RPC_URL = "https://mainnet.base.org"
w3 = Web3(Web3.HTTPProvider(RPC_URL))
WALLET_ADDRESS = "0xf8dE79CaFA7D94eD74d5c4Df74B64de137351A24" # Extracted from logs/user context (or env if available)
# Actually, let's verify if we have the public key in ENV or if I need to derive it/ask. 
# The user mentioned "Send ... to 0xf8dE...". I will assume this is the address.
# Wait, let's check .env content view or derive from private key if needed, but safest is to trust the user's snippet "0xf8dE...".
# Actually, run_species.py uses Executor which derives from PK. 
# I will use the address from the previous context or just derive it again to be safe.

USDC_ADDRESS = Web3.to_checksum_address("0x833589fCD6eDb6E08f4c7C32D4f71b54bDA02913")
USDC_ABI = '[{"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"}, {"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"payable":false,"stateMutability":"view","type":"function"}]'

def check_funds():
    if not os.getenv("PRIVATE_KEY"):
        print("ERROR: PRIVATE_KEY not found in .env")
        return

    # Derive address from PK for absolute certainty
    account = w3.eth.account.from_key(os.getenv("PRIVATE_KEY"))
    address = account.address
    print(f"Checking Balance for: {address}")

    # 1. ETH Balance
    eth_wei = w3.eth.get_balance(address)
    eth_bal = w3.from_wei(eth_wei, 'ether')

    # 2. USDC Balance
    usdc_contract = w3.eth.contract(address=USDC_ADDRESS, abi=USDC_ABI)
    usdc_wei = usdc_contract.functions.balanceOf(address).call()
    usdc_dec = usdc_contract.functions.decimals().call()
    usdc_bal = usdc_wei / (10 ** usdc_dec)

    print(f"--- WALLET REPORT ---")
    print(f"ETH:  {eth_bal:.6f} (Target: > 0.01)")
    print(f"USDC: {usdc_bal:.2f} (Target: > 50.00)")
    
    if eth_bal < 0.01:
        print("[ALERT] LOW FUEL (Gas). Please Fill.")
    else:
        print("[OK] Fuel Levels Nominal.")

    if usdc_bal < 50.0:
        print("[ALERT] LOW AMMO (Capital). Please Fill.")
    else:
        print("[OK] Ammo Loaded.")

if __name__ == "__main__":
    check_funds()
