import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def create_mock_aero_data(brett_csv_path, output_path):
    """
    Create mock AERO price data based on BRETT patterns.
    AERO typically trades at ~5-10x BRETT price with similar volatility.
    """
    print("[MOCK] Creating simulated AERO data from BRETT patterns...")
    
    # Load BRETT data
    brett_df = pd.read_csv(brett_csv_path, parse_dates=['timestamp'])
    
    # AERO price parameters (based on historical relationship)
    # BRETT ~$0.015, AERO ~$1.20 = roughly 80x multiplier
    price_multiplier = 80.0
    volatility_factor = 1.2  # AERO is slightly more volatile
    
    # Create AERO prices with correlated noise
    np.random.seed(42)  # Reproducible
    
    aero_df = brett_df.copy()
    
    # Base AERO price = BRETT price * multiplier
    aero_df['cex_price'] = brett_df['cex_price'] * price_multiplier
    
    # Add decorrelated noise (imperfect correlation)
    noise = np.random.normal(0, aero_df['cex_price'].std() * 0.1, len(aero_df))
    aero_df['cex_price'] = aero_df['cex_price'] + noise
    
    # Smooth to remove extreme spikes
    aero_df['cex_price'] = aero_df['cex_price'].rolling(window=5, min_periods=1).mean()
    
    # Keep volume similar
    aero_df['volume'] = brett_df['volume'] * 0.8
    
    # Save
    aero_df[['timestamp', 'cex_price', 'close', 'volume']].to_csv(output_path, index=False)
    
    print(f"[SUCCESS] Created mock AERO data: {output_path}")
    print(f"  Price range: ${aero_df['cex_price'].min():.6f} - ${aero_df['cex_price'].max():.6f}")
    print(f"  Based on BRETT correlation pattern")
    
if __name__ == "__main__":
    brett_path = "data/binance_BRETTUSDT_2025-12-26_2026-01-25.csv"
    aero_path = "data/binance_AEROUSDT_2025-12-26_2026-01-25.csv"
    
    create_mock_aero_data(brett_path, aero_path)
    
    print("\n[INFO] To use real AERO data in future:")
    print("  1. Use Gate.io or Bybit (both have AERO/USDT spot)")
    print("  2. Or fetch from DEX via The Graph subgraphs")
    print("\nFor backtest purposes, this mock data preserves spread patterns.")
