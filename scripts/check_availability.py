#!/usr/bin/env python3
"""CLI script to check product availability and send notifications."""

import argparse
import sys
from pathlib import Path

# Add parent directory to path to import from src
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.loader import ConfigLoader
from src.core.checker import WooCommerceChecker
from src.core.notifier import SlackNotifier
from src.core.service import MonitoringService
from src.core.state import JsonStateStore
from src.utils.exceptions import FoodReminderError
from src.utils.logger import get_logger


def main() -> None:
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="Check food product availability and send Slack notifications"
    )
    parser.add_argument(
        "-c",
        "--config",
        default="conf/config.yaml",
        help="Path to configuration file (default: conf/config.yaml)",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose logging"
    )
    parser.add_argument(
        "--clear-state", metavar="URL", help="Clear notification state for specific product URL"
    )

    args = parser.parse_args()

    # Setup logging
    log_level = "DEBUG" if args.verbose else "INFO"
    logger = get_logger(__name__, log_level)

    try:
        # Load configuration
        logger.info(f"Loading configuration from {args.config}")
        config = ConfigLoader.load(args.config)

        # Initialize components
        checker = WooCommerceChecker(
            timeout=config.timeout,
            user_agent=config.user_agent,
            max_retries=config.max_retries,
            retry_delay=config.retry_delay,
        )
        notifier = SlackNotifier(
            webhook_url=str(config.slack.webhook_url),
            username=config.slack.username,
            icon_emoji=config.slack.icon_emoji,
        )
        state_store = JsonStateStore(config.state.file_path)

        # Handle --clear-state
        if args.clear_state:
            logger.info(f"Clearing notification state for {args.clear_state}")
            state_store.clear_notification(args.clear_state)
            print(f"Cleared notification state for {args.clear_state}")
            return

        # Run monitoring service
        service = MonitoringService(checker, notifier, state_store)
        service.check_and_notify(config.products)

        logger.info("Check complete")

    except FoodReminderError as e:
        logger.error(f"Error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.exception("Unexpected error")
        sys.exit(1)


if __name__ == "__main__":
    main()
