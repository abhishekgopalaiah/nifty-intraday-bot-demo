"""
Risk Manager — Industry-Grade Position Sizing and Guardrails

Responsibilities:
- Capital and risk-based position sizing with fallback on high-confidence signals
- Dynamic SL/Target level setting
- Daily P&L monitoring and guardrails
- Quant-grade risk control integration with signal engine

Usage:
from core.risk_manager import calculate_position_size, set_trade_risk_levels
premium = 120
qty = calculate_position_size(premium, confidence=0.85)
if qty > 0:
    levels = set_trade_risk_levels(entry_price=premium, direction="CE")
    print("Quantity:", qty)
    print("SL:", levels['stop_loss'], "Target:", levels['target'])
"""

from config.settings import CAPITAL_PER_TRADE, RISK_PER_TRADE, MAX_DAILY_LOSS, MAX_DAILY_PROFIT, LOT_SIZE
from utils.logger import get_logger

logger = get_logger()

# Internal trackers
daily_pnl = 0.0
open_trades = {}  # trade_id -> dict with SL, Target, qty


def calculate_position_size(premium: float, confidence: float = 1.0, stoploss_pct: float = 0.25) -> int:
    """
    Calculates position size (lots) based on capital and risk constraints. Allows override with high-confidence.

    Args:
        premium (float): Option premium (entry price)
        confidence (float): Signal confidence (0–1)
        stoploss_pct (float): SL percentage assumed for risk sizing

    Returns:
        int: Total quantity to buy (multiple of LOT_SIZE), or 0 if not affordable.
    """
    if premium <= 0:
        logger.warning("Invalid premium provided.")
        return 0

    cost_per_lot = premium * LOT_SIZE
    risk_budget = CAPITAL_PER_TRADE * RISK_PER_TRADE
    risk_per_lot = premium * stoploss_pct * LOT_SIZE

    risk_lots = int(risk_budget // risk_per_lot)
    capital_lots = int(CAPITAL_PER_TRADE // cost_per_lot)
    num_lots = min(risk_lots, capital_lots)

    # Fallback: Allow 1 lot for high-confidence signals if capital allows
    if num_lots == 0 and confidence >= 0.75 and cost_per_lot <= CAPITAL_PER_TRADE:
        logger.warning(f"High-confidence fallback enabled — Forcing 1 lot (Confidence: {confidence})")
        num_lots = 1

    # Fallback: Allow 2 lot for high-confidence signals if capital allows
    if num_lots == 0 and confidence > 1 and cost_per_lot <= CAPITAL_PER_TRADE:
        logger.warning(f"High-confidence fallback enabled — Forcing 2 lot (Confidence: {confidence})")
        num_lots = 2

    if num_lots < 1:
        logger.warning(f"[RISK] Cannot proceed — Premium too high or risk too low: ₹{premium:.2f}")
        return 0

    total_qty = num_lots * LOT_SIZE
    logger.info(
        f"CAPITAL={CAPITAL_PER_TRADE}, RISK={RISK_PER_TRADE}, Premium={premium:.2f}, Lots={num_lots}, Qty={total_qty}, Confidence={confidence}"
    )
    return total_qty


def set_trade_risk_levels(entry_price: float, direction: str, sl_pct=30, tgt_pct=60) -> dict:
    """
    Calculate SL and Target levels relative to entry.

    Args:
        entry_price (float): Entry premium
        direction (str): "CE" or "PE"
        sl_pct (float): Stop loss % (default: 30)
        tgt_pct (float): Target % (default: 60)

    Returns:
        dict: {"stop_loss": float, "target": float}
    """
    sl = round(entry_price * (1 - sl_pct / 100), 1)
    tgt = round(entry_price * (1 + tgt_pct / 100), 1)
    return {"stop_loss": sl, "target": tgt}


def update_daily_pnl(pnl: float):
    """
    Adds trade P&L to daily tracker.

    Args:
        pnl (float): Trade profit/loss
    """
    global daily_pnl
    daily_pnl += pnl
    logger.info(f"[RISK] Updated daily PnL: ₹{daily_pnl:.2f}")


def is_risk_limit_breached() -> bool:
    """
    Stop trading if P&L exceeds configured daily loss or profit thresholds.

    Returns:
        bool: True if limits are breached
    """
    if daily_pnl <= -MAX_DAILY_LOSS:
        logger.warning("Max daily loss breached! Stopping further trades.")
        return True
    if daily_pnl >= MAX_DAILY_PROFIT:
        logger.info("Max daily profit achieved. Stopping further trades.")
        return True
    return False
