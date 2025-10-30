import pandas as pd


def get_prev_day_ohlc_zones(df: pd.DataFrame):
    """
    Extract previous day's high, low, and close as fallback S/R zones.

    Args:
        df (pd.DataFrame): Must contain 'timestamp', 'high', 'low', 'close'

    Returns:
        List of zone dicts: Each with band, type, source, confidence, etc.
    """
    df = df.copy()
    df['date'] = df['timestamp'].dt.date
    unique_days = sorted(df['date'].unique())

    if len(unique_days) < 2:
        return []  # not enough history

    prev_day = unique_days[-2]
    prev_data = df[df['date'] == prev_day]

    zones = []
    for label, price in [('prev_high', prev_data['high'].max()),
                         ('prev_low', prev_data['low'].min()),
                         ('prev_close', prev_data['close'].iloc[-1])]:
        band = (price - 5, price + 5)
        midpoint = round((band[0] + band[1]) / 2, 2)

        zones.append({
            "type": "resistance" if label == 'prev_high' else "support",
            "band": band,
            "price": midpoint,
            "zone_span": band[1] - band[0],
            "touch_count": 0,
            "confidence": "low",
            "sources": [label],
            "subtype": "fallback",
            "volume_cluster": False,
            "vwap_zone": False,
            "timeframes": [],
            "last_touched": pd.to_datetime(prev_data['timestamp'].iloc[-1]),
            "flipped": False  # will be evaluated later
        })

    return zones


# Example:
# df = pd.read_csv("nifty_fut_5m.csv", parse_dates=['timestamp'])
# fallback_zones = get_prev_day_ohlc_zones(df)
