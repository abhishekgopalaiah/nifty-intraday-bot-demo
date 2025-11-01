import pandas as pd
from core.signal_engine import generate_trade_signal
from core.risk_manager import calculate_position_size
from core.strike_selector import round_to_nearest_strike, get_option_symbol
from core.support_resistance.zone_multiframe import build_zones_multi_tf
from utils.expiry_utils import get_weekly_expiry_str
from utils.logger import get_logger
from data.fetch_data import enrich_with_indicators

logger = get_logger()


def estimated_option_premium(ltp, strike, option_type):
    moneyness = abs(strike - ltp) / ltp
    base = ltp * 0.005
    adjustment = max(1 - moneyness * 4, 0.5)
    return round(max(base * adjustment, 25), 1)


def load_csv_multi_tf(base_path: str, symbol: str) -> dict:
    """Loads 5m, 15m, 1h candles for spot or futures from CSVs"""
    return {
        '5m': pd.read_csv(f"{base_path}/{symbol}_5m.csv", parse_dates=['timestamp']),
        '15m': pd.read_csv(f"{base_path}/{symbol}_15m.csv", parse_dates=['timestamp']),
        '1h': pd.read_csv(f"{base_path}/{symbol}_1h.csv", parse_dates=['timestamp'])
    }


def run_backtest(base_path: str) -> pd.DataFrame:
    spot_dict = load_csv_multi_tf(base_path, "nifty_spot")

    spot_dict['5m'] = enrich_with_indicators(spot_dict['5m'])
    index_df = spot_dict['5m']
    trades = []
    position = None
    used_signals = {"CE": False, "PE": False}
    missed_trades = []
    prev_day = None

    for i in range(75, len(index_df)):
        df_slice = index_df.iloc[:i + 1].copy()
        latest = df_slice.iloc[-1]
        today = latest['timestamp'].date()
        timestamp = latest['timestamp']
        ltp = latest['close']
        logger.info("=" * 60)
        logger.info(f"[BACKTEST CANDLE START] Processing candle at {timestamp} | LTP: {ltp}")

        if today != prev_day:
            used_signals = {"CE": False, "PE": False}
            prev_day = today

        if position is None:
            # Slice multi-timeframe data
            spot_data = {
                '5m': df_slice,
                '15m': spot_dict['15m'][spot_dict['15m']['timestamp'] <= timestamp],
                '1h': spot_dict['1h'][spot_dict['1h']['timestamp'] <= timestamp]
            }

            zones = build_zones_multi_tf(spot_data)
            logger.info(f"-----------------------zones: {zones} ----------------------")
            if not zones:
                continue

            signal = generate_trade_signal(df_slice, df_slice, zones, signal_flags=used_signals)
            if not signal:
                continue

            # Filter based on entry_score threshold
            if signal.get("entry_score", 0) < 0.3:
                missed_trades.append({
                    "time": timestamp,
                    "option_type": signal["option_type"],
                    "reason": f"EntryScore < threshold | {signal.get('entry_reasons', {})}"
                })
                continue

            strike = round_to_nearest_strike(ltp, direction=signal["strike_direction"])
            expiry = get_weekly_expiry_str()
            symbol = get_option_symbol(expiry, strike, signal["option_type"])

            premium = estimated_option_premium(ltp, strike, signal["option_type"])
            confidence = signal.get("confidence", 1.0)

            confidence_map = {
                "high": 1.0,
                "medium": 0.7,
                "low": 0.4
            }
            confidence = confidence_map.get(confidence.lower(), 0.7)

            qty = calculate_position_size(premium, confidence=confidence)
            if qty == 0:
                continue

            atr = latest['atr']
            sl = round(premium - atr, 1)
            target = round(premium + 2 * atr, 1)

            position = {
                "type": signal["option_type"],
                "entry_price": premium,
                "sl": sl,
                "target": target,
                "entry_time": timestamp,
                "symbol": symbol,
                "qty": qty,
            }

            used_signals[signal["option_type"]] = True
            logger.info(f"[ENTRY] {timestamp} | Signal: {signal['option_type']} | Premium: {premium}")

        else:
            # Exit condition checks
            if latest['low'] <= position['sl']:
                exit_price = position['sl']
                reason = "SL Hit"
            elif latest['high'] >= position['target']:
                exit_price = position['target']
                reason = "Target Hit"
            elif i == len(index_df) - 1:
                exit_price = ltp
                reason = "EOD Exit"
            else:
                continue

            pnl = (exit_price - position["entry_price"]) * position["qty"]

            trades.append({
                "entry_time": position["entry_time"],
                "exit_time": timestamp,
                "symbol": position["symbol"],
                "type": position["type"],
                "entry_price": position["entry_price"],
                "exit_price": exit_price,
                "qty": position["qty"],
                "pnl": round(pnl, 2),
                "reason": reason,
            })

            position = None

    if missed_trades:
        pd.DataFrame(missed_trades).to_csv("missed_signals.csv", index=False)

    return pd.DataFrame(trades)
