
# 📈 Nifty Intraday Options Bot (SmartAPI)

This is a **fully automated intraday NIFTY options trading bot** built using Angel One's SmartAPI.  
It runs every 5 minutes, detects breakout patterns, and places CE/PE option trades using technical indicators with **dynamic SL, target, and trailing stop loss logic**.

---

## ✅ Features

- 📉 Trades based on **index-level breakout** logic (RSI, VWAP, EMA, ADX)
- 🔁 **Trailing Stop Loss (TSL)** with breakeven and lock-in logic
- 📬 Sends **Telegram alerts** for entry/exit
- 📊 Handles **risk per trade** and position sizing
- 🕰 Works in **9:20 AM to 12:30 PM** entry window
- ♻️ Runs every 5 minutes and exits on SL/Target or 3:15 PM
- ⚠️ Supports **pre-target trailing SL** (configurable)
- ✅ Auto-fetches tokens using caching mechanism

---

## 🗂️ Project Structure



nifty-intraday-bot/
│
├── config/
│   └── settings.py                # API keys, thresholds, capital config
│
├── core/
│   ├── signal_engine.py           # Entry signal logic (RSI, VWAP, EMA, ADX, S/R, candle patterns)
│   ├── order_manager.py           # Place orders, modify SL/Target, square-off
│   ├── strike_selector.py         # Identify ATM, OTM strikes dynamically
│   ├── risk_manager.py            # Position sizing, max loss, target tracking
│   └── pattern_checker.py         # Bullish/bearish candle pattern recognizer
│
├── data/
│   └── fetch_data.py              # 5-min candle data, LTP, indicators from SmartAPI
│
├── utils/
|   |__ expiry_utils.py            # Weekly expiry string generator
│   ├── logger.py                  # Rotating logger setup
│   └── telegram_alerts.py         # Telegram alert sender
│   ├── time_utils.py              # Time checks (market open, 5-min intervals)
|   |__ token_cache.py             # Token mapping and caching
│
|                  
|── token_cache.json               # Cache for storing token data
|
├── main.py                        # Main bot runner (every 5 mins)
|
└── requirements.txt
|
|── README.md




---
## ⚙️ Installation

```bash
git clone https://github.com/yourusername/nifty-intraday-bot.git
cd nifty-intraday-bot
pip install -r requirements.txt


python main.py

``

## ⚙️ Configuration

Edit values in `config/settings.py`:

```python
CAPITAL = 50000
RISK_PER_TRADE = 0.02
SL_ATR_MULTIPLIER = 1.2
TARGET_ATR_MULTIPLIER = 2.0
TRAIL_SL_ENABLED = True
ENABLE_PRETARGET_TRAIL_SL = True

# For SmartAPI:
SMART_API_KEY = os.getenv("SMART_API_KEY")
SMART_API_CLIENT_ID = os.getenv("SMART_API_CLIENT_ID")
SMART_API_PIN = os.getenv("SMART_API_PIN")
SMART_API_TOTP_SECRET = os.getenv("SMART_API_TOTP_SECRET")

# For Telegram alerts:
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

🚀 How to Run

🔧 Setup .env file with API credentials (optional):

SMART_API_KEY=xxx
SMART_API_CLIENT_ID=xxx
SMART_API_PIN=xxx
SMART_API_TOTP_SECRET=xxx
TELEGRAM_TOKEN=xxx
TELEGRAM_CHAT_ID=xxx


📦 Install dependencies:

pip install -r requirements.txt


▶️ Run the bot:

python main.py

✅ Best Practices
- Run using virtual environment

- Schedule via CRON or PM2

- Backtest your strategies before real trading

- Enable TRAIL_SL_ENABLED + ENABLE_PRETARGET_TRAIL_SL for dynamic exits

🛑 Disclaimer
This project is for educational purposes only. Use it at your own risk.
Trading options involves risk. Please consult with a certified advisor before deploying real capital.

👨‍💻 Author
Abhishek G | Techjaala
GitHub: github.com/abhishek-techjaala

Happy Trading! 🚀📊💰




```

📌 Notes
Live trading requires Angel One's SmartAPI credentials and trading account.

This project is for educational purposes only. Trade at your own risk.


### ✅ Why Entry Window: `09:20` to `12:30`?

This time range is **intentionally selected** based on how most **professional traders** (including quant firms and prop desks) operate.

---

### 📌 1. **Why start at 09:20 instead of 09:15?**

| Time          | Reason                                                                                        |
| ------------- | --------------------------------------------------------------------------------------------- |
| `09:15–09:20` | Market opening volatility is **extremely high**; spreads are wide and signals are unreliable. |
| `09:20+`      | Prices begin to **settle**, technical indicators like VWAP, RSI become more **meaningful**.   |

This is **industry standard** — many algos **skip first 5–15 minutes** to avoid false breakouts and whipsaws.

---

### 📌 2. **Why stop new entries at 12:30 PM?**

| Time         | Reason                                                                                                |
| ------------ | ----------------------------------------------------------------------------------------------------- |
| `12:30+`     | Market enters **low-volume lunch zone**. Price often moves sideways or gives false breakouts.         |
| After `1:00` | Volatility returns, but it's often **erratic**, driven by option decay, FII flows, or afternoon news. |
| Post 2:30 PM | Theta decay accelerates, moves are sharp, **risk of reversal** increases.                             |

Hence, we only want to **enter trades when market is clean and technical indicators are reliable**.

---

### ✅ Summary: This is **Best Practice**

| Time Slot     | Action       | Reason                             |
| ------------- | ------------ | ---------------------------------- |
| `09:15–09:20` | Avoid        | High volatility & noise            |
| `09:20–12:30` | Entry window | Indicators most reliable           |
| `12:30–15:30` | Hold/Manage  | No new entries, manage open trades |

---

### 📈 Bonus Tip:

Many **institutional algo desks** in India limit **entry windows** too. Even brokers like Zerodha/Streak, Dhan, etc., encourage bots to **avoid full-day entry** and focus on **predictable market phases.**

-------------

Set-Alias python "C:\Users\4906031\AppData\Local\Microsoft\WindowsApps\python3.10.exe"

& "C:\Users\4906031\AppData\Local\Microsoft\WindowsApps\python3.10.exe" -m venv .venv

.\.venv\Scripts\Activate.ps1


nifty-intraday-bot/
└── backtest/
    ├── backtest_runner.py          # Main script to run the backtest
    ├── backtest_executor.py        # Core backtest logic and PnL tracking
    └── sample_data/
        └── nifty_2024.csv          # Sample NIFTY 5-min candle data with indicators (RSI, VWAP)




nifty-intraday-bot/
│
├── config/
│   └── settings.py                    # API keys, strategy config, toggles
│
├── core/
│   ├── signal_engine.py               # Strategy logic: RSI, VWAP, S/R, patterns
│   ├── order_manager.py               # Place orders, manage SL/target/TSL
│   ├── strike_selector.py             # ATM/OTM strike selector
│   ├── risk_manager.py                # Capital allocation, max loss, position sizing
│   ├── position_tracker.py            # NEW: Maintain active position states
│   ├── state_persistence.py           # NEW: Save/load position state between restarts
│   └── hedging_engine.py              # NEW: Optional hedging logic
│
├── data/
│   ├── fetch_data.py                  # Candle data, LTP, indicators
│   ├── backtest_engine.py             # NEW: Run historical backtests on strategy
│   └── pnl_tracker.py                 # NEW: Real-time P&L tracking
│
├── utils/
│   ├── logger.py                      # Rotating logs
│   ├── telegram_alerts.py             # Alerts for entries/exits/errors
│   ├── time_utils.py                  # Market open, exit time check, scheduler
│   ├── expiry_utils.py                # Weekly expiry builder
│   ├── token_cache.py                 # Token management
│   ├── test_runner.py                 # NEW: Unit testing framework
│   └── exception_handler.py           # NEW: Recovery, reconnects, restart logic
│
├── reports/
│   └── trades_log.csv                 # All trades with timestamps & result
│   └── backtest_results/              # Backtest reports
│
├── main.py                            # Live bot runner
├── backtest.py                        # CLI entry for backtest
├── README.md
└── requirements.txt

 # TODOS in Queue (Future Enhancement)
 ----------
 🧱 Step-by-Step Philosophy for Robust Trading Systems
Phase 1: Core System Must Be Rock Solid
You're very close to completing this phase:

✅ Signal engine: Clean logic, indicator-based, CE/PE cap per day

✅ Backtest engine: Functional with capital, PnL, and SL/Target tracking

✅ Risk manager: Capital sizing and daily risk control

✅ Order manager: Modular, toggle-based SL/TSL logic

✅ State management: Tracks daily signals and active positions

✅ Main script: Clean, cron-based, production-ready loop

What’s left:

🔲 Clean up and finalize the main.py and backtest consistency

🔲 Finalize the PnL report generator + charts

🔲 Add minimal unit tests for signal_engine, risk_manager, support_resistance

Once this phase is done, you’ll have a plug-and-play quant-grade intraday NIFTY bot.

🚀 Phase 2: Strategic Enhancements (Optional, Modular)
Once the base is stable, then plug these in one at a time:

Enhancement	Type	Benefit
🔲 Volume-based breakout (NIFTY FUT)	Signal Filter	Confirms real buying/selling pressure
🔲 OI-based directional bias	Macro Bias	Filters fake breakouts or traps
🔲 Multi-entry/day with trail logic	Risk Tweak	Extracts more alpha from trends
🔲 Statistical regime detection	Quant Logic	Applies signals only in trending phases
🔲 Live performance tracker	Analytics	Visualizes trades & PnL in real time

All of these can be plugged into your clean modular pipeline one by one.
Not a rewrite — just bolt-on upgrades.

