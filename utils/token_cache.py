"""
Token Cache with Expiry Support

- Automatically expires tokens after expiry date.
- Persists symbol-token-expiry mapping in JSON.
"""

import json
import os
import time
from datetime import datetime
from config.settings import TOKEN_CACHE_FILE
from utils.logger import get_logger

logger = get_logger()


def load_token_cache():
    if os.path.exists(TOKEN_CACHE_FILE):
        try:
            with open(TOKEN_CACHE_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}


def save_token_cache(cache):
    with open(TOKEN_CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)


def is_expired(expiry_str):
    """
    Checks if the given expiry string (e.g., "27JUN25") has passed.

    Returns:
        bool: True if expired
    """
    try:
        expiry_date = datetime.strptime(expiry_str, "%d%b%y")
        return datetime.now() > expiry_date
    except Exception:
        return True


def get_token_from_cache(client, symbol: str, expiry_str: str, exchange: str = "NFO") -> str:
    """
    Get token from cache or SmartAPI. Auto-expires after expiry.

    Args:
        client (SmartConnect): Authenticated client
        symbol (str): Trading symbol like "NIFTY27JUN24500CE"
        expiry_str (str): Expiry like "27JUN25"
        exchange (str): "NFO" for options

    Returns:
        str: Valid symbol token # e.g., "27JUN25"
    """
    cache = load_token_cache()
    cache_key = f"{exchange}:{symbol}"

    # Check valid token
    entry = cache.get(symbol)
    if entry and not is_expired(entry.get("expiry", "")):
        return entry["token"]

    # Fetch fresh from API
    for attempt in range(2):  # Retry once
        try:
            response = client.searchScrip(exchange, symbol)
            token = response["data"][0]["symboltoken"]

            # Save with expiry
            cache[cache_key] = {
                "token": token,
                "expiry": expiry_str.upper() if expiry_str else "PERPETUAL" # e.g., "27JUN25"
            }
            save_token_cache(cache)
            logger.debug(f"[TOKEN CACHE] Cached token for {symbol} on {exchange} with expiry={expiry_str or 'PERPETUAL'}")
            return token

        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} token fetch failed for {symbol}: {e}")
            time.sleep(1)

    raise RuntimeError(f"❌ Failed to get token for {symbol}")
