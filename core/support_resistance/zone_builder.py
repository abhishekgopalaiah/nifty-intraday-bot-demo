"""
Zone Builder Module
-------------------
Constructs dynamic support and resistance zones using multiple techniques:
- Reversal swing detection
- Volume profile clustering
- VWAP-based zones
- Gap up/down logic
- Previous day OHLC fallback zones

Includes scoring, flip tagging, recency weighting, and volume confluence.
"""

from datetime import datetime, timedelta, time

import pandas as pd

from .swing_detector import detect_reversal_swings
from .zone_cluster import cluster_zones
from .volume_profile import get_volume_profile_zones
from .zone_filter import filter_and_validate_zones, log_final_zones
from .zone_scorer import score_zones
from .anchor_vwap import get_vwap_zones
from .zone_fallback import get_prev_day_ohlc_zones
from utils.logger import get_logger

logger = get_logger("zone_builder")


def zones_overlap(b1, b2, buffer=5):
    """Check whether two price bands overlap within a given buffer."""
    return not (b1[1] < b2[0] - buffer or b1[0] > b2[1] + buffer)


def merge_volume_into_swing_zones(swing_zones, volume_zones, overlap_buffer=5):
    """Merge volume zones into swing zones if they overlap within a buffer."""
    merged = []
    for sz in swing_zones:
        matched = False
        for vz in volume_zones:
            if zones_overlap(sz['band'], vz['band'], overlap_buffer):
                sz['volume_cluster'] = True
                sz['sources'] = list(set(sz.get('sources', []) + ['swing', 'volume']))
                sz['subtype'] = 'swing_volume'

                # Copy total_volume from volume zone to swing zone (for scoring)
                if 'total_volume' in vz:
                    sz['total_volume'] = vz['total_volume']

                matched = True
                break
        if not matched:
            sz['sources'] = list(set(sz.get('sources', []) + ['swing']))
            sz['subtype'] = 'swing'  # Unmatched swing zones
        merged.append(sz)

    # Add unmatched volume-only zones (retain total_volume)
    unmatched_volume = [
        z for z in volume_zones
        if all(not zones_overlap(z['band'], sz['band'], overlap_buffer) for sz in swing_zones)
    ]
    for vz in unmatched_volume:
        vz['sources'] = ['volume']
        vz['subtype'] = 'vp_zone'  # Explicit tagging
        vz['volume_cluster'] = True  # Ensure flag consistency
    return merged + unmatched_volume


def detect_flip_zones(zones, df, flip_window=30, flip_margin_ratio=0.25):
    """
    Tag zones that flipped from support to resistance or vice versa based on recent price retests.

    Args:
        zones (list): List of zone dicts with 'band' and 'type'
        df (pd.DataFrame): Price data with 'timestamp' and 'close'
        flip_window (int): Number of minutes to look back
        flip_margin_ratio (float): Fraction of zone height to consider as retest range

    Returns:
        List[dict]: Zones with 'flipped', 'subtype', and optional 'flipped_from'
    """

    price_series = df.set_index("timestamp")['close']
    recent_start = price_series.index[-1] - pd.Timedelta(minutes=flip_window)
    recent = price_series.loc[price_series.index >= recent_start]

    for z in zones:
        low, high = z['band']
        zone_type = z.get('type', '')
        flip_margin = max(2.0, (high - low) * flip_margin_ratio)

        if zone_type == 'resistance':
            if any((recent < high) & (recent > high - flip_margin)):
                z['flipped'] = True
                z['subtype'] = 'retest'
                z['flipped_from'] = 'resistance'
                logger.debug(f"[FLIP] Resistance zone flipped to retest: band={z['band']}")
            else:
                z['flipped'] = False
                z['subtype'] = 'primary'

        elif zone_type == 'support':
            if any((recent > low) & (recent < low + flip_margin)):
                z['flipped'] = True
                z['subtype'] = 'retest'
                z['flipped_from'] = 'support'
                logger.debug(f"[FLIP] Support zone flipped to retest: band={z['band']}")
            else:
                z['flipped'] = False
                z['subtype'] = 'primary'

        else:
            z['flipped'] = False
            z['subtype'] = 'primary'

    return zones


def detect_gap_zone(df, mean_atr, tf_label):
    """Detect and return a gap-up or gap-down zone if recent gap is significant and unfilled."""
    try:
        df_sorted = df.sort_values("timestamp")
        today = df_sorted['timestamp'].iloc[-1].date()
        yesterday = today - timedelta(days=1)

        today_df = df_sorted[df_sorted['timestamp'].dt.date == today]
        yest_df = df_sorted[df_sorted['timestamp'].dt.date == yesterday]

        if not today_df.empty and not yest_df.empty:
            y_close = yest_df['close'].iloc[-1]
            t_open = today_df['open'].iloc[0]
            gap_pct = abs(t_open - y_close) / y_close * 100

            if gap_pct > 0.3:
                gap_type = 'support' if t_open > y_close else 'resistance'
                gap_band = [y_close - mean_atr, y_close + mean_atr]

                filled = (today_df.head(5)['low'].min() < y_close) if gap_type == 'support' \
                    else (today_df.head(5)['high'].max() > y_close)

                if not filled:
                    return [{
                        "type": gap_type,
                        "price": y_close,
                        "band": gap_band,
                        "touch_count": 0,
                        "sources": ["gap"],
                        "subtype": "gap",
                        "timeframes": [tf_label],
                        "last_touched": df['timestamp'].iloc[-1],
                        "zone_span": gap_band[1] - gap_band[0],
                        "confidence": "medium",
                        "volume_cluster": False,
                        "vwap_zone": False,
                        "flipped": False
                    }]
    except Exception as e:
        logger.warning(f"[ZONE BUILDER] Gap detection failed: {e}")

    return []


def get_zone_status(zone_band, price):
    """Classify price-zone relationship as inside, testing, rejected, untouched."""
    low, high = zone_band
    if low <= price <= high:
        return "inside"
    elif abs(price - low) <= 0.1 * (high - low) or abs(price - high) <= 0.1 * (high - low):
        return "testing"
    elif price > high:
        return "rejected"
    else:
        return "untouched"


def enrich_zone_metadata(zones, current_price, df=None, now=None):
    """Add age and live status metadata to each zone."""
    now = now or (df['timestamp'].iloc[-1] if df is not None else pd.Timestamp.utcnow())
    now = pd.Timestamp(now)  # ensures .time() works

    for z in zones:
        last_touched = z.get("last_touched")
        if last_touched:
            age_minutes = (now - pd.Timestamp(last_touched)).total_seconds() / 60
            # 🛠️ Reset age if zone is from yesterday and we're early today
            zone_is_yesterday = pd.Timestamp(last_touched).date() < now.date()

            early_session = now.time() < time(11, 0)

            if early_session and zone_is_yesterday:
                age_minutes = min(age_minutes, 60)

            z['zone_age_minutes'] = round(age_minutes, 2)
        else:
            z['zone_age_minutes'] = None

        z['zone_status'] = get_zone_status(z['band'], current_price)

    return zones


def get_active_zones(df, fut_df=None, include_vwap=True, tf_label="5m"):
    """
    Builds active S/R zones from swings, volume profile, VWAP anchors, gaps, and fallback.

    Parameters:
        df (pd.DataFrame): Spot/index candle data
        fut_df (pd.DataFrame): Futures candle data (optional)
        include_vwap (bool): Whether to include VWAP zones
        tf_label (str): Timeframe label
        vwap_anchor (str): Anchor point for VWAP zone ('open', 'first_15min_high', etc.)

    Returns:
        List[dict]: List of enriched zone dictionaries
    """
    flip_window_map = {
        "5m": 30,  # 6 bars
        "15m": 60,  # 4 bars
        "1h": 120  # 2 bars
    }
    flip_window = flip_window_map.get(tf_label, 30)  # default fallback
    current_price = df['close'].iloc[-1]
    df = df.copy()
    fut_df = fut_df.copy() if fut_df is not None else None

    logger.debug(
        f"[ZONE BUILDER] Building zones for {tf_label}, last candle: {df['timestamp'].iloc[-1]} , current_price : {current_price}")

    # ATR Calculation
    df['tr'] = df['high'] - df['low']
    df['atr'] = df['tr'].rolling(14).mean()
    mean_atr = df['atr'].mean() if df['atr'].mean() > 0 else 20.0

    # Swing Detection and Clustering
    swing_hi, swing_lo = detect_reversal_swings(df, 14, 0.4, 3)

    logger.debug(f"[SWING] TF={tf_label} | Highs={len(swing_hi)} | Lows={len(swing_lo)}")

    if swing_hi.empty or swing_lo.empty:
        logger.warning(f"[ZONE BUILDER] No swings found in {tf_label} timeframe.")
        return []

    swing_hi = swing_hi.set_index('timestamp')
    swing_lo = swing_lo.set_index('timestamp')
    atr_series = df.set_index("timestamp")["atr"]
    support_zones = cluster_zones(swing_lo['low'], atr_series=atr_series)
    resistance_zones = cluster_zones(swing_hi['high'], atr_series=atr_series)

    zones = (
            [{"type": "support", **z, "timeframes": [tf_label], "subtype": "cluster", "sources": ["swing"]} for z in
             support_zones] +
            [{"type": "resistance", **z, "timeframes": [tf_label], "subtype": "cluster", "sources": ["swing"]} for z in
             resistance_zones]
    )

    # Volume Profile Zones
    volume_zones = []
    now = df['timestamp'].iloc[-1]
    now = pd.Timestamp(now)
    current_time = now.time()
    today = now.date()
    if fut_df is None or 'timestamp' not in fut_df.columns:
        fut_slice = pd.DataFrame()
    else:
        if current_time >= datetime.strptime("12:00", "%H:%M").time():
            fut_slice = fut_df[fut_df['timestamp'].dt.date == today]
        else:
            prev_day = today - timedelta(days=1)
            fut_slice = fut_df[fut_df['timestamp'].dt.date == prev_day]

    logger.debug(f"[VWAP] Futures slice for volume zones: rows={len(fut_slice)}")
    if not fut_slice.empty:
        volume_zones = get_volume_profile_zones(fut_slice)

    zones = merge_volume_into_swing_zones(zones, volume_zones)

    # VWAP Zones
    if include_vwap:
        vwap_df = fut_df if fut_df is not None and not fut_df.empty else df
        vwap_today = vwap_df[vwap_df['timestamp'].dt.date == df['timestamp'].iloc[-1].date()]
        for band in get_vwap_zones(vwap_today):
            low, high = float(band[0]), float(band[1])
            midpoint = round((low + high) / 2, 2)

            zones.append({
                "type": "vwap",
                "band": (low, high),
                "price": midpoint,  # required for scoring
                "touch_count": 0,
                "volume_cluster": False,
                "vwap_zone": True,
                "sources": ["vwap"],
                "timeframes": [tf_label],
                "last_touched": df['timestamp'].iloc[-1],
                "subtype": "vwap_zone",
                "zone_span": round(high - low, 2),
                "confidence": "medium",
            })

    # Gap Zones
    zones += detect_gap_zone(df, mean_atr, tf_label)

    # Fallback Zones
    fallback_source_df = fut_df if fut_df is not None and not fut_df.empty else df
    fallback_zones = get_prev_day_ohlc_zones(fallback_source_df)

    for z in fallback_zones:
        z['sources'] = ['fallback']
        z['subtype'] = 'fallback'
        z['zone_span'] = z['band'][1] - z['band'][0]
        if z['band'][0] <= current_price <= z['band'][1]:
            z['touch_count'] = 1  # mark as touched if near current price
    zones += fallback_zones

    # Flip Zone Detection
    zones = detect_flip_zones(zones, df, flip_window=flip_window)

    for z in zones:
        if 'zone_span' not in z:
            z['zone_span'] = round(z['band'][1] - z['band'][0], 2)
            logger.warning(f"[ZONE BUILDER] zone_span missing — added dynamically for {z['type']} @ {z['price']}")

    # Scoring and Filtering
    # Enrich zones with live metadata (status/age) before scoring
    if 'close' in df.columns and not df.empty:
        current_price = df['close'].iloc[-1]
        zones = enrich_zone_metadata(zones, current_price, df)

    # for z in zones:
    #     logger.debug(
    #         f"[ZONE STATUS] {z['type'].upper()} @ {z['price']} | Status={z['zone_status']} | Age={z['zone_age_minutes']} min"
    #     )

    live_zones = [z for z in zones if z['zone_status'] in {'inside', 'testing'}]
    logger.info(f"[ENRICH] Total zones: {len(zones)} | Live actionable: {len(live_zones)}")

    zones = score_zones(zones, current_price=current_price)

    zones = filter_and_validate_zones(zones, atr=mean_atr, tf_label=tf_label, current_price=current_price)

    # Assign fallback price if missing (use avg_price or midpoint of band)
    for z in zones:
        if 'price' not in z or z['price'] is None:
            try:
                low = float(z['band'][0])
                high = float(z['band'][1])
                z['price'] = z.get('avg_price') or round((low + high) / 2, 2)
                logger.warning(
                    f"[ZONE BUILDER] Zone missing price: type={z['type']} band={z['band']} sources={z.get('sources')}")
            except Exception as e:
                logger.warning(
                    f"[ZONE BUILDER] Failed to assign price for zone: {z.get('type')} | band={z.get('band')} | error={e}")

    log_final_zones(zones, current_price, now)

    return zones
