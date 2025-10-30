"""
Pattern Checker — Candlestick Pattern Recognition for Intraday Bot

Purpose:
Detects major candlestick patterns that confirm reversals, breakouts, or continuation setups.
Used in combination with S/R zones, trend filters, and volatility regimes.

✅ Included Patterns:
- Bullish/Bearish Engulfing
- Hammer / Inverted Hammer / Hanging Man / Shooting Star
- Doji
- Morning Star / Evening Star
- Piercing Line / Dark Cloud Cover
- Three White Soldiers / Three Black Crows
- Marubozu (Green/Red)
- Inside Bar / Outside Bar
"""

import pandas as pd
from utils.logger import get_logger

logger = get_logger("pattern_checker")


# === TWO-CANDLE REVERSALS ===

def is_bullish_engulfing(df):
    """
    Bullish Engulfing: Green candle fully engulfs prior red body.
    """
    if len(df) < 2:
        return False
    prev, curr = df.iloc[-2], df.iloc[-1]
    return (
            prev['close'] < prev['open'] and
            curr['close'] > curr['open'] and
            curr['close'] > prev['open'] and
            curr['open'] < prev['close']
    )


def is_bearish_engulfing(df):
    """
    Bearish Engulfing: Red candle fully engulfs prior green body.
    """
    if len(df) < 2:
        return False
    prev, curr = df.iloc[-2], df.iloc[-1]
    return (
            prev['close'] > prev['open'] and
            curr['close'] < curr['open'] and
            curr['open'] > prev['close'] and
            curr['close'] < prev['open']
    )


# === SINGLE-CANDLE PATTERNS ===

def is_hammer(df):
    """
    Hammer: Small body in upper third, long lower wick (2x body), minimal upper wick.
    Indicates potential bullish reversal after a downtrend.
    """
    if len(df) < 1:
        return False
    c = df.iloc[-1]
    body_size = abs(c['close'] - c['open'])
    total_range = c['high'] - c['low']
    if total_range == 0:  # Avoid division by zero
        return False
    lower_wick = min(c['open'], c['close']) - c['low']
    upper_wick = c['high'] - max(c['open'], c['close'])
    body_position = (max(c['open'], c['close']) - c['low']) / total_range
    return (lower_wick > 2 * body_size and  # Long lower wick
            upper_wick < body_size * 0.5 and  # Small/no upper wick
            body_position > 0.6)  # Body in upper third


def is_inverted_hammer(df):
    """
    Inverted Hammer: Small body in lower third, long upper wick (2x body), minimal lower wick.
    Indicates potential bullish reversal after a downtrend.
    """
    if len(df) < 1:
        return False
    c = df.iloc[-1]
    body_size = abs(c['close'] - c['open'])
    total_range = c['high'] - c['low']
    if total_range == 0:
        return False
    upper_wick = c['high'] - max(c['open'], c['close'])
    lower_wick = min(c['open'], c['close']) - c['low']
    body_position = (c['high'] - min(c['open'], c['close'])) / total_range
    return (upper_wick > 2 * body_size and  # Long upper wick
            lower_wick < body_size * 0.5 and  # Small/no lower wick
            body_position < 0.4)  # Body in lower third


def is_hanging_man(df):
    """
    Hanging Man: Like hammer but after an uptrend (bearish).
    """
    if len(df) < 1:
        return False
    c = df.iloc[-1]
    body = abs(c['close'] - c['open'])
    lower = min(c['open'], c['close']) - c['low']
    upper = c['high'] - max(c['open'], c['close'])
    return lower > 2 * body and upper < body and c['close'] < c['open']


def is_shooting_star(df):
    """
    Shooting Star: Small body in lower third, long upper wick (2x body), minimal lower wick.
    Indicates potential bearish reversal after an uptrend.
    """
    if len(df) < 1:
        return False
    c = df.iloc[-1]
    body_size = abs(c['close'] - c['open'])
    total_range = c['high'] - c['low']
    if total_range == 0:
        return False
    upper_wick = c['high'] - max(c['open'], c['close'])
    lower_wick = min(c['open'], c['close']) - c['low']
    body_position = (c['high'] - min(c['open'], c['close'])) / total_range
    return (upper_wick > 2 * body_size and  # Long upper wick
            lower_wick < body_size * 0.5 and  # Small/no lower wick
            body_position < 0.4)  # Body in lower third


def is_doji(df):
    """
    Doji: Open and close are almost equal → indecision
    """
    if len(df) < 1:
        return False
    c = df.iloc[-1]
    return abs(c['close'] - c['open']) <= (c['high'] - c['low']) * 0.1
    
def is_marubozu_green(df):
    """
    Green Marubozu: Full body candle with no wicks. Bullish momentum.
    """
    if len(df) < 1:
        return False
    c = df.iloc[-1]
    return c['open'] == c['low'] and c['close'] == c['high'] and c['close'] > c['open']


def is_marubozu_red(df):
    """
    Red Marubozu: Full red body with no wicks. Bearish momentum.
    """
    if len(df) < 1:
        return False
    c = df.iloc[-1]
    return c['open'] == c['high'] and c['close'] == c['low'] and c['close'] < c['open']


# === THREE-CANDLE PATTERNS ===

def is_morning_star(df):
    """
    Morning Star: Bearish candle → small body/doji → strong bullish candle
    The third candle should close above the midpoint of the first candle's body.
    """
    if len(df) < 3:
        return False
    a, b, c = df.iloc[-3], df.iloc[-2], df.iloc[-1]
    # First candle is bearish
    is_first_bearish = a['close'] < a['open']
    # Second candle is a doji or small body (less than 30% of first candle's range)
    is_doji_or_small = abs(b['close'] - b['open']) <= (a['high'] - a['low']) * 0.3
    # Third candle is bullish and closes into first candle's body
    is_third_bullish = c['close'] > c['open']
    penetration = c['close'] > (a['open'] + a['close']) / 2
    return is_first_bearish and is_doji_or_small and is_third_bullish and penetration


def is_evening_star(df):
    """
    Evening Star: Bullish candle → small body/doji → strong bearish candle
    The third candle should close below the midpoint of the first candle's body.
    """
    if len(df) < 3:
        return False
    a, b, c = df.iloc[-3], df.iloc[-2], df.iloc[-1]
    # First candle is bullish
    is_first_bullish = a['close'] > a['open']
    # Second candle is a doji or small body (less than 30% of first candle's range)
    is_doji_or_small = abs(b['close'] - b['open']) <= (a['high'] - a['low']) * 0.3
    # Third candle is bearish and closes into first candle's body
    is_third_bearish = c['close'] < c['open']
    penetration = c['close'] < (a['open'] + a['close']) / 2
    return is_first_bullish and is_doji_or_small and is_third_bearish and penetration


def is_three_white_soldiers(df):
    """
    Three White Soldiers: 3 strong green candles, opens higher each time
    """
    if len(df) < 3:
        return False
    a, b, c = df.iloc[-3], df.iloc[-2], df.iloc[-1]
    return (
            a['close'] > a['open'] and
            b['close'] > b['open'] and
            c['close'] > c['open'] and
            a['close'] < b['open'] < b['close'] < c['open'] < c['close']
    )


def is_three_black_crows(df):
    """
    Three Black Crows: 3 strong red candles, opens lower each time
    """
    if len(df) < 3:
        return False
    a, b, c = df.iloc[-3], df.iloc[-2], df.iloc[-1]
    return (
            a['close'] < a['open'] and
            b['close'] < b['open'] and
            c['close'] < c['open'] and
            a['close'] > b['open'] > b['close'] > c['open'] > c['close']
    )


# === CONTRACTION / EXPANSION PATTERNS ===

def is_inside_bar(df):
    """
    Inside Bar: Range of current candle is within previous.
    """
    if len(df) < 2:
        return False
    prev, curr = df.iloc[-2], df.iloc[-1]
    return curr['high'] < prev['high'] and curr['low'] > prev['low']


def is_outside_bar(df):
    """
    Outside Bar: Current candle range breaks both high/low of previous.
    """
    if len(df) < 2:
        return False
    prev, curr = df.iloc[-2], df.iloc[-1]
    return curr['high'] > prev['high'] and curr['low'] < prev['low']


def is_piercing_line(candles):
    if len(candles) < 2:
        return False
    prev, curr = candles.iloc[-2], candles.iloc[-1]
    return (
            prev['close'] < prev['open'] and
            curr['close'] > curr['open'] and
            curr['open'] < prev['low'] and
            curr['close'] > (prev['open'] + prev['close']) / 2
    )


def is_dark_cloud_cover(candles):
    if len(candles) < 2:
        return False
    prev, curr = candles.iloc[-2], candles.iloc[-1]
    return (
            prev['close'] > prev['open'] and
            curr['close'] < curr['open'] and
            curr['open'] > prev['high'] and
            curr['close'] < (prev['open'] + prev['close']) / 2
    )


def is_tweezer_bottom(candles, tolerance_pct=0.05):
    """
    Tweezer Bottom: Two candles with nearly identical lows, first bearish, second bullish.
    tolerance_pct: Allowed difference between lows as percentage of price.
    """
    if len(candles) < 2:
        return False
    prev, curr = candles.iloc[-2], candles.iloc[-1]
    price_level = (prev['low'] + curr['low']) / 2
    tolerance = price_level * (tolerance_pct / 100)
    return (abs(prev['low'] - curr['low']) <= tolerance and 
            prev['close'] < prev['open'] and  # First candle bearish
            curr['close'] > curr['open'])     # Second candle bullish


def is_tweezer_top(candles, tolerance_pct=0.05):
    """
    Tweezer Top: Two candles with nearly identical highs, first bullish, second bearish.
    tolerance_pct: Allowed difference between highs as percentage of price.
    """
    if len(candles) < 2:
        return False
    prev, curr = candles.iloc[-2], candles.iloc[-1]
    price_level = (prev['high'] + curr['high']) / 2
    tolerance = price_level * (tolerance_pct / 100)
    return (abs(prev['high'] - curr['high']) <= tolerance and 
            prev['close'] > prev['open'] and  # First candle bullish
            curr['close'] < curr['open'])     # Second candle bearish


# === Pattern Router ===

def detect_patterns(df: pd.DataFrame) -> str:
    """
    Scans the last few candles and returns the first pattern detected.
    Returns:
        str: Pattern name or 'None'
    """
    patterns = [
        (is_bullish_engulfing, {"name": "bullish_engulfing", "type": "bullish", "strength": 0.8}),
        (is_bearish_engulfing, {"name": "bearish_engulfing", "type": "bearish", "strength": 0.8}),
        (is_morning_star, {"name": "morning_star", "type": "bullish", "strength": 0.75}),
        (is_evening_star, {"name": "evening_star", "type": "bearish", "strength": 0.75}),
        (is_three_white_soldiers, {"name": "three_white_soldiers", "type": "bullish", "strength": 0.7}),
        (is_three_black_crows, {"name": "three_black_crows", "type": "bearish", "strength": 0.7}),
        (is_hammer, {"name": "hammer", "type": "bullish", "strength": 0.6}),
        (is_inverted_hammer, {"name": "inverted_hammer", "type": "bearish", "strength": 0.6}),
        (is_hanging_man, {"name": "hanging_man", "type": "bearish", "strength": 0.6}),
        (is_shooting_star, {"name": "shooting_star", "type": "bearish", "strength": 0.6}),
        (is_marubozu_green, {"name": "marubozu_green", "type": "bullish", "strength": 0.55}),
        (is_marubozu_red, {"name": "marubozu_red", "type": "bearish", "strength": 0.55}),
        (is_inside_bar, {"name": "inside_bar", "type": "neutral", "strength": 0.5}),
        (is_outside_bar, {"name": "outside_bar", "type": "neutral", "strength": 0.5}),
        (is_doji, {"name": "doji", "type": "neutral", "strength": 0.4}),
        (is_piercing_line, {"name": "piercing_line", "type": "bullish", "strength": 0.75}),
        (is_dark_cloud_cover, {"name": "dark_cloud_cover", "type": "bearish", "strength": 0.75}),
        (is_tweezer_bottom, {"name": "tweezer_bottom", "type": "bullish", "strength": 0.75}),
        (is_tweezer_top, {"name": "tweezer_top", "type": "bearish", "strength": 0.75})
    ]

    for fn, meta in patterns:
        try:
            if fn(df):
                return meta
        except Exception:
            continue

    return {"name": "none", "type": "neutral", "strength": 0.0}
