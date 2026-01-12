import logging
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from typing import Any
import time
import re

from .scraper_base import BaseScraper
from .snowpilot import SnowPilotClient
from .exceptions import NetworkError

logger = logging.getLogger(__name__)

# Headers to mimic a browser request
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

# Mapping of Utah avalanche forecast region names to their numeric IDs
lookup = {
    "Logan": 1,
    "Ogden": 2,
    "Uintas": 3,
    "Salt Lake": 4,
    "Provo": 5,
    "Skyline": 6,
    "Moab": 7,
    "Abajos": 8,
    "Southwest": 9,
}


class UtahScraper(BaseScraper):
    """Scraper for Utah Avalanche Center observation and avalanche data.

    This scraper fetches and parses daily observation reports and avalanche
    incidents from the Utah Avalanche Center website. It extracts:
    - Geographic data (coordinates, elevation, aspect, slope angle)
    - Snow conditions and observations
    - Avalanche problems and danger ratings
    - Avalanche incident details (trigger, size, casualties)

    Attributes:
        day (str): Two-digit day of month.
        month (str): Two-digit month.
        year (str): Four-digit year.
        url (str): Constructed URL for the observation query.
        session (requests.Session): Persistent session with browser headers.
    """

    def __init__(self, date: tuple[str, str, str]):
        """Initialize the Utah scraper with a specific date.

        Args:
            date: Tuple of (day, month, year) as strings with leading zeros.
                  Example: ('15', '12', '2024')
        """
        self.day, self.month, self.year = date
        self.url = f"https://utahavalanchecenter.org/observations?term=All&fodv%5Bmin%5D%5Bdate%5D={self.month}%2F{self.day}%2F{self.year}&fodv%5Bmax%5D%5Bdate%5D={self.month}%2F{self.day}%2F{self.year}"
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        logger.info(
            f"Initialized UtahScraper for date: {self.year}-{self.month}-{self.day}"
        )
        super().__init__(self.url)

    def get_field_value(self, web_access: BeautifulSoup, label_text: str) -> str | None:
        """Extract field value from observation page by label text.

        Args:
            web_access: BeautifulSoup object of the observation page.
            label_text: The exact label text to search for.

        Returns:
            str | None: The field value text, or None if not found.
        """
        label = web_access.find("div", class_="field-label", string=label_text)
        if label is None:
            logger.debug(f"Field label not found: {label_text}")
            return None
        value_div = label.find_next_sibling("div")
        return value_div.get_text(strip=True) if value_div else None

    def get_lat_lon(
        self, web_access: BeautifulSoup
    ) -> tuple[float | None, float | None]:
        """
        Extract latitude and longitude coordinates from observation page.

        Attempts to extract coordinates from the embedded map script. If not found,
        falls back to SnowPilot profile if available.

        Args:
            web_access: BeautifulSoup object of the observation page.

        Returns:
            tuple: (longitude, latitude) or (None, None) if unavailable.
        """
        script_tag = web_access.find("script", string=re.compile("window.Backdrop"))
        # Directly search for the POINT WKT in the script text
        match = re.search(
            r'geofield_formatter"\s*:\s*\{.*?"wkt"\s*:\s*"POINT \(([-\d.]+) ([-\d.]+)\)"',
            script_tag.string,
            re.DOTALL,
        )
        longitude, latitude = None, None
        if match:
            longitude = float(match.group(1))
            latitude = float(match.group(2))
            logger.debug(f"Extracted coordinates from map: ({longitude}, {latitude})")
            return longitude, latitude
        else:  # try to check if there is a snowprofile
            logger.debug("Coordinates not found in map, checking SnowPilot")
            snowpilot_table = self.get_field_value(web_access, "Snow Pilot URL")
            if snowpilot_table is None:
                logger.debug("No SnowPilot URL available")
                return longitude, latitude
            try:
                snowpilot = SnowPilotClient(snowpilot_table)
                longitude = snowpilot.longitude
                latitude = snowpilot.latitude
                logger.debug(
                    f"Extracted coordinates from SnowPilot: ({longitude}, {latitude})"
                )
                return longitude, latitude
            except Exception as e:
                logger.exception(f"Error parsing Snow Pilot XML: {e}")
                return longitude, latitude

    def get_region(self, web_access: BeautifulSoup) -> tuple[str, str]:
        """
        Extract parent region and subregion names.

        Args:
            web_access: BeautifulSoup object of the observation page.

        Returns:
            tuple: (parent_region, subregion) strings.
        """
        region = self.get_field_value(web_access, "Region")
        parts = [p.strip() for p in region.split("»")]
        parent, subregion = parts[0], parts[-1]
        logger.debug(f"Extracted region: {parent} » {subregion}")
        return parent, subregion

    def get_snow_profile(
        self, web_access: BeautifulSoup
    ) -> tuple[str | None, str | None, str | None]:
        """
        Extract snow profile information (aspect, elevation, slope angle).

        First attempts to extract from the observation page, then falls back to
        SnowPilot profile if available.

        Args:
            web_access: BeautifulSoup object of the observation page.

        Returns:
            tuple: (aspect, elevation, slope_angle) or (None, None, None) if unavailable.
        """
        aspect, elevation, slope_angle = None, None, None
        # try to get the information for snow profile from UTAC
        aspect = self.get_field_value(web_access, "Aspect")
        elevation = self.get_field_value(web_access, "Elevation")
        slope_angle = self.get_field_value(web_access, "Slope Angle")
        if slope_angle is not None:
            if slope_angle.lower() == "unknown":
                slope_angle = None
            else:
                slope_angle = "".join(re.findall(r"[\d\.]+", slope_angle))

        # is there any of the values missing
        if aspect is not None and elevation is not None and slope_angle is not None:
            logger.debug(
                f"Extracted snow profile: aspect={aspect}, elevation={elevation}, angle={slope_angle}"
            )
            return aspect, elevation, slope_angle

        # is there a snow profile table?
        logger.debug("Some snow profile data missing, checking SnowPilot")
        snowpilot_table = self.get_field_value(web_access, "Snow Pilot URL")
        if snowpilot_table is None:
            logger.debug("No SnowPilot URL available for snow profile data")
            return aspect, elevation, slope_angle
        try:
            snowpilot = SnowPilotClient(snowpilot_table)
            aspect = aspect or snowpilot.aspect
            slope_angle = slope_angle or snowpilot.slope_angle
            elevation = elevation or snowpilot.elevation
            logger.debug(
                f"Merged snow profile with SnowPilot: aspect={aspect}, elevation={elevation}, angle={slope_angle}"
            )
        except Exception as e:
            logger.exception("Error parsing Snow Pilot XML: %s", e)
            return None, None, None
        return aspect, elevation, slope_angle

    def get_avalanche_problem(
        self, index: int, web_access: BeautifulSoup
    ) -> tuple[str | None, str | None]:
        """
        Extract avalanche problem and trend from observation page.

        Args:
            index: Problem index (1 or 2) to extract.
            web_access: BeautifulSoup object of the observation page.

        Returns:
            tuple: (problem_type, trend) or (None, None) if not found.
        """
        fieldset = web_access.find("fieldset", class_=f"group-avy-problem-{index}")
        if fieldset is None:
            return None, None
        data = {}

        labels = fieldset.find_all("div", class_="field-label")

        for label in labels:
            key = label.get_text(strip=True)
            value_div = label.find_next_sibling("div", class_="text_02 mb2")
            value = value_div.get_text(strip=True) if value_div else None
            data[key] = value

        return data.get("Problem"), data.get("Trend")

    def get_red_flags(self, web_access: BeautifulSoup) -> list[str] | None:
        """
        Extract all red flag warnings from observation page.

        Args:
            web_access: BeautifulSoup object of the observation page.

        Returns:
            list[str] | None: List of red flag warnings, or None if not found.
        """
        # Find the label div exactly
        label_div = web_access.find(
            "div", string=lambda t: t and t.strip() == "Red Flags"
        )
        if not label_div:
            return None

        values = []
        for sib in label_div.find_next_siblings():
            # Stop if we reach the next label if this
            if "field-label" in sib.get("class", []):
                break
            # Only include value divs
            if "text_02" in sib.get("class", []):
                values.append(sib.get_text(strip=True))
        return values

    def _get_base_info(self, web_url: str, web_access: BeautifulSoup) -> dict[str, Any]:
        """
        Extract base information common to all report types.

        Args:
            web_url: URL of the observation/avalanche page.
            web_access: BeautifulSoup object of the page.

        Returns:
            dict: Base information dictionary including location, region, and geography.
        """
        longitude, latitude = self.get_lat_lon(web_access)
        parent_region, subregion = self.get_region(web_access)
        aspect, elevation, slope_angle = self.get_snow_profile(web_access)
        base_info = {
            "report_id": web_url.split("/")[-1],
            "state_id": 45,
            "state_name": "Utah",
            "report_url": web_url,
            "observation_date": f"{self.year}-{self.month}-{self.day}",
            "location_name": web_access.find(
                "div", class_="field-label", string="Location Name or Route"
            )
            .find_next_sibling("div")
            .get_text(strip=True),
            "region_id": lookup.get(parent_region),
            "region_name": parent_region,
            "sub-region_name": subregion,
            "latitude": latitude,
            "longitude": longitude,
            "elevation_ft": elevation,
            "aspect": aspect,
            "slope_angle": slope_angle,
        }
        return base_info

    def _normalize_avalanche(
        self, web_url: str, web_access: BeautifulSoup
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """
        Parse and normalize avalanche incident data.

        Args:
            web_url: URL of the avalanche report page.
            web_access: BeautifulSoup object of the page.

        Returns:
            tuple: (base_info dict, avalanche_information dict)
        """
        logger.debug(f"Normalizing avalanche report: {web_url}")
        base_info = self._get_base_info(web_url, web_access)
        avalanche_information = {
            "report_id": web_url.split("/")[-1],
            "avalanche_date": datetime.strptime(
                self.get_field_value(web_access, "Avalanche Date"), "%A, %B %d, %Y"
            ).strftime("%Y-%m-%d"),
            "trigger": self.get_field_value(web_access, "Trigger"),
            "trigger_additional": self.get_field_value(
                web_access, "Trigger: additional info"
            ),
            "avalanche_type": self.get_field_value(web_access, "Avalanche Type"),
            "problem": self.get_field_value(web_access, "Avalanche Problem"),
            "weak_layer": self.get_field_value(web_access, "Weak Layer"),
            "depth": self.get_field_value(web_access, "Depth"),
            "width_feet": self.get_field_value(web_access, "Width"),
            "vertical_feet": self.get_field_value(web_access, "Vertical"),
            "Caught": self.get_field_value(web_access, "Caught"),
            "Carried": self.get_field_value(web_access, "Carried"),
        }
        return base_info, avalanche_information

    def _normalize_observation(
        self, web_url: str, web_access: BeautifulSoup
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """
        Parse and normalize observation data.

        Args:
            web_url: URL of the observation page.
            web_access: BeautifulSoup object of the page.

        Returns:
            tuple: (base_info dict, snow_observations dict)
        """
        logger.debug(f"Normalizing observation: {web_url}")
        base_info = self._get_base_info(web_url, web_access)
        problem1, trend1 = self.get_avalanche_problem(index=1, web_access=web_access)
        problem2, trend2 = self.get_avalanche_problem(index=2, web_access=web_access)
        snow_observations = {
            "red_flags": self.get_red_flags(web_access),
            "new_snow_depth": self.get_field_value(web_access, "New Snow Depth"),
            "new_snow_density": self.get_field_value(web_access, "New Snow Density"),
            "snow_surface_conditions": self.get_field_value(
                web_access, "Snow Surface Conditions"
            ),
            "avy_problem_1": problem1,
            "avy_problem_1_trend": trend1,
            "avy_problem_2": problem2,
            "avy_problem_2_trend": trend2,
            "today_rating": self.get_field_value(
                web_access, "Today's Observed Danger Rating"
            ),
            "tomorrow_rating": self.get_field_value(
                web_access, "Tomorrows Estimated Danger Rating"
            ),
            "report_id": web_url.split("/")[-1],
        }
        return base_info, snow_observations

    def get_data(self) -> list[tuple[dict, dict]]:
        """
        Fetch and parse all observation and avalanche reports for the specified date.

        Retrieves all report links, then iterates through each one to extract
        and normalize the data.

        Returns:
            list: List of tuples containing (base_info, specific_data) for each report.

        Raises:
            NetworkError: If a report page cannot be reached.
            ValueError: If an unsupported report type is encountered.
        """
        logger.info(f"Fetching data for {self.year}-{self.month}-{self.day}")
        table_links = self.extract_report_links()
        logger.info(f"Found {len(table_links)} reports to process")
        results = []

        for link in table_links:
            page_url = f"https://utahavalanchecenter.org{link}"
            try:
                logger.debug(f"Processing report: {page_url}")
                time.sleep(1)  # Add delay between requests
                web_access = BeautifulSoup(
                    self.session.get(page_url, timeout=10).text, features="html.parser"
                )
                first_word = link.split("/")[1]
                if first_word == "avalanche":
                    data = self._normalize_avalanche(page_url, web_access)
                    results.append(data)
                elif first_word == "observation":
                    data = self._normalize_observation(page_url, web_access)
                    results.append(data)
                else:
                    logger.error(f"Unsupported report type: {first_word}")
                    raise ValueError(f"{first_word} data is not currently supported")
            except requests.RequestException as e:
                logger.error(f"Failed to fetch {page_url}: {e}")
                raise NetworkError(page_url, "Could not reach report page")

        logger.info(f"Successfully processed {len(results)} reports")
        return results

    def extract_report_links(self) -> list[str]:
        """
        Extract all report links from the observations search page.

        Returns:
            list[str]: List of relative URLs for each report.

        Raises:
            NetworkError: If the page cannot be reached or parsed.
        """
        try:
            logger.debug(f"Extracting report links from: {self.url}")
            response = self.session.get(self.url, timeout=10)
            main_page = BeautifulSoup(response.text, "html.parser")
            get_table = main_page.find("div", class_="view-content")

            table = get_table.find("table")

            links = [link.get("href") for link in table.find_all("a")]
            logger.debug(f"Found {len(links)} report links")
            return links

        except Exception as e:
            logger.error(f"Error extracting report links: {e}")
            raise NetworkError(self.url, f"Failed to extract report links: {e}")
