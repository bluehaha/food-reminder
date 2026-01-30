#!/usr/bin/env python3
"""CLI script to automate product purchasing."""

import argparse
import sys
import os
import time
from pathlib import Path

# Add parent directory to path to import from src
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.loader import ConfigLoader
from src.config.models import PurchaseConfig
from src.core.notifier import SlackNotifier
from src.core.purchaser import WooCommercePurchaser
from src.core.state import JsonStateStore
from src.utils.exceptions import FoodReminderError, PurchaseError, Purchase502Error
from src.utils.logger import configure_logging, get_logger


logger = get_logger(__name__)


def parse_arguments() -> argparse.Namespace:
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
        "--clear-state",
        action="store_true",
        help="Clear purchase state to allow re-purchase",
    )

    return parser.parse_args()


def main() -> None:
    """Main entry point for the CLI."""
    args = parse_arguments()

    # Setup logging
    log_level = "DEBUG" if args.verbose else "INFO"
    configure_logging(level=log_level)

    # Initialize
    config = ConfigLoader.load(args.config, PurchaseConfig)
    slack_notifier = SlackNotifier(
        webhook_url=str(config.slack.webhook_url),
        username=config.slack.username,
        icon_emoji=config.slack.icon_emoji,
        env=config.env
    )
    state_store = JsonStateStore(config.state.file_path)
    purchaser = WooCommercePurchaser(
        config,
        slack_notifier,
        base_path=os.path.abspath(os.getcwd())
    )

    # Clear state if requested
    if args.clear_state:
        state_store.delete(str(config.product.product_id))
        print("Purchase state cleared. You can now re-purchase this product.")
        sys.exit(0)

    # Check if already purchased
    if state_store.has_key(str(config.product.product_id)):
        order_id = state_store.get(str(config.product.product_id))
        logger.info(
            f"Product already purchased. Order ID: {order_id}"
        )
        print(f"Product already purchased. Order ID: {order_id}")
        print("Run the script with --clear-state flag to allow re-purchase.")
        sys.exit(0)

    while True:
        try:
            purchase_result = purchaser.purchase()
            if purchase_result:
                logger.info("Purchase process completed successfully.")
                # Mark as purchased in state
                state_store.set(str(config.product.product_id), 'fake-order-id')
                break
            else:
                logger.info("Purchase process did not complete. Retrying in 30 seconds...")
                time.sleep(30)
        except Purchase502Error as e:
            logger.error(f"Receive 502 Error during purchase: {e}. Retrying immediately...")
            slack_notifier.send_purchase_error(e, 'fail')
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}. shutting down.")
            slack_notifier.send_purchase_error(e, 'fail')


if __name__ == "__main__":
    main()
