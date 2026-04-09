# core/utils/logger.py

import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime

LOG_DIR = "logs"

# Ensure logs directory exists
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)


def get_logger(name="app"):
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger  # Prevent duplicate handlers

    logger.setLevel(logging.INFO)

    # ================= FORMAT ================= #
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        "%Y-%m-%d %H:%M:%S"
    )

    # ================= FILE HANDLER ================= #
    file_handler = RotatingFileHandler(
        f"{LOG_DIR}/{name}.log",
        maxBytes=5 * 1024 * 1024,   # 5 MB
        backupCount=5
    )
    file_handler.setFormatter(formatter)

    # ================= CONSOLE HANDLER ================= #
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


# ================= GLOBAL LOGGER ================= #
logger = get_logger("backend")


# ================= HELPER FUNCTIONS ================= #

def log_info(message, extra=None):
    logger.info(format_message(message, extra))


def log_warning(message, extra=None):
    logger.warning(format_message(message, extra))


def log_error(message, extra=None):
    logger.error(format_message(message, extra))


def log_debug(message, extra=None):
    logger.debug(format_message(message, extra))


# ================= STRUCTURED FORMAT ================= #

def format_message(message, extra):
    if not extra:
        return message

    try:
        extra_str = " | ".join([f"{k}={v}" for k, v in extra.items()])
        return f"{message} | {extra_str}"
    except Exception:
        return message