from datetime import datetime, time, timezone, timedelta
import pytz
from config.settings import ENTRY_START, ENTRY_END

# Set timezone
IST = pytz.timezone('Asia/Kolkata')

EXIT_TIME = "15:15"


def is_market_open(now: datetime = None) -> bool:
    """
    Check if the current time is within NSE market hours (09:15 to 15:30).
    """
    now = now or datetime.now(IST)
    current_time = now.time()  # Extract time part
    market_open = time(9, 15, tzinfo=IST)
    market_close = time(15, 30, tzinfo=IST)
    return market_open <= current_time <= market_close


def is_exit_time(now: datetime = None):
    now = now or datetime.now(IST)
    exit_time = datetime.strptime(EXIT_TIME, "%H:%M").time()
    return now.time() >= exit_time


def is_within_entry_window(now: datetime = None) -> bool:
    """
    Check if the current time is within the defined ENTRY window for taking trades.
    """
    now = now or datetime.now(IST)
    current_time = now.time()
    entry_start = time.fromisoformat(ENTRY_START).replace(tzinfo=IST)
    entry_end = time.fromisoformat(ENTRY_END).replace(tzinfo=IST)
    return entry_start <= current_time <= entry_end


def is_five_minute_candle(now: datetime = None):
    """
    Check if the current minute is a multiple of 5 (e.g., 09:20, 09:25).
    """
    now = now or datetime.now(IST)
    return now.minute % 5 == 0

# from utils.time_utils import is_market_open, is_within_entry_window, is_five_minute_candle

# if is_market_open() and is_within_entry_window() and is_five_minute_candle():
#     run_bot()
