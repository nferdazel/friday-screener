"""Helper utilities untuk berbagai operasi umum.

Module ini berisi fungsi-fungsi helper yang digunakan di berbagai bagian aplikasi.
"""

from typing import Any


def safe_float(value: Any, default: float | None = None) -> float | None:
    """Safely convert value to float.

    Args:
        value: Value to convert
        default: Default value if conversion fails

    Returns:
        Float value or default if conversion fails

    """
    if value is None:
        return default

    try:
        # Handle numpy types
        import numpy as np
        if isinstance(value, (np.integer, np.floating)):
            return float(value)

        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            # Remove common formatting (commas, currency symbols, etc)
            cleaned = value.replace(",", "").replace("$", "").replace("%", "").strip()
            return float(cleaned)
        return default
    except (ValueError, TypeError, AttributeError):
        return default
    except ImportError:
        # If numpy is not available, fall back to standard types
        if isinstance(value, (int, float)):
            return float(value)
        return default


def safe_int(value: Any, default: int | None = None) -> int | None:
    """Safely convert value to int.

    Args:
        value: Value to convert
        default: Default value if conversion fails

    Returns:
        Int value or default if conversion fails

    """
    if value is None:
        return default

    try:
        # Handle numpy types
        import numpy as np
        if isinstance(value, np.integer):
            return int(value)
        if isinstance(value, np.floating):
            return int(float(value))

        if isinstance(value, int):
            return value
        if isinstance(value, (float, str)):
            return int(float(str(value).replace(",", "")))
        return default
    except (ValueError, TypeError, AttributeError):
        return default
    except ImportError:
        # If numpy is not available, fall back to standard types
        if isinstance(value, int):
            return value
        if isinstance(value, (float, str)):
            return int(float(str(value).replace(",", "")))
        return default


def format_currency(value: float | None, currency: str = "IDR") -> str:
    """Format number as currency.

    Args:
        value: Numeric value
        currency: Currency code (default: IDR)

    Returns:
        Formatted currency string

    """
    if value is None:
        return "N/A"

    # For Indonesian Rupiah, use trillion/billion format
    if currency == "IDR":
        if abs(value) >= 1_000_000_000_000:  # Trillion
            return f"Rp {value / 1_000_000_000_000:.2f}T"
        if abs(value) >= 1_000_000_000:  # Billion
            return f"Rp {value / 1_000_000_000:.2f}B"
        if abs(value) >= 1_000_000:  # Million
            return f"Rp {value / 1_000_000:.2f}M"
        return f"Rp {value:,.0f}"

    # For USD or other currencies
    if abs(value) >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f}B"
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:.2f}M"
    return f"${value:,.2f}"


def format_percentage(value: float | None, decimals: int = 2) -> str:
    """Format number as percentage.

    Args:
        value: Numeric value (can be decimal or already percentage)
        decimals: Number of decimal places

    Returns:
        Formatted percentage string

    """
    if value is None:
        return "N/A"

    # If value is likely already a percentage (> 1), use as is
    # Otherwise multiply by 100
    if abs(value) <= 1:
        value = value * 100

    return f"{value:.{decimals}f}%"


def format_ratio(value: float | None, decimals: int = 2) -> str:
    """Format number as ratio.

    Args:
        value: Numeric value
        decimals: Number of decimal places

    Returns:
        Formatted ratio string

    """
    if value is None:
        return "N/A"

    return f"{value:.{decimals}f}x"


def format_number(value: float | None, decimals: int = 2) -> str:
    """Format number with thousands separator.

    Args:
        value: Numeric value
        decimals: Number of decimal places

    Returns:
        Formatted number string

    """
    if value is None:
        return "N/A"

    return f"{value:,.{decimals}f}"


def calculate_percentage_change(old_value: float, new_value: float) -> float:
    """Calculate percentage change between two values.

    Args:
        old_value: Original value
        new_value: New value

    Returns:
        Percentage change (as decimal, e.g., 0.1 = 10% increase)

    """
    if old_value == 0:
        return 0.0
    return (new_value - old_value) / abs(old_value)


def is_growing_trend(values: list[float], min_positive_years: int = 3) -> bool:
    """Check if values show a growing trend.

    Args:
        values: List of values in chronological order
        min_positive_years: Minimum number of positive year-over-year changes

    Returns:
        True if trend is growing, False otherwise

    """
    if len(values) < 2:
        return False

    positive_changes = 0
    for i in range(1, len(values)):
        if values[i] > values[i - 1]:
            positive_changes += 1

    return positive_changes >= min_positive_years


def normalize_ticker(ticker: str) -> str:
    """Normalize stock ticker symbol.

    For Indonesian stocks, adds .JK suffix if not present.

    Args:
        ticker: Stock ticker symbol

    Returns:
        Normalized ticker symbol

    """
    ticker = ticker.strip().upper()

    # Check if it's likely an Indonesian stock (all letters, no suffix)
    if ticker.isalpha() and "." not in ticker:
        # Add .JK suffix for Jakarta Stock Exchange
        return f"{ticker}.JK"

    return ticker


def get_ticker_without_suffix(ticker: str) -> str:
    """Get ticker symbol without exchange suffix.

    Args:
        ticker: Stock ticker with or without suffix

    Returns:
        Ticker without suffix

    """
    if "." in ticker:
        return ticker.split(".")[0]
    return ticker
