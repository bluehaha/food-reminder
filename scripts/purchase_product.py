#!/usr/bin/env python3
"""CLI script to automate product purchasing."""

import argparse
import sys
from pathlib import Path

# Add parent directory to path to import from src
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.loader import ConfigLoader
from src.config.models import PurchaseConfig
from src.core.notifier import SlackNotifier
from src.core.purchaser import WooCommercePurchaser
from src.core.state import JsonStateStore
from src.utils.exceptions import FoodReminderError, PurchaseError
from src.utils.logger import configure_logging, get_logger


def main() -> None:
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="Automate product purchasing on WooCommerce sites"
    )
    parser.add_argument(
        "-c",
        "--config",
        default="conf/purchase.yaml",
        help="Path to purchase configuration file (default: conf/purchase.yaml)",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose logging"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run mode - add to cart but don't checkout",
    )
    parser.add_argument(
        "--clear-state",
        action="store_true",
        help="Clear purchase state to allow re-purchase",
    )

    args = parser.parse_args()

    # Setup logging
    log_level = "DEBUG" if args.verbose else "INFO"
    configure_logging(level=log_level)

    logger = get_logger(__name__)
    logger.debug(f"Arguments: {args}")

    slack_notifier = None

    try:
        # Load configuration
        logger.info(f"Loading configuration from {args.config}")
        config = ConfigLoader.load(args.config, PurchaseConfig)

        slack_notifier = SlackNotifier(
            webhook_url=str(config.slack.webhook_url),
            username=config.slack.username,
            icon_emoji=config.slack.icon_emoji,
        )

        # Initialize state store
        state_store = JsonStateStore(config.state.file_path)

        # Clear state if requested
        if args.clear_state:
            state_store.clear_purchase(
                product_id=config.product.product_id,
                variation_id=config.product.variation_id,
            )
            logger.info("Purchase state cleared")
            print("Purchase state cleared. You can now re-purchase this product.")
            return

        # Check if already purchased
        if state_store.has_purchased(
            product_id=config.product.product_id,
            variation_id=config.product.variation_id,
        ):
            purchase_info = state_store.get_purchase_info(
                product_id=config.product.product_id,
                variation_id=config.product.variation_id,
            )
            logger.info(
                f"Product already purchased. Order ID: {purchase_info.get('order_id')}, "
                f"Time: {purchase_info.get('timestamp')}"
            )
            print(f"Product already purchased. Order ID: {purchase_info.get('order_id')}")
            print("Run the script with --clear-state flag to allow re-purchase.")
            sys.exit(0)

        # Initialize purchaser
        purchaser = WooCommercePurchaser(
            base_url=str(config.base_url),
            timeout=config.timeout,
            user_agent=config.user_agent,
        )

        success = purchaser.add_to_cart(
            product_url=config.product.url,
            product_id=config.product.product_id,
            variation_id=config.product.variation_id,
            quantity=config.product.quantity,
            attributes=config.product.attributes,
        )

        if not success:
            logger.error("Failed to add product to cart")
            sys.exit(1)

        logger.info("Product added to cart successfully")

        # Checkout (unless dry run)
        if args.dry_run:
            logger.info("Dry run mode - skipping checkout")
            print("Dry run complete. Product added to cart but not purchased.")
            return

        logger.info("Proceeding to checkout...")

        # Convert config models to dicts
        billing_info = config.billing_info.model_dump()
        shipping_info = config.shipping_info.model_dump()
        payment_info = config.payment_info.model_dump()

        order_id = purchaser.checkout(
            billing_info=billing_info,
            shipping_info=shipping_info,
            payment_info=payment_info,
        )

        logger.info(f"Purchase complete! Order ID: {order_id}")
        print(f"✓ Purchase successful! Order ID: {order_id}")

        # Mark as purchased in state
        state_store.mark_purchased(
            product_id=config.product.product_id,
            variation_id=config.product.variation_id,
            order_id=order_id,
        )

        slack_notifier.send_success(
            order_id=order_id,
            product_name=config.product.url,
        )

    except FileNotFoundError as e:
        logger.error(f"Configuration file not found: {e}")
        print(f"Error: Configuration file '{args.config}' not found.")
        sys.exit(1)
    except PurchaseError as e:
        logger.error(f"Purchase error: {e}")
        print(f"Error: {e}")
        sys.exit(1)
    except FoodReminderError as e:
        logger.error(f"Error: {e}")
        print(f"Error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        print("\nOperation cancelled by user")
        sys.exit(130)
    except Exception as e:
        logger.exception("Unexpected error")
        print(f"Unexpected error: {e}")
        sys.exit(1)
    finally:
        if 'e' in locals():
            slack_notifier.send_error(e)


if __name__ == "__main__":
    main()
