from web3 import Web3
import time

RPC_URL = "https://mainnet.base.org"
w3 = Web3(Web3.HTTPProvider(RPC_URL))

ROUTERS = {
    "SwapBased": "0xaaa3b1F1bd7BCc97fD1917c18ADE665C5D31F066",
    "AlienBase": "0x8c1A3cF8f83074169FE5D7aD50B978e1cD6b37c7" # Found via search or guess? Let's verify.
    # Actually I don't have AlienBase router. I'll search for it.
}

# Scan results said AlienBase Factory: 0xd233c94971bF7F310d9f01630138515286D22D69
# Let's check what factory SwapBased Router returns.

ROUTER_ABI = '[{"inputs":[],"name":"factory","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"}]'

def check_factories():
    router_addr = "0xaaa3b1F1bd7BCc97fD1917c18ADE665C5D31F066" # SwapBased
    print(f"Checking Factory for SwapBased Router: {router_addr}")
    try:
        router = w3.eth.contract(address=router_addr, abi=ROUTER_ABI)
        factory = router.functions.factory().call()
        print(f"SwapBased Router reports Factory: {factory}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_factories()
