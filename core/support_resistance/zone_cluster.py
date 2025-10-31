"""
Zone Cluster Module
-------------------
Clusters swing highs/lows into support/resistance zones using DBSCAN,
with ATR-based dynamic radius and configurable strength filtering.
"""

from sklearn.cluster import DBSCAN
import pandas as pd


def cluster_zones(
        levels: pd.Series,
        atr_series: pd.Series = None,
        atr_multiplier: float = 1.0,
        min_samples: int = 2,
        require_strong: bool = False
):
    """
    Cluster price levels into S/R zones using DBSCAN, with ATR-based dynamic radius.

    Args:
        levels (pd.Series): Swing highs or lows, indexed by timestamp.
        atr_series (pd.Series): ATR series aligned with levels index (optional).
        atr_multiplier (float): Controls DBSCAN eps = ATR * multiplier.
        min_samples (int): Minimum points to form a cluster.
        require_strong (bool): If True, discard clusters with < 3 touches.

    Returns:
        List[dict]: Each dict contains zone metadata:
            - band: (low, high)
            - touch_count: number of levels in cluster
            - confidence: low / medium / high
            - last_touched: latest timestamp in cluster
            - avg_price: mean of clustered prices
            - span: width of the zone
            - timestamps: list of timestamps in the cluster
    """
    if levels.empty:
        return []

    # Convert price series into shape (n, 1) for clustering
    data = levels.values.reshape(-1, 1)

    # Compute average ATR if available
    if atr_series is not None and not atr_series.dropna().empty:
        aligned_atr = atr_series.reindex(levels.index).bfill().ffill()
        avg_atr = aligned_atr.mean() if not aligned_atr.isna().all() else 20.0
    else:
        avg_atr = 20.0

    eps = round(avg_atr * atr_multiplier, 2)

    # Apply DBSCAN clustering
    model = DBSCAN(eps=eps, min_samples=min_samples)
    labels = model.fit_predict(data)

    zones = []
    for label in set(labels):
        if label == -1:
            continue  # noise

        cluster_points = levels[labels == label]
        if cluster_points.empty:
            continue

        touch_count = len(cluster_points)
        if require_strong and touch_count < 3:
            continue

        zone_low = cluster_points.min()
        zone_high = cluster_points.max()
        last_touched = cluster_points.index[-1]

        confidence = "high" if touch_count >= 3 else "medium"
        zone = {
            "band": (zone_low, zone_high),
            "touch_count": touch_count,
            "confidence": confidence,
            "last_touched": last_touched,
            "avg_price": round(cluster_points.mean(), 2),
            "price": round(cluster_points.mean(), 2),
            "zone_span": round(zone_high - zone_low, 2),
            "timestamps": list(cluster_points.index)
        }
        zones.append(zone)

    # Fallback: return last level as low-confidence zone if no clusters found
    if not zones:
        last_val = levels.iloc[-1]
        zones.append({
            "band": (last_val - 10, last_val + 10),
            "touch_count": 1,
            "subtype": "cluster_fallback",
            "confidence": "low",
            "source": ["fallback"],
            "last_touched": levels.index[-1],
            "avg_price": last_val,
            "price": last_val,
            "zone_span": 20.0,
            "timestamps": [levels.index[-1]]
        })

    return zones

# Example usage:
# atr = df['atr']  # Precomputed ATR series
# hi_zones = cluster_zones(swing_hi['high'], atr)
# lo_zones = cluster_zones(swing_lo['low'], atr)
