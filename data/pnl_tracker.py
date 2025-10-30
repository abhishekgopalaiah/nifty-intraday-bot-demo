import csv
import os
from datetime import datetime
import pytz

# Set timezone
IST = pytz.timezone('Asia/Kolkata')
from config.settings import TRADE_LOG_PATH
from utils.logger import get_logger

logger = get_logger()


def log_trade(symbol, qty, entry_price, exit_price, exit_reason, entry_time=None, exit_time=None):
    """
    Logs a completed trade to the CSV PnL tracker and returns the PnL.

    Args:
        symbol (str): Option symbol traded.
        qty (int): Quantity traded.
        entry_price (float): Entry price.
        exit_price (float): Exit price.
        exit_reason (str): Reason for exiting the trade.
        entry_time (str, optional): Entry timestamp (format: YYYY-MM-DD HH:MM:SS)

    Returns:
        float: PnL for the trade
    """
    pnl = round((exit_price - entry_price) * qty, 2)
    exit_time = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")

    row = {
        "Symbol": symbol,
        "Qty": qty,
        "Entry": entry_price,
        "Exit": exit_price,
        "PnL": pnl,
        "Entry Time": entry_time or "NA",
        "Exit Time": exit_time,
        "Exit Reason": exit_reason
    }

    file_exists = os.path.exists(TRADE_LOG_PATH)
    with open(TRADE_LOG_PATH, mode="a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

    logger.info(f"PnL Tracked | Symbol: {symbol} | PnL: Rupees {pnl} | Exit: {exit_reason}")
    return pnl