from web3 import Web3

RPC_URL = "https://mainnet.base.org"
w3 = Web3(Web3.HTTPProvider(RPC_URL))

# Known Router from debug_v2.py
UNI_ROUTER = "0x4752ba5DBc23f44D87826276BF6Fd6b1C372aD24"
# AlienBase Router (need to find this or just Factory)
# SwapBased Router: 0xaaa3b1F1bd7BCc97fD1917c18ADE665C5D31F066

ROUTER_ABI = '[{"inputs":[],"name":"factory","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"}]'

def check_factory():
    print(f"Checking Factory for Router: {UNI_ROUTER}")
    try:
        router = w3.eth.contract(address=UNI_ROUTER, abi=ROUTER_ABI)
        factory = router.functions.factory().call()
        print(f"Factory: {factory}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_factory()
