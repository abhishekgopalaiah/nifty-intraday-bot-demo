
import pandas as pd

def calculate_bollinger_width(df: pd.DataFrame, window: int = 20) -> pd.Series:
    """
    Calculate Bollinger Band Width as a percentage of the middle band.
    """
    mid = df['close'].rolling(window).mean()
    std = df['close'].rolling(window).std()
    upper = mid + 2 * std
    lower = mid - 2 * std
    width = (upper - lower) / mid
    return width


def calculate_atr_percentile(df: pd.DataFrame, atr_column: str = 'atr', window: int = 60) -> pd.Series:
    """
    Calculate ATR percentile rank over a rolling window.
    """
    def rank_pct(series):
        return pd.Series(series).rank(pct=True).iloc[-1]

    return df[atr_column].rolling(window).apply(rank_pct, raw=False)


def get_volatility_regime(latest_atr_pct: float, bb_width: float) -> str:
    """
    Classify volatility regime based on ATR percentile and Bollinger width.
    """
    if latest_atr_pct > 0.8 or bb_width > 0.04:
        return "HighVol"
    elif latest_atr_pct < 0.3 and bb_width < 0.015:
        return "LowVol"
    else:
        return "Normal"
