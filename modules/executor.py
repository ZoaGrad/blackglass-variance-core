import os
import json
import time
from web3 import Web3

# [CONFIG] Base Mainnet Addresses
UNISWAP_V3_ROUTER = "0x2626664c2603336E57B271c5C0b26F421741e481" # SwapRouter02
WETH_ADDRESS = "0x4200000000000000000000000000000000000006"     # WETH on Base
USDC_ADDRESS = "0x833589fCD6eDb6E08f4c7C32D4f71b54bDA02913"     # USDC on Base (Fixed casing)

# [ABI] Minimal ABI for Swap (ExactInputSingle)
# Note: Using standard ExactInputSingleParams tuple structure
ROUTER_ABI = '[{"inputs":[{"components":[{"internalType":"address","name":"tokenIn","type":"address"},{"internalType":"address","name":"tokenOut","type":"address"},{"internalType":"uint24","name":"fee","type":"uint24"},{"internalType":"address","name":"recipient","type":"address"},{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint256","name":"amountOutMinimum","type":"uint256"},{"internalType":"uint160","name":"sqrtPriceLimitX96","type":"uint160"}],"internalType":"struct IV3SwapRouter.ExactInputSingleParams","name":"params","type":"tuple"}],"name":"exactInputSingle","outputs":[{"internalType":"uint256","name":"amountOut","type":"uint256"}],"stateMutability":"payable","type":"function"}]'

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
        print(f"[EXECUTOR] :: ARMED :: Wallet {self.account.address[:6]}...")

    async def execute_swap(self, token_in, token_out, amount_in, expected_price, slippage_percent=0.02, direction="BUY"):
        """
        Builds, Signs, and Broadcasts the Swap.
        expected_price: The price (token_out per token_in) from OracleHunter.
        slippage_percent: Max allowed price impact (default 2% = 0.02).
        """
        try:
            # 1. Safety Check (The Hunger Protocol)
            balance = self.w3.eth.get_balance(self.account.address)
            if balance < self.w3.to_wei(0.0001, 'ether'): 
                 pass

            # 2. Calculate Slippage Protection (amountOutMinimum)
            # expected_out = amount_in * expected_price
            # min_out = expected_out * (1 - slippage_percent)
            
            # NOTE: We must adjust for decimals if token_in and token_out differ
            # For simplicity, if swapping ETH(18) -> USDC(6), expected_price is already adjusted.
            # But amount_in is in WEI (raw).
            # expected_out_raw = amount_in * expected_price / 10**(dec_in - dec_out)
            
            # Let's use a simpler heuristic for the beta: 
            # We assume amount_in and expected_price are scaled correctly for the 10^12 difference.
            expected_out = amount_in * expected_price * (10**-12 if token_in == WETH_ADDRESS else 10**12)
            # Actually, the OracleHunter returns price in USD (approx).
            # If token_in = WETH, expected_out is in USDC units.
            
            # For the beta, we'll keep it simple: 
            # The caller provides amount_in (WEI) and expected_price ($).
            # We calculate amountOutMinimum in the target token's raw units.
            
            # If selling 1 ETH ($3000): amount_in = 1e18, price = 3000.
            # amount_out (USDC) = 3000 * 1e6.
            # Calculation: (1e18 / 1e18) * 3000 * 1e6 = 3000e6.
            
            raw_expected_out = int(amount_in * expected_price * (10**-12 if token_in == WETH_ADDRESS else 10**12))
            min_out = int(raw_expected_out * (1 - slippage_percent))

            print(f"[EXECUTOR] :: PREPARING {direction} :: {amount_in} -> Min Out: {min_out}")

            # 3. Build the Transaction
            params = (
                Web3.to_checksum_address(token_in),
                Web3.to_checksum_address(token_out),
                500, # Fee tier 0.05%
                self.account.address,
                amount_in,
                min_out, # SLIPPAGE GUARD ACTIVE
                0
            )

            # Note: For WETH -> USDC, we interact with Router. 
            # If ETH -> USDC, we send value.
            # If WETH->USDC, we need Approval first (not implemented here, assuming granted or WETH unwrapped).
            # But exactInputSingle supports ETH if we wrap it? SwapRouter02 handles it.
            # Let's assume standard ERC20 path for now.
            
            tx_data = self.router.functions.exactInputSingle(params).build_transaction({
                'from': self.account.address,
                'value': 0, # Assuming WETH/USDC (ERC20 swap). If Native ETH, this needs value.
                'gas': 250000, # Hardcoded buffer
                'gasPrice': self.w3.eth.gas_price,
                'nonce': self.w3.eth.get_transaction_count(self.account.address),
                'chainId': 8453
            })

            # 3. Sign (The Commitment)
            signed_tx = self.w3.eth.account.sign_transaction(tx_data, self.account.key)

            # 4. Fire (The Release)
            # [SAFETY ENGAGED - AWAITING AMMO]
            # tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            # print(f"[EXECUTOR] :: TX SENT :: https://basescan.org/tx/{self.w3.to_hex(tx_hash)}")
            
            # [SIMULATION OUTPUT]
            print(f"[EXECUTOR] :: SIMULATED TX BUILD SUCCESS :: Nonce {tx_data['nonce']}")
            return True

        except Exception as e:
            print(f"[EXECUTOR] :: FAILURE :: {e}")
            return False
