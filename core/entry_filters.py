# entry_filters.py — Final Production-Grade Entry Filter System for NIFTY 50
"""
Scored entry filtering logic tuned for:
- NIFTY 5-minute intraday candles
- High-confidence, data-enriched support/resistance zones
- Quant-level scoring with contextual logic

Features:
- Wick rejection, trap candle check, flipped zone boost
- Zone subtype and score-aware adaptation
- ATR-based zone distance scaling
- ADX/EMA/RSI trend strength blending
- Dynamic regime and zone-based thresholding
"""

from utils.logger import get_logger

logger = get_logger("entry_filters")


def evaluate_entry_score(price, candle, zone, atr, rsi, ema9, ema21, adx, direction, bias=None, pattern_strength=0.0,
                         mode="lenient"):
    """
    Score a potential entry against multi-factor conditions.

    Parameters:
        price (float): Current close price
        candle (dict): Current candle dict with OHLC and pattern
        zone (dict): Enriched support/resistance zone dict
        atr (float): ATR value
        rsi (float): RSI value
        ema9, ema21 (float): Moving averages
        adx (float): Trend strength
        direction (str): 'CE' or 'PE'
        bias (str): Optional trend bias
        pattern_strength (float): Pattern strength
        mode (str): 'strict', 'normal', or 'lenient'

    Returns:
        score (float), reasons (dict): Total score with factor breakdown
    """
    if not zone or "band" not in zone:
        return 0.0, {"zone": "missing"}

    score = 0.0
    reasons = {}
    low, high = zone["band"]
    flipped = zone.get("flipped", False)
    subtype = zone.get("subtype", "primary")
    confidence = zone.get("confidence", "medium")
    sources = zone.get("sources", [])
    touch_count = zone.get("touch_count", 0)

    open_, close = candle["open"], candle["close"]
    high_, low_ = candle["high"], candle["low"]
    body = abs(close - open_)
    range_ = high_ - low_ + 1e-6
    upper_wick = high_ - max(open_, close)
    lower_wick = min(open_, close) - low_
    body_ratio = body / range_
    is_strong_body = body_ratio > 0.5

    # Trap candle penalty — unless flipped or strong ADX
    trap_patterns = {"Doji", "Shooting Star", "Hanging Man"}
    if candle.get("pattern") in trap_patterns and not flipped and adx < 20:
        reasons["trap_candle"] = -0.1 if mode == "strict" else -0.05
    else:
        reasons["trap_candle"] = 0.0

    # Body strength bonus
    reasons["body_strength"] = 0.3 if is_strong_body and mode == "strict" else 0.2 if is_strong_body else -0.1

    # Rejection wick check
    if direction == "CE" and lower_wick > 1.2 * body:
        reasons["rejection_wick"] = 0.1
    elif direction == "PE" and upper_wick > 1.2 * body:
        reasons["rejection_wick"] = 0.1
    else:
        reasons["rejection_wick"] = 0.0

    # Trend momentum blend
    trend_score = 0.0
    if adx > 16: trend_score += 0.1
    if direction == "CE" and price > ema9 > ema21: trend_score += 0.1
    if direction == "PE" and price < ema9 < ema21: trend_score += 0.1
    if (direction == "CE" and rsi > 52) or (direction == "PE" and rsi < 48): trend_score += 0.1
    if adx > 25: trend_score += 0.1
    reasons["trend_alignment"] = round(trend_score, 2)

    # Zone proximity scoring
    distance = min(abs(price - high), abs(price - low))
    if low <= price <= high:
        proximity = 0.4
    elif distance <= 0.75 * atr:
        proximity = 0.3
    elif distance <= 1.5 * atr:
        proximity = 0.15
    else:
        proximity = -0.1
    reasons["zone_proximity"] = round(proximity, 2)

    # Zone quality boost
    zone_bonus = 0.0
    if flipped: zone_bonus += 0.15
    if subtype == "retest": zone_bonus += 0.1
    if "vwap" in sources: zone_bonus += 0.05
    if touch_count >= 3: zone_bonus += 0.05
    reasons["zone_quality"] = round(zone_bonus, 2)

    # Bias agreement
    bias_score = 0.1 if bias and direction in bias else 0.0
    if adx > 22: bias_score += 0.1
    reasons["bias_alignment"] = round(bias_score, 2)

    # Pattern strength bonus
    if pattern_strength >= 0.6:
        reasons["pattern_strength"] = round(min(pattern_strength * 0.3, 0.3), 2)
    else:
        reasons["pattern_strength"] = 0.0

    score = round(sum(reasons.values()), 2)
    logger.debug(
        f"[ENTRY SCORE] {score} | reasons={reasons} | zone_subtype={subtype} | flipped={flipped} | touch={touch_count}")
    return score, reasons


def is_entry_allowed(score, threshold=0.25, regime="normal", zone=None):
    """
    Decide if an entry score is allowed based on dynamic context.
    Supports regime (volatility) and zone-based adjustment.
    """
    adj_threshold = threshold

    if regime.lower() == "highvol":
        adj_threshold -= 0.05
    elif regime.lower() == "lowvol":
        adj_threshold += 0.05

    if zone:
        if zone.get("subtype") == "retest":
            adj_threshold -= 0.03
        if zone.get("confidence") == "high":
            adj_threshold -= 0.02

    adj_threshold = round(max(0.15, min(0.7, adj_threshold)), 2)

    allowed = score >= adj_threshold
    logger.debug(f"[ENTRY CHECK] Score={score} | Threshold={adj_threshold} | Allowed={allowed}")
    return allowed
