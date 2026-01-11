"""Unit tests for WooCommerceChecker."""

from pathlib import Path

import pytest
import responses

from src.core.checker import WooCommerceChecker
from src.utils.exceptions import CheckerError


@pytest.fixture
def checker() -> WooCommerceChecker:
    """Create a WooCommerceChecker instance for testing."""
    return WooCommerceChecker(timeout=10, max_retries=2, retry_delay=0)


@pytest.fixture
def in_stock_html() -> str:
    """Load in-stock product HTML."""
    fixture_path = Path(__file__).parent.parent / "fixtures" / "in_stock.html"
    return fixture_path.read_text(encoding="utf-8")


@pytest.fixture
def out_of_stock_html() -> str:
    """Load out-of-stock product HTML."""
    fixture_path = Path(__file__).parent.parent / "fixtures" / "out_of_stock.html"
    return fixture_path.read_text(encoding="utf-8")


class TestWooCommerceChecker:
    """Test cases for WooCommerceChecker."""

    def test_check_product_class_in_stock(self, checker: WooCommerceChecker) -> None:
        """Test _check_product_class with in-stock HTML."""
        html = '<div id="product-3316" class="product type-product post-3316 status-publish first instock product_cat-69">'
        result = checker._check_product_class(html)
        assert result is True

    def test_check_product_class_out_of_stock(self, checker: WooCommerceChecker) -> None:
        """Test _check_product_class with out-of-stock HTML."""
        html = '<div id="product-2909" class="product type-product post-2909 status-publish first outofstock product_cat-62">'
        result = checker._check_product_class(html)
        assert result is False

    def test_check_product_class_no_match(self, checker: WooCommerceChecker) -> None:
        """Test _check_product_class with no product div."""
        html = "<div>No product here</div>"
        result = checker._check_product_class(html)
        assert result is None

    @responses.activate
    def test_is_available_in_stock(
        self, checker: WooCommerceChecker, in_stock_html: str
    ) -> None:
        """Test is_available with in-stock product."""
        url = "https://www.wagashi.com.tw/product/test/"

        # Add product ID to HTML fixture
        html_with_product = in_stock_html.replace(
            '<div id="product-',
            '<form class="cart"><input type="hidden" name="add-to-cart" value="3316" /></form><div id="product-'
        )

        responses.add(responses.GET, url, body=html_with_product, status=200)
        # Mock the POST request for add-to-cart
        responses.add(responses.POST, url, body="<html>Success</html>", status=200)

        result = checker.is_available(url)
        assert result is True

    @responses.activate
    def test_is_available_out_of_stock(
        self, checker: WooCommerceChecker, out_of_stock_html: str
    ) -> None:
        """Test is_available with out-of-stock product."""
        url = "https://www.wagashi.com.tw/product/test/"

        # Add product ID to HTML fixture
        html_with_product = out_of_stock_html.replace(
            '<div id="product-',
            '<form class="cart"><input type="hidden" name="add-to-cart" value="2909" /></form><div id="product-'
        )

        responses.add(responses.GET, url, body=html_with_product, status=200)
        # Mock POST request that returns error
        error_response = '<div class="woocommerce-error">You cannot add to cart because the product is out of stock</div>'
        responses.add(responses.POST, url, body=error_response, status=200)

        result = checker.is_available(url)
        assert result is False

    @responses.activate
    def test_is_available_with_wrapper(self, checker: WooCommerceChecker) -> None:
        """Test is_available detects out_of_stock_wrapper."""
        url = "https://www.wagashi.com.tw/product/test/"
        html = '<div class="out_of_stock_wrapper">Out of stock</div>'
        responses.add(responses.GET, url, body=html, status=200)

        result = checker.is_available(url)
        assert result is False

    @responses.activate
    def test_is_available_http_error(self, checker: WooCommerceChecker) -> None:
        """Test is_available with HTTP error."""
        url = "https://www.wagashi.com.tw/product/test/"
        responses.add(responses.GET, url, status=404)

        with pytest.raises(CheckerError):
            checker.is_available(url)

    @responses.activate
    def test_fetch_html_with_retry(self, checker: WooCommerceChecker) -> None:
        """Test _fetch_html retries on failure."""
        url = "https://www.wagashi.com.tw/product/test/"

        # First attempt fails, second succeeds
        responses.add(responses.GET, url, status=500)
        responses.add(responses.GET, url, body="<html>Success</html>", status=200)

        result = checker._fetch_html(url)
        assert "Success" in result
        assert len(responses.calls) == 2
