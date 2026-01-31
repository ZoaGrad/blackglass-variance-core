import sys
import os

# Add root directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import asyncio
import glob
from datetime import datetime, timedelta
from modules.learner import Learner

class DuneBacktester:
    def __init__(self, dune_csv_path, cex_data_dir='data'):
        """
        Initialize backtester with Dune DEX data and Binance CEX data.
        
        Args:
            dune_csv_path: Path to Dune CSV export
            cex_data_dir: Directory containing Binance CSV files
        """
        print(f"[INIT] Loading Dune DEX data from {dune_csv_path}")
        self.dune_df = pd.read_csv(dune_csv_path, parse_dates=['timestamp'])
        print(f"  Loaded {len(self.dune_df)} DEX price points")
        
        # Auto-discover and load CEX data files
        self.cex_dfs = {}
        self._load_cex_data(cex_data_dir)
        
        self.results = []
        self.learner = Learner()
        
    def _load_cex_data(self, cex_data_dir):
        """Auto-load all Binance CSV files from directory"""
        pattern = f"{cex_data_dir}/binance_*.csv"
        files = glob.glob(pattern)
        
        if not files:
            print(f"[WARN] No Binance CSV files found in {cex_data_dir}")
            print(f"  Run 'python scripts/fetch_binance_historical.py' first")
            return
        
        print(f"[INIT] Loading CEX data files:")
        for filepath in files:
            # Extract symbol from filename (e.g., binance_AEROUSDT_...)
            filename = filepath.split('\\')[-1] if '\\' in filepath else filepath.split('/')[-1]
            symbol = filename.split('_')[1]  # e.g., 'AEROUSDT'
            
            df = pd.read_csv(filepath, parse_dates=['timestamp'])
            df.set_index('timestamp', inplace=True)
            df.sort_index(inplace=True)
            
            self.cex_dfs[symbol] = df
            print(f"  {symbol}: {len(df)} candles")
    
    def get_dex_price(self, timestamp, asset):
        """Get DEX price at specific timestamp from Dune data"""
        # Find closest price within 2-minute window
        window = self.dune_df[
            (self.dune_df['timestamp'] >= timestamp - timedelta(minutes=2)) &
            (self.dune_df['timestamp'] <= timestamp) &
            (self.dune_df['asset'] == asset)
        ]
        
        if window.empty:
            return None
        
        # Use median price for stability
        return window.iloc[-1]['median_price']
    
    def get_cex_price(self, timestamp, asset):
        """Get real CEX price from Binance data"""
        # Map asset to Binance symbol
        symbol_map = {
            'AERO': 'AEROUSDT',
            'BRETT': 'BRETTUSDT',
        }
        
        symbol = symbol_map.get(asset.upper())
        if symbol not in self.cex_dfs:
            return None
        
        df = self.cex_dfs[symbol]
        
        # Find closest timestamp <= requested time
        candidates = df.index[df.index <= timestamp]
        if candidates.empty:
            return None
        
        closest_ts = candidates.max()
        return df.loc[closest_ts, 'cex_price']
    
    def convert_to_weth_terms(self, usdt_price, timestamp):
        """
        Convert USDT price to WETH terms for proper spread calculation.
        Uses ETH/USDT from Binance data if available.
        """
        if 'ETHUSDT' in self.cex_dfs:
            df = self.cex_dfs['ETHUSDT']
            candidates = df.index[df.index <= timestamp]
            if not candidates.empty:
                eth_price = df.loc[candidates.max(), 'cex_price']
                return usdt_price / eth_price
        
        # Fallback: assume ~$3000 ETH
        return usdt_price / 3000.0
    
    async def run_backtest(self, start_date, end_date, threshold=0.005, position_size_usd=500):
        """
        Run backtest simulation over historical data.
        
        Args:
            start_date: datetime
            end_date: datetime
            threshold: Minimum spread to trigger trade (0.005 = 0.5%)
            position_size_usd: USD value per trade
        """
        print("\n" + "="*60)
        print("STARTING BACKTEST")
        print("="*60)
        print(f"Window: {start_date.date()} to {end_date.date()}")
        print(f"Spread Threshold: {threshold*100:.2f}%")
        print(f"Position Size: ${position_size_usd}")
        print()
        
        assets = list(set(self.dune_df['asset'].unique()))
        print(f"Assets to test: {assets}")
        print()
        
        # Sample every 5 minutes
        current_time = start_date
        trade_id = 0
        skipped_no_dex = 0
        skipped_no_cex = 0
        
        while current_time <= end_date:
            for asset in assets:
                dex_price = self.get_dex_price(current_time, asset)
                cex_price_usdt = self.get_cex_price(current_time, asset)
                
                if dex_price is None:
                    skipped_no_dex += 1
                    continue
                    
                if cex_price_usdt is None:
                    skipped_no_cex += 1
                    continue
                
                # Convert CEX price to WETH terms for accurate comparison
                cex_price = self.convert_to_weth_terms(cex_price_usdt, current_time)
                
                # Calculate spread (DEX is in WETH, CEX now in WETH)
                spread = (cex_price - dex_price) / dex_price
                
                if abs(spread) > threshold:
                    trade_id += 1
                    direction = "BUY_DEX" if spread > 0 else "SELL_DEX"
                    
                    # Estimate realistic costs
                    gross_profit = position_size_usd * abs(spread)
                    gas_cost_usd = 0.20  # Conservative Base gas estimate
                    slippage_cost = position_size_usd * 0.0015  # 0.15% realistic slippage
                    net_pnl = gross_profit - gas_cost_usd - slippage_cost
                    
                    result = {
                        'trade_id': trade_id,
                        'timestamp': current_time,
                        'asset': asset,
                        'direction': direction,
                        'dex_price_weth': dex_price,
                        'cex_price_weth': cex_price,
                        'spread_pct': spread * 100,
                        'gross_profit': gross_profit,
                        'gas_cost': gas_cost_usd,
                        'slippage_cost': slippage_cost,
                        'net_pnl': net_pnl,
                        'success': net_pnl > 0
                    }
                    
                    self.results.append(result)
                    
                    # Log losses for Learner
                    if net_pnl < -1.0:
                        print(f"[LOSS] {asset} @ {current_time.strftime('%m-%d %H:%M')} → ${net_pnl:.2f}")
            
            # Advance by 5 minutes
            current_time += timedelta(minutes=5)
        
        print(f"\n[STATS] Skipped: {skipped_no_dex} (no DEX), {skipped_no_cex} (no CEX)")
        
        return self.analyze_results()
    
    def analyze_results(self):
        """Calculate comprehensive performance metrics"""
        df = pd.DataFrame(self.results)
        
        if df.empty:
            return {
                "error": "No trades triggered in backtest window",
                "recommendation": "Lower threshold or check data availability"
            }
        
        total_trades = len(df)
        winning_trades = len(df[df['net_pnl'] > 0])
        losing_trades = total_trades - winning_trades
        
        total_pnl = df['net_pnl'].sum()
        avg_win = df[df['net_pnl'] > 0]['net_pnl'].mean() if winning_trades > 0 else 0
        avg_loss = df[df['net_pnl'] <= 0]['net_pnl'].mean() if losing_trades > 0 else 0
        
        # Sharpe Ratio (annualized, assuming ~100 trades/month)
        returns = df['net_pnl'] / 500
        if returns.std() > 0:
            sharpe = (returns.mean() / returns.std()) * (12 ** 0.5)  # Monthly → Annualized
        else:
            sharpe = 0
        
        # Max Drawdown
        cumulative = df['net_pnl'].cumsum()
        running_max = cumulative.cummax()
        drawdown = cumulative - running_max
        max_drawdown = drawdown.min()
        
        # Profit Factor
        gross_profit = df[df['net_pnl'] > 0]['net_pnl'].sum()
        gross_loss = abs(df[df['net_pnl'] <= 0]['net_pnl'].sum())
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        report = {
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate_pct": (winning_trades / total_trades) * 100 if total_trades > 0 else 0,
            "total_pnl_usd": total_pnl,
            "avg_win_usd": avg_win,
            "avg_loss_usd": avg_loss,
            "sharpe_ratio": sharpe,
            "max_drawdown_usd": max_drawdown,
            "profit_factor": profit_factor,
            "roi_pct": (total_pnl / (500 * total_trades)) * 100 if total_trades > 0 else 0,
            "avg_spread_pct": df['spread_pct'].abs().mean(),
        }
        
        return report

if __name__ == "__main__":
    # Initialize backtester (auto-loads data from data/ directory)
    backtester = DuneBacktester(
        dune_csv_path="data/dune_base_dex_30d.csv"
    )
    
    # Test window (last 7 days for faster iteration)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    # Run backtest
    report = asyncio.run(backtester.run_backtest(
        start_date, 
        end_date, 
        threshold=0.003,  # 0.3% minimum spread (tuned for realistic base markets)
        position_size_usd=500
    ))
    
    # Print results
    print("\n" + "="*60)
    print("BACKTEST RESULTS")
    print("="*60)
    
    if "error" in report:
        print(f"ERROR: {report['error']}")
        if "recommendation" in report:
            print(f"→ {report['recommendation']}")
    else:
        for key, value in report.items():
            if isinstance(value, float):
                if 'pct' in key or 'rate' in key:
                    print(f"{key:.<40} {value:.2f}%")
                elif 'ratio' in key or 'factor' in key:
                    print(f"{key:.<40} {value:.4f}")
                else:
                    print(f"{key:.<40} ${value:.2f}")
            else:
                print(f"{key:.<40} {value}")
    
    print("="*60)
    
    # Success criteria evaluation
    if "error" not in report:
        print("\nSUCCESS CRITERIA:")
        
        passed = []
        failed = []
        
        if report['win_rate_pct'] >= 60:
            passed.append(f"✓ Win Rate: {report['win_rate_pct']:.1f}% (target: >60%)")
        else:
            failed.append(f"✗ Win Rate: {report['win_rate_pct']:.1f}% (target: >60%)")
        
        if report['sharpe_ratio'] >= 1.5:
            passed.append(f"✓ Sharpe Ratio: {report['sharpe_ratio']:.2f} (target: >1.5)")
        else:
            failed.append(f"✗ Sharpe Ratio: {report['sharpe_ratio']:.2f} (target: >1.5)")
        
        if report['max_drawdown_usd'] > -50:
            passed.append(f"✓ Max Drawdown: ${report['max_drawdown_usd']:.2f} (target: >-$50)")
        else:
            failed.append(f"✗ Max Drawdown: ${report['max_drawdown_usd']:.2f} (target: >-$50)")
        
        for item in passed:
            print(item)
        for item in failed:
            print(item)
        
        print("\n" + ("="*60))
        if len(failed) == 0:
            print("STATUS: READY FOR PAPER TRADING")
        elif len(passed) >= 2:
            print("STATUS: PROMISING - TUNE PARAMETERS")
        else:
            print("STATUS: NEEDS REFINEMENT")
        print("="*60)
    
    # Save detailed results
    import json
    with open("data/backtest_report.json", "w") as f:
        json.dump(report, f, indent=2)
    
    if backtester.results:
        pd.DataFrame(backtester.results).to_csv("data/backtest_trades.csv", index=False)
        print("\nDetailed trade log saved to: data/backtest_trades.csv")
