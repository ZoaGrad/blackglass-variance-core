import requests
import pandas as pd
import time
from datetime import datetime

# Key Pools on Base
POOLS = {
    'AERO': '0x2223f97db93c3add8a62a7d6390315bd5c5783a0', # vAMM-AERO/WETH
    'BRETT': '0x403c47348986eb793444009f4fb949f57eb26ebc'  # vAMM-BRETT/WETH (Verify this)
}

def fetch_gecko_ohlcv(pool_address, asset_name):
    """
    Fetch OHLCV from GeckoTerminal (Max 1000 candles per call).
    """
    url = f"https://api.geckoterminal.com/api/v2/networks/base/pools/{pool_address}/ohlcv/minute"
    
    print(f"[GECKO] Fetching {asset_name} data from {pool_address}...")
    
    # GeckoTerminal pagination is... strictly time-limited.
    # We can only get the LAST 1000 minutes (16 hours) easily via the public free endpoint.
    # To get 30 days is hard without specific aggregated buckets.
    # BETTER: Get 'hour' data for 30 days, or 'minute' for today.
    # Let's try to get as much minute data as allowed.
    
    params = {'limit': 1000} 
    
    try:
        resp = requests.get(url, params=params)
        data = resp.json()
        
        ohlcv_list = data.get('data', {}).get('attributes', {}).get('ohlcv_list', [])
        
        if not ohlcv_list:
            print(f"  No data returned for {asset_name}")
            return None
            
        # Parse [time, open, high, low, close, volume]
        records = []
        for row in ohlcv_list:
            records.append({
                'timestamp': datetime.fromtimestamp(row[0]),
                'asset': asset_name,
                'dex_price_weth': row[4], # Close price
                'median_price': row[4]    # Proxy
            })
            
        df = pd.DataFrame(records)
        print(f"  Fetched {len(df)} rows for {asset_name}")
        return df
        
    except Exception as e:
        print(f"  Error: {e}")
        return None

if __name__ == "__main__":
    all_dfs = []
    
    # 1. Fetch AERO
    df_aero = fetch_gecko_ohlcv(POOLS['AERO'], 'AERO')
    if df_aero is not None:
        all_dfs.append(df_aero)
        
    # 2. Fetch BRETT
    # Note: Address needs to be correct. If unsure, we skip or use known good ones.
    # Trying specific BRETT/WETH pool: 0xcf77a3ba9a5ca699bc7c9ca57b67e5370a715508 (Uniswap v3) or similar
    # For now, let's just stick to AERO as the primary test.
    
    if all_dfs:
        final_df = pd.concat(all_dfs)
        final_df.sort_values('timestamp', inplace=True)
        
        output_path = "data/dune_base_dex_30d.csv"
        final_df.to_csv(output_path, index=False)
        print(f"\n[SUCCESS] Saved {len(final_df)} rows to {output_path}")
        print("Note: GeckoTerminal free API limits history to ~24h for minute resolution.")
        print("For 30-day backtest, we really need that Dune Dump or a paid API.")
    else:
        print("[FAIL] No data fetched.")
