import os
import json
from web3 import Web3
from dotenv import load_dotenv

"""
APPROVE ALL TARGETS
====================
One-time script to approve the Uniswap V3 Router to spend target tokens.
Must be run after funding the wallet and before activating the swarm.
"""

def approve_all():
    load_dotenv()
    
    # 1. Setup Web3
    rpc_url = os.getenv("BASE_RPC_URL")
    private_key = os.getenv("PRIVATE_KEY")
    if not rpc_url or not private_key:
        print("[ERROR] :: Missing BASE_RPC_URL or PRIVATE_KEY in .env")
        return

    w3 = Web3(Web3.HTTPProvider(rpc_url))
    account = w3.eth.account.from_key(private_key)
    print(f"[AUTH] :: Wallet Address: {account.address}")

    # 2. Uniswap V3 Router Address (Base)
    ROUTER_ADDRESS = w3.to_checksum_address("0x2626664c2603336E57B271c5C0b26F421741e481")
    
    # Minimal ERC20 ABI for Approval
    ERC20_ABI = [
        {"constant": False, "inputs": [{"name": "_spender", "type": "address"}, {"name": "_value", "type": "uint256"}], "name": "approve", "outputs": [{"name": "", "type": "bool"}], "type": "function"},
        {"constant": True, "inputs": [{"name": "_owner", "type": "address"}, {"name": "_spender", "type": "address"}], "name": "allowance", "outputs": [{"name": "", "type": "uint256"}], "type": "function"},
        {"constant": True, "inputs": [], "name": "symbol", "outputs": [{"name": "", "type": "string"}], "type": "function"}
    ]

    # 3. Load Targets from config.json
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
    except Exception as e:
        print(f"[ERROR] :: Failed to load config.json: {e}")
        return

    # Extract unique tokens from clones
    tokens_to_approve = set()
    for clone in config.get("clones", []):
        tokens_to_approve.add(clone["base_address"])
        tokens_to_approve.add(clone["pair_address"])

    print(f"[READY] :: Found {len(tokens_to_approve)} tokens to check.")

    # 4. Execute Approvals
    max_amount = 2**256 - 1
    
    for token_addr in tokens_to_approve:
        try:
            checksum_addr = w3.to_checksum_address(token_addr)
            contract = w3.eth.contract(address=checksum_addr, abi=ERC20_ABI)
            symbol = contract.functions.symbol().call()
            
            # Check current allowance
            allowance = contract.functions.allowance(account.address, ROUTER_ADDRESS).call()
            
            if allowance < (10**18): # If less than essentially anything, approve
                print(f"[ACTION] :: Approving {symbol} ({checksum_addr})...")
                
                nonce = w3.eth.get_transaction_count(account.address)
                tx = contract.functions.approve(ROUTER_ADDRESS, max_amount).build_transaction({
                    'from': account.address,
                    'nonce': nonce,
                    'gas': 100000,
                    'gasPrice': w3.eth.gas_price
                })
                
                signed_tx = w3.eth.account.sign_transaction(tx, private_key)
                # For safety, we print the hash but user must fund wallet for it to succeed
                # tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
                # print(f"[SUCCESS] :: Approved {symbol}. TX: {tx_hash.hex()}")
                print(f"[PRE-FLIGHT] :: Built Approval for {symbol}. (Broadcast disabled for safety)")
            else:
                print(f"[SKIP] :: {symbol} already approved.")
                
        except Exception as e:
            print(f"[ERROR] :: Failed to process token {token_addr}: {e}")

if __name__ == "__main__":
    approve_all()
