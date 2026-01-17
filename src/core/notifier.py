"""Slack notification sender."""

import traceback
from typing import Any, Dict, Optional

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

    def send_error(self, error: Exception, context: Optional[str] = None) -> bool:
        """Send error notification to Slack.

        Args:
            error: Exception that occurred
            context: Additional context information

        Returns:
            True if notification sent successfully, False otherwise
        """
        try:
            error_type = type(error).__name__
            error_message = str(error)

            attachment = {
                "color": "danger",
                "title": f":x: Error: {error_type}",
                "text": error_message,
                "fields": [],
                "footer": "Food Reminder Bot",
                "ts": int(__import__("time").time()),
            }

            if context:
                attachment["fields"].append({
                    "title": "Context",
                    "value": context,
                    "short": False,
                })

            tb = traceback.format_exc()
            if tb and tb != "NoneType: None\n":
                if len(tb) > 1000:
                    tb = tb[:1000] + "\n... (truncated)"
                attachment["fields"].append({
                    "title": "Traceback",
                    "value": f"```{tb}```",
                    "short": False,
                })

            payload = {
                "username": self.username,
                "icon_emoji": self.icon_emoji,
                "attachments": [attachment],
            }

            response = requests.post(self.webhook_url, json=payload, timeout=10)
            response.raise_for_status()

            logger.info("Error notification sent to Slack")
            return True

        except Exception as e:
            logger.error(f"Failed to send Slack error notification: {e}")
            return False

    def send_success(self, order_id: str, product_name: Optional[str] = None) -> bool:
        """Send success notification to Slack.

        Args:
            order_id: Order ID of successful purchase
            product_name: Optional product name

        Returns:
            True if notification sent successfully, False otherwise
        """
        try:
            message = f":white_check_mark: Purchase successful! Order ID: {order_id}"
            if product_name:
                message += f"\nProduct: {product_name}"

            payload = {
                "username": self.username,
                "icon_emoji": self.icon_emoji,
                "attachments": [{
                    "color": "good",
                    "text": message,
                    "footer": "Food Reminder Bot",
                    "ts": int(__import__("time").time()),
                }],
            }

            response = requests.post(self.webhook_url, json=payload, timeout=10)
            response.raise_for_status()

            logger.info("Success notification sent to Slack")
            return True

        except Exception as e:
            logger.error(f"Failed to send Slack success notification: {e}")
            return False

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
