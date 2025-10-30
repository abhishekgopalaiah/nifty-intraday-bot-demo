"""
Purpose:
This script dynamically selects the correct strike prices (ATM, 1 OTM CE/PE) for NIFTY options based on the current index LTP. It supports both CE and PE detection.
"""

from math import ceil, floor
from utils.logger import get_logger
from utils.expiry_utils import get_monthly_expiry_date

logger = get_logger()

# NIFTY options strike step size is 50
STRIKE_STEP = 100


def round_to_nearest_strike(price, direction="ATM"):
    """
    Rounds the given price to the nearest valid NIFTY strike.
    
    Args:
        price (float): Current index value.
        direction (str): "ATM", "OTM_CE", "OTM_PE"
    
    Returns:
        int: Strike price
    """
    base = round(price / STRIKE_STEP) * STRIKE_STEP

    if direction == "ATM":
        return base
    elif direction == "OTM_CE":
        return base + STRIKE_STEP
    elif direction == "OTM_PE":
        return base - STRIKE_STEP
    else:
        logger.warning(f"Invalid strike direction: {direction}")
        return base


def get_option_symbol(expiry: str, strike: int, option_type: str) -> str:
    """
    Constructs the option trading symbol.

    Example: NIFTY24JUL17500CE

    Args:
        expiry (str): Expiry string in format "24JUL"
        strike (int): Strike price (e.g., 17500)
        option_type (str): "CE" or "PE"

    Returns:
        str: Full option trading symbol.
    """
    return f"NIFTY{expiry}{strike}{option_type}"

def get_nifty_futures_symbol():
    """
    Constructs the NIFTY futures symbol like NIFTY27JUN24FUT
    """
    expiry = get_monthly_expiry_date()  # e.g., 27JUN24
    return f"NIFTY{expiry}FUT"

"""
Example:
ltp = 23685  # Assume this is current index price from LTP fetch

atm_strike = round_to_nearest_strike(ltp, "ATM")
otm_ce = round_to_nearest_strike(ltp, "OTM_CE")
otm_pe = round_to_nearest_strike(ltp, "OTM_PE")

print("ATM:", atm_strike)
print("OTM CE:", otm_ce)
print("OTM PE:", otm_pe)

symbol = get_option_symbol("27JUN", atm_strike, "CE")
print("Option symbol:", symbol)


"""
