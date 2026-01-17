"""Abstract interfaces for core components."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, Dict, Any


class Checker(ABC):
    """Interface for product availability checking."""

    @abstractmethod
    def is_available(self, url: str) -> bool:
        """Check if product is available.

        Args:
            url: Product URL to check

        Returns:
            True if product is in stock, False otherwise

        Raises:
            CheckerError: If check fails
        """
        pass


class Notifier(ABC):
    """Interface for sending notifications."""

    @abstractmethod
    def notify(self, product_name: str, product_url: str) -> None:
        """Send notification about product availability.

        Args:
            product_name: Name of the product
            product_url: URL of the product

        Raises:
            NotificationError: If notification fails
        """
        pass


class StateStore(ABC):
    """Interface for managing notification state."""

    @abstractmethod
    def was_notified(self, product_url: str) -> bool:
        """Check if product was already notified.

        Args:
            product_url: Product URL

        Returns:
            True if already notified, False otherwise
        """
        pass

    @abstractmethod
    def mark_notified(self, product_url: str, timestamp: Optional[datetime] = None) -> None:
        """Mark product as notified.

        Args:
            product_url: Product URL
            timestamp: Notification timestamp (defaults to now)
        """
        pass

    @abstractmethod
    def clear_notification(self, product_url: str) -> None:
        """Clear notification record for product.

        Args:
            product_url: Product URL
        """
        pass


class Purchaser(ABC):
    """Interface for automating product purchases."""

    @abstractmethod
    def add_to_cart(
        self,
        product_url: str,
        product_id: int,
        variation_id: int,
        quantity: int = 1,
        attributes: Optional[Dict[str, str]] = None
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
        pass

    @abstractmethod
    def checkout(self, billing_info: Dict[str, Any], shipping_info: Dict[str, Any],
                 payment_info: Dict[str, Any]) -> str:
        """Complete checkout process.

        Args:
            billing_info: Billing information
            shipping_info: Shipping information
            payment_info: Payment information

        Returns:
            Order ID or confirmation number

        Raises:
            PurchaseError: If checkout fails
        """
        pass
