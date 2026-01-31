import os
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

BASE_RPC_URL = os.getenv("BASE_RPC_URL", "https://mainnet.base.org")
w3 = Web3(Web3.HTTPProvider(BASE_RPC_URL))

# MOLT/WETH Pair identified in Recon
PAIR_ADDRESS = "0x15f351bf1637b43d70631ba95fb9bbb1ff21761c29b034c1b380aecb922464dd"
WETH_ADDRESS = "0x4200000000000000000000000000000000000006"

# Check if connected
if not w3.is_connected():
    print("RPC Connection Failed")
    exit()

# Minimal ABI for Pair
ABI = [
    {"constant":True,"inputs":[],"name":"token0","outputs":[{"name":"","type":"address"}],"payable":False,"stateMutability":"view","type":"function"},
    {"constant":True,"inputs":[],"name":"token1","outputs":[{"name":"","type":"address"}],"payable":False,"stateMutability":"view","type":"function"}
]

try:
    pair_contract = w3.eth.contract(address=Web3.to_checksum_address(PAIR_ADDRESS), abi=ABI)
    token0 = pair_contract.functions.token0().call()
    token1 = pair_contract.functions.token1().call()

    print(f"Token0: {token0}")
    print(f"Token1: {token1}")

    if token0.lower() == WETH_ADDRESS.lower():
        print(f"MOLT Address (Token1): {token1}")
    elif token1.lower() == WETH_ADDRESS.lower():
        print(f"MOLT Address (Token0): {token0}")
    else:
        print("WETH not found in pair! Validate pair manually.")

except Exception as e:
    print(f"Error resolving pair: {e}")
