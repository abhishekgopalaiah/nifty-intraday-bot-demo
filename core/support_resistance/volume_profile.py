import pandas as pd

import numpy as np
import pandas as pd


def get_volume_profile_zones(df: pd.DataFrame, atr: float = 20.0, default_bin_width: float = 10.0):
    """
    Compute volume profile zones using dynamic bin width and embed total volume for scoring.

    Args:
        df (pd.DataFrame): Futures dataframe with 'close' and 'volume'
        atr (float): ATR to scale bin width (optional, fallback to default)
        default_bin_width (float): Used if ATR is missing

    Returns:
        List[dict]: Volume-based zones with price band, midpoint, and volume weight
    """
    df = df.copy()
    if 'close' not in df or 'volume' not in df:
        return []

    bin_width = max(atr / 2, default_bin_width)

    price_min = df['close'].min()
    price_max = df['close'].max()
    bins = np.arange(price_min, price_max + bin_width, bin_width)

    df['price_bin'] = pd.cut(df['close'], bins=bins)
    vol_by_price = df.groupby('price_bin', observed=False)['volume'].sum().sort_values(ascending=False)

    zones = []
    for bin_range, vol in vol_by_price.head(3).items():
        low = float(bin_range.left)
        high = float(bin_range.right)
        midpoint = round((low + high) / 2, 2)

        zones.append({
            "type": "vp_zone",
            "band": (low, high),
            "price": midpoint,
            "total_volume": int(vol),  # ✅ added for scoring
            "touch_count": 0,
            "volume_cluster": True,
            "vwap_zone": False,
            "confidence": "medium",
            "sources": ["volume"],
            "timeframes": [],
            "zone_span": high - low,
            "last_touched": df['timestamp'].iloc[-1],
            "subtype": "vp_zone"
        })

    return zones

# Example:
# zones = get_volume_profile_zones(fut_df, default_bin_width=25)
