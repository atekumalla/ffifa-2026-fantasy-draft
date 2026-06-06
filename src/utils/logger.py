"""Logging setup for the FIFA 2026 Fantasy Draft app."""

import logging
import sys

from src.config import Config


def setup_logging():
    """Configure logging for the application."""
    level = getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO)

    # Format: timestamp - module - level - message
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(name)-25s | %(levelname)-7s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(console_handler)

    # Suppress noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("gspread").setLevel(logging.WARNING)
    logging.getLogger("google").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.WARNING)
