"""Abstract interfaces for core components."""

from abc import ABC, abstractmethod
from typing import Any


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


class StateStore(ABC):
    """Interface for managing notification state."""

    @abstractmethod
    def set(self, key: str, value: str) -> None:
        """Set a state value.

        Args:
            key: State key
            value: State value
        """
        pass

    @abstractmethod
    def get(self, key: str) -> str | None:
        """Get a state value.

        Args:
            key: State key

        Returns:
            State value
        """
        pass

    @abstractmethod
    def delete(self, key: str) -> None:
        """Delete a state value.

        Args:
            key: State key
        """
        pass

    @abstractmethod
    def has_key(self, key: str) -> bool:
        """Check if state has a specific key.

        Args:
            key: State key

        Returns:
            True if key exists, False otherwise
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
        attributes: dict[str, str] | None = None
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
    def checkout(
        self,
        billing_info: dict[str, Any],
        shipping_info: dict[str, Any],
        payment_info: dict[str, Any]
    ) -> str:
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
