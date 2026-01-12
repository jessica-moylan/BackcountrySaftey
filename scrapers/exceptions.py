class ScraperError(Exception):
    """Base exception for all scraper-related errors."""

    pass


class NetworkError(ScraperError):
    """Raised when network requests fail or timeout."""

    def __init__(self, url: str, message: str = "Network request failed"):
        self.url = url
        self.message = f"{message}: {url}"
        super().__init__(self.message)


class DataExtractionError(ScraperError):
    """Raised when data cannot be extracted from the HTML/XML."""

    def __init__(self, field: str, message: str = "Failed to extract field"):
        self.field = field
        self.message = f"{message}: {field}"
        super().__init__(self.message)


class InvalidDataError(ScraperError):
    """Raised when scraped data fails validation."""

    def __init__(self, field: str, value: any, reason: str = "Invalid data"):
        self.field = field
        self.value = value
        self.message = f"{reason} for field '{field}': {value}"
        super().__init__(self.message)


class ParsingError(ScraperError):
    """Raised when HTML or XML parsing fails."""

    def __init__(self, content_type: str, message: str = "Parsing failed"):
        self.content_type = content_type
        self.message = f"{message} for {content_type}"
        super().__init__(self.message)


class SnowPilotError(ScraperError):
    """Raised when SnowPilot XML data cannot be loaded or parsed."""

    def __init__(self, url: str, message: str = "SnowPilot error"):
        self.url = url
        self.message = f"{message}: {url}"
        super().__init__(self.message)


class RegionNotFoundError(ScraperError):
    """Raised when a specified region is not recognized."""

    def __init__(self, region: str, available_regions: list = None):
        self.region = region
        self.available_regions = available_regions
        message = f"Region '{region}' not found"
        if available_regions:
            message += f". Available regions: {', '.join(available_regions)}"
        super().__init__(message)


class RateLimitError(ScraperError):
    """Raised when rate limiting is detected from the server."""

    def __init__(self, retry_after: int = None):
        self.retry_after = retry_after
        message = "Rate limit exceeded"
        if retry_after:
            message += f". Retry after {retry_after} seconds"
        super().__init__(message)
