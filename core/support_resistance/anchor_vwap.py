import pandas as pd


import pandas as pd

def get_vwap_zones(df: pd.DataFrame, buffer: float = 0.005):
    """
    Build a VWAP zone around the actual VWAP (volume-weighted average price) from today's intraday data.

    Args:
        df (pd.DataFrame): Futures OHLCV DataFrame for today only
        buffer (float): Percent buffer around VWAP (e.g., 0.005 = ±0.5%)

    Returns:
        List of (low, high) tuples representing the VWAP zone
    """
    df = df.copy()
    if 'volume' not in df.columns or df['volume'].sum() == 0:
        return []

    # VWAP calculation (true volume-weighted mean price)
    df['vwap'] = (df['close'] * df['volume']).cumsum() / df['volume'].cumsum()
    vwap_value = df['vwap'].iloc[-1]

    # Build zone around VWAP
    zone_low = round(vwap_value * (1 - buffer), 2)
    zone_high = round(vwap_value * (1 + buffer), 2)

    return [(zone_low, zone_high)]



# Example:
# zones = get_vwap_zones(futures_df, anchor_point='first_15min_high')
