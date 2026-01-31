import ccxt
import pandas as pd
from datetime import datetime, timedelta
import time
import os

def fetch_ohlcv(exchange, symbol, timeframe='1m', since=None, limit=1000):
    """
    Fetch OHLCV data with pagination to get large date ranges.
    Binance has a 1000-candle limit per request.
    """
    data = []
    fetched_count = 0
    
    while True:
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=limit)
            if not ohlcv:
                break
                
            data += ohlcv
            fetched_count += len(ohlcv)
            print(f"  Fetched {fetched_count} candles so far...")
            
            # Move to next batch
            since = ohlcv[-1][0] + 60000  # +1 minute in ms
            time.sleep(exchange.rateLimit / 1000)  # Respect rate limits
            
            # If we got less than limit, we've hit the end
            if len(ohlcv) < limit:
                break
                
        except ccxt.NetworkError as e:
            print(f"  Network error: {e}. Retrying in 5s...")
            time.sleep(5)
            continue
        except ccxt.ExchangeError as e:
            print(f"  Exchange error: {e}")
            break
            
    return data

def save_to_csv(symbols, start_date, end_date, output_dir='data', exchange_type='future', use_binance_us=False):
    """
    Fetch historical OHLCV for given symbols from Binance.
    
    Args:
        symbols: List of symbol strings (futures format: 'AEROUSDT', spot: 'AERO/USDT')
        start_date: datetime object
        end_date: datetime object
        output_dir: Directory to save CSVs
        exchange_type: 'spot' or 'future' (default 'future' for AERO/BRETT)
        use_binance_us: If True, use binanceus instead of binance
    """
    exchange_class = ccxt.binanceus if use_binance_us else ccxt.binance
    
    try:
        exchange = exchange_class({
            'enableRateLimit': True,
            'options': {'defaultType': exchange_type if not use_binance_us else 'spot'},
        })
    except Exception as e:
        print(f"[ERROR] Could not initialize exchange: {e}")
        return
    
    os.makedirs(output_dir, exist_ok=True)
    
    start_ts = int(start_date.timestamp() * 1000)
    end_ts = int(end_date.timestamp() * 1000)
    
    for symbol in symbols:
        print(f"\n[FETCH] Pulling {symbol} from {start_date.date()} to {end_date.date()}")
        print(f"[INFO] Exchange type: {exchange_type}")
        
        try:
            # Verify symbol exists
            exchange.load_markets()
            if symbol not in exchange.markets:
                print(f"[ERROR] {symbol} not found on Binance {exchange_type}. Available similar:")
                # Try to find similar symbols
                similar = [s for s in exchange.symbols if symbol.split('/')[0] in s]
                for s in similar[:5]:
                    print(f"  - {s}")
                continue
            
            ohlcv = fetch_ohlcv(exchange, symbol, timeframe='1m', since=start_ts)
            
            if not ohlcv:
                print(f"[WARN] No data returned for {symbol}")
                continue
            
            # Convert to DataFrame
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # Filter to exact date range
            df = df[(df['timestamp'] >= start_date) & (df['timestamp'] <= end_date)]
            
            if df.empty:
                print(f"[WARN] No data in date range for {symbol}")
                continue
            
            # Calculate mid-price (more accurate than just close)
            df['cex_price'] = (df['high'] + df['low']) / 2
            
            # Save with metadata
            safe_symbol = symbol.replace('/', '')
            filename = os.path.join(
                output_dir, 
                f"binance_{safe_symbol}_{start_date.date()}_{end_date.date()}.csv"
            )
            
            df[['timestamp', 'cex_price', 'close', 'volume']].to_csv(filename, index=False)
            print(f"[SUCCESS] Saved {len(df)} candles to {filename}")
            print(f"  Price range: ${df['cex_price'].min():.6f} - ${df['cex_price'].max():.6f}")
            print(f"  Avg volume: {df['volume'].mean():.2f}")
            
        except Exception as e:
            print(f"[ERROR] {symbol}: {e}")
            time.sleep(2)

if __name__ == "__main__":
    # Date range (match your Dune query)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    print("="*60)
    print("BINANCE HISTORICAL DATA FETCHER")
    print("="*60)
    print(f"Date Range: {start_date.date()} to {end_date.date()}")
    print(f"Output Dir: data/")
    print()
    
    # Try Binance.US spot (accessible from US IPs)
    # Note: Binance.US has BRETT but AERO availability varies
    spot_symbols = [
        'AERO/USDT',
        'BRETT/USDT',
    ]
    
    print("\n--- ATTEMPT 1: BINANCE.US SPOT ---")
    print("(Using Binance.US to avoid geolocation restrictions)")
    save_to_csv(spot_symbols, start_date, end_date, exchange_type='spot', use_binance_us=True)
    
    # Fallback: If Binance.US doesn't have AERO, we'll simulate or use alternative
    print("\n--- FALLBACK: If symbols unavailable, will use mock data ---")
    
    print("\n" + "="*60)
    print("FETCH COMPLETE")
    print("="*60)
