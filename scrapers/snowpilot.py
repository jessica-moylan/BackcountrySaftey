import logging
import re
import requests
import xml.etree.ElementTree as ET
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from .exceptions import SnowPilotError

logger = logging.getLogger(__name__)


class SnowPilotClient:
    """Client for fetching and parsing SnowPilot XML snow profile data.

    SnowPilot provides standardized XML representations of snow pit profiles.
    This client downloads and parses these profiles to extract key metadata
    such as location, elevation, aspect, and slope angle.

    Attributes:
        url (str): The URL to the SnowPilot HTML page.
        _root (ET.Element): The root element of the parsed XML document.
    """

    def __init__(self, url: str):
        """Initialize the SnowPilot client and load XML data.

        Args:
            url (str): URL to the SnowPilot HTML page containing XML link.

        Raises:
            SnowPilotError: If XML data cannot be loaded.
        """
        self.url = url
        logger.info(f"Initializing SnowPilot client for: {url}")
        self._root = self._load_xml()
        if self._root is None:
            raise SnowPilotError(url, "Failed to load SnowPilot XML data")

    def _load_xml(self) -> ET.Element | None:
        self._root = None
        try:
            logger.info("Fetching SnowPilot page: %s", self.url)
            soup = BeautifulSoup(requests.get(self.url, timeout=10).text, "html.parser")
            xml_href = next(
                (
                    a["href"]
                    for a in soup.find_all("a", href=True)
                    if "xml" in a.text.lower()
                ),
                None,
            )
            if xml_href is None:
                logger.warning("SnowPilot XML link not found")
                return None

            xml_url = urljoin(self.url, xml_href)
            logger.info("Downloading SnowPilot XML: %s", xml_url)

            xml = requests.get(xml_url, timeout=10).content
            self._root = ET.fromstring(xml)
            return self._root

        except Exception:
            logger.exception("Failed to load SnowPilot XML")
            return None

    def _degrees_to_compass(self, degrees) -> str | None:
        """
        Convert degrees to 8-point compass direction.

        Args:
            degrees: Numeric degrees (0-360) or string containing degrees.

        Returns:
            str | None: Compass direction (N, NE, E, SE, S, SW, W, NW) or None if invalid.
        """
        if degrees is None:
            return None
        try:
            degrees = float("".join(re.findall(r"[\d\.]+", degrees)))
            directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
            index = round(degrees / 45) % 8
            return directions[index]
        except (ValueError, TypeError):
            return None

    @property
    def aspect(self) -> str | None:
        aspect_degrees = self._root.get("aspect") if self._root else None
        return self._degrees_to_compass(aspect_degrees)

    @property
    def slope_angle(self) -> str | None:
        return self._root.get("incline") if self._root else None

    @property
    def elevation(self) -> str | None:
        if self._root is None:
            return None
        location = self._root.find("Location")
        if location is not None:
            return location.get("elv")
        return None

    @property
    def latitude(self) -> str | None:
        return self._root.get("lat") if self._root else None

    @property
    def longitude(self) -> str | None:
        return self._root.get("longitude") if self._root else None
