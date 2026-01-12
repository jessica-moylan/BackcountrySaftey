import logging
import requests
from abc import ABC
from .exceptions import NetworkError

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Abstract base class for all avalanche data scrapers.

    Provides common functionality for fetching and processing data from
    avalanche center websites.

    Attributes:
        base_url (str): The base URL for the scraper.
    """

    def __init__(self, base_url: str):
        """Initialize the scraper with a base URL.

        Args:
            base_url (str): The base URL to scrape data from.
        """
        self.base_url = base_url
        logger.info(f"Initialized {self.__class__.__name__} with URL: {base_url}")

    def fetch_data(self) -> str:
        """Fetch raw HTML data from the base URL.

        Returns:
            str: The HTML content of the page.

        Raises:
            NetworkError: If the request fails or times out.
        """
        try:
            logger.debug(f"Fetching data from {self.base_url}")
            response = requests.get(self.base_url, timeout=10)
            response.raise_for_status()
            logger.info(f"Successfully fetched data from {self.base_url}")
            return response.text
        except requests.RequestException as e:
            logger.error(f"Failed to fetch data from {self.base_url}: {e}")
            raise NetworkError(self.base_url, str(e))
