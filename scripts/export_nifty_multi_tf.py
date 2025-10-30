import os
import sys
import time
from pathlib import Path

from data.fetch_data import connect_smartapi, get_candle_data, enrich_with_indicators

sys.path.append(str(Path(__file__).parent.parent))

# Get the project root directory (one level up from scripts)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPORT_PATH = os.path.join(PROJECT_ROOT, "backtest", "sample_data")
os.makedirs(EXPORT_PATH, exist_ok=True)

client = connect_smartapi()
if not client:
    print("SmartAPI login failed.")
    exit()

# --- Spot Token ---
spot_token = "99926000"  # Replace with correct if needed
spot_intervals = {"5m": "FIVE_MINUTE", "15m": "FIFTEEN_MINUTE", "1h": "ONE_HOUR"}


# --- Download Spot Data ---
for tf, interval in spot_intervals.items():
    time.sleep(2)
    df = get_candle_data(client, symbol_token=spot_token, interval=interval, days_back=3, exchange="NSE")
    if tf == "5m":
        df = enrich_with_indicators(df)
    path = os.path.join(EXPORT_PATH, f"nifty_spot_{tf}.csv")
    df.to_csv(path, index=False)
    print(f"✅ Exported {path}")
