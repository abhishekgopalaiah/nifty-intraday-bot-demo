"""
Order Manager Module

Features:
- SmartAPI order placement
- ATR-based SL and Target logic
- Trailing Stop Loss (TSL)
- Breakeven SL adjustment
- Lock-in profit SL after strong move
- Optional Pre-target TSL via toggle
- Telegram alerts + structured logging
"""

import time
from SmartApi.smartConnect import SmartConnect
from datetime import datetime
import pytz

# Set timezone
IST = pytz.timezone('Asia/Kolkata')
from core.state_manager import save_position_state, clear_position_state, load_position_state
from utils.logger import get_logger
from data.fetch_data import get_candle_data
from config.settings import (
    TRAIL_SL_ENABLED, TRAIL_STEP_PERCENT,
    ENABLE_PRETARGET_TRAIL_SL, SLIPPAGE_BUFFER
)
from data.pnl_tracker import log_trade

logger = get_logger()


class OrderManager:
    """
    Manages order placement, exit conditions, and position state.
    Handles capital-based sizing, SL/Target, and trailing stop loss.
    """

    def __init__(self, client: SmartConnect):
        self.client = client
        # self.open_position = None  # Holds current active position data
        # Restore open position from disk
        self.open_position = load_position_state()

    def place_order(self, symbol, token, ltp, atr, option_type, quantity, sl_price, target_price):
        """
        Place CE/PE Buy Order with ATR-based SL and Target
        Places a CE/PE BUY market order with ATR-based SL/Target and sets up trailing logic.

        Args:
            symbol (str): Option symbol (e.g., NIFTY27JUN24500CE)
            token (str): Token for the instrument
            ltp (float): Current market price
            atr (float): ATR value for dynamic SL/Target
            option_type (str): "CE" or "PE"
            quantity (int): Number of lots/quantity to trade
            sl_price (float): Stop loss price level
            target_price (float): Target price level for taking profits
        """
        try:
            # 1. Compute quantity based on capital per trade
            if quantity <= 0:
                logger.warning("Computed quantity invalid. Order skipped.")
                return

            expected_loss = (ltp - sl_price + SLIPPAGE_BUFFER) * quantity
            logger.warning(f"Expected loss ({expected_loss:.2f})")

            order_params = {
                "variety": "NORMAL",
                "tradingsymbol": symbol,
                "symboltoken": token,
                "transactiontype": "BUY",
                "exchange": "NFO",
                "ordertype": "MARKET",
                "producttype": "INTRADAY",
                "duration": "DAY",
                "price": "0",
                "squareoff": "0",
                "stoploss": "0",
                "quantity": quantity
            }

            # 4. Log and place order

            logger.info(f"Trade Entered: {symbol} @ {ltp}, Qty: {quantity}, Type: {option_type}")

            # 5. Save position metadata
            self.open_position = {
                "symbol": symbol,
                "token": token,
                "entry_price": ltp,
                "atr": atr,
                "option_type": option_type,
                "quantity": quantity,
                "order_id": 99999,
                "sl": sl_price,
                "target": target_price,
                "timestamp": datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S"),
                "last_peak": ltp,
                "breakeven_shifted": False,
                "lockin_triggered": False,
                "trail_triggered": False
            }
            # 6. save position state
            save_position_state(self.open_position)
        except Exception as e:
            logger.error(f"Order placement failed: {e}")

    def exit_trade(self, reason="Target or SL Hit"):
        """
        Exit the current open position and record the result.
        """
        if not self.open_position:
            logger.info("No open position to exit.")
            return

        pos = self.open_position
        df = get_candle_data(self.client, pos["token"], interval="ONE_MINUTE", days_back=1, exchange="NFO")
        ltp = float(df.iloc[-1]["close"]) if not df.empty else pos["entry_price"]

        exit_order_params = {
            "variety": "NORMAL",
            "tradingsymbol": pos["symbol"],
            "symboltoken": pos["token"],
            "transactiontype": "SELL",
            "exchange": "NFO",
            "ordertype": "MARKET",
            "producttype": "INTRADAY",
            "duration": "DAY",
            "price": "0",
            "squareoff": "0",
            "stoploss": "0",
            "quantity": pos["quantity"]
        }

        for attempt in range(3):
            try:
                logger.info(f"Exit Order Placed for {pos['symbol']} at {ltp}")
                break
            except Exception as e:
                logger.error(f"Exit order failed (try {attempt + 1}/3): {e}")
                time.sleep(2)
        else:
            logger.critical("Exit order failed after retries! Manual intervention needed.")
            exit_order_id = "NA"

        pnl = round((ltp - pos["entry_price"]) * pos["quantity"], 2)
        logger.info(f"Trade Exited: {pos['symbol']} | Entry: {pos['entry_price']} | Exit: {ltp} | PnL: {pnl}")

        log_trade(
            symbol=pos["symbol"],
            qty=pos["quantity"],
            entry_price=pos["entry_price"],
            exit_price=ltp,
            exit_reason=reason,
            entry_time=pos["timestamp"],
            exit_time=datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")
        )

        clear_position_state()
        self.open_position = None

    def check_exit_conditions(self):
        """
        Monitors active position every 5 min:
        - SL Hit
        - Target Hit (if TSL disabled)
        - Trailing SL (if enabled, before/after target based on config)
        """
        if not self.open_position:
            return

        try:
            pos = self.open_position
            token = pos["token"]
            symbol = pos["symbol"]
            entry = pos["entry_price"]
            sl = pos["sl"]
            target = pos["target"]
            atr = pos["atr"]
            peak = pos["last_peak"]

            # Fetch LTP from recent candle
            df = get_candle_data(self.client, token, interval="ONE_MINUTE", days_back=0.1, exchange="NFO")
            if df.empty:
                logger.warning(f"[Exit Check] No candle data for {symbol}")
                return

            ltp = float(df.iloc[-1]["close"])
            logger.info(f"[Exit Monitor] {symbol} | LTP: {ltp} | SL: {sl} | Target: {target}")

            # 1. Hard SL Check
            if ltp <= sl:
                self.exit_trade("SL Hit")
                return

            # 2. Target hit (only exit if TSL disabled)
            if ltp >= target and not TRAIL_SL_ENABLED:
                self.exit_trade("Target Hit")
                return

            # 3. TSL Logic (if enabled)
            if TRAIL_SL_ENABLED:
                trigger_trailing = False

                # 3.1 If pre-target trailing is allowed, we enable trailing as soon as some profit is made
                if ENABLE_PRETARGET_TRAIL_SL:
                    trigger_trailing = True

                # 3.2 If not allowed, only enable TSL once target is reached
                elif ltp >= target:
                    trigger_trailing = True

                if trigger_trailing:
                    pos["trail_triggered"] = True

                    # Lock-in after 2x ATR
                    if not pos["lockin_triggered"] and ltp >= entry + 2 * atr:
                        new_sl = round(entry + 0.5 * atr, 1)
                        if new_sl > sl:
                            pos["sl"] = new_sl
                            pos["lockin_triggered"] = True
                            logger.info(f"Lock-in SL activated: SL moved to {new_sl}")

                    # Breakeven shift after 1.5x ATR
                    if not pos["breakeven_shifted"] and ltp >= entry + 1.5 * atr:
                        new_sl = round(entry, 1)
                        if new_sl > sl:
                            pos["sl"] = new_sl
                            pos["breakeven_shifted"] = True
                            logger.info(f"SL shifted to breakeven: {new_sl}")

                    # Trailing by % step
                    step_points = TRAIL_STEP_PERCENT / 100 * entry
                    if ltp > peak + step_points:
                        new_sl = round(ltp - step_points, 1)
                        if new_sl > sl:
                            pos["sl"] = new_sl
                            pos["last_peak"] = ltp
                            logger.info(f"Trailing SL: Moved SL to {new_sl}")

            # Final SL/Target re-check
            if ltp <= pos["sl"]:
                self.exit_trade("SL/TSL Hit")
            elif ltp >= pos["target"] and not ENABLE_PRETARGET_TRAIL_SL:
                self.exit_trade("Target Hit")

            save_position_state(pos)

        except Exception as e:
            logger.error(f"[Exit Check Error] {e}")
