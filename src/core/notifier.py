"""Slack notification sender."""

from typing import Any, Dict

import requests

from src.core.interfaces import Notifier
from src.utils.exceptions import NotificationError
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SlackNotifier(Notifier):
    """Sends notifications via Slack webhook."""

    def __init__(
        self, webhook_url: str, username: str = "Food Availability Bot", icon_emoji: str = ":bento:"
    ):
        """Initialize Slack notifier.

        Args:
            webhook_url: Slack webhook URL
            username: Bot username
            icon_emoji: Bot icon emoji
        """
        self.webhook_url = webhook_url
        self.username = username
        self.icon_emoji = icon_emoji

    def notify(self, product_name: str, product_url: str) -> None:
        """Send Slack notification.

        Args:
            product_name: Name of the product
            product_url: URL of the product

        Raises:
            NotificationError: If notification fails
        """
        message = self._build_message(product_name, product_url)

        try:
            logger.info(f"Sending Slack notification for {product_name}")
            response = requests.post(self.webhook_url, json=message, timeout=10)
            response.raise_for_status()
            logger.info("Slack notification sent successfully")
        except requests.RequestException as e:
            raise NotificationError(f"Failed to send Slack notification: {e}")

    def _build_message(self, product_name: str, product_url: str) -> Dict[str, Any]:
        """Build Slack message payload.

        Args:
            product_name: Name of the product
            product_url: URL of the product

        Returns:
            Slack message payload
        """
        return {
            "username": self.username,
            "icon_emoji": self.icon_emoji,
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "🎉 Food Now Available!",
                        "emoji": True,
                    },
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*{product_name}* is now in stock!"},
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"<{product_url}|View Product>"},
                },
            ],
        }
