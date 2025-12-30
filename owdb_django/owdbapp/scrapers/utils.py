"""
Shared utility functions for scrapers.

Consolidates common text cleaning, date parsing, and year extraction
functions used across all scraper modules.
"""

import re
from datetime import datetime
from typing import Optional


def clean_text(text: str) -> str:
    """
    Clean extracted text by removing reference markers and normalizing whitespace.

    Args:
        text: Raw text to clean

    Returns:
        Cleaned text with normalized whitespace
    """
    if not text:
        return ""
    # Remove reference markers like [1], [2], etc.
    text = re.sub(r"\[\d+\]", "", text)
    # Remove extra whitespace
    text = " ".join(text.split())
    return text.strip()


def parse_year(text: str) -> Optional[int]:
    """
    Extract a 4-digit year (1900-2099) from text.

    Args:
        text: Text that may contain a year

    Returns:
        Year as integer, or None if not found
    """
    if not text:
        return None
    match = re.search(r"\b(19|20)\d{2}\b", text)
    if match:
        return int(match.group())
    return None


def parse_date(text: str) -> Optional[str]:
    """
    Parse various date formats and return ISO format (YYYY-MM-DD).

    Supported formats:
    - January 1, 2020
    - 1 January 2020
    - 2020-01-01
    - 01.01.2020 (European)
    - 01/01/2020 (US)

    Args:
        text: Text containing a date

    Returns:
        Date in YYYY-MM-DD format, or None if parsing fails
    """
    if not text:
        return None

    # Pattern-format pairs for date extraction
    patterns = [
        # ISO format: 2020-01-01
        (r"(\d{4})-(\d{2})-(\d{2})", lambda m: f"{m.group(1)}-{m.group(2)}-{m.group(3)}", "%Y-%m-%d"),
        # US format: January 1, 2020
        (r"(\w+) (\d{1,2}), (\d{4})", lambda m: f"{m.group(1)} {m.group(2)}, {m.group(3)}", "%B %d, %Y"),
        # UK format: 1 January 2020
        (r"(\d{1,2}) (\w+) (\d{4})", lambda m: f"{m.group(1)} {m.group(2)} {m.group(3)}", "%d %B %Y"),
        # European format: 01.01.2020
        (r"(\d{2})\.(\d{2})\.(\d{4})", lambda m: f"{m.group(1)}.{m.group(2)}.{m.group(3)}", "%d.%m.%Y"),
        # US slash format: 01/01/2020
        (r"(\d{1,2})/(\d{1,2})/(\d{4})", lambda m: f"{m.group(1)}/{m.group(2)}/{m.group(3)}", "%m/%d/%Y"),
    ]

    for pattern, date_builder, date_format in patterns:
        match = re.search(pattern, text)
        if match:
            try:
                date_str = date_builder(match)
                dt = datetime.strptime(date_str, date_format)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue

    return None
