import asyncio
import aiohttp
import time
from web3 import Web3

class OracleHunter:
    def __init__(self, config):
        self.config = config
        
        # THE HIT LIST (Map CEX Symbol -> Base Token Address + Threshold)
        # Thresholds are volatility-adjusted: Stable = 0.5%, Volatile = 2.0%
        self.targets = {
            "ETH": {
                "cex_symbol": "ETHUSD",  # Kraken uses ETHUSD
                "base_address": "0x4200000000000000000000000000000000000006",  # WETH
                "pair_address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bDA02913",  # USDC
                "threshold": 0.005  # 0.5% (Safe)
            },
            "AERO": {
                "cex_symbol": "AEROUSDT",
                "base_address": "0x940181a94a35A4569E4529A3CDfB74e38FD98631",  # AERO
                "pair_address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bDA02913",  # USDC
                "threshold": 0.01  # 1.0% (Volatile - needs wider gap)
            },
            "BRETT": {
                "cex_symbol": "BRETTUSDT",
                "base_address": "0x532f27101965dd16442e59d40670faf5ebb142e4",  # BRETT
                "pair_address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bDA02913",  # USDC
                "threshold": 0.02  # 2.0% (Chaos Mode - Memecoin)
            }
        }
        
        # Legacy compatibility: default to ETH
        self.threshold = self.targets["ETH"]["threshold"]
        self.last_cex_price = 0.0
        self.last_dex_price = 0.0

    def get_on_chain_price(self, w3, token_in=None, token_out=None):
        """
        Query Uniswap V3 Pool directly (Slot0) to get price.
        Robust against Quoter reverts.
        Supports multi-token queries.
        """
        # Uniswap V3 Factory (Base)
        FACTORY_ADDRESS = Web3.to_checksum_address("0x33128a8fC17869897dcE68Ed026d694621f6FDfD")
        
        # Factory ABI
        FACTORY_ABI = [{"inputs":[{"internalType":"address","name":"","type":"address"},{"internalType":"address","name":"","type":"address"},{"internalType":"uint24","name":"","type":"uint24"}],"name":"getPool","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"}]
        
        # Pool ABI (Minimal for slot0)
        POOL_ABI = [{"inputs":[],"name":"slot0","outputs":[{"internalType":"uint160","name":"sqrtPriceX96","type":"uint160"},{"internalType":"int24","name":"tick","type":"int24"},{"internalType":"uint16","name":"observationIndex","type":"uint16"},{"internalType":"uint16","name":"observationCardinality","type":"uint16"},{"internalType":"uint16","name":"observationCardinalityNext","type":"uint16"},{"internalType":"uint8","name":"feeProtocol","type":"uint8"},{"internalType":"bool","name":"unlocked","type":"bool"}],"stateMutability":"view","type":"function"}]

        try:
            # Default to WETH/USDC if not specified (backward compatibility)
            if not token_in:
                token_in = "0x4200000000000000000000000000000000000006"  # WETH
            if not token_out:
                token_out = "0x833589fCD6eDb6E08f4c7C32D4f71b54bDA02913"  # USDC
            
            TOKEN_IN = Web3.to_checksum_address(token_in)
            TOKEN_OUT = Web3.to_checksum_address(token_out)
            FEE = 500  # 0.05% - standard fee tier

            factory = w3.eth.contract(address=FACTORY_ADDRESS, abi=FACTORY_ABI)
            pool_address = factory.functions.getPool(TOKEN_IN, TOKEN_OUT, FEE).call()
            
            if pool_address == "0x0000000000000000000000000000000000000000":
                print(f"[QUOTER] :: ERROR :: Pool Not Found for {token_in[:6]}.../{token_out[:6]}...")
                return 0.0

            pool = w3.eth.contract(address=pool_address, abi=POOL_ABI)
            slot0 = pool.functions.slot0().call()
            sqrtPriceX96 = slot0[0]

            # Price Calculation: (sqrtPriceX96 / 2^96)^2
            price_raw = (sqrtPriceX96 / (2**96)) ** 2
            
            # Adjust for decimals (assumes token_out has 6 decimals, token_in has 18)
            # For WETH/USDC: price_raw * 10^12 gives USDC per WETH
            # For other pairs, this may need adjustment based on actual decimals
            final_price = price_raw * (10**12)
            
            return final_price

        except Exception as e:
            print(f"[QUOTER] :: ERROR fetching price: {e}")
            return 0.0

    async def get_cex_price(self, cex_symbol="ETHUSD"):
        """
        Fetch the 'Future' price from Kraken (US-Friendly).
        Supports multiple symbols via parameter.
        """
        # Kraken Public Ticker
        kraken_url = f"https://api.kraken.com/0/public/Ticker?pair={cex_symbol}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(kraken_url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        
                        # Kraken returns a dict where the key is the pair name (e.g., XETHZUSD).
                        # We grab the first key dynamically to avoid hardcoding weird pair names.
                        result = data.get('result', {})
                        if not result:
                            print(f"[HUNTER] :: KRAKEN API EMPTY RESULT for {cex_symbol}")
                            return 0.0
                        
                        pair_name = list(result.keys())[0]
                        # The 'c' array contains: [last trade closed, ...]
                        price_str = result[pair_name]['c'][0]
                        
                        return float(price_str)
                    else:
                        print(f"[HUNTER] :: KRAKEN API ERROR :: Status {resp.status} for {cex_symbol}")
                        return 0.0
        except Exception as e:
            print(f"[HUNTER] :: CONNECTION ERROR :: {e}")
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
        
        for symbol, data in self.targets.items():
            try:
                print(f"[OMNI-HUNTER] :: Scanning {symbol}...")
                
                # 1. Fetch CEX Price for this symbol
                cex_price = await self.get_cex_price(data['cex_symbol'])
                if cex_price == 0:
                    continue
                
                # 2. Fetch Chain Price
                chain_price = self.get_on_chain_price(
                    w3, 
                    token_in=data['base_address'], 
                    token_out=data['pair_address']
                )
                if chain_price == 0:
                    continue
                
                # 3. Calculate Deviation with token-specific threshold
                delta = (cex_price - chain_price) / chain_price
                threshold = data['threshold']
                
                # 4. Log the Pulse
                print(f"[HUNTER:{symbol}] :: CEX: ${cex_price:.2f} | CHAIN: ${chain_price:.2f} | DELTA: {delta*100:.3f}% | THRESHOLD: {threshold*100:.1f}%")
                
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
                        "pair_address": data['pair_address']
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
