import pandas as pd
from utils.logger import get_logger

logger = get_logger('swing_detector')


def detect_swings(df: pd.DataFrame, window: int = 3, volume_filter: bool = False, method: str = "strict") -> tuple[
    pd.DataFrame, pd.DataFrame]:
    """
    Detect swing highs and lows using either strict (== rolling) or flexible (> neighbors) method.

    Args:
        df (pd.DataFrame): Input OHLCV dataframe.
        window (int): Rolling window size for swing detection.
        volume_filter (bool): Whether to filter swings by above-average volume.
        method (str): "strict" for exact max/min; "flex" for peak > neighbors.

    Returns:
        swing_highs (pd.DataFrame), swing_lows (pd.DataFrame)
    """
    df = df.copy()
    df['rolling_high'] = df['high'].rolling(window=window, center=True).max()
    df['rolling_low'] = df['low'].rolling(window=window, center=True).min()
    if method == "strict":
        swing_highs = df[df['high'] == df['rolling_high']]
        swing_lows = df[df['low'] == df['rolling_low']]

    elif method == "flex":
        swing_highs = df[
            (df['high'] > df['rolling_high'].shift(1)) &
            (df['high'] > df['rolling_high'].shift(-1))
            ]
        swing_lows = df[
            (df['low'] < df['rolling_low'].shift(1)) &
            (df['low'] < df['rolling_low'].shift(-1))
            ]

    else:
        raise ValueError("method must be 'strict' or 'flex'")

    if volume_filter and 'volume' in df.columns:
        avg_vol = df['volume'].mean()
        swing_highs = swing_highs[swing_highs['volume'] > avg_vol]
        swing_lows = swing_lows[swing_lows['volume'] > avg_vol]

    return swing_highs, swing_lows


"""
Swing Detector Module
---------------------
Detects meaningful swing highs and lows using structural reversal shapes
confirmed by future price movement and volatility (ATR-based threshold).
Supports optional volume filtering and metadata tagging.
"""


def detect_reversal_swings(df, atr_window=14, atr_multiplier=1.2, lookback=5, volume_filter=False):
    """
    Detect swing highs and lows using structure + ATR + future confirmation.

    Args:
        df (pd.DataFrame): Input data with columns: ['high', 'low', 'close', 'timestamp', 'volume']
        atr_window (int): ATR period for volatility estimation
        atr_multiplier (float): Minimum move size relative to ATR
        lookback (int): Window before/after for structure confirmation
        volume_filter (bool): If True, ignore low-volume swings

    Returns:
        swing_hi_df (pd.DataFrame), swing_lo_df (pd.DataFrame)
    """
    df = df.copy()

    if 'timestamp' not in df.columns:
        df = df.reset_index()

    # Calculate True Range and ATR
    df['tr'] = df[['high', 'low', 'close']].apply(
        lambda row: max(
            row['high'] - row['low'],
            abs(row['high'] - row['close']),
            abs(row['low'] - row['close'])
        ), axis=1
    )
    df['atr'] = df['tr'].rolling(atr_window).mean()

    swing_highs, swing_lows = [], []
    avg_volume = df['volume'].mean() if volume_filter and 'volume' in df.columns else None

    for i in range(lookback, len(df) - lookback):
        window = df.iloc[i - lookback:i + lookback + 1]
        current = df.iloc[i].copy()  # already the center of window

        DEFAULT_ATR = 20.0
        atr = current['atr']
        if pd.isna(atr) or atr <= 0:
            logger.debug(f"[SWING] Invalid ATR at {df['timestamp'].iloc[i]}, using fallback={DEFAULT_ATR}")
            atr = DEFAULT_ATR

        threshold = atr * atr_multiplier

        # Volume filter (if enabled)
        if volume_filter and current.get('volume', 0) < avg_volume:
            continue

        # Detect Swing High
        if current['high'] == window['high'].max():
            future_lows = df['low'].iloc[i + 1:i + lookback + 1]
            if future_lows.empty:
                continue

            if (current['high'] - future_lows.min()) >= threshold:
                current['strength'] = current['high'] - future_lows.min()
                current['atr_at_swing'] = atr
                swing_highs.append(current)

        # Detect Swing Low
        if current['low'] == window['low'].min():
            future_highs = df.iloc[i + 1:i + lookback + 1]['high']
            if (future_highs.max() - current['low']) >= threshold:
                current['strength'] = future_highs.max() - current['low']
                current['atr_at_swing'] = atr
                swing_lows.append(current)

    swing_hi_df = pd.DataFrame(swing_highs)
    swing_lo_df = pd.DataFrame(swing_lows)

    if not swing_hi_df.empty and 'timestamp' in swing_hi_df.columns:
        swing_hi_df['timestamp'] = pd.to_datetime(swing_hi_df['timestamp'])
    if not swing_lo_df.empty and 'timestamp' in swing_lo_df.columns:
        swing_lo_df['timestamp'] = pd.to_datetime(swing_lo_df['timestamp'])
    return swing_hi_df, swing_lo_df

# Example usage:
# df = pd.read_csv("nifty_fut_5m.csv", parse_dates=['timestamp'])
# hi, lo = detect_reversal_swings(df)
# print(hi[['timestamp', 'high']])
# print(lo[['timestamp', 'low']])

# df = pd.read_csv("../../backtest/sample_data/nifty_spot_5m.csv", parse_dates=['timestamp'])
# swing_hi, swing_lo = detect_swings(df, method="strict", volume_filter=False)
# print(f"swing hi : {swing_hi}")
# print(f"swing lo : {swing_lo}")
# swing_hi.to_csv("swing_highs.csv")
# swing_lo.to_csv("swing_lows.csv")
