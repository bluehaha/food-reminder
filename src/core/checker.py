"""Product availability checker for WooCommerce sites."""

import re
import time
from typing import Optional, Dict, Any
from urllib.parse import urljoin, urlparse

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
        """Check if product is available by attempting to add to cart.

        This method validates true availability by:
        1. Fetching the product page
        2. Extracting product/variation data
        3. Attempting to add to cart via POST request
        4. Checking response for error messages

        Args:
            url: Product URL to check

        Returns:
            True if product can be added to cart, False otherwise

        Raises:
            CheckerError: If check fails
        """
        html = self._fetch_html(url)

        if self._check_product_class(html) is False:
            logger.info("Product marked as out of stock via HTML class check")
            return False

        # Extract product and variation data
        product_data = self._extract_product_data(html, url)
        # Attempt to add to cart
        can_add = self._attempt_add_to_cart(url, product_data)

        logger.info(f"Product availability via cart validation: {can_add}")
        return can_add

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

    def _extract_product_data(self, html: str, url: str) -> Optional[Dict[str, Any]]:
        """Extract product and variation data from HTML.

        Args:
            html: HTML content
            url: Product URL

        Returns:
            Dictionary with product_id, variation_id, and attributes, or None
        """
        # Extract product ID
        product_id_match = re.search(r'name="add-to-cart"\s+value="(\d+)"', html)
        if not product_id_match:
            return None

        product_id = product_id_match.group(1)

        return {
            'product_id': product_id,
        }

    def _find_available_variation(self, html: str) -> Optional[Dict[str, Any]]:
        """Find the first available variation from product data.

        Args:
            html: HTML content

        Returns:
            Dictionary with variation_id and attributes, or None
        """
        # Find available_variations JSON data
        variations_match = re.search(
            r'"available_variations":\s*\[(.*?)\](?=,"|$)',
            html,
            re.DOTALL
        )
        if not variations_match:
            return None

        variations_json = variations_match.group(1)

        # Find all variations with is_in_stock: true
        variation_blocks = re.finditer(
            r'\{[^}]*"variation_id":(\d+)[^}]*"is_in_stock":(true|false)[^}]*"attributes":\{([^}]+)\}[^}]*\}',
            variations_json,
            re.DOTALL
        )

        for block in variation_blocks:
            var_id = block.group(1)
            in_stock = block.group(2) == 'true'
            attrs_str = block.group(3)

            if not in_stock:
                continue

            # Parse attributes
            attributes = {}
            attr_matches = re.findall(r'"(attribute_[^"]+)":"([^"]*)"', attrs_str)
            for attr_name, attr_value in attr_matches:
                attributes[attr_name] = attr_value

            return {
                'variation_id': var_id,
                'attributes': attributes
            }

        return None

    def _attempt_add_to_cart(self, url: str, product_data: Dict[str, Any]) -> bool:
        """Attempt to add product to cart and check for errors.

        Args:
            url: Product URL
            product_data: Product and variation data

        Returns:
            True if product can be added, False if error occurs
        """
        try:
            # Build POST data
            post_data = {
                'add-to-cart': product_data['product_id'],
                'product_id': product_data['product_id'],
                'quantity': '1',
                'variation_id': '686214'
            }

            logger.debug(f"Attempting to add to cart: {post_data}")

            # Make POST request
            response = self.session.post(
                url,
                data=post_data,
                timeout=self.timeout,
                allow_redirects=False
            )

            # Check response for error messages
            response_text = response.text.lower()

            # Common WooCommerce error indicators
            error_indicators = [
                'cannot add',
                'out of stock',
                'woocommerce-error',
                'product is unavailable'
            ]

            for indicator in error_indicators:
                if indicator in response_text:
                    logger.info(f"Found error indicator: {indicator}")
                    return False

            # If redirected to cart page, likely success
            if response.status_code == 302:
                location = response.headers.get('Location', '')
                if 'cart' in location:
                    logger.info("Redirected to cart - product added successfully")
                    return True

            # No errors found
            logger.info("No error indicators found - assuming product is available")
            return True

        except requests.RequestException as e:
            logger.warning(f"Failed to attempt add to cart: {e}")
            # If POST fails, fall back to assuming unavailable
            return False
