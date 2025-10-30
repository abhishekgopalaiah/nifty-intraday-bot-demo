"""
Logger Configuration

This logger:
- Saves logs to logs/bot.log
- Keeps the last 3 logs (5MB max each)
- Streams real-time logs to the terminal
- Makes debugging and monitoring your bot seamless
"""

import logging
from datetime import datetime
import pytz
from logging.handlers import RotatingFileHandler
import os

# Set timezone
IST = pytz.timezone('Asia/Kolkata')


def get_logger(name: str = "nifty_bot") -> logging.Logger:
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)

    today_str = datetime.now(IST).strftime("%Y%m%d")
    log_filename = f"bot_{today_str}.log"

    logger = logging.getLogger(name)

    # Prevent adding multiple handlers on repeated imports
    if logger.hasHandlers():
        return logger

    logger.setLevel(logging.DEBUG)  # Switch to INFO in production

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # File handler with rotation
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, log_filename),
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=3,
        encoding='utf-8',
        delay=True  # Delay file opening until first write
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
