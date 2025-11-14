import logging
import sys
import warnings
from typing import Optional

try:
    import pandas as pd
except ImportError:
    pd = None


def get_logger(name: str, level: Optional[int] = None) -> logging.Logger:
    """
    Get configured logger untuk aplikasi.

    Args:
        name: Logger name
        level: Logging level (default: from environment or WARNING)

    Returns:
        Configured logger instance
    """
    # Allow environment variable to control log level
    if level is None:
        import os

        log_level_str = os.getenv("FRIDAY_SCREENER_LOG_LEVEL", "WARNING").upper()
        level = getattr(logging, log_level_str, logging.WARNING)

    logger = logging.getLogger(name)
    logger.setLevel(level or logging.WARNING)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)-8s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.propagate = False

    return logger


def suppress_warnings():
    """Suppress deprecation warnings dari libraries eksternal."""
    # Suppress yfinance deprecation warnings
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    warnings.filterwarnings("ignore", message=".*Ticker.earnings.*")
    warnings.filterwarnings("ignore", category=FutureWarning)
    warnings.filterwarnings("ignore", module="yfinance")

    # Suppress pandas warnings if pandas is available
    if pd is not None:
        try:
            warnings.filterwarnings("ignore", category=pd.errors.SettingWithCopyWarning)
            warnings.filterwarnings("ignore", category=pd.errors.PerformanceWarning)
        except (AttributeError, TypeError):
            # Handle older pandas versions or missing attributes
            pass


def set_log_level(level: str) -> None:
    """
    Set log level for all loggers.

    Args:
        level: Log level name (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    log_level = getattr(logging, level.upper(), logging.WARNING)
    logging.getLogger("src").setLevel(log_level)


# Auto-suppress warnings saat module di-import
suppress_warnings()
