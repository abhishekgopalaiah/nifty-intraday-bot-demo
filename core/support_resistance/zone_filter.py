from utils.logger import get_logger

logger = get_logger("zone_filter")


def log_final_zones(zones, current_price, now):
    """Log details of each filtered zone with context."""
    logger.info(f"[TIME] Evaluating zones at {now} | LTP: {current_price}")
    logger.info(f"[SUMMARY] {len(zones)} zones after filtering")

    for z in zones:
        # Ensure band is cast to float for clean logging
        band = (float(z['band'][0]), float(z['band'][1]))
        logger.info(
            f"[ZONE] {z['type'].upper()} | Score={z['score']} ({z['confidence']}) | "
            f"Band={band} | Status={z['zone_status']} | Age={z.get('zone_age_minutes')}m | "
            f"TFs={z.get('timeframes')} | Src={z.get('sources')} | Subtype={z.get('subtype')} | Span={z.get('zone_span')}"
        )


def filter_and_validate_zones(
        zones,
        atr=None,
        tf_label="5m",
        atr_mult_width=1.5,
        atr_mult_gap=1.0,
        min_gap_fallback=5,
        max_zones=8,
        min_score=2.5,
        max_zone_age=9999,
        current_price=None
):
    """
    Adaptive zone filter using ATR and scoring rules:
    - Filters overly wide or stale zones
    - Drops low-score or low-confidence zones
    - Enforces spacing between zones
    - Keeps high-quality volume/VWAP/fallback zones
    - Logs rejection reasons

    Args:
        zones (list): List of zone dictionaries
        atr (float): Average True Range (5m preferred)
        tf_label (str): Timeframe label ("5m", "15m", "1h")
        atr_mult_width (float): Max zone span = ATR * multiplier
        atr_mult_gap (float): Min gap between zones = ATR * multiplier
        min_gap_fallback (int): Fallback min spacing in points
        max_zones (int): Max number of zones to retain
        min_score (float): Minimum score threshold
        max_zone_age (int): Max age in minutes before zone is considered stale
        current_price (float): Last traded price to fallback sort nearest zones

    Returns:
        list: Filtered zones
    """
    if not zones:
        return []

    default_span = {"5m": 60, "15m": 75, "1h": 90}.get(tf_label, 60)
    max_span = atr * atr_mult_width if atr else default_span
    min_gap = max((atr or 0) * atr_mult_gap, min_gap_fallback)
    logger.debug(f"[FILTER CONFIG] tf={tf_label} | max_span={max_span:.2f} | min_gap={min_gap:.2f}")

    zones = sorted(zones, key=lambda z: z['band'][0])
    valid = []
    prev = None

    for z in zones:
        low, high = z['band']
        zone_span = z.get("zone_span", high - low)
        score = z.get("score", 0)
        age_min = z.get("zone_age_minutes", 0)
        confidence = z.get("confidence", "medium")
        zone_type = z.get("type", "")
        zone_id = f"{zone_type.upper()} [{round(low)}–{round(high)}]"

        if zone_span > max_span:
            logger.debug(f"[FILTER] Dropped {zone_id} – span too wide ({zone_span:.2f})")
            continue

        if score < min_score and confidence != "high":
            logger.debug(f"[FILTER] Dropped {zone_id} – score too low ({score})")
            continue

        if age_min and age_min > max_zone_age:
            logger.debug(f"[FILTER] Dropped {zone_id} – stale zone ({age_min:.1f} mins old)")
            continue

        if zone_span > max_span and not (
                z.get("volume_cluster") or z.get("vwap_zone") or "fallback" in z.get("sources", [])
        ):
            logger.debug(f"[FILTER] Dropped {zone_id} – too wide without volume/VWAP/fallback")
            continue

        if prev and (low - prev['band'][1] < min_gap):
            if confidence == 'low':
                logger.debug(f"[FILTER] Dropped {zone_id} – low confidence + overlap")
                continue
            logger.debug(f"[FILTER] Dropped {zone_id} – too close to previous zone")
            continue

        valid.append(z)
        prev = z

        if len(valid) >= max_zones:
            logger.debug(f"[FILTER] Reached max zone count: {max_zones}")
            break

    if not valid and zones:
        if current_price:
            valid = sorted(zones, key=lambda z: abs(float(z["price"]) - current_price))[:3]
            logger.warning("[FALLBACK] No strong zones passed — returning nearest fallback zones.")
            logger.info(f"[FALLBACK] Selected zones closest to LTP: {current_price}")

        else:
            valid = sorted(zones, key=lambda z: z.get("score", 0), reverse=True)[:3]
            logger.warning("[FALLBACK] No strong zones passed — fallback to top scoring zones.")


        logger.info(f"[FALLBACK] Selected {len(valid)} fallback zone(s).")

    logger.info(f"[FILTER SUMMARY] Final zones: {len(valid)} / {len(zones)} passed filtering.")
    return valid
