"""Monitoring service orchestrating product checks and notifications."""

from typing import Dict, List

from src.config.models import ProductConfig
from src.core.interfaces import Checker, Notifier, StateStore
from src.utils.exceptions import CheckerError, NotificationError
from src.utils.logger import get_logger

logger = get_logger(__name__)


class MonitoringService:
    """Orchestrates product monitoring and notifications."""

    def __init__(self, checker: Checker, notifier: Notifier, state_store: StateStore):
        """Initialize monitoring service.

        Args:
            checker: Product availability checker
            notifier: Notification sender
            state_store: State management
        """
        self.checker = checker
        self.notifier = notifier
        self.state_store = state_store

    def check_and_notify(self, products: List[ProductConfig]) -> None:
        """Check products and send notifications for newly available items.

        Args:
            products: List of products to check
        """
        logger.info(f"Checking {len(products)} products")

        results: Dict[str, int] = {
            "checked": 0,
            "available": 0,
            "notified": 0,
            "already_notified": 0,
            "errors": 0,
        }

        for product in products:
            results["checked"] += 1

            try:
                # Check availability
                is_available = self.checker.is_available(str(product.url))

                if is_available:
                    results["available"] += 1
                    self._handle_available_product(product, results)
                else:
                    self._handle_unavailable_product(product)

            except CheckerError as e:
                results["errors"] += 1
                logger.error(f"Failed to check {product.name}: {e}")
            except NotificationError as e:
                results["errors"] += 1
                logger.error(f"Failed to notify for {product.name}: {e}")

        self._log_summary(results)

    def _handle_available_product(
        self, product: ProductConfig, results: Dict[str, int]
    ) -> None:
        """Handle product that is available.

        Args:
            product: Product configuration
            results: Results dictionary to update
        """
        product_url = str(product.url)

        # Check if already notified
        if self.state_store.was_notified(product_url):
            logger.info(f"{product.name} is available but already notified - skipping")
            results["already_notified"] += 1
            return

        # Send notification
        logger.info(f"{product.name} is available - sending notification")
        self.notifier.notify(product.name, product_url)

        # Mark as notified
        self.state_store.mark_notified(product_url)
        results["notified"] += 1

    def _handle_unavailable_product(self, product: ProductConfig) -> None:
        """Handle product that is unavailable.

        Args:
            product: Product configuration
        """
        logger.info(f"{product.name} is not available")

        # If it becomes unavailable again, clear notification state
        # so we notify when it comes back in stock
        product_url = str(product.url)
        if self.state_store.was_notified(product_url):
            logger.info(f"Clearing notification state for {product.name} (back out of stock)")
            self.state_store.clear_notification(product_url)

    def _log_summary(self, results: Dict[str, int]) -> None:
        """Log summary of check results.

        Args:
            results: Results dictionary
        """
        logger.info(
            f"Check complete - "
            f"Checked: {results['checked']}, "
            f"Available: {results['available']}, "
            f"Notified: {results['notified']}, "
            f"Already notified: {results['already_notified']}, "
            f"Errors: {results['errors']}"
        )
