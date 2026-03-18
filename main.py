"""Main entry point for the Backcountry Safety data scraper.

This script initializes and runs the Utah Avalanche Center scraper
to collect observation and avalanche data for analysis.
"""

import logging
import sys
from pathlib import Path

# Support running this script directly from repository root with a src layout.
sys.path.insert(0, str(Path(__file__).parent / "src"))

from backcountrysaftey.database.db_utils import get_all_in_region


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
    # try:
    #     logger.info("Starting Backcountry Safety scraper")
    #     utah = UtahScraper(get_yesterday_date())
    #     logger.info(
    #         f"{len(utah.get_data())} reports were collected for {get_yesterday_date()}"
    #     )

    # except ScraperError as e:
    #     logger.error(f"Scraper error: {e}")
    #     sys.exit(1)
    # except Exception as e:
    #     logger.exception(f"Unexpected error: {e}")
    #     sys.exit(1)

    print(len(get_all_in_region(4)))
