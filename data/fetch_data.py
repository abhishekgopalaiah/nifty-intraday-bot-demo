import time

import pandas as pd
from datetime import datetime, timedelta
import pytz

# Set timezone
IST = pytz.timezone('Asia/Kolkata')
from SmartApi.smartConnect import SmartConnect
import pyotp
import numpy as np
import ta

from config.settings import SMART_API_KEY, SMART_API_CLIENT_ID, SMART_API_PIN, SMART_API_TOTP_SECRET
from utils.logger import get_logger

logger = get_logger()


def connect_smartapi():
    """
    Establishes a secure session with SmartAPI and returns the authenticated client.
    """
    try:
        client = SmartConnect(api_key=SMART_API_KEY)
        totp = pyotp.TOTP(SMART_API_TOTP_SECRET).now()
        session = client.generateSession(SMART_API_CLIENT_ID, SMART_API_PIN, totp)
        client.feed_token = client.getfeedToken()
        logger.info("SmartAPI session established.")
        return client
    except Exception as e:
        logger.error(f"Failed to connect to SmartAPI: {e}")
        return None


def get_previous_trading_dates(n=2):
    """
    Returns last n trading days (weekdays only, skips Sat/Sun).
    Optionally, integrate NSE holiday calendar for more accuracy.
    """
    dates = []
    current = datetime.now(IST).date()
    while len(dates) < n:
        current -= timedelta(days=1)
        if current.weekday() < 5:
            dates.append(current)
    return dates[::-1]


def get_date_range_for_candle_fetch(days_back=2.0):
    """
    Returns a valid (from_date, to_date) for candle fetch.
    Handles both integer and fractional days_back values.
    For values < 1 day, returns data for the specified fraction of the current day.
    """
    to_date = datetime.now(IST)
    
    if days_back < 1:
        # For fractional days, calculate hours back from current time
        hours_back = days_back * 24
        from_date = to_date - timedelta(hours=hours_back)
        # Ensure we don't go before market open (9:15 AM) if within the same day
        market_open = to_date.replace(hour=9, minute=15, second=0, microsecond=0)
        if from_date < market_open and from_date.date() == to_date.date():
            from_date = market_open
    else:
        # For 1 or more days, use the existing logic
        trading_days = get_previous_trading_dates(max(1, int(days_back)))
        from_date = datetime.combine(trading_days[0], datetime.min.time()).replace(hour=9, minute=15).astimezone(IST)
    
    return from_date.strftime("%Y-%m-%d %H:%M"), to_date.strftime("%Y-%m-%d %H:%M")


def get_candle_data(client, symbol_token: str, interval: str, days_back: float = 2,
                    exchange: str = "NSE") -> pd.DataFrame:
    """
    Fetches historical candle data (OHLCV) for the given token.

    Args:
        client (SmartConnect): Authenticated SmartAPI client
        symbol_token (str): SmartAPI token for the instrument
        interval (str): Candle interval (e.g., "FIVE_MINUTE")
        days_back (int): Number of days of data to fetch
        exchange (str): Market segment (e.g., "NSE" for stocks/index, "NFO" for options)

    Returns:
        pd.DataFrame: DataFrame with columns [timestamp, open, high, low, close, volume]
    """
    try:
        from_date_str, to_date_str = get_date_range_for_candle_fetch(days_back)
        logger.info(f"[FETCH_DATA] Fetching {interval} data for {symbol_token} from_date: {from_date_str} | to_date: {to_date_str}")

        params = {
            "exchange": exchange,
            "symboltoken": symbol_token,
            "interval": interval,
            "fromdate": from_date_str,
            "todate": to_date_str
        }
        time.sleep(1)
        data = client.getCandleData(params)
        candles = data.get('data', [])

        if not candles:
            logger.warning(f"[FETCH_DATA] No {interval} candle data received from SmartAPI for {symbol_token} from_date: {from_date_str} | to_date: {to_date_str}")
            return pd.DataFrame()

        df = pd.DataFrame(candles, columns=["timestamp", "open", "high", "low", "close", "volume"])
        # Convert to datetime and handle timezone
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        if df['timestamp'].dt.tz is None:
            df['timestamp'] = df['timestamp'].dt.tz_localize('UTC')
        df['timestamp'] = df['timestamp'].dt.tz_convert(IST)
        df = df.sort_values('timestamp').reset_index(drop=True)

        # Ensure numeric types
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        return df

    except Exception as e:
        logger.error(f"[FETCH_DATA] Error fetching candle data: {e}")
        return pd.DataFrame()


def calculate_vwap_session_based(df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes VWAP per trading session (reset daily at 9:15 AM).
    Returns updated DataFrame with 'vwap' column.
    """
    if df.empty:
        return df

    df['date'] = df['timestamp'].dt.date
    df['typical_price'] = (df['high'] + df['low'] + df['close']) / 3
    df['tp_volume'] = df['typical_price'] * df['volume']

    df['cum_tp_vol'] = df.groupby('date')['tp_volume'].cumsum()
    df['cum_vol'] = df.groupby('date')['volume'].cumsum()

    df['vwap'] = df['cum_tp_vol'] / df['cum_vol']

    # Cleanup
    df.drop(columns=['date', 'typical_price', 'tp_volume', 'cum_tp_vol', 'cum_vol'], inplace=True)
    return df


def enrich_with_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Enriches a DataFrame with technical indicators using the `ta` library.

    Indicators added:
    - RSI (14-period)
    - EMA 9 & 21
    - VWAP (14-period rolling approximation)
    - MACD diff (histogram)
    - ADX (14-period)
    - ATR (14-period)
    - 10-period average volume

    Returns:
        pd.DataFrame: DataFrame with additional indicator columns
    """
    if df.empty:
        logger.warning("Empty DataFrame passed to enrich_with_indicators.")
        return df

    try:
        # Ensure numeric columns are float
        df = df.astype({"open": float, "high": float, "low": float, "close": float, "volume": float})
        # RSI
        df["rsi"] = ta.momentum.RSIIndicator(close=df["close"], window=14).rsi()
        # EMA
        df["ema9"] = df["close"].ewm(span=9, adjust=False).mean()
        df["ema21"] = df["close"].ewm(span=21, adjust=False).mean()

        # MACD (histogram)
        df["macd"] = ta.trend.macd_diff(df["close"])

        # ADX
        df["adx"] = ta.trend.ADXIndicator(high=df["high"], low=df["low"], close=df["close"], window=14).adx()

        # ATR
        df["atr"] = ta.volatility.AverageTrueRange(
            high=df["high"], low=df["low"], close=df["close"], window=14
        ).average_true_range()
        # Avg volume
        df["avg_vol"] = df["volume"].rolling(window=10).mean()

        # # VWAP (rolling approximation — not reset daily)
        # df["vwap"] = ta.volume.volume_weighted_average_price(
        #     high=df["high"], low=df["low"], close=df["close"], volume=df["volume"], window=14
        # )
        df = calculate_vwap_session_based(df)

        # Drop only rows where ALL indicators are missing (not just one)
        indicator_cols = ["rsi", "ema9", "ema21", "vwap", "macd", "adx", "atr"]
        # df[indicator_cols] = df[indicator_cols].fillna(method='NA')
        df = df.dropna(subset=indicator_cols, how="all")

        # Optional: log how many rows survived
        logger.info(f"[FETCH_DATA] Final enriched DataFrame rows: {len(df)}")

        return df.reset_index(drop=True)

    except Exception as e:
        logger.error(f"[FETCH_DATA] Error enriching indicators: {e}")
        return df

# from data.fetch_data import connect_smartapi, get_candle_data, enrich_with_indicators

# client = connect_smartapi()
# df = get_candle_data(client, symbol_token="99926000", interval="FIVE_MINUTE")  # Replace with actual token
# # df = enrich_with_indicators(df)
# #
# print(df.tail())
