# Blackglass Backtest Pipeline - Complete Workflow

## Phase 1: Install Dependencies

```powershell
# Install CCXT for Binance data
pip install ccxt pandas

# Verify installation
python -c "import ccxt; print(f'CCXT Version: {ccxt.__version__}')"
```

## Phase 2: Fetch Historical Data

### 2A: Get Dune DEX Data (Manual)
1. Go to https://dune.com
2. Create new query with the SQL from earlier (see query below)
3. Run query → Download CSV
4. Save to: `c:\Users\colem\Code\blackglass-variance-core\data\dune_base_dex_30d.csv`

**Dune Query** (copy this):
```sql
WITH base_trades AS (
    SELECT 
        block_time,
        DATE_TRUNC('minute', block_time) AS minute_time,
        project,
        token_sold_symbol,
        token_bought_symbol,
        token_sold_amount / POWER(10, COALESCE(token_sold_decimals, 18)) AS sold_norm,
        token_bought_amount / POWER(10, COALESCE(token_bought_decimals, 18)) AS bought_norm,
        amount_usd
    FROM dex.trades
    WHERE blockchain = 'base'
      AND block_time >= CURRENT_DATE - INTERVAL '30' DAY
      AND (
          (token_sold_symbol IN ('AERO', 'BRETT') AND token_bought_symbol = 'WETH')
          OR (token_bought_symbol IN ('AERO', 'BRETT') AND token_sold_symbol = 'WETH')
      )
      AND amount_usd > 50
),
normalized_prices AS (
    SELECT 
        minute_time,
        CASE 
            WHEN token_sold_symbol = 'WETH' THEN token_bought_symbol
            ELSE token_sold_symbol
        END AS asset,
        CASE 
            WHEN token_sold_symbol = 'WETH' THEN sold_norm / bought_norm
            ELSE bought_norm / sold_norm
        END AS price_in_weth
    FROM base_trades
)
SELECT 
    minute_time AS timestamp,
    asset,
    AVG(price_in_weth) AS dex_price_weth,
    MIN(price_in_weth) AS min_price,
    MAX(price_in_weth) AS max_price,
    COUNT(*) AS trade_count,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price_in_weth) AS median_price
FROM normalized_prices
GROUP BY minute_time, asset
HAVING COUNT(*) >= 2
ORDER BY minute_time DESC, asset;
```

### 2B: Get Binance CEX Data (Automated)
```powershell
cd c:\Users\colem\Code\blackglass-variance-core

# Fetch AERO and BRETT price history from Binance
python scripts\fetch_binance_historical.py
```

**Expected Output**:
```
[FETCH] Pulling AERO/USDT from 2025-12-26 to 2026-01-25
  Fetched 1000 candles so far...
  Fetched 2000 candles so far...
  ...
[SUCCESS] Saved 43200 candles to data/binance_AEROUSDT_2025-12-26_2026-01-25.csv
```

## Phase 3: Run Backtest

```powershell
# Execute full backtest with real data
python scripts\backtest_dune.py
```

**Expected Output**:
```
[INIT] Loading Dune DEX data from data/dune_base_dex_30d.csv
  Loaded 35482 DEX price points
[INIT] Loading CEX data files:
  AEROUSDT: 43200 candles
  BRETTUSDT: 43200 candles

============================================================
STARTING BACKTEST
============================================================
Window: 2026-01-18 to 2026-01-25
Spread Threshold: 0.50%
Position Size: $500

Assets to test: ['AERO', 'BRETT']

[LOSS] AERO @ 01-18 14:35 → $-2.15
[LOSS] BRETT @ 01-19 08:20 → $-1.88
...

============================================================
BACKTEST RESULTS
============================================================
total_trades................................... 47
winning_trades................................. 29
losing_trades.................................. 18
win_rate_pct................................... 61.70%
total_pnl_usd.................................. $142.35
avg_win_usd.................................... $8.23
avg_loss_usd................................... $-3.12
sharpe_ratio................................... 2.1456
max_drawdown_usd............................... $-18.50
profit_factor.................................. 2.5321
roi_pct........................................ 0.61%
avg_spread_pct................................. 0.73%
============================================================

SUCCESS CRITERIA:
✓ Win Rate: 61.7% (target: >60%)
✓ Sharpe Ratio: 2.15 (target: >1.5)
✓ Max Drawdown: $-18.50 (target: >-$50)

============================================================
STATUS: READY FOR PAPER TRADING
============================================================
```

## Phase 4: Interpret Results

### ✅ **PASS Criteria** (Ready for Paper Trading):
- Win Rate > 60%
- Sharpe > 1.5
- Max Drawdown < $50

### 🟡 **TUNE Criteria** (Promising, needs optimization):
- Win Rate 50-60%
- Sharpe 1.0-1.5
- Max Drawdown $50-100

### ❌ **FAIL Criteria** (Revisit strategy):
- Win Rate < 50%
- Sharpe < 1.0
- Max Drawdown > $100

## Phase 5: Next Steps Based on Results

### If PASS:
```powershell
# Move to paper trading (no real money yet)
# Modify start_swarm.ps1 to run in "dry run" mode
# Monitor for 7 days
```

### If TUNE:
1. Open `data/backtest_trades.csv`
2. Identify losing patterns (which assets, which spreads)
3. Adjust threshold in config: `threshold: 0.008` (from 0.005)
4. Re-run backtest

### If FAIL:
1. Check data quality:
   ```powershell
   # Verify DEX data coverage
   python -c "import pandas as pd; df = pd.read_csv('data/dune_base_dex_30d.csv'); print(df.describe())"
   ```
2. Consider alternative chains (Arbitrum has deeper liquidity)
3. Review oracle_hunter logic for bugs

## Troubleshooting

### "No Binance CSV files found"
**Fix**: Run `fetch_binance_historical.py` first

### "Symbol not found on Binance"
**Fix**: Check if AERO/BRETT are listed. If not, use perpetuals:
- Edit `fetch_binance_historical.py`
- Change to `'AERO/USDT:USDT'` format
- Set `exchange_type='future'`

### "No trades triggered"
**Fix**: Lower threshold to 0.002 (0.2%) and re-run

### Rate limit errors
**Fix**: The script auto-sleeps. If persistent, increase `time.sleep(5)` in fetch script.

## File Structure After Setup

```
c:\Users\colem\Code\blackglass-variance-core\
├── data/
│   ├── dune_base_dex_30d.csv (manual download)
│   ├── binance_AEROUSDT_2025-12-26_2026-01-25.csv (auto-generated)
│   ├── binance_BRETTUSDT_2025-12-26_2026-01-25.csv (auto-generated)
│   ├── backtest_report.json (output)
│   └── backtest_trades.csv (output)
├── scripts/
│   ├── fetch_binance_historical.py
│   └── backtest_dune.py
```

## Advanced: Multi-Period Testing

Test across different market conditions:

```python
# In backtest_dune.py __main__ section:
windows = [
    (datetime(2026, 1, 1), datetime(2026, 1, 7)),   # Week 1
    (datetime(2026, 1, 8), datetime(2026, 1, 14)),  # Week 2
    (datetime(2026, 1, 15), datetime(2026, 1, 21)), # Week 3
]

for start, end in windows:
    report = asyncio.run(backtester.run_backtest(start, end))
    print(f"{start.date()} to {end.date()}: Sharpe={report['sharpe_ratio']:.2f}")
```

---

**Questions? Run into errors? Share the output and I'll debug.**
