# Updated backtest_runner.py — Uses multi-timeframe CSV-based backtesting
import sys, os
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backtest.backtest_executor import run_backtest

CSV_BASE_PATH = "sample_data"  # Folder with nifty_spot_* and nifty_fut_* files


def main():
    print("Starting NIFTY Backtest (Multi-Timeframe)...")

    if not os.path.exists(CSV_BASE_PATH):
        print(f"❌ Folder not found: {CSV_BASE_PATH}")
        return

    trades = run_backtest(CSV_BASE_PATH)

    if trades.empty:
        print("No trades were generated.")
        return

    trades.to_csv("backtest_results.csv", index=False)

    # Summary
    total_trades = len(trades)
    winning_trades = trades[trades["pnl"] > 0]
    losing_trades = trades[trades["pnl"] <= 0]
    total_pnl = trades["pnl"].sum()

    print("\n📊 Backtest Summary")
    print("-" * 40)
    print(f"Total Trades     : {total_trades}")
    print(f"Winning Trades   : {len(winning_trades)}")
    print(f"Losing Trades    : {len(losing_trades)}")
    print(f"Win Rate         : {len(winning_trades) / total_trades * 100:.2f}%")
    print(f"Total PnL        : ₹{total_pnl:.2f}")
    print("-" * 40)

    print("\n✅ Trade Details:")
    print(trades.tail(5))


if __name__ == "__main__":
    main()
