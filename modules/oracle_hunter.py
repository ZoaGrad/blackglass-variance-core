import asyncio
import aiohttp
import requests
import time
from web3 import Web3

# --- AERODROME (BASE) ---
AERODROME_ROUTER_ADDRESS = "0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43"
AERODROME_FACTORY_ADDRESS = "0x420DD381b31aEf6683db6B902084cB0FFECe40Da"

AERODROME_ROUTER_ABI = [
    {
        "inputs": [
            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
            {
                "components": [
                    {"internalType": "address", "name": "from", "type": "address"},
                    {"internalType": "address", "name": "to", "type": "address"},
                    {"internalType": "bool", "name": "stable", "type": "bool"},
                    {"internalType": "address", "name": "factory", "type": "address"}
                ],
                "internalType": "struct IRouter.Route[]",
                "name": "routes",
                "type": "tuple[]"
            }
        ],
        "name": "getAmountsOut",
        "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# --- UNISWAP V2 (BASE) ---
UNISWAP_V2_ROUTER_ADDRESS = "0x4752ba5DBc23f44D87826276BF6Fd6b1C372aD24"

UNISWAP_V2_ROUTER_ABI = [
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


# --- PRESEEDED DECIMALS (CACHE) ---
PRESEEDED_DECIMALS = {
    "0x4200000000000000000000000000000000000006": 18, # WETH
    "0x833589fCD6eDb6E08f4c7C32D4f71b54bDA02913": 6,  # USDC (Base)
    "0x4ed4E862860beD51a9570b96D8014711ad151522": 18, # DEGEN
    "0xAC1Bd2486aAf3B5C0fc3Fd868558b082a531B2B4": 18, # TOSHI
    "0x940181a94a35A4569E4529A3CDfB74e38FD98631": 18, # AERO
    "0x532f27101965dd16442e59d40670faf5ebb142e4": 18, # BRETT
}
# [PHASE 11] OMNI-KEY GENERATION
for k in list(PRESEEDED_DECIMALS.keys()):
    PRESEEDED_DECIMALS[k.lower()] = PRESEEDED_DECIMALS[k]


class OracleHunter:
    def __init__(self, config):
        self.config = config
        
        # THE HIT LIST (Map CEX Symbol -> Base Token Address + Threshold)
        # Thresholds are volatility-adjusted: Stable = 0.5%, Volatile = 2.0%
        self.targets = {
            "ETH": {
                "cex_symbol": "ETHUSD",  # Kraken uses ETHUSD
                "coingecko_id": "ethereum",
                "base_address": "0x4200000000000000000000000000000000000006",  # WETH
                "pair_address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bDA02913",  # USDC
                "threshold": 0.005  # 0.5% (Safe)
            },
            "AERO": {
                "cex_symbol": "AEROUSDT",
                "coingecko_id": "aerodrome-finance",
                "base_address": "0x940181a94a35A4569E4529A3CDfB74e38FD98631",  # AERO
                "pair_address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bDA02913",  # USDC
                "threshold": 0.01  # 1.0% (Volatile - needs wider gap)
            },
            "BRETT": {
                "cex_symbol": "BRETTUSDT",
                "coingecko_id": "brett-based",
                "base_address": "0x532f27101965dd16442e59d40670faf5ebb142e4",  # BRETT
                "pair_address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bDA02913",  # USDC
                "threshold": 0.02  # 2.0% (Chaos Mode - Memecoin)
            },
            "DEGEN": {
                "cex_symbol": "DEGENUSDT",
                "coingecko_id": "degen-base",
                "base_address": "0x4ed4E862860beD51a9570b96d8014711Ad151522",
                "pair_address": "0x4200000000000000000000000000000000000006",
                "threshold": 0.02
            },
            "TOSHI": {
                "cex_symbol": "TOSHIUSDT",
                "coingecko_id": "toshi",
                "base_address": "0xAC1Bd2486aAf3B5C0fc3Fd868558b082a531B2B4",
                "pair_address": "0x4200000000000000000000000000000000000006",
                "threshold": 0.02
            }
        }
        
        # Legacy compatibility: default to ETH
        self.threshold = self.targets["ETH"]["threshold"]
        self.last_cex_price = 0.0
        self.last_dex_price = 0.0
        self.decimals_cache = {} # Cache for token decimals

    def get_token_decimals(self, w3, token_address):
        """
        Fetch ERC20 decimals with OMNI-KEY CACHING (Phase 22 Fix).
        Checks local cache first (Mixed + Lower), then RPC.
        """
        try:
            # 1. Normalize Address (Robust)
            try:
                checksum_address = Web3.to_checksum_address(token_address)
            except Exception:
                # Fallback: Try lowercasing
                try:
                    checksum_address = Web3.to_checksum_address(token_address.lower())
                except:
                    print(f"[HUNTER] :: FATAL :: Invalid address format: {token_address}")
                    return None
            
            # 2. Cache Check (Omni-Key)
            if checksum_address in PRESEEDED_DECIMALS:
                return PRESEEDED_DECIMALS[checksum_address]
            if checksum_address.lower() in PRESEEDED_DECIMALS:
                return PRESEEDED_DECIMALS[checksum_address.lower()]

            # 3. Check Internal Cache
            if checksum_address in self.decimals_cache:
                return self.decimals_cache[checksum_address]

            # 4. RPC Fetch
            contract = w3.eth.contract(address=checksum_address, abi=[{"constant":True,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"payable":False,"stateMutability":"view","type":"function"}])
            decimals = contract.functions.decimals().call()
            
            # 5. Store in Internal Cache
            self.decimals_cache[checksum_address] = decimals
            return decimals

        except Exception as e:
            # print(f"[HUNTER] :: Decimals fetch error: {e}")
            return None

    def get_aerodrome_price(self, w3, token_in, token_out, decimals_in, decimals_out, stable=False):
        """
        Queries Aerodrome Router using getAmountsOut (Solidly Logic).
        stable=False for Volatile (PEPE/ETH), stable=True for USDC/USDT.
        """
        try:
            # 1. Setup Router
            router = w3.eth.contract(address=AERODROME_ROUTER_ADDRESS, abi=AERODROME_ROUTER_ABI)
            
            # 2. Define Amount (1 Unit of Input Token)
            amount_in = int(1 * (10 ** decimals_in))
            
            # 3. Build Route Struct: (from, to, stable, factory)
            # Note: Web3.py expects a list of tuples for the struct array
            route_tuple = (
                Web3.to_checksum_address(token_in),
                Web3.to_checksum_address(token_out),
                stable,
                Web3.to_checksum_address(AERODROME_FACTORY_ADDRESS)
            )
            
            # 4. Call Contract
            # routes expects a list of structs, so we pass [route_tuple]
            amounts = router.functions.getAmountsOut(amount_in, [route_tuple]).call()
            
            # 5. Calculate Price
            amount_out_raw = amounts[-1] # Last item is the output amount
            price = amount_out_raw / (10 ** decimals_out)
            
            return price

        except Exception as e:
            # Log specific error if needed, or just fail silently to fallback
            print(f"[AERO ERROR] {e}") 
            return 0.0

    def get_v2_price(self, w3, token_in, token_out, decimals_in, decimals_out):
        """
        Queries Uniswap V2 Logic for Legacy Liquidity.
        """
        try:
            # 1. Setup Router
            router = w3.eth.contract(address=UNISWAP_V2_ROUTER_ADDRESS, abi=UNISWAP_V2_ROUTER_ABI)
            
            # 2. Define Amount
            amount_in = int(1 * (10 ** decimals_in))
            
            # 3. Build Path (Standard V2 Array)
            path = [
                Web3.to_checksum_address(token_in),
                Web3.to_checksum_address(token_out)
            ]
            
            # 4. Call Contract
            amounts = router.functions.getAmountsOut(amount_in, path).call()
            
            # 5. Calculate Price
            amount_out_raw = amounts[-1]
            price = amount_out_raw / (10 ** decimals_out)
            return price

        except Exception as e:
            # [PHASE 24 FIX] Suppress "execution reverted" which just means No Liquidity on V2
            if "execution reverted" in str(e):
                 # print(f"[V2] :: No Liquidity Found (Expected)") # Uncomment for debug
                 return 0.0
            
            print(f"[V2 ERROR] {e}")
            return 0.0


    def find_active_pool(self, w3, token_in, token_out, factory_address, factory_abi):
        """Scan all fee tiers [0.05%, 0.3%, 1.0%] to find live liquidity."""
        FEE_TIERS = [500, 3000, 10000] # 0.05%, 0.3%, 1.0%
        POOL_ABI_MIN = [{"inputs":[],"name":"slot0","outputs":[{"internalType":"uint160","name":"sqrtPriceX96","type":"uint160"},{"internalType":"int24","name":"tick","type":"int24"},{"internalType":"uint16","name":"observationIndex","type":"uint16"},{"internalType":"uint16","name":"observationCardinality","type":"uint16"},{"internalType":"uint16","name":"observationCardinalityNext","type":"uint16"},{"internalType":"uint8","name":"feeProtocol","type":"uint8"},{"internalType":"bool","name":"unlocked","type":"bool"}],"stateMutability":"view","type":"function"}]

        for fee in FEE_TIERS:
            try:
                factory = w3.eth.contract(address=factory_address, abi=factory_abi)
                pool_address = factory.functions.getPool(token_in, token_out, fee).call()
                
                if pool_address != "0x0000000000000000000000000000000000000000":
                    # Check if pool is initialized
                    pool = w3.eth.contract(address=pool_address, abi=POOL_ABI_MIN)
                    slot0 = pool.functions.slot0().call()
                    if slot0[0] != 0:
                        return pool_address, fee
            except:
                continue
                
        return None, None

    async def get_eth_price_usd(self):
        """Helper to get ETH price for normalization. LOOPS until success."""
        while True:
            # Use DexScreener for WETH Anchor (High Frequency)
            WETH_ADDRESS = "0x4200000000000000000000000000000000000006"
            price = await self.get_dexscreener_price(WETH_ADDRESS)
            
            if price > 0:
                return price
            print("[HUNTER] :: Waiting for ETH Anchor Price...")
            await asyncio.sleep(2)

    def get_on_chain_price(self, w3, eth_price_usd, token_in=None, token_out=None):
        """
        Query Uniswap V3 Pool directly (Slot0) to get price.
        Robust against Quoter reverts. Supports PEPE/DEGEN dynamic scaling.
        Fallbacks to Aerodrome CL if UniV3 pool not found.
        """
        # SwapBased V3 Factory (Base)
        FACTORY_ADDRESS_SWAPBASED = Web3.to_checksum_address("0x816fF4C7447186730c46D4c46d04412bE4246220")
        
        FACTORY_ABI = [{"inputs":[{"internalType":"address","name":"","type":"address"},{"internalType":"address","name":"","type":"address"},{"internalType":"uint24","name":"","type":"uint24"}],"name":"getPool","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"}]
        POOL_ABI = [
            {"inputs":[],"name":"slot0","outputs":[{"internalType":"uint160","name":"sqrtPriceX96","type":"uint160"},{"internalType":"int24","name":"tick","type":"int24"},{"internalType":"uint16","name":"observationIndex","type":"uint16"},{"internalType":"uint16","name":"observationCardinality","type":"uint16"},{"internalType":"uint16","name":"observationCardinalityNext","type":"uint16"},{"internalType":"uint8","name":"feeProtocol","type":"uint8"},{"internalType":"bool","name":"unlocked","type":"bool"}],"stateMutability":"view","type":"function"},
            {"inputs":[],"name":"token0","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"}
        ]

        try:
            # Default to WETH/USDC if not specified
            if not token_in: token_in = "0x4200000000000000000000000000000000000006" # WETH
            if not token_out: token_out = "0x833589fCD6eDb6E08f4c7C32D4f71b54bDA02913" # USDC
            
            TOKEN_IN = Web3.to_checksum_address(token_in)
            TOKEN_OUT = Web3.to_checksum_address(token_out)

            FACTORIES = [
                ("Uniswap V3", Web3.to_checksum_address("0x33128a8fC17869897dcE68Ed026d694621f6FDfD")),
                ("Aerodrome CL", Web3.to_checksum_address("0x420dd381b31aef6683db6b902084cb0ffece4fab")),
                ("SwapBased V3", Web3.to_checksum_address("0x816fF4C7447186730c46D4c46d04412bE4246220"))
            ]

            pool_address = None
            venue = None
            
            # [MOVED UP] Need decimals for all paths (V3, Aero, V2)
            dec_in = self.get_token_decimals(w3, TOKEN_IN)
            dec_out = self.get_token_decimals(w3, TOKEN_OUT)
            if dec_in is None or dec_out is None:
                return 0.0, 0, "Error"

            for name, factory_addr in FACTORIES:
                pool_address, fee_tier = self.find_active_pool(w3, TOKEN_IN, TOKEN_OUT, factory_addr, FACTORY_ABI)
                if pool_address:
                    venue = name
                    break
                # Try reversed order
                pool_address, fee_tier = self.find_active_pool(w3, TOKEN_OUT, TOKEN_IN, factory_addr, FACTORY_ABI)
                if pool_address:
                    venue = name
                    break

            final_price = 0.0
            fee_tier = 0

            if pool_address:
                # 3. Query Pool Data
                pool = w3.eth.contract(address=pool_address, abi=POOL_ABI)
                slot0 = pool.functions.slot0().call()
                token0 = pool.functions.token0().call()
                sqrtPriceX96 = slot0[0]

                # 4. Calculate Raw Price
                price_ratio = (sqrtPriceX96 / (2**96)) ** 2
                
                if TOKEN_IN == token0:
                    price_raw = price_ratio
                else:
                    price_raw = 1 / price_ratio if price_ratio != 0 else 0
                
                scaler = 10 ** (dec_in - dec_out)
                final_price = price_raw * scaler
            
                # Return immediately if valid price found from V3
                if final_price > 1e-9:
                    # NORMALIZE V3 PRICE AS WELL
                    # This was logically missing in previous specific-path patches
                    pass 
                
            # 3. If Uniswap is Blind (Ghost Pool), Attempt Aerodrome
            if final_price < 1e-9: # Dust threshold (PEPE is ~1e-6, so 1e-9 is safe)
                # Determine if pair is stable (USDT/USDC/DAI addresses)
                STABLES = [
                    "0x833589fCD6eDb6E08f4c7C32D4f71b54bDA02913", # USDC
                    "0xfde4c96c8593536e31f229ea8f37b2adb8523a2a", # USDT
                    "0x50c5725949a6f0c72e6c4a641f24049a917db0cb"  # DAI
                ]
                is_stable = (token_in.lower() in [s.lower() for s in STABLES]) and (token_out.lower() in [s.lower() for s in STABLES])
                
                aero_price = self.get_aerodrome_price(w3, TOKEN_IN, TOKEN_OUT, dec_in, dec_out, stable=is_stable)
                
                if aero_price > 1e-9:
                    final_price = aero_price
                    venue = "Aerodrome"
                else: 
                    # 4. Check Uniswap V2 - The Last Resort
                    try:
                        v2_price = self.get_v2_price(w3, TOKEN_IN, TOKEN_OUT, dec_in, dec_out)
                        if v2_price > 0:
                            final_price = v2_price
                            venue = "Uniswap V2"
                    except Exception as e:
                        pass

            # 5. UNIT NORMALIZATION (The Rosetta Stone Fix)
            WETH_ADDRESS = "0x4200000000000000000000000000000000000006"
            
            # DEBUG PRINT
            # print(f"[DEBUG] Check Norm: Out={TOKEN_OUT} vs WETH={WETH_ADDRESS} | ETH_Price={eth_price_usd}")

            if TOKEN_OUT.lower() == WETH_ADDRESS.lower():
                # print(f"[DEBUG] :: Normalizing... {final_price} -> {final_price * eth_price_usd}")
                final_price = final_price * eth_price_usd

            return final_price, fee_tier, venue if venue else "V3-Dust"
        
        except Exception as e:
            print(f"[QUOTER] :: ERROR fetching price: {e}")
            return 0.0, 0, "Error"

    async def get_dexscreener_price(self, token_address):
        """
        Fetch price from DexScreener (High Frequency, No Auth, 300 req/min).
        Returns the USD price of the most liquid pair.
        """
        try:
            url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                pairs = data.get('pairs', [])
                if not pairs:
                    return 0.0
                
                # DexScreener sorts by liquidity by default, but let's be safe.
                # Return the priceUsd of the first pair (highest liquidity).
                price_usd = float(pairs[0].get('priceUsd', 0.0))
                return price_usd
                
        except Exception as e:
            print(f"[HUNTER] :: DexScreener Error for {token_address}: {e}")
            
        return 0.0

    async def get_cex_price(self, cex_symbol="ETH/USD", coingecko_id=None, base_address=None):
        """
        Fetch reference price. Prioritize Coinbase (CEX) > DexScreener (DEX Aggregator).
        Renamed logic to reflect 'Reference Price' rather than strict CEX.
        """
        # 1. Try Coinbase (Public API, no key needed) - GOOD FOR ETH
        cb_symbol = cex_symbol.replace("/", "-").upper()
        if "USDT" in cb_symbol: cb_symbol = cb_symbol.replace("USDT", "USD") 
        
        # Only use Coinbase for Major assets (ETH)
        if "ETH" in cex_symbol or "BTC" in cex_symbol:
            try:
                url = f"https://api.coinbase.com/v2/prices/{cb_symbol}/spot"
                # Synchronous call inside async function (acceptable for this loop speed)
                response = requests.get(url, timeout=5, verify=False)
                if response.status_code == 200:
                    data = response.json()
                    price = float(data['data']['amount'])
                    return price
            except Exception as e:
                # print(f"[HUNTER] :: Coinbase API Error: {e}")
                pass

        # 2. DexScreener Strategy (Operation Hawkeye) - GOOD FOR ALTS (TOSHI, DEGEN)
        # Replaces CoinGecko (Rate Limits)
        if base_address:
            price = await self.get_dexscreener_price(base_address)
            if price > 0:
                return price

        return 0.0


    async def scan(self, current_chain_price):
        """
        Compare the Future (CEX) vs Present (Chain).
        Returns: 'SHORT', 'LONG', or 'WAIT'
        """
        try:
            # 1. Get the 'True' Price
            cex_price = await self.get_cex_price()
            if not cex_price:
                return None
            
            # 2. Calculate the Deviation (The Alpha)
            # If CEX is $3000 and Chain is $3020 -> Chain is WRONG. It will drop.
            delta = (cex_price - current_chain_price) / current_chain_price
            
            # 3. Log the "Pulse" (For your dopamine)
            print(f"[HUNTER] :: CEX: ${cex_price:.2f} | CHAIN: ${current_chain_price:.2f} | DELTA: {delta*100:.3f}%")

            # 4. The Trigger
            if delta < -self.threshold:
                return {
                    "signal": "SHORT",
                    "confidence": abs(delta) * 100,
                    "reason": "CEX_CRASH_DETECTED",
                    "cex_price": cex_price
                }
            elif delta > self.threshold:
                return {
                    "signal": "LONG",
                    "confidence": abs(delta) * 100,
                    "reason": "CEX_PUMP_DETECTED",
                    "cex_price": cex_price
                }
            
            return None

        except Exception as e:
            print(f"[HUNTER] :: SCAN ERROR :: {e}")
            return None

    async def scan_all(self, w3):
        """
        OMNI-HUNTER: Cycles through the Hit List and checks for opportunities.
        Returns a list of all detected arbitrage signals.
        """
        results = []
        
        # 1. Fetch ETH Price First (The Anchor)
        eth_price = await self.get_eth_price_usd()

        for symbol, data in self.targets.items():
            try:
                print(f"[OMNI-HUNTER] :: Scanning {symbol}...")
                
                # 2. Fetch CEX Price for this symbol
                cex_price = await self.get_cex_price(data['cex_symbol'], data.get('coingecko_id'), data.get('base_address'))
                if cex_price == 0:
                    continue
                
                # 3. Fetch Chain Price (Normalized)
                chain_price, fee_tier, source = self.get_on_chain_price(
                    w3, 
                    eth_price,
                    token_in=data['base_address'], 
                    token_out=data['pair_address']
                )
                if chain_price == 0:
                    continue
                
                # 4. Calculate Deviation with token-specific threshold
                delta = (cex_price - chain_price) / chain_price
                threshold = data['threshold']
                
                # 5. Log the Pulse
                print(f"[HUNTER:{symbol}] :: CEX: ${cex_price:.2f} | CHAIN: ${chain_price:.2f} ({source}) | DELTA: {delta*100:.3f}% | THRESHOLD: {threshold*100:.1f}%")
                
                # 5. Check Trigger
                if delta < -threshold:
                    results.append({
                        "symbol": symbol,
                        "signal": "SHORT",
                        "confidence": abs(delta) * 100,
                        "reason": "CEX_CRASH_DETECTED",
                        "cex_price": cex_price,
                        "chain_price": chain_price,
                        "base_address": data['base_address'],
                        "pair_address": data['pair_address'],
                        "fee": fee_tier
                    })
                elif delta > threshold:
                    results.append({
                        "symbol": symbol,
                        "signal": "LONG",
                        "confidence": abs(delta) * 100,
                        "reason": "CEX_PUMP_DETECTED",
                        "cex_price": cex_price,
                        "chain_price": chain_price,
                        "base_address": data['base_address'],
                        "pair_address": data['pair_address']
                    })
                    
            except Exception as e:
                print(f"[OMNI-HUNTER] :: ERROR scanning {symbol}: {e}")
                continue
        
        return results if results else None
