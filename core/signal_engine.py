from core.pattern_checker import detect_patterns
from core.volatility_utils import (
    get_volatility_regime,
    calculate_bollinger_width,
    calculate_atr_percentile,
)
from core.entry_filters import evaluate_entry_score, is_entry_allowed
from utils.logger import get_logger
from datetime import datetime

logger = get_logger("SignalEngine")


def infer_trend(indicator_df, threshold_pct=0.1):
    """Infer trend based on EMA9 and EMA21 crossover with percentage threshold.
    
    Args:
        indicator_df: DataFrame containing indicator values
        threshold_pct: Percentage difference threshold (default 0.1%)
                      Increase for choppy markets, decrease for trending markets
    """
    ema9 = indicator_df.iloc[-1]["ema9"]
    ema21 = indicator_df.iloc[-1]["ema21"]
    diff_pct = (ema9 - ema21) / ema21 * 100

    if diff_pct > threshold_pct:
        return "up"
    elif diff_pct < -threshold_pct:
        return "down"
    return "sideways"


def infer_bias(indicator_df, pattern_type, pattern_strength=0):
    """
    Infer trade bias for Nifty 50 intraday using trend, RSI, and pattern alignment.
    
    Args:
        indicator_df: DataFrame with indicator values
        pattern_type: 'bullish' or 'bearish' pattern
        pattern_strength: Strength of the pattern (0-1)
    
    Returns:
        'CE' for call entry, 'PE' for put entry, or None if no clear bias
    """
    trend = infer_trend(indicator_df)
    rsi = indicator_df.iloc[-1]["rsi"]
    atr = indicator_df.iloc[-1].get("atr", 1)  # Get ATR if available

    # Priority 1: Strong trend confirmation
    if trend == "up" and rsi > 52:
        return "CE"
    elif trend == "down" and rsi < 45:
        return "PE"

    # Priority 2: Pattern confirmation in trend direction
    if trend == "down" and 45 <= rsi <= 50 and pattern_type == "bearish":
        return "PE"
    if trend == "up" and 50 <= rsi <= 52 and pattern_type == "bullish":
        return "CE"

    # Priority 3: Sideways market with strong confirmation
    if trend == "sideways":
        if rsi < 45 and pattern_type == "bearish":
            return "PE"
        elif rsi > 55 and pattern_type == "bullish":
            return "CE"

    # Priority 4: Strong pattern override (only for high probability setups)
    if pattern_strength >= 0.8:
        return "CE" if pattern_type == "bullish" else "PE" if pattern_type == "bearish" else None

    return None


def select_best_zone(zones, price, zone_type, bias=None):
    """Score zones based on band proximity, flipped/retest bonuses, and directional match."""
    candidates = [z for z in zones if z.get("type") == zone_type]
    if not candidates:
        return None

    def zone_priority(z):
        center = sum(z.get("band", [0, 0])) / 2
        proximity = abs(center - price)
        score = z.get("score", 0)
        weight = score - proximity * 0.01
        if z.get("flipped"): weight += 0.2
        if z.get("subtype") == "retest": weight += 0.1
        if z.get("confidence") == "high": weight += 0.1
        if bias and ((bias == "CE" and zone_type == "support") or (bias == "PE" and zone_type == "resistance")):
            weight += 0.1
        return weight

    return max(candidates, key=zone_priority)


def compute_trend_inertia(indicator_df, direction, window=3):
    """Score trend persistence over last N bars."""
    if len(indicator_df) < window + 1:
        return 0.0

    recent = indicator_df.tail(window)
    if direction == "CE" and all(recent["ema9"] > recent["ema21"]):
        return 0.15
    elif direction == "PE" and all(recent["ema9"] < recent["ema21"]):
        return 0.15
    return 0.0


def is_valid_proximity(price, zone, atr, entry_score=0.0, adx=None):
    """
    Adaptive proximity check for Nifty 50 intraday trading.
    Adjusts buffer size based on volatility and entry quality.
    
    Args:
        price: Current price
        zone: Zone dictionary with 'band' key containing (low, high) tuple
        atr: Current ATR value
        entry_score: Score of the trade setup (0.0 to 1.0)
        adx: Current ADX value if available
        
    Returns:
        bool: True if price is within valid proximity of the zone
    """
    if not zone or "band" not in zone:
        return False

    zone_low, zone_high = zone["band"]
    zone_mid = (zone_low + zone_high) / 2
    distance = abs(price - zone_mid)

    # Base buffer is 0.5 * ATR
    dynamic_buffer = 0.5 * atr

    # Increase buffer for high-probability setups or strong trends
    if entry_score > 0.9 or (adx and adx > 35):
        dynamic_buffer = atr  # Allow up to 1x ATR for high-conviction setups

    # For Nifty, also consider zone width (wider zones can have slightly more tolerance)
    zone_width = zone_high - zone_low
    if zone_width > 2 * atr:  # For very wide zones
        dynamic_buffer = min(dynamic_buffer * 1.2, atr * 1.5)  # Cap at 1.5x ATR

    return distance <= dynamic_buffer


def generate_trade_signal(index_df, indicator_df, zones, signal_flags=None):
    """
    Main signal engine: Combines pattern, trend, S/R, volatility regime, and filters
    with fallback and trend inertia logic (Batch 3)
    """
    if signal_flags is None:
        signal_flags = {"CE": False, "PE": False}

    latest = index_df.iloc[-1]
    price = latest["close"]
    candle = latest.to_dict()

    # Pattern detection
    pattern = detect_patterns(index_df)
    pattern_type = pattern.get("type", "neutral")
    pattern_name = pattern.get("name", "pattern")
    pattern_strength = pattern.get("strength", 0.0)
    logger.info(f"[PATTERN] {pattern_name} detected | Strength={pattern_strength}")

    # Volatility regime
    indicator_df["bb_width"] = calculate_bollinger_width(index_df)
    indicator_df["atr_pct"] = calculate_atr_percentile(indicator_df)
    regime = get_volatility_regime(
        indicator_df["atr_pct"].iloc[-1], indicator_df["bb_width"].iloc[-1]
    )

    # Trend + Bias
    trend = infer_trend(indicator_df)
    bias = infer_bias(indicator_df, pattern_type, pattern_strength)
    direction = bias

    # Zone selection
    support_zone = select_best_zone(zones, price, "support", bias)
    resistance_zone = select_best_zone(zones, price, "resistance", bias)
    selected_zone = support_zone if direction == "CE" else resistance_zone if direction == "PE" else None

    if selected_zone:
        logger.info(
            f"[ZONE SELECTED] {selected_zone['type']} | Band={selected_zone['band']} | Score={selected_zone['score']}")
    else:
        logger.warning(f"[ZONE] No suitable {direction} zone near price {price}")

    # Indicators
    atr = indicator_df.iloc[-1].get("atr", 0)
    rsi = indicator_df.iloc[-1]["rsi"]
    ema9 = indicator_df.iloc[-1]["ema9"]
    ema21 = indicator_df.iloc[-1]["ema21"]
    adx = indicator_df.iloc[-1]["adx"]

    # Trend inertia boost
    inertia_score = compute_trend_inertia(indicator_df, direction)

    # Boost pattern strength if aligned with zone type and RSI
    if selected_zone:
        if pattern_type == "bullish" and selected_zone["type"] == "support" and rsi < 45:
            pattern_strength += 0.05
        elif pattern_type == "bearish" and selected_zone["type"] == "resistance" and rsi > 55:
            pattern_strength += 0.05
        # Cap at 1.0
        pattern_strength = min(pattern_strength, 1.0)

    # Entry score evaluation
    entry_score, reasons = evaluate_entry_score(
        price, candle, selected_zone, atr, rsi, ema9, ema21, adx, direction, bias=bias,
        pattern_strength=pattern_strength
    )
    entry_score += inertia_score
    reasons["trend_inertia"] = round(inertia_score, 2)

    allowed = is_entry_allowed(entry_score, regime=regime, zone=selected_zone)

    # Fallback logic: strong pattern + trend + no good zone
    fallback_allowed = False
    debug_reason = "allowed"
    if not allowed and pattern_strength >= 0.75 and inertia_score >= 0.1:
        fallback_allowed = True
        debug_reason = "fallback_allowed"
        logger.warning("[FALLBACK] Strong pattern + trend inertia -> allowing trade without clean zone")

    final_allowed = allowed or fallback_allowed
    if regime == "HighVol":
        strike_direction = "ATM"
    else:
        strike_direction = "OTM_CE" if direction == "CE" else "OTM_PE" if direction == "PE" else "ATM"

    # Zone proximity for reversal patterns
    if pattern_name in {"hammer", "inverted_hammer", "doji"} and selected_zone:
        if not is_valid_proximity(price, selected_zone, atr, entry_score, adx):
            final_allowed = False
            debug_reason = "pattern_far_from_zone"

    return {
        "option_type": direction,
        "strike_direction": strike_direction,
        "side": direction,
        "confidence": "high" if entry_score > 0.6 else "medium" if entry_score > 0.3 else "low",
        "pattern": pattern,
        "pattern_strength": round(pattern_strength, 2),
        "zone": selected_zone,
        "trend": trend,
        "regime": regime,
        "bias": bias,
        "allowed": final_allowed,
        "entry_score": round(entry_score, 2),
        "entry_reasons": reasons,
        "reason": f"{pattern_name} near {direction} zone in {trend} trend",
        "debug_reason": debug_reason if not final_allowed else "entry_passed",
        "indicators": {
            "rsi": rsi, "ema9": ema9, "ema21": ema21, "adx": adx, "atr": atr
        },
        "last_signal_time": datetime.now().strftime("%H:%M:%S")
    }
