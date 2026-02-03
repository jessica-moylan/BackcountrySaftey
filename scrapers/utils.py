from datetime import date, timedelta
import re


def get_yesterday_date() -> tuple[str, str, str]:
    """Get yesterday's date formatted for scraping.

    Returns a tuple containing the day, month, and year of yesterday's date,
    each with leading zeros where applicable.

    Returns:
        tuple[str, str, str]: A tuple of (day, month, year) strings.
            - day: Two-digit day with leading zero (e.g., '05', '23')
            - month: Two-digit month with leading zero (e.g., '01', '12')
            - year: Four-digit year (e.g., '2024', '2025')

    Example:
        >>> get_yesterday_date()
        ('09', '01', '2026')  # If today is January 10, 2026
    """
    yesterday = date.today() - timedelta(days=1)
    day = yesterday.strftime("%d")
    month = yesterday.strftime("%m")
    year = yesterday.strftime("%Y")
    return (day, month, year)


def convert_to_inches(length_str):
    # Regex to find numbers followed by ' or "
    # Matches: (optional feet)(') (optional space) (optional inches)(")
    pattern = r"(?P<feet>\d+)\'\s*(?P<inches>\d+(?:\.\d+)?)?\"?"
    match = re.search(pattern, length_str)

    if not match:
        # Fallback for inches-only strings (e.g., "12\"")
        if '"' in length_str:
            return float(length_str.replace('"', ""))
        return 0.0

    feet = int(match.group("feet")) if match.group("feet") else 0
    inches = float(match.group("inches")) if match.group("inches") else 0.0

    return int((feet * 12) + inches)


def clean_numeric(value: str | None) -> int | None:
    if value is None:
        return None
    cleaned = re.sub(r"[\[\],'`\"]", "", value)
    return int(cleaned) if cleaned else None
