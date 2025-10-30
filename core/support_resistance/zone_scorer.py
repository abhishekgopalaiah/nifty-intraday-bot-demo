from utils.logger import get_logger

logger = get_logger("zone_scorer")


def score_zones(zones, current_price=None):
    """
    Assigns a score to each zone based on:
    - Recency (zone_age_minutes)
    - Zone status (inside/testing get a boost)
    - Multi-timeframe confluence
    - Source diversity (swing, volume, vwap)
    - Flip/retest tagging
    - Volume profile strength
    - Penalty for fallback zones
    - Proximity to current price (status)

    Normalized to 0–10, and confidence level tagged.
    Also logs individual component contributions to score.
    """
    scored = []
    for z in zones:
        components = {}
        score = 0

        # Touch count
        touch_score = 0
        if z.get("subtype") in ("swing", "swing_volume"):
            touch_score = min(z.get('touch_count', 0), 2) * 0.5
            score += touch_score
        components["touch"] = round(touch_score, 2)

        # Age-based recency: under 180 min gets full credit, decay after
        age = z.get('zone_age_minutes', 9999)
        recency_weight = max(0.2, 1.0 - min(age, 720) / 1440)
        recency_score = recency_weight * 1.5
        score += recency_score
        components["recency"] = round(recency_score, 2)

        # Multi-timeframe bonus, Zones appearing on multiple timeframes (e.g. ["5m", "15m", "1h"]) get more credit
        tf_score = min(len(set(z.get("timeframes", []))) / 3.0, 1.0) * 1.0
        score += tf_score
        components["multi_tf"] = round(tf_score, 2)

        # Source diversity
        source_score = min(len(set(z.get("sources", []))) / 3.0, 1.0) * 0.8
        score += source_score
        components["source_diversity"] = round(source_score, 2)

        # VWAP / Volume tags
        vwap_bonus = 0.5 if z.get("vwap_zone") else 0.0
        volume_tag_bonus = 0.5 if z.get("volume_cluster") else 0.0
        score += vwap_bonus + volume_tag_bonus
        components["vwap_tag"] = vwap_bonus
        components["volume_tag"] = volume_tag_bonus

        # Volume magnitude
        volume_score = 0
        if z.get("volume_cluster") and z.get("total_volume"):
            volume_score = min(z['total_volume'] / 100000, 1.2)
            score += volume_score
        components["volume_strength"] = round(volume_score, 2)

        # Zone status
        status = z.get("zone_status")
        status_score = {"inside": 1.2, "testing": 1.0, "rejected": 0.2}.get(status, 0.0)
        score += status_score
        components["status"] = status_score

        # Flip/retest
        flip_score = 0.5 if z.get("flipped") or z.get("subtype") == "retest" else 0.0
        score += flip_score
        components["flip_retest"] = flip_score

        # Span penalty
        span_penalty = -0.1 if z.get("zone_span") and z["zone_span"] > 60 else 0.0
        score += span_penalty
        components["span_penalty"] = span_penalty

        # Age penalty
        age_penalty = -0.1 if age > 720 else 0.0
        score += age_penalty
        components["age_penalty"] = age_penalty

        # Fallback zones — penalize
        if z.get("subtype") == "fallback":
            score *= 0.75
            components["fallback_penalty"] = True
        else:
            components["fallback_penalty"] = False

        z["_score_components"] = components
        z["score"] = round(score, 2)
        z["normalized_score"] = round(min(score / 6.0 * 10.0, 10.0), 2)
        z["confidence"] = (
            "high" if score >= 6.0 else
            "medium" if score >= 2.5 else
            "low"
        )
        scored.append(z)

    # Fallback: boost if no zones qualify
    if all(z["score"] < 2.5 for z in scored):
        nearest = min(scored, key=lambda z: abs(z["price"] - current_price))
        nearest["score"] += 1.2
        nearest["confidence"] = "medium"
        nearest["_score_components"]["fallback_boost"] = 1.2
        logger.info(f"[FALLBACK BOOST] Applied to zone at {nearest['price']} due to weak S/R context.")

    for z in scored:
        logger.debug(
            f"[SCORE] {z['type'].upper()} @ {z['price']} | Score={z['score']} | Status={z.get('zone_status')} | TFs={z.get('timeframes')} | Src={z.get('sources')}")

    return scored
