import json
import os
from utils.logger import get_logger
from config.settings import POSITION_STATE_FILE, SIGNAL_STATE_FILE
from datetime import datetime, date

logger = get_logger()

DEFAULT_SIGNAL_STATE = {
    "used_signals": {"CE": False, "PE": False},
    "last_signal_day": str(date.today())
}


def save_position_state(position: dict):
    try:
        with open(POSITION_STATE_FILE, "w") as f:
            json.dump(position, f, indent=2)
        logger.info(f"💾 Position state saved.")
    except Exception as e:
        logger.error(f"❌ Failed to save position state: {e}")


def load_position_state():
    if not os.path.exists(POSITION_STATE_FILE):
        return None

    try:
        with open(POSITION_STATE_FILE, "r") as f:
            data = json.load(f)
        logger.info("🔁 Position state loaded from disk.")
        return data
    except Exception as e:
        logger.error(f"❌ Failed to load position state: {e}")
        return None


def clear_position_state():
    try:
        if os.path.exists(POSITION_STATE_FILE):
            os.remove(POSITION_STATE_FILE)
            logger.info("🧹 Cleared saved position state.")
    except Exception as e:
        logger.error(f"❌ Failed to clear position state: {e}")


# ---------- Signal State ----------

def load_signal_state() -> dict:
    """Load signal usage (CE/PE) and last signal day."""
    if not os.path.exists(SIGNAL_STATE_FILE):
        logger.info("Signal state file not found. Using defaults.")
        return DEFAULT_SIGNAL_STATE.copy()

    try:
        with open(SIGNAL_STATE_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"❌ Failed to load signal state: {e}")
        return DEFAULT_SIGNAL_STATE.copy()


def save_signal_state(state: dict):
    """Save current CE/PE signal flags and signal date."""
    try:
        with open(SIGNAL_STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
        logger.info("💾 Signal state saved.")
    except Exception as e:
        logger.error(f"❌ Failed to save signal state: {e}")


def reset_daily_signals(state: dict) -> dict:
    """Resets signals if a new day has started."""
    today = str(date.today())
    if state.get("last_signal_day") != today:
        logger.info("📅 New trading day. Resetting CE/PE signal flags.")
        state["used_signals"] = {"CE": False, "PE": False}
        state["last_signal_day"] = today
        save_signal_state(state)
    return state
