from datetime import date, timedelta


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
