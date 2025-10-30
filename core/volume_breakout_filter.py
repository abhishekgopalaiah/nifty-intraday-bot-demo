# core/volume_breakout_filter.py

"""
Volume-Based Breakout Filter — NIFTY Futures (Quant Grade)

This module checks if the current breakout (CE/PE) has supporting volume from the NIFTY Futures chart.
It avoids fake breakouts where price breaks a level but there's no real demand/supply.

Logic:
- Fetch last N candles of NIFTY FUTURES (5-min)
- Compute average volume of prior candles
- Confirm latest volume is >= avg × multiplier

Author: Abhishek G
"""

from datetime import datetime, timedelta
from data.fetch_data import get_candle_data
from config.settings import FUTURE_SYMBOL_TOKEN
from utils.logger import get_logger

logger = get_logger()

def is_fut_volume_breakout(
    exchange: str = "NSE",
    interval: str = "FIVE_MINUTE",
    lookback: int = 5,
    volume_multiplier: float = 1.5
) -> bool:
    """
    Checks whether NIFTY Futures shows a volume-supported breakout.

    Returns:
        bool: True if volume confirms breakout, else False.
    """
    try:
        to_date = datetime.now()
        from_date = to_date - timedelta(minutes=lookback * 5)

        fut_df = get_candle_data(
            client=None,  # handled inside fetch_data
            symbol_token=FUTURE_SYMBOL_TOKEN,
            interval=interval,
            days_back=1,
            exchange=exchange
        )

        if fut_df.empty or len(fut_df) < lookback:
            logger.warning("[FUTURE VOLUME] Not enough data.")
            return False

        latest_vol = fut_df.iloc[-1]["volume"]
        avg_vol = fut_df.iloc[-(lookback+1):-1]["volume"].mean()

        logger.debug(f"[FUTURE VOLUME] Latest: {latest_vol}, Avg: {avg_vol:.1f}")

        if latest_vol >= volume_multiplier * avg_vol:
            logger.info("[FUTURE VOLUME] Breakout confirmed with volume.")
            return True
        else:
            logger.info("[FUTURE VOLUME] No volume support. Skipping.")
            return False

    except Exception as e:
        logger.error(f"[FUTURE VOLUME ERROR] {e}")
        return False
