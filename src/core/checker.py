"""Product availability checker for WooCommerce sites."""

import re
import time
from typing import Optional

import requests

from src.core.interfaces import Checker
from src.utils.exceptions import CheckerError
from src.utils.logger import get_logger

logger = get_logger(__name__)


class WooCommerceChecker(Checker):
    """Checks product availability on WooCommerce sites."""

    def __init__(
        self,
        timeout: int = 30,
        user_agent: str = "Mozilla/5.0",
        max_retries: int = 3,
        retry_delay: int = 2,
    ):
        """Initialize checker.

        Args:
            timeout: Request timeout in seconds
            user_agent: User agent string
            max_retries: Maximum number of retries
            retry_delay: Delay between retries in seconds
        """
        self.timeout = timeout
        self.user_agent = user_agent
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create configured requests session."""
        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-US,en;q=0.9",
            }
        )
        return session

    def is_available(self, url: str) -> bool:
        """Check if product is available using WooCommerce stock indicators.

        Uses multiple methods:
        1. Check product div class for 'instock' or 'outofstock'
        2. Check for 'out_of_stock_wrapper' div

        Args:
            url: Product URL to check

        Returns:
            True if product is in stock, False otherwise

        Raises:
            CheckerError: If check fails
        """
        html = self._fetch_html(url)

        # Method 1: Check product div class (primary method)
        availability = self._check_product_class(html)
        if availability is not None:
            logger.info(f"Product availability determined from class: {availability}")
            return availability

        # Method 2: Check for out_of_stock_wrapper (secondary)
        if "out_of_stock_wrapper" in html:
            logger.info("Found out_of_stock_wrapper - product unavailable")
            return False

        # If we can't determine, log warning and assume unavailable
        logger.warning("Could not determine stock status - assuming unavailable")
        return False

    def _fetch_html(self, url: str) -> str:
        """Fetch HTML content with retries.

        Args:
            url: URL to fetch

        Returns:
            HTML content

        Raises:
            CheckerError: If fetch fails after retries
        """
        last_error = None
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Fetching {url} (attempt {attempt + 1}/{self.max_retries})")
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
                return response.text
            except requests.RequestException as e:
                last_error = e
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)

        raise CheckerError(
            f"Failed to fetch {url} after {self.max_retries} attempts: {last_error}"
        )

    def _check_product_class(self, html: str) -> Optional[bool]:
        """Check product availability from div class attribute.

        Args:
            html: HTML content

        Returns:
            True if in stock, False if out of stock, None if unknown
        """
        # Look for <div id="product-XXXX" class="...">
        match = re.search(r'<div[^>]*id="product-\d+"[^>]*class="([^"]*)"', html)
        if not match:
            return None

        classes = match.group(1)
        if "outofstock" in classes:
            return False
        if "instock" in classes:
            return True

        return None
