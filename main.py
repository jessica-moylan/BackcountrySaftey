"""Main entry point for the Backcountry Safety data scraper.

This script initializes and runs the Utah Avalanche Center scraper
to collect observation and avalanche data for analysis.
"""

import logging
import sys
from scrapers.utils import get_yesterday_date
from scrapers.utah_scraper import UtahScraper
from scrapers.exceptions import ScraperError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("scraper.log")],
)

logger = logging.getLogger(__name__)

REGION = "Salt Lake"
FROM_DATE = "12"

if __name__ == "__main__":
    try:
        logger.info("Starting Backcountry Safety scraper")
        utah = UtahScraper(get_yesterday_date())
        data = utah.get_data()
        print(data)
        logger.info(f"{len(data)} reports were collected for {get_yesterday_date()}")

    except ScraperError as e:
        logger.error(f"Scraper error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        sys.exit(1)
