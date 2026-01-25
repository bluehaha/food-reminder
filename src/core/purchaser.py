"""WooCommerce product purchaser implementation."""

import json
import os
import re
from datetime import datetime
from typing import Any
from urllib.parse import urlencode
import requests
from requests.adapters import HTTPAdapter
from requests.models import Response
from urllib3.util.retry import Retry

from src.core.interfaces import Purchaser
from src.utils.exceptions import PurchaseError
from src.utils.logger import get_logger


class WooCommercePurchaser(Purchaser):
    """WooCommerce-specific purchaser implementation."""

    def __init__(
        self,
        base_url: str,
        timeout: int = 120,
        user_agent: str = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:146.0) Gecko/20100101 Firefox/146.0",
        base_path: str = '',
    ):
        """Initialize purchaser.

        Args:
            base_url: Base URL of the WooCommerce site
            timeout: Request timeout in seconds
            user_agent: User agent string
        """
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._user_agent = user_agent
        self._logger = get_logger(__name__)
        self._session = self._init_session(user_agent, base_path)

    def _init_session(self, user_agent: str, base_path: str) -> requests.Session:
        session = requests.Session()
        session.headers.update({
            "User-Agent": user_agent,
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "zh-TW,zh;q=0.8,en-US;q=0.5,en;q=0.3",
        })

        retry_strategy = Retry(
            total=180,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST"]
        )
        adapter = HTTPAdapter(
            pool_connections=10,
            pool_maxsize=15,
            max_retries=retry_strategy
        )

        session.mount("https://", adapter)
        session.mount("http://", adapter)

        # I am not sure if this function can accelerate the process, so it is disabled for now.
        # self._load_session_cookies_or_create_new(session, os.path.join(base_path, "state/cookies.json"))

        return session

    def _load_session_cookies_or_create_new(self, session: requests.Session, filepath: str) -> None:
        """Load cookies from file into session.

        Args:
            session: Requests session
            filepath: Path to cookies file
        """
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                cookies_dict = json.load(f)
                session.cookies.update(requests.utils.cookiejar_from_dict(cookies_dict))
                self._logger.info(f"Loaded cookies from {filepath}")
        except FileNotFoundError:
            self._logger.info(f"Cookies file {filepath} not found, creating new session")
            response = session.get(f"{self._base_url}/")
            print(response.cookies.items())
            with open(filepath, "w", encoding="utf-8") as f:
                cookies_dict = requests.utils.dict_from_cookiejar(session.cookies)
                json.dump(cookies_dict, f, ensure_ascii=False, indent=4)
                self._logger.info(f"Saved new cookies to {filepath}")

    def add_to_cart(
        self,
        product_url: str,
        product_id: int,
        variation_id: int,
        quantity: int = 1,
        attributes: dict[str, str] | None = None,
    ) -> bool:
        """Add product to cart.

        Args:
            product_url: Product URL or slug (e.g., "product/草莓大福/" or full URL)
            product_id: Product ID
            variation_id: Variation ID
            quantity: Quantity to add
            attributes: Product attributes (e.g., {"盒數": "5盒"})

        Returns:
            True if successfully added to cart

        Raises:
            PurchaseError: If add to cart fails
        """
        self._logger.info(f"Adding product {product_id} (variation {variation_id}) to cart")

        try:
            # Build form data
            form_data = {
                "quantity": str(quantity),
                "add-to-cart": str(product_id),
                "product_id": str(product_id),
                "variation_id": str(variation_id),
            }

            # Add attributes if provided
            if attributes:
                for key, value in attributes.items():
                    form_data[f"attribute_{key}"] = value

            # Construct full URL if needed
            if product_url.startswith("http"):
                full_url = product_url
            else:
                # Remove leading slash if present
                product_url = product_url.lstrip("/")
                full_url = f"{self._base_url}/{product_url}"

            self._logger.debug(f"Posting to URL: {full_url}")
            self._logger.debug(f"Form data: {form_data}")

            # Use form-encoded POST (WooCommerce accepts both multipart and form-encoded)
            # Note: Browser typically uses multipart/form-data, but form-encoded should work

            response = self._session.post(
                url=full_url,
                data=form_data,
                timeout=self._timeout,
                allow_redirects=True,
            )

            # Check for error messages in response
            response_lower = response.text.lower()
            if 'cannot add' in response_lower or 'out of stock' in response_lower or '缺貨' in response.text:
                return False

            return True
        except requests.RequestException as e:
            raise PurchaseError(f"Failed to add to cart: {e}") from e

    def checkout(
        self,
        billing_info: dict[str, Any],
        shipping_info: dict[str, Any],
        payment_info: dict[str, Any],
    ) -> str:
        """Complete checkout process.

        Args:
            billing_info: Billing information dict with keys:
                - first_name, last_name, company, country, address_1, city,
                  postcode, phone, email, carruer_type, invoice_type
            shipping_info: Shipping information dict with keys:
                - method, delivery_date, time_slot (optional)
            payment_info: Payment information dict with keys:
                - method (e.g., "sinopac-self-hosted-credit")
                - card_number, expiry_month, expiry_year, cvv (for credit card)

        Returns:
            Order ID or confirmation number

        Raises:
            PurchaseError: If checkout fails
        """
        self._logger.info("Starting checkout process")

        try:
            # Step 1: Visit checkout page to establish session and get update_order_review_nonce
            self._logger.debug("Visiting checkout page to establish session")
            checkout_page_url = f"{self._base_url}/checkout/"
            checkout_page = self._session.get(
                url=checkout_page_url,
                timeout=self._timeout,
            )

            # Extract update_order_review_nonce from wc_checkout_params
            update_nonce = self._extract_update_order_review_nonce(checkout_page.text)
            if not update_nonce:
                raise PurchaseError("Failed to extract update_order_review_nonce from checkout page")

            self._logger.debug(f"Extracted update_order_review_nonce: {update_nonce[:10]}...")

            # Step 2: Call update_order_review to get the checkout nonce
            self._logger.debug("Calling update_order_review to get checkout nonce")
            checkout_data_for_review = self._build_checkout_payload(
                billing_info, shipping_info, payment_info
            )

            # update_review_data = {
            #     "security": update_nonce,
            #     "payment_method": payment_info.get("method", "sinopac-self-hosted-credit"),
            #     "country": billing_info.get("country", "TW"),
            #     "s_country": shipping_info.get("country", "TW"),
            #     "has_full_address": "false",
            #     "post_data": urlencode(checkout_data_for_review),
            #     "shipping_method[0]": shipping_info.get("method", "local_pickup:8"),
            # }
            #
            # update_review_response = self._session.post(
            #     url=f"{self._base_url}/?wc-ajax=update_order_review",
            #     data=urlencode(update_review_data),
            #     headers={
            #         "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            #         "X-Requested-With": "XMLHttpRequest",
            #     },
            #     timeout=self._timeout,
            # )
            # update_review_response.raise_for_status()
            #
            # # Extract checkout nonce from response
            # checkout_nonce = self._extract_checkout_nonce(update_review_response.text)
            # if not checkout_nonce:
            #     raise PurchaseError("Failed to extract checkout nonce from update_order_review response")
            #
            # self._logger.debug(f"Extracted checkout nonce: {checkout_nonce[:10]}...")

            # Step 3: Submit final checkout with the nonce
            # checkout_data_for_review["woocommerce-process-checkout-nonce"] = checkout_nonce
            checkout_data_for_review["woocommerce-process-checkout-nonce"] = update_nonce
            checkout_data_for_review["_wp_http_referer"] = "/?wc-ajax=update_order_review"

            self._logger.debug("Submitting final checkout")
            checkout_url = f"{self._base_url}/?wc-ajax=checkout"
            response = self._session.post(
                url=checkout_url,
                data=urlencode(checkout_data_for_review),
                headers={
                    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                    "X-Requested-With": "XMLHttpRequest",
                },
                timeout=self._timeout,
            )

            response.raise_for_status()

            # Parse response
            result = response.json()

            if result.get("result") == "success":
                order_id = result.get("order_id", "unknown")
                self._logger.info(f"Checkout successful, order ID: {order_id}")
                return str(order_id)
            else:
                error_msg = result.get("messages", "Unknown error")
                raise PurchaseError(f"Checkout failed: {error_msg}")

        except requests.RequestException as e:
            raise PurchaseError(f"Checkout request failed: {e}") from e
        except Exception as e:
            raise PurchaseError(f"Checkout failed: {e}") from e

    def _extract_update_order_review_nonce(self, html: str) -> str | None:
        """Extract update_order_review nonce from checkout page.

        Args:
            html: HTML content of checkout page

        Returns:
            Nonce value if found, None otherwise
        """
        # Look for wc_checkout_params.update_order_review_nonce in JavaScript
        pattern = r'"update_order_review_nonce"\s*:\s*"([a-f0-9]+)"'
        match = re.search(pattern, html)
        if match:
            return match.group(1)

        return None

    def _extract_checkout_nonce(self, response_text: str) -> str | None:
        """Extract checkout nonce from update_order_review response.

        Args:
            response_text: Response text from update_order_review AJAX call

        Returns:
            Nonce value if found, None otherwise
        """
        # Look for nonce in input field within the JSON response
        # The response contains HTML fragments with the nonce
        pattern = r'name=\\"woocommerce-process-checkout-nonce\\" value=\\"([a-f0-9]+)\\"'
        match = re.search(pattern, response_text)
        if match:
            return match.group(1)

        # Alternative: unescaped version
        pattern2 = r'name="woocommerce-process-checkout-nonce" value="([a-f0-9]+)"'
        match = re.search(pattern2, response_text)
        if match:
            return match.group(1)

        return None

    def _build_checkout_payload(
        self,
        billing_info: dict[str, Any],
        shipping_info: dict[str, Any],
        payment_info: dict[str, Any],
    ) -> dict[str, str]:
        """Build checkout form payload.

        Args:
            billing_info: Billing information
            shipping_info: Shipping information
            payment_info: Payment information

        Returns:
            Form data dictionary
        """
        # Build base payload with order attribution
        payload = {
            "wc_order_attribution_source_type": "typein",
            "wc_order_attribution_referrer": "(none)",
            "wc_order_attribution_utm_campaign": "(none)",
            "wc_order_attribution_utm_source": "(direct)",
            "wc_order_attribution_utm_medium": "(none)",
            "wc_order_attribution_utm_content": "(none)",
            "wc_order_attribution_utm_id": "(none)",
            "wc_order_attribution_utm_term": "(none)",
            "wc_order_attribution_utm_source_platform": "(none)",
            "wc_order_attribution_utm_creative_format": "(none)",
            "wc_order_attribution_utm_marketing_tactic": "(none)",
            "wc_order_attribution_session_entry": self._base_url,
            "wc_order_attribution_session_pages": "5",
            "wc_order_attribution_session_count": "1",
            "wc_order_attribution_user_agent": self._user_agent,
        }

        # Add billing info
        payload.update({
            "billing_first_name": billing_info.get("first_name", ""),
            "billing_last_name": billing_info.get("last_name", ""),
            "billing_company": billing_info.get("company", ""),
            "billing_country": billing_info.get("country", "TW"),
            "billing_address_1": billing_info.get("address_1", "none"),
            "billing_city": billing_info.get("city", "none"),
            "billing_postcode": billing_info.get("postcode", "none"),
            "billing_phone": billing_info.get("phone", ""),
            "billing_email": billing_info.get("email", ""),
            "billing_carruer_type": str(billing_info.get("carruer_type", "1")),
            "billing_invoice_type": billing_info.get("invoice_type", "p"),
            "billing_customer_identifier": billing_info.get("customer_identifier", ""),
            "billing_love_code": billing_info.get("love_code", ""),
            "billing_carruer_num": billing_info.get("carruer_num", ""),
        })

        # Add shipping info
        shipping_method = shipping_info.get("method", "local_pickup:8")
        payload.update({
            "shipping_first_name": shipping_info.get("first_name", ""),
            "shipping_last_name": shipping_info.get("last_name", ""),
            "shipping_company": shipping_info.get("company", ""),
            "shipping_country": shipping_info.get("country", "TW"),
            "shipping_address_1": shipping_info.get("address_1", ""),
            "shipping_address_2": shipping_info.get("address_2", ""),
            "shipping_city": shipping_info.get("city", ""),
            "shipping_state": shipping_info.get("state", ""),
            "shipping_postcode": shipping_info.get("postcode", ""),
            "shipping_phone": shipping_info.get("phone", ""),
            "shipping_method[0]": shipping_method,
            "e_deliverydate_0": self._get_earliest_delivery_date(shipping_method),
        })

        # Add payment info
        payment_method = payment_info.get("method", "sinopac-self-hosted-credit")
        payload["payment_method"] = payment_method

        if payment_method == "sinopac-self-hosted-credit":
            payload.update({
                "as_sinopac_card_number": payment_info.get("card_number", ""),
                "as_sinopac_expiry_month": payment_info.get("expiry_month", ""),
                "as_sinopac_expiry_year": payment_info.get("expiry_year", ""),
                "as_sinopac_card_cvv": payment_info.get("cvv", ""),
            })

        return payload

    def _get_earliest_delivery_date(
        self,
        shipping_method: str = "local_pickup:8",
    ) -> str:
        """Get the earliest available delivery date.

        Args:
            shipping_method: Shipping method ID (default: "local_pickup:8")

        Returns:
            Date string in YYYY-MM-DD format

        Raises:
            PurchaseError: If no dates available or API call fails
        """
        dates = self._get_available_delivery_dates(shipping_method)

        if not dates:
            raise PurchaseError("No delivery dates available")

        today = datetime.now().date()

        # Find the first date that is later than today
        for date_str, availability in dates:
            try:
                # Parse the date
                date_obj = datetime.strptime(date_str, "%m-%d-%Y")

                # Check if date is later than today
                if date_obj.date() > today:
                    formatted_date = date_obj.strftime("%Y-%m-%d")
                    self._logger.info(f"Earliest delivery date: {formatted_date} (availability: {availability})")
                    return formatted_date

            except ValueError as e:
                self._logger.warning(f"Failed to parse date '{date_str}': {e}")
                continue

        # If no future date found, raise error
        raise PurchaseError("No delivery dates available after today")

    def _get_available_delivery_dates(
        self,
        shipping_method: str = "local_pickup:8",
    ) -> list[tuple[str, str]]:
        """Fetch available delivery dates from the API.

        Args:
            shipping_method: Shipping method ID (default: "local_pickup:8")

        Returns:
            List of tuples containing (date_string, availability)
            Date format: "M-D-YYYY" (e.g., "3-5-2024")
            Availability: number string or "Unlimited"

        Raises:
            PurchaseError: If API call fails or cannot parse dates
        """
        self._logger.info("Fetching available delivery dates")

        try:
            # Build request data
            request_data = {
                "shipping_method": shipping_method,
                "settings_based_on": "category_shipping",
                "setting_ids[]": "11",
                "called_from": "",
                "vendor_id": "0",
            }

            # Call the API
            response = self._session.post(
                url=f"{self._base_url}/?wc-ajax=orddd_update_delivery_session",
                data=urlencode(request_data, doseq=True),
                headers={
                    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                    "X-Requested-With": "XMLHttpRequest",
                },
                timeout=self._timeout,
            )

            response.raise_for_status()

            # Parse the response to extract dates
            # Format: '3-5-2024>Available Deliveries: 30','3-6-2024>Available Deliveries: 28',...
            response_text = response.text
            date_pattern = r"'(\d+-\d+-\d+)>Available Deliveries: (\d+|Unlimited)'"
            matches = re.findall(date_pattern, response_text)

            if not matches:
                raise PurchaseError("No delivery dates found in API response")

            self._logger.debug(f"Found {len(matches)} available delivery dates")
            return matches

        except Exception as e:
            raise PurchaseError(f"Failed to fetch delivery dates: {e}") from e
