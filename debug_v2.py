import sys
import os
import time
from web3 import Web3

# Add current dir to path to import modules
sys.path.append(os.getcwd())

from modules.oracle_hunter import OracleHunter

# Config Mock
class MockConfig:
    pass

def test_v2():
    print(":: INITIALIZING DEBUG V2 ::")
    
    # 1. Connect to Base
    rpc_url = "https://mainnet.base.org"
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        print(":: ERROR :: Could not connect to RPC")
        return

    print(":: CONNECTED TO BASE ::")

    # 2. Setup Hunter
    hunter = OracleHunter(MockConfig())
    
    # 3. Define Targets
    PEPE = "0x698dC45E4f10966F6D1D98E3bFd7071D8144C233"
    WETH = "0x4200000000000000000000000000000000000006"
    USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bDA02913"
    
    dec_pepe = 18
    dec_weth = 18
    dec_usdc = 6
    
    # Inspect Source - REMOVED
    print("\n:: SOURCE CHECK SKIPPED ::")

    # 4. Direct Contract Test
    print(f"\n:: DIRECT ROUTER CALL CHECK ::")
    router_addr = "0x4752ba5DBc23f44D87826276BF6Fd6b1C372aD24"
    router_abi = [
    {
        "inputs": [
            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
            {"internalType": "address[]", "name": "path", "type": "address[]"}
        ],
        "name": "getAmountsOut",
        "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}],
        "stateMutability": "view",
        "type": "function"
    }
    ]
    
    router = w3.eth.contract(address=router_addr, abi=router_abi)
    # PEPE -> WETH
    print(f"\n:: CHECKING PEPE -> WETH ::")
    try:
        path = [Web3.to_checksum_address(PEPE), Web3.to_checksum_address(WETH)]
        amount_in = 1 * 10**18 
        amounts = router.functions.getAmountsOut(amount_in, path).call()
        print(f"PEPE -> WETH Check: {amounts}")
    except Exception as e:
        print(f"PEPE -> WETH Failed: {e}")

    # PEPE -> USDC
    print(f"\n:: CHECKING PEPE -> USDC ::")
    try:
        path = [Web3.to_checksum_address(PEPE), Web3.to_checksum_address(USDC)]
        amount_in = 1 * 10**18 
        amounts = router.functions.getAmountsOut(amount_in, path).call()
        print(f"PEPE -> USDC Check: {amounts}")
    except Exception as e:
        print(f"PEPE -> USDC Failed: {e}")

    # WETH -> USDC (Control)
    print(f"\n:: CHECKING WETH -> USDC ::")
    path = [Web3.to_checksum_address(WETH), Web3.to_checksum_address(USDC)]
    amount_in = 1 * 10**18 # 1 ETH
    
    try:
        amounts = router.functions.getAmountsOut(amount_in, path).call()
        print(f"Direct Call Result (ETH->USDC): {amounts}")
    except Exception as e:
        print(f"Direct Call ERROR: {e}")

if __name__ == "__main__":
    test_v2()
