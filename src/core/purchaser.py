"""WooCommerce product purchaser implementation."""

import json
import os
import re
from datetime import datetime
from typing import Any
from urllib.parse import urlencode

from src.config.models import PurchaseConfig
from src.core.notifier import SlackNotifier
from src.utils.exceptions import Purchase502Error, PurchaseError
from src.utils.logger import get_logger

import requests
from requests.models import Response
import concurrent.futures


class WooCommercePurchaser():
    """WooCommerce-specific purchaser implementation."""

    def __init__(
        self,
        config: PurchaseConfig,
        slack_notifier: SlackNotifier,
        base_path: str = '',
    ):
        """Initialize purchaser.

        Args:
            config: Purchase configuration
            slack_notifier: Slack notifier instance
            base_path: Base path for storing state files
        """
        self._config = config
        self._slack_notifier = slack_notifier
        self._logger = get_logger(__name__)
        self._session = self._init_session(base_path)
        self._refresh_flags()

    def _init_session(self, base_path: str) -> requests.Session:
        session = requests.Session()
        session.headers.update({
            "User-Agent": self._config.user_agent,
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "zh-TW,zh;q=0.8,en-US;q=0.5,en;q=0.3",
        })

        # I am not sure if this function can accelerate the process, so it is disabled for now.
        # self._load_session_cookies_or_create_new(session, os.path.join(base_path, "state/cookies.json"))

        return session

    def _refresh_flags(self) -> None:
        self._multi_thread_flags = {
            'add_to_cart': False,
            'checkout_page': False,
            'delivery_dates': False,
            'checkout': False,
        }


    def purchase(self) -> bool:
        self._refresh_flags()

        try:
            success = self._add_to_cart()

            if not success:
                self._logger.error("Failed to add product to cart")
                return False

            self._logger.info("Product added to cart successfully")
            self._slack_notifier.send_product_available("Strawberry", f"{self._config.base_url}/{self._config.product.url}")

            self._checkout()

            self._logger.info("Maybe Purchase complete!")
            print("✓ Maybe Purchase successful!")

            self._slack_notifier.send_successful_purchase(
                order_id="fake-order-id",
                product_name=self._config.product.url,
            )

            return True
        except PurchaseError as e:
            self._logger.error(f"Purchase error: {e}")
            print(f"Error: {e}")
            self._slack_notifier.send_purchase_error(e, 'fail')

        return False

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
            response = session.get(f"{self._config.base_url}/")
            print(response.cookies.items())
            with open(filepath, "w", encoding="utf-8") as f:
                cookies_dict = requests.utils.dict_from_cookiejar(session.cookies)
                json.dump(cookies_dict, f, ensure_ascii=False, indent=4)
                self._logger.info(f"Saved new cookies to {filepath}")

    def _add_to_cart(self) -> bool:
        """Add product to cart.

        Returns:
            True if successfully added to cart

        Raises:
            Purchase502Error: If 502 Bad Gateway received
        """
        form_data, url = self._prepare_add_to_cart_payload()

        self._logger.debug(f"Add to Cart Form data: {form_data}")

        responses = self._call_api_with_multi_threaded('add_to_cart', 'GET', url, data=form_data)

        has_502_error = False

        for response in responses:
            if isinstance(response, Response):
                if response.status_code == 502:
                    has_502_error = True
                    continue

                # Check for error messages in response
                response_lower = response.text.lower()
                if response.status_code == 200 and 'you cannot add' not in response_lower:
                    return True

        if has_502_error:
            raise Purchase502Error("Received 502 Bad Gateway during add to cart")

        return False

    def _call_api_with_multi_threaded(self, flag: str, method: str, url: str, **kwargs) -> list[Response | None]:
        responses = []
        urls = [url] * 5

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_url = {
                executor.submit(self._send_request_with_retry, flag, method, url, **kwargs): url for url in urls
            }
            for future in concurrent.futures.as_completed(future_to_url):
                response = future.result()
                responses.append(response)

        return responses

    def _send_request_with_retry(self, flag: str, method: str, url: str, **kwargs) -> Response | None:
        max_retries = self._config.max_retries
        response = None

        while (not self._multi_thread_flags[flag]) and max_retries > 0:
            response = self._session.request(
                method=method,
                url=url,
                timeout=self._config.timeout,
                **kwargs,
            )
            max_retries -= 1

            if response.status_code == 200:
                self._multi_thread_flags[flag] = True
                self._logger.info(f"Successfully performed {method} request to {url}")
                break

        return response

    def _prepare_add_to_cart_payload(self) -> tuple[dict[str, Any], str]:
        product_url=self._config.product.url

        # Build form data
        form_data = {
            "quantity": str(self._config.product.quantity),
            "add-to-cart": str(self._config.product.product_id),
            "product_id": str(self._config.product.product_id),
            "variation_id": str(self._config.product.variation_id),
        }

        # Add attributes if provided
        if self._config.product.attributes:
            for key, value in self._config.product.attributes.items():
                form_data[f"attribute_{key}"] = value

        # Construct full URL if needed
        if product_url.startswith("http"):
            url = product_url
        else:
            # Remove leading slash if present
            product_url = product_url.lstrip("/")
            url = f"{self._config.base_url}/{product_url}"

        return form_data, url

    def _checkout(self) -> None:
        """Complete checkout process.

        Raises:
            PurchaseError: If checkout fails
        """
        self._logger.info("Starting checkout process")

        # Convert config models to dicts
        billing_info = self._config.billing_info.model_dump()
        shipping_info = self._config.shipping_info.model_dump()
        payment_info = self._config.payment_info.model_dump()

        try:
            # Step 1: Visit checkout page to establish session and get update_order_review_nonce
            self._logger.debug("Visiting checkout page to establish session")
            checkout_page_url = f"{self._config.base_url}/checkout/"

            checkout_page_responses = self._call_api_with_multi_threaded('checkout_page', 'GET', checkout_page_url)

            # Extract update_order_review_nonce from wc_checkout_params
            update_nonce = self._extract_update_order_review_nonce(checkout_page_responses)
            if not update_nonce:
                raise PurchaseError("Failed to extract update_order_review_nonce from checkout page")

            self._logger.debug(f"Extracted update_order_review_nonce: {update_nonce[:10]}...")

            checkout_data_for_review = self._build_checkout_payload(
                billing_info, shipping_info, payment_info
            )

            # Step 2: Submit final checkout with the nonce
            checkout_data_for_review["woocommerce-process-checkout-nonce"] = update_nonce
            checkout_data_for_review["_wp_http_referer"] = "/?wc-ajax=update_order_review"

            self._logger.debug(f"Add to Cart Form data: {urlencode(checkout_data_for_review)}")
            checkout_url = f"{self._config.base_url}/?wc-ajax=checkout"

            checkout_responses = self._call_api_with_multi_threaded(
                'checkout',
                'POST',
                checkout_url,
                data=urlencode(checkout_data_for_review),
                headers={
                    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                    "X-Requested-With": "XMLHttpRequest",
                },
            )

            for response in checkout_responses:
                if response is None:
                    continue

                self._logger.info(f"---------\n\n{response.text}\n\n")

        except Exception as e:
            raise PurchaseError(f"Checkout failed: {e}") from e

    def _extract_update_order_review_nonce(self, responses: list[Response|None]) -> str | None:
        """Extract update_order_review nonce from checkout page.

        Args:
            html: HTML content of checkout page

        Returns:
            Nonce value if found, None otherwise
        """
        for response in responses:
            if response is None:
                continue

            html = response.text

            pattern = r'"update_order_review_nonce"\s*:\s*"([a-f0-9]+)"'
            match = re.search(pattern, html)
            if match:
                return match.group(1)

        # save responses for debugging
        for index, response in enumerate(responses):
            if response is not None:
                with open(f"log/checkout_response_{index}.html", "w", encoding="utf-8") as f:
                    if response is not None:
                        f.write(response.text)

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
            "wc_order_attribution_session_entry": self._config.base_url,
            "wc_order_attribution_session_pages": "5",
            "wc_order_attribution_session_count": "1",
            "wc_order_attribution_user_agent": self._config.user_agent,
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
                url=f"{self._config.base_url}/?wc-ajax=orddd_update_delivery_session",
                data=urlencode(request_data, doseq=True),
                headers={
                    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                    "X-Requested-With": "XMLHttpRequest",
                },
                timeout=self._config.timeout,
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
            #     url=f"{self._config.base_url}/?wc-ajax=update_order_review",
            #     data=urlencode(update_review_data),
            #     headers={
            #         "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            #         "X-Requested-With": "XMLHttpRequest",
            #     },
            #     timeout=self._config.timeout,
            # )
            # update_review_response.raise_for_status()
            #
            # # Extract checkout nonce from response
            # checkout_nonce = self._extract_checkout_nonce(update_review_response.text)
            # if not checkout_nonce:
            #     raise PurchaseError("Failed to extract checkout nonce from update_order_review response")
            #
            # self._logger.debug(f"Extracted checkout nonce: {checkout_nonce[:10]}...")
