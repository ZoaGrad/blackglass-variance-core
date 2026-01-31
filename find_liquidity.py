import time
from web3 import Web3

# --- CONFIGURATION ---
RPC_URL = "https://mainnet.base.org" 
w3 = Web3(Web3.HTTPProvider(RPC_URL))

# TOKENS
WETH = w3.to_checksum_address("0x4200000000000000000000000000000000000006")
PEPE = w3.to_checksum_address("0x698dC45E4f10966F6D1D98E3bFd7071D8144C233") # Base Native PEPE

# DEX FACTORIES (The architects that know where the pools are)
# DEX FACTORIES (The architects that know where the pools are)
FACTORIES = {
    "Uniswap V2 (Official)": "0x8909Dc15e40173Ff4699343b6eB8132c65e18eC6", 
    "SwapBased V2 (CORRECTED)": "0x04C9f118d21e8B767D2e50C946f0cC9F6C367300",
    "AlienBase V2": "0xd233c94971bF7F310d9f01630138515286D22D69",
    "BaseSwap V2": "0xFDa619b6d20975be80A10332cD39b9a4b0FAa8BB" 
}

# ABI (Minimal)
FACTORY_ABI = '[{"constant":true,"inputs":[{"name":"tokenA","type":"address"},{"name":"tokenB","type":"address"}],"name":"getPair","outputs":[{"name":"pair","type":"address"}],"payable":false,"stateMutability":"view","type":"function"}]'
PAIR_ABI = '[{"constant":true,"inputs":[],"name":"getReserves","outputs":[{"name":"_reserve0","type":"uint112"},{"name":"_reserve1","type":"uint112"},{"name":"_blockTimestampLast","type":"uint32"}],"payable":false,"stateMutability":"view","type":"function"}, {"constant":true,"inputs":[],"name":"token0","outputs":[{"name":"","type":"address"}],"payable":false,"stateMutability":"view","type":"function"}]'

# Additional Token
USDC = w3.to_checksum_address("0x833589fCD6eDb6E08f4c7C32D4f71b54bDA02913")

def scan_for_liquidity():
    output = []
    output.append(f"[SENTINEL] :: HUNTING PEPE LIQUIDITY ON BASE...")
    output.append(f"Target Token: {PEPE}\n")

    pairs_to_check = [("WETH", WETH), ("USDC", USDC)]

    for name, raw_addr in FACTORIES.items():
        try:
            output.append(f"--- CHECKING {name} ---")
            try:
                factory_addr = w3.to_checksum_address(raw_addr.lower())
            except Exception as e:
                output.append(f"   > ERROR: Invalid Factory Address {raw_addr} - {e}")
                continue

            factory = w3.eth.contract(address=factory_addr, abi=FACTORY_ABI)
            
            for symbol, token_addr in pairs_to_check:
                time.sleep(1.0) # Avoid 429
                output.append(f"   > Pair: PEPE/{symbol}")
                # 1. Ask Factory
                pair_address = factory.functions.getPair(PEPE, token_addr).call()
                
                if pair_address == "0x0000000000000000000000000000000000000000":
                    output.append(f"     > RESULT: NO PAIR FOUND.")
                    continue
                    
                output.append(f"     > PAIR FOUND: {pair_address}")
                
                # 2. Ask Pair
                pair = w3.eth.contract(address=pair_address, abi=PAIR_ABI)
                try:
                    reserves = pair.functions.getReserves().call()
                    token0 = pair.functions.token0().call()
                    
                    if token0 == PEPE:
                        res_pepe = reserves[0] / 10**18 
                        res_quote = reserves[1] / (10**6 if symbol=="USDC" else 10**18)
                    else:
                        res_quote = reserves[0] / (10**6 if symbol=="USDC" else 10**18)
                        res_pepe = reserves[1] / 10**18
                    
                    output.append(f"     > LIQUIDITY: {res_quote:,.2f} {symbol} | {res_pepe:,.0f} PEPE")
                    
                    if res_quote > (100 if symbol=="USDC" else 0.1): # > $100 or > 0.1 ETH
                        output.append(f"     > STATUS: ✅ VALID TARGET (Liquidity Found)")
                    else:
                        output.append(f"     > STATUS: ❌ GHOST POOL (Dust)")
                except Exception as e:
                     output.append(f"     > ERROR reading pair: {e}")

        except Exception as e:
            output.append(f"   > ERROR: {e}")
        output.append("")

    with open("scan_results.log", "w", encoding="utf-8") as f:
        f.write("\n".join(output))
    print("Scan complete. Results written to scan_results.log")

if __name__ == "__main__":
    scan_for_liquidity()
