import os
from dotenv import load_dotenv

# Load from .env file if available
load_dotenv()

# === SMARTAPI (Angel One) Credentials ===
SMART_API_KEY = os.getenv("SMART_API_KEY", "your_api_key_here")
SMART_API_CLIENT_ID = os.getenv("SMART_API_CLIENT_ID", "your_client_id")
SMART_API_PIN = os.getenv("SMART_API_PIN", "your_pin")
SMART_API_TOTP_SECRET = os.getenv("SMART_API_TOTP_SECRET", "totp_secret_here")

# === Entry Window ===
ENTRY_START = "11:00"
ENTRY_END = "14:45"

# === Exit & Risk Management ===
SL_PERCENT = 30  # 30% Stop Loss
TARGET_PERCENT = 60  # 60% Target
TRAIL_SL_ENABLED = False
TRAIL_STEP_PERCENT = 10  # Every 10% increase, trail SL
ENABLE_PRETARGET_TRAIL_SL = True  # Toggle for early TSL before target
# ENABLE_PRE_TARGET_TSL = True  # or False, based on your strategy
SLIPPAGE_BUFFER = 1.0         # Rupee buffer for expected loss calculation

# === Token Cache Config ===
TOKEN_CACHE_FILE = "token_cache.json"
# Path for trade logs
TRADE_LOG_PATH = "reports/trades_log.csv"
POSITION_STATE_FILE = "reports/position_state.json"
SIGNAL_STATE_FILE = "reports/signal_state.json"

# === Index Info ===
INDEX_SYMBOL = "NIFTY"
EXCHANGE = "NSE"  # For index candles, typically "NSE"
NIFTY_SYMBOL_TOKEN = "99926000"  # Example token for NIFTY spot from SmartAPI

# === Trading Config ===
LOT_SIZE = 75  # 500                 # Lot size for NIFTY
MAX_TRADES_PER_DAY = 2  # 1 CE + 1 PE max
# === Order Management ===
CAPITAL_PER_TRADE = 50000  # Capital per trade (you can tweak this)

# === Risk Limits (used by risk_manager) ===
MAX_DAILY_LOSS = 5000  # Max loss allowed in a day, Add capital check: not more than 5% of full capital
MAX_DAILY_PROFIT = 10000  # Max profit allowed in a day
RISK_PER_TRADE = 0.02  # 2% of capital per trade

# Enable or disable directional bias filtering
ENABLE_BIAS_CHECK = True
ENABLE_DELAY_TRAP_CHECK = True

# settings.py
ENABLE_FUTURE_VOLUME_CONFIRMATION = False  # Toggle for volume breakout filter
FUTURE_SYMBOL_TOKEN = "26000"  # NIFTY FUT Token (double-check via Angel One)
