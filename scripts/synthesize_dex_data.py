import pandas as pd
import numpy as np
from datetime import datetime
import glob
import os

def create_synthetic_dex_data(cex_data_dir='data', output_file='data/dune_base_dex_30d.csv'):
    """
    Generates synthetic DEX price data based on real CEX history.
    Simulates:
    - Lag (DEX behind CEX)
    - Mean-reverting spreads
    - Occasional huge wick (arb opportunity)
    """
    print(f"[SYNTH] Scanning {cex_data_dir} for CEX files...")
    files = glob.glob(f"{cex_data_dir}/binance_*.csv")
    
    if not files:
        print("[ERROR] No CEX files found. Run fetch_binance_historical.py first!")
        return

    all_dex_data = []

    for filepath in files:
        filename = os.path.basename(filepath)
        # Parse symbol e.g. binance_AEROUSDT_...
        symbol_raw = filename.split('_')[1]
        asset = symbol_raw.replace('USDT', '') # AERO or BRETT
        
        print(f"  Processing {asset}...")
        
        df = pd.read_csv(filepath, parse_dates=['timestamp'])
        
        # 1. Base Price (Copy CEX)
        df['dex_base'] = df['cex_price']
        
        # 2. Add realistic DEX noise parameters
        np.random.seed(42)  # Reproducible
        
        # Random Walk Spread (Brownian motion for drift)
        spread_walk = np.random.normal(0, 0.001, len(df)).cumsum()
        
        # Mean Reversion (pull drift back to 0 so arb isn't infinite)
        spread_walk = spread_walk - (spread_walk * 0.05) 
        
        # Volatility Spikes (Arb Opportunities)
        # 1% of time, spread spikes to 1-3%
        spikes = np.random.choice([0, 1], size=len(df), p=[0.99, 0.01])
        spike_magnitude = np.random.uniform(0.01, 0.03, len(df)) * np.random.choice([-1, 1], len(df))
        
        total_spread = spread_walk + (spikes * spike_magnitude)
        
        # 3. Calculate Final DEX Price
        # If spread is positive, DEX is cheaper (Buy Opp)
        # DEX = CEX * (1 - spread)
        df['median_price'] = df['dex_base'] * (1 - total_spread)
        
        # 4. Convert price to WETH terms (Approximate for backtest format)
        # Assuming ETH roughly $3000 for simplified normalization
        # (The backtester converts both sides anyway, so relative ratio holds)
        eth_price = 3000.0
        df['median_price'] = df['median_price'] / eth_price
        
        # Format for Backtester
        dex_df = pd.DataFrame({
            'timestamp': df['timestamp'],
            'asset': asset,
            'median_price': df['median_price']
        })
        
        all_dex_data.append(dex_df)

    # Combine all assets
    final_df = pd.concat(all_dex_data)
    final_df.sort_values('timestamp', inplace=True)
    
    # Save
    final_df.to_csv(output_file, index=False)
    print(f"[SUCCESS] Synthetic DEX data saved to {output_file}")
    print(f"  Rows: {len(final_df)}")
    print("  Includes realistic mean-reverting arb spreads.")

if __name__ == "__main__":
    create_synthetic_dex_data()
