"""
Option Volume Filter — NIFTY Intraday Options Bot (Quant Grade)

This module validates whether a given option (CE/PE) has sufficient trading interest
based on recent volume data. It is used to confirm signal quality before execution.

Supports two modes:
1. Using a SmartAPI symbol token (fetches data via API)
2. Using pre-fetched option_df (avoids duplicate API calls)

Author: Abhishek G
"""

from datetime import datetime, timedelta
import pandas as pd
from data.fetch_data import get_candle_data
from utils.logger import get_logger

logger = get_logger()


def volume_confirmation_passed_token(
        symbol_token: str,
        exchange: str = "NFO",
        interval: str = "FIVE_MINUTE",
        lookback: int = 5,
        volume_multiplier: float = 1.5,
) -> bool:
    """
    Fetches option data via token and confirms if volume exceeds threshold.

    Args:
        symbol_token (str): Option token from SmartAPI.
        exchange (str): Exchange (default NFO).
        interval (str): Candle interval (default 5min).
        lookback (int): Number of candles for average volume.
        volume_multiplier (float): Threshold multiple.

    Returns:
        bool: True if volume spike confirmed.
    """
    try:
        to_date = datetime.now()
        from_date = to_date - timedelta(minutes=lookback * 5)

        historic_param = {
            "exchange": exchange,
            "symboltoken": symbol_token,
            "interval": interval,
            "fromdate": from_date.strftime("%Y-%m-%d %H:%M"),
            "todate": to_date.strftime("%Y-%m-%d %H:%M"),
        }

        candles = get_candle_data(historic_param)

        if not candles or len(candles) < lookback:
            logger.warning(f"[VOLUME FILTER] Not enough candles for {symbol_token}")
            return False

        volumes = [candle[5] for candle in candles[-lookback:]]
        latest_vol = volumes[-1]
        avg_vol = sum(volumes[:-1]) / max(1, len(volumes) - 1)

        logger.debug(f"[VOLUME TOKEN] {symbol_token} | Latest: {latest_vol}, Avg: {avg_vol:.1f}")

        if latest_vol >= volume_multiplier * avg_vol:
            logger.info(f"[VOLUME PASS] {symbol_token} | Volume spike confirmed")
            return True
        else:
            logger.info(f"[VOLUME FAIL] {symbol_token} | Volume below threshold")
            return False

    except Exception as e:
        logger.error(f"[VOLUME ERROR — TOKEN] {e}")
        return False


def volume_confirmation_passed_df(
        option_df: pd.DataFrame,
        lookback: int = 5,
        volume_multiplier: float = 1.5,
        min_abs_volume=1000
) -> bool:
    """
    Validates volume using existing option_df.

    Args:
        min_abs_volume:
        option_df (pd.DataFrame): Option candle data with 'volume'.
        lookback (int): Number of candles to average.
        volume_multiplier (float): Required spike over average.

    Returns:
        bool: True if volume confirmation passed.
    """
    try:
        recent_df = option_df.tail(lookback)
        latest_vol = recent_df.iloc[-1]["volume"]
        avg_vol = recent_df.iloc[:-1]["volume"].clip(upper=5000).mean()  # Any volume higher than 5000 will be treated
        # as 5000

        logger.debug(f"[VOLUME DF] Latest: {latest_vol}, Avg: {avg_vol:.1f}")

        # Hard floor: ensure minimum liquidity
        if latest_vol < min_abs_volume:
            logger.info(f"[VOLUME DF FAIL] Latest volume {latest_vol} below minimum {min_abs_volume}")
            return False

        # Spike logic
        if latest_vol >= volume_multiplier * avg_vol:
            logger.info("[VOLUME DF PASS] Volume spike confirmed")
            return True

        # Soft fallback: allow if absolute volume is healthy
        if latest_vol >= 2000 and avg_vol >= 2000:
            logger.info("[VOLUME DF PASS] Acceptable liquidity without spike")
            return True

        logger.info("[VOLUME DF FAIL] Volume not sufficient")
        return False

    except Exception as e:
        logger.error(f"[VOLUME ERROR — DF] {e}")
        return False


def is_fut_volume_breakout(symbol_token, client, lookback=5, multiplier=1.5, min_abs_volume=1000):
    """
    Confirms volume breakout on NIFTY futures with improved logic.
    - Allows fallback on decent absolute volume
    - Caps average to avoid distortion from outliers
    """
    try:
        df = get_candle_data(client, symbol_token, interval="FIVE_MINUTE", days_back=1, exchange="NFO")
        if df.empty or len(df) < lookback + 1:
            logger.warning("Not enough candles for volume check on futures.")
            return False

        recent = df.tail(lookback + 1)
        latest_vol = recent.iloc[-1]['volume']
        avg_vol = recent.iloc[:-1]['volume'].clip(upper=8000).mean()

        logger.info(f"[FUT VOL] Avg: {avg_vol:.1f}, Latest: {latest_vol}")

        # 1. Absolute floor
        if latest_vol < min_abs_volume:
            logger.info(f"[FUT VOL FAIL] Latest volume {latest_vol} below minimum {min_abs_volume}")
            return False

        # 2. Spike logic
        if latest_vol >= multiplier * avg_vol:
            logger.info("[FUT VOL PASS] Spike confirmed")
            return True

        # 3. Fallback on steady volume
        if latest_vol >= 1000 and avg_vol >= 1000:  # change to 2000 retest
            logger.info("[FUT VOL PASS] No spike but sufficient liquidity")
            return True

        logger.info("[FUT VOL FAIL] No spike and volume insufficient")
        return False

    except Exception as e:
        logger.error(f"[FUT VOL ERROR] {e}")
        return False
