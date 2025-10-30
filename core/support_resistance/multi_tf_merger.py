from collections import defaultdict
import logging

logger = logging.getLogger("ZoneMerger")

def merge_timeframe_zones(zones_by_tf, proximity=20):
    """
    Merge S/R zones from multiple timeframes into a unified, enriched list.
    Zones are merged if their band edges are within `proximity` points.
    Merged zones retain aggregated metadata: score, sources, timeframes, status.

    Args:
        zones_by_tf (dict): Zones keyed by timeframe (e.g., {'5m': [...], '15m': [...]}).
        proximity (float): Maximum distance between bands to consider for merging.

    Returns:
        List[dict]: Merged and enriched support/resistance zones.
    """
    merged_zones = []
    seen = set()
    all_zones = []

    # Flatten and tag zones with their timeframe
    for tf, zones in zones_by_tf.items():
        for z in zones:
            zone_copy = z.copy()
            zone_copy.setdefault('timeframes', []).append(tf)
            all_zones.append(zone_copy)

    all_zones.sort(key=lambda z: z['band'][0])

    for i, zone in enumerate(all_zones):
        if i in seen:
            continue

        band_low, band_high = zone['band']
        merged = [zone]

        for j in range(i + 1, len(all_zones)):
            other = all_zones[j]
            if j in seen:
                continue
            o_low, o_high = other['band']

            if abs(band_low - o_low) <= proximity or abs(band_high - o_high) <= proximity:
                merged.append(other)
                seen.add(j)

        # Merge band range and compute average mid-price
        new_band = (
            min(z['band'][0] for z in merged),
            max(z['band'][1] for z in merged)
        )
        mid_price = round((new_band[0] + new_band[1]) / 2, 2)

        # Aggregate timeframes, sources, and scores
        all_tfs = sorted(set(tf for z in merged for tf in z.get('timeframes', [])))
        all_sources = set(s for z in merged for s in z.get('sources', []))
        all_statuses = [z.get('zone_status') for z in merged if z.get('zone_status')]
        latest_touch = max(z.get('last_touched') for z in merged if z.get('last_touched'))

        score = round(sum(z.get('score', 0) for z in merged) / len(merged), 2)
        norm_score = round(min((score / 6.0) * 10.0, 10.0), 2)
        confidence = max(z.get('confidence', 'low') for z in merged)
        age = min(z.get('zone_age_minutes', 9999) for z in merged)
        touch_count = sum(z.get('touch_count', 0) for z in merged)

        # Boolean and subtype metadata
        flipped = any(z.get('flipped', False) for z in merged)
        vwap_zone = any(z.get('vwap_zone', False) for z in merged)
        volume_cluster = any(z.get('volume_cluster', False) for z in merged)
        subtypes = set(z.get('subtype') for z in merged if z.get('subtype'))
        subtype = subtypes.pop() if len(subtypes) == 1 else 'mixed'

        zone_status = (
            'inside' if 'inside' in all_statuses else
            'testing' if 'testing' in all_statuses else
            'untouched'
        )

        merged_zone = {
            'band': new_band,
            'price': mid_price,
            'score': score,
            'normalized_score': norm_score,
            'merged_from': len(merged),
            'timeframes': all_tfs,
            'type': merged[0]['type'],
            'sources': list(sorted(all_sources)),
            'confidence': confidence,
            'last_touched': latest_touch,
            'zone_status': zone_status,
            'zone_age_minutes': age,
            'touch_count': touch_count,
            'flipped': flipped,
            'subtype': subtype,
            'vwap_zone': vwap_zone,
            'volume_cluster': volume_cluster
        }

        logger.debug(
            f"[MERGE] Zone merged from {len(merged)} zones | TFs={all_tfs} | Subtype={subtype} | Flipped={flipped}"
        )
        merged_zones.append(merged_zone)

    return merged_zones
