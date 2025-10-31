"""
main.py — NIFTY Intraday Options Bot Entry Point

Runs a fully automated intraday NIFTY options bot using:
    - Multi-timeframe support/resistance zone analysis
    - Signal generation with pattern + trend + regime scoring
    - Entry filter based on real-time candle action
    - Confidence-based risk management
    - DRY_RUN and SmartAPI order handling

Author: Abhishek G
"""

import time
import traceback
from datetime import datetime, timedelta
import pytz
import statistics

from data.fetch_data import connect_smartapi, get_candle_data, enrich_with_indicators
from core.signal_engine import generate_trade_signal
from core.order_manager import OrderManager
from core.strike_selector import round_to_nearest_strike, get_option_symbol
from core.risk_manager import calculate_position_size, is_risk_limit_breached
from core.support_resistance.zone_multiframe import build_zones_multi_tf
from utils.time_utils import is_market_open, is_exit_time, is_within_entry_window
from utils.logger import get_logger
from utils.token_cache import get_token_from_cache
from utils.expiry_utils import get_weekly_expiry_str
from config.settings import NIFTY_SYMBOL_TOKEN
from core.state_manager import (
    load_position_state, load_signal_state, save_signal_state, reset_daily_signals
)

# Set timezone
IST = pytz.timezone('Asia/Kolkata')

logger = get_logger()
order_manager = None
DRY_RUN = True


def wait_until_next_5_minute_slot(buffer_sec: int = 3):
    now = datetime.now(IST)
    next_slot = now + timedelta(minutes=5 - now.minute % 5)
    next_slot = next_slot.replace(second=0, microsecond=0)
    sleep_sec = (next_slot - now).total_seconds() + buffer_sec
    logger.info(f"Sleeping for {round(sleep_sec, 2)} sec until next 5-min slot: {next_slot}")
    logger.info("-" * 50)
    time.sleep(sleep_sec)


def get_multi_tf_data(client, symbol_token, exchange="NSE"):
    return {
        '5m': get_candle_data(client, symbol_token, "FIVE_MINUTE", 5, exchange=exchange),
        '15m': get_candle_data(client, symbol_token, "FIFTEEN_MINUTE", 7, exchange=exchange),
        '1h': get_candle_data(client, symbol_token, "ONE_HOUR", 10, exchange=exchange)
    }


def run_bot():
    global order_manager
    logger.info("Nifty Intraday Bot Started")

    signal_state = reset_daily_signals(load_signal_state())
    used_signals = signal_state["used_signals"]

    now = datetime.now(IST)
    if not is_market_open(now):
        logger.info("Market closed. Bot idle.")
        exit()

    if is_exit_time(now):
        logger.info("Exit time reached. Closing any open positions.")
        if order_manager:
            order_manager.exit_trade("EOD Exit")
        return

    client = connect_smartapi()
    if not client:
        logger.error("Failed to connect to SmartAPI.")
        return
    if not order_manager:
        order_manager = OrderManager(client)

    spot_data = get_multi_tf_data(client, NIFTY_SYMBOL_TOKEN)
    index_df = spot_data['5m']
    if index_df.empty or len(index_df) < 20:
        logger.warning("Insufficient candle data. Skipping this run.")
        return

    indicator_df = enrich_with_indicators(index_df.copy())
    ltp = index_df.iloc[-1]["close"]
    logger.info("=" * 60)
    logger.info(f"[CANDLE START] Processing candle at {now} | LTP: {ltp}")
    logger.info(f"Latest NIFTY LTP: {ltp}")

    if order_manager.open_position:
        logger.info("Active position exists. Skipping new entry.")
        return

    zones = build_zones_multi_tf(spot_data)
    zones = sorted(zones, key=lambda z: z.get('score', 0), reverse=True)

    for i, z in enumerate(zones[:5]):
        logger.info(
            f"[ZONE RANK] #{i + 1} | Score={z.get('score')} | Type={z['type']} | Band={z['band']} | Confidence={z['confidence']} | TFs={z.get('timeframes')}")

    all_scores = [z.get('score', 0) for z in zones]
    if all_scores:
        mean_score = round(statistics.mean(all_scores), 2)
        high_conf = sum(1 for z in zones if z['confidence'] == 'high')
        logger.info(
            f"[ZONE STATS] Total Zones: {len(zones)} | Mean Score: {mean_score} | High Confidence Zones: {high_conf}")

    # Generate signal using structured pipeline
    signal = generate_trade_signal(index_df, indicator_df, zones, signal_flags=used_signals)
    logger.info(f"signal response : {signal}")
    if signal.get("allowed"):
        logger.info(
            f"[SIGNAL GENERATED] Type={signal['option_type']} | Strike Dir={signal['strike_direction']} | "
            f"Confidence={signal.get('confidence')} | Entry Score={signal.get('entry_score')} | Regime={signal.get('regime')}"
        )

        if not is_within_entry_window(now):
            logger.info("Time check: Skipping entry signals before 9:45 and after 2:45 PM.")
            return

    # If no valid signal is returned (filtered out by score or entry filters)
    if not signal.get("allowed") or not signal.get("option_type"):
        logger.warning("[BOT] Signal not tradable or direction undefined. Skipping.")
        return

    # cooldown enforcement
    last_trade_time = signal_state.get("last_trade_time")
    last_side = signal_state.get("last_side")
    if last_side and last_side != signal["option_type"]:
        time_diff = (datetime.now(IST) - datetime.strptime(last_trade_time, "%H:%M:%S").replace(tzinfo=IST)).seconds
        if time_diff < 1800:
            logger.info("Cooldown triggered: skipping opposite-side entry too soon.")
            return

    expiry_str = get_weekly_expiry_str()
    strike = round_to_nearest_strike(ltp, direction=signal["strike_direction"])
    option_symbol = get_option_symbol(expiry_str, strike, signal["option_type"])
    option_token = get_token_from_cache(client, option_symbol, expiry_str)
    logger.info(f"strike: {strike} | expiry_str: {expiry_str} | option_token: {option_token}")
    if not option_token:
        logger.warning("Token fetch failed.")
        return

    option_df = get_candle_data(client, option_token, interval="FIVE_MINUTE", days_back=1, exchange="NFO")
    if option_df.empty:
        logger.warning("Option candle data unavailable.")
        return

    option_df = enrich_with_indicators(option_df)
    atr = option_df.iloc[-1]['atr']
    if not atr or atr == 0:
        logger.warning("Invalid ATR for option.")
        return

    option_ltp = option_df.iloc[-1]["close"]
    confidence_label = signal.get("confidence", "medium")

    confidence_map = {
        "high": 1.0,
        "medium": 0.7,
        "low": 0.4
    }
    confidence = confidence_map.get(confidence_label.lower(), 0.7)

    stoploss_pct = atr / option_ltp
    quantity = calculate_position_size(option_ltp, confidence=confidence, stoploss_pct=stoploss_pct)

    if quantity == 0:
        logger.warning("Capital too small or risk limit hit.")
        return

    if is_risk_limit_breached():
        logger.warning("Daily risk limit breached.")
        return

    sl = round(option_ltp - atr, 1)
    target = round(option_ltp + 2 * atr, 1)
    if sl <= 5:
        logger.warning("SL is too tight. Skipping trade.")
        return

    logger.info(
        f"[TRADE READY] {signal['option_type']} @ ₹{option_ltp}, Qty: {quantity}, SL: ₹{sl}, Target: ₹{target}, Confidence: {confidence}"
    )

    if used_signals.get(signal["option_type"]):
        logger.info(f"[ENTRY BLOCKED] {signal['option_type']} already used today. Skipping.")
        return

    if DRY_RUN:
        order_manager.place_order(symbol=option_symbol, token=option_token, ltp=option_ltp, atr=atr,
                                  option_type=signal["option_type"], quantity=quantity, sl_price=sl,
                                  target_price=target)
        logger.info("[DRY RUN] Trade not executed.")

    used_signals[signal["option_type"]] = True
    signal_state["used_signals"] = used_signals
    signal_state["last_trade_time"] = datetime.now(IST).strftime("%H:%M:%S")
    signal_state["last_side"] = signal["option_type"]
    save_signal_state(signal_state)


def main_loop():
    logger.info("NIFTY Bot Main Loop Started")
    while True:
        try:
            logger.info("-" * 50)
            logger.info(f"[{datetime.now(IST).strftime('%H:%M:%S')}] Triggering run_bot()")
            run_bot()
            if order_manager and order_manager.open_position:
                logger.info("[EXIT MONITOR] Checking SL/TSL/Target for open position...")
                order_manager.check_exit_conditions()

                # Reload from disk
                state = load_position_state()
                if not state:
                    order_manager.open_position = None
                    logger.info("Position state cleared from disk. Proceeding with new entry.")

            time.sleep(5)
        except Exception as e:
            err_msg = f"Bot Crashed at {datetime.now(IST)}: {str(e)}\n{traceback.format_exc()}"
            logger.exception(err_msg)
        wait_until_next_5_minute_slot()


if __name__ == "__main__":
    main_loop()
