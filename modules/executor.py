import os
import json
import time
import asyncio
from web3 import Web3
from modules.council_bridge import CouncilBridge

# [CONFIG] Base Mainnet Addresses
UNISWAP_V3_ROUTER = "0x2626664c2603336E57B271c5C0b26F421741e481" # SwapRouter02
WETH_ADDRESS = "0x4200000000000000000000000000000000000006"     # WETH on Base
USDC_ADDRESS = "0x833589fCD6eDb6E08f4c7C32D4f71b54bDA02913"     # USDC on Base (Fixed casing)

# [ABI] Minimal ABI
ERC20_ABI = [
    {"constant":True,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"payable":False,"stateMutability":"view","type":"function"},
    {"constant":True,"inputs":[{"name":"_owner","type":"address"},{"name":"_spender","type":"address"}],"name":"allowance","outputs":[{"name":"","type":"uint256"}],"payable":False,"stateMutability":"view","type":"function"},
    {"constant":False,"inputs":[{"name":"_spender","type":"address"},{"name":"_value","type":"uint256"}],"name":"approve","outputs":[{"name":"","type":"bool"}],"payable":False,"stateMutability":"nonpayable","type":"function"},
    {"constant":True,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"payable":False,"stateMutability":"view","type":"function"}
]
ROUTER_ABI = '[{"inputs":[{"components":[{"internalType":"address","name":"tokenIn","type":"address"},{"internalType":"address","name":"tokenOut","type":"address"},{"internalType":"uint24","name":"fee","type":"uint24"},{"internalType":"address","name":"recipient","type":"address"},{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint256","name":"amountOutMinimum","type":"uint256"},{"internalType":"uint160","name":"sqrtPriceLimitX96","type":"uint160"}],"internalType":"struct IV3SwapRouter.ExactInputSingleParams","name":"params","type":"tuple"}],"name":"exactInputSingle","outputs":[{"internalType":"uint256","name":"amountOut","type":"uint256"}],"stateMutability":"payable","type":"function"}]'

# [PHASE 10] MEMCACHED VISION - Pre-seeded immutable decimals
PRESEEDED_DECIMALS = {
    "0x4200000000000000000000000000000000000006": 18, # WETH
    "0x833589fCD6eDb6E08f4c7C32D4f71b54bDA02913": 6,  # USDC (Base)
    "0x4ed4E862860beD51a9570b96D8014711ad151522": 18, # DEGEN
    "0xAC1Bd2486aAf3B5C0fc3Fd868558b082a531B2B4": 18, # TOSHI
    "0x940181a94a35A4569E4529A3CDfB74e38FD98631": 18, # AERO
    "0x532f27101965dd16442e59d40670faf5ebb142e4": 18, # BRETT
}
# [PHASE 11] OMNI-KEY GENERATION
# Ensure both Checksum (mixed) and Lowercase keys exist.
for k in list(PRESEEDED_DECIMALS.keys()):
    PRESEEDED_DECIMALS[k.lower()] = PRESEEDED_DECIMALS[k]

class Executor:
    def __init__(self, w3, private_key):
        self.w3 = w3
        if not private_key or "YOUR_KEY" in private_key:
             # Fallback for safety if key not set
             print("[EXECUTOR] :: WARNING :: NO VALID KEY FOUND. DUMMY MODE.")
             self.account = self.w3.eth.account.create() # Random dummy
        else:
             self.account = self.w3.eth.account.from_key(private_key)
             
        self.router = self.w3.eth.contract(address=Web3.to_checksum_address(UNISWAP_V3_ROUTER), abi=json.loads(ROUTER_ABI))
        self.bridge = CouncilBridge(enabled=True) # Could be pulled from config load
        print(f"[EXECUTOR] :: ARMED :: Wallet {self.account.address[:6]}...")

    def get_token_balance(self, token_address):
        """Fetch ERC20 balance for the armed account."""
        try:
            checksum_address = Web3.to_checksum_address(token_address)
            contract = self.w3.eth.contract(address=checksum_address, abi=ERC20_ABI)
            return contract.functions.balanceOf(self.account.address).call()
        except Exception as e:
            print(f"[EXECUTOR] :: BALANCE FETCH ERROR :: {e}")
            return 0

    def check_approval(self, token_address, spender_address, amount):
        """Ensure the spender is approved for the amount."""
        try:
            checksum_token = Web3.to_checksum_address(token_address)
            checksum_spender = Web3.to_checksum_address(spender_address)
            contract = self.w3.eth.contract(address=checksum_token, abi=ERC20_ABI)
            
            allowance = contract.functions.allowance(self.account.address, checksum_spender).call()
            
            if allowance < amount:
                print(f"[EXECUTOR] :: APPROVING {token_address[:6]} for Router...")
                tx = contract.functions.approve(checksum_spender, 2**256 - 1).build_transaction({
                    'from': self.account.address,
                    'gas': 100000,
                    'gasPrice': self.w3.eth.gas_price,
                    'nonce': self.w3.eth.get_transaction_count(self.account.address),
                    'chainId': 8453
                })
                signed_tx = self.w3.eth.account.sign_transaction(tx, self.account.key)
                tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
                print(f"[EXECUTOR] :: APPROVAL SENT :: {self.w3.to_hex(tx_hash)}")
                # Wait for approval to mine
                self.w3.eth.wait_for_transaction_receipt(tx_hash)
                return True
            return True
        except Exception as e:
            print(f"[EXECUTOR] :: APPROVAL FAILED :: {e}")
            return False

    def get_token_decimals(self, token_address):
        """Fetch ERC20 decimals."""
        try:
            try:
                # --- PHASE 10 FIX: CHECKSUM NORMALIZATION ---
                checksum_address = Web3.to_checksum_address(token_address)
            except Exception:
                # Fallback: Try lowercasing (Fix for bad checksums)
                try:
                    checksum_address = Web3.to_checksum_address(token_address.lower())
                except:
                    return None
            # ---------------------------------------------
            
            # 2. [PHASE 11] OMNI-KEY CACHE CHECK
            # Try Strict Checksum
            if checksum_address in PRESEEDED_DECIMALS:
                return PRESEEDED_DECIMALS[checksum_address]
            
            # Try Lowercase Fallback
            if checksum_address.lower() in PRESEEDED_DECIMALS:
                return PRESEEDED_DECIMALS[checksum_address.lower()]

            # 3. RPC Fetch
            ABI = [{"constant":True,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"payable":False,"stateMutability":"view","type":"function"}]
            contract = self.w3.eth.contract(address=checksum_address, abi=ABI)
            return contract.functions.decimals().call()
        except Exception:
            return None

    async def execute_swap(self, token_in, token_out, amount_in_human, expected_price, slippage_percent=0.01, direction="BUY", fee=3000):
        """
        Builds, Signs, and Broadcasts the Swap.
        [PHASE 9 UPDATE] Includes Aggressive Gas Bump Logic (The Reflex).
        """
        try:
            dec_in = self.get_token_decimals(token_in)
            dec_out = self.get_token_decimals(token_out)
            
            if dec_in is None or dec_out is None:
                print("[EXECUTOR] :: ERROR :: Decimals missing for swap. Aborting.")
                return False

            amount_in_raw = int(amount_in_human * (10**dec_in))
            
            # 1. Safety Check (The Hunger Protocol)
            eth_balance = self.w3.eth.get_balance(self.account.address)
            if eth_balance < self.w3.to_wei(0.0005, 'ether'): 
                 print("[EXECUTOR] :: FATAL :: INSUFFICIENT GAS FUNDS")
                 return False

            # 1.5 THE JUDICIAL FILTER
            success, reason = await self.bridge.request_pre_flight_clearance({
                "asset": direction,
                "token_in": token_in,
                "token_out": token_out,
                "amount": amount_in_human,
                "direction": direction
            })
            
            if not success:
                print(f"[EXECUTOR] :: VETOED BY COUNCIL :: {reason}")
                return False

            # 1.6 APPROVAL CHECK
            if token_in != WETH_ADDRESS: 
                # Note: check_approval is synchronous/blocking in current design
                self.check_approval(token_in, UNISWAP_V3_ROUTER, amount_in_raw)

            # 2. Calculate Slippage Protection (amountOutMinimum)
            raw_expected_out = int(amount_in_raw * expected_price * (10**(dec_out - dec_in)))
            min_out = int(raw_expected_out * (1 - slippage_percent))

            print(f"[EXECUTOR] :: PREPARING {direction} :: {amount_in_human} units -> Min Out: {min_out}")

            # 3. Execution Loop with Gas Bumping
            max_retries = 3
            current_gas_price = self.w3.eth.gas_price # Start with network price
            if current_gas_price < Web3.to_wei(0.3, 'gwei'):
                 current_gas_price = Web3.to_wei(0.3, 'gwei')

            for attempt in range(max_retries):
                try:
                    # Re-fetch nonce for each attempt to be safe (though usually same unless mined)
                    nonce = self.w3.eth.get_transaction_count(self.account.address)

                    print(f"[EXECUTOR] :: ATTEMPT {attempt+1}/{max_retries} :: Gas Price: {current_gas_price / 1e9:.2f} Gwei")

                    params = (
                        Web3.to_checksum_address(token_in),
                        Web3.to_checksum_address(token_out),
                        fee, 
                        self.account.address,
                        amount_in_raw,
                        min_out, 
                        0
                    )

                    tx_data = self.router.functions.exactInputSingle(params).build_transaction({
                        'from': self.account.address,
                        'value': 0,
                        'gas': 350000, # Safety buffer
                        'gasPrice': int(current_gas_price),
                        'nonce': nonce,
                        'chainId': 8453
                    })

                    # Sign
                    signed_tx = self.w3.eth.account.sign_transaction(tx_data, self.account.key)

                    # Fire
                    print("[EXECUTOR] :: BROADCASTING TRANSACTION...")
                    tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
                    print(f"[EXECUTOR] :: TX SENT :: https://basescan.org/tx/{self.w3.to_hex(tx_hash)}")
                    
                    return True

                except Exception as e:
                    # Check for replacement underpriced error (-32000) or other RPC errors
                    error_str = str(e)
                    if "-32000" in error_str or "replacement transaction underpriced" in error_str or "underpriced" in error_str.lower():
                        # Bump logic: New = Max(Network, Old * 1.125)
                        # We use 1.125 (12.5%) to be safely above the 10% node requirement
                        old_price = current_gas_price
                        network_price = self.w3.eth.gas_price
                        if network_price < Web3.to_wei(0.3, 'gwei'):
                             network_price = Web3.to_wei(0.3, 'gwei')

                        min_required = int(old_price * 1.125)
                        
                        current_gas_price = max(network_price, min_required)
                        
                        print(f"[EXECUTOR] :: GAS WAR DETECTED (-32000). REFLEX BUMP: {old_price/1e9:.2f} -> {current_gas_price/1e9:.2f} Gwei")
                        await asyncio.sleep(1) # Brief pause/breath
                        continue # Retry loop
                    else:
                        print(f"[EXECUTOR] :: TX ERROR :: {e}")
                        return False # Break on other errors (e.g., revert)

            print("[EXECUTOR] :: FAILURE :: Max retries exhausted.")
            return False

        except Exception as e:
            print(f"[EXECUTOR] :: FATAL FAILURE :: {e}")
            return False

        except Exception as e:
            print(f"[EXECUTOR] :: FAILURE :: {e}")
            return False
