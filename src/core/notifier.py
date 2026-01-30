"""Slack notification sender."""

import traceback
from typing import Any, Dict

import requests

from src.utils.exceptions import NotificationError
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SlackNotifier():
    """Sends notifications via Slack webhook."""

    def __init__(
        self,
        webhook_url: str,
        username: str = "Food Availability Bot",
        icon_emoji: str = ":bento:",
        env: str | None = None
    ):
        """Initialize Slack notifier.

        Args:
            webhook_url: Slack webhook URL
            username: Bot username
            icon_emoji: Bot icon emoji
        """
        self._webhook_url = webhook_url
        self._username = username
        self._icon_emoji = icon_emoji
        self._env = env

    def _send(self, payload: Dict[str, Any]) -> None:
        """Send Slack notification.

        Args:
            payload: Slack message payload

        Raises:
            NotificationError: If notification fails
        """
        if self._env in ['dev', 'develop', 'local']:
            return

        try:
            response = requests.post(self._webhook_url, json=payload, timeout=10)
            response.raise_for_status()
        except Exception as e:
            logger.error(f"Unexpected error sending Slack notification: {e}")
            raise NotificationError(f"Failed to send Slack notification: {e}")

    def send_product_available(self, product_name: str, product_url: str) -> None:
        """Send Slack notification.

        Args:
            product_name: Name of the product
            product_url: URL of the product

        Raises:
            NotificationError: If notification fails
        """
        payload = {
            "username": self._username,
            "icon_emoji": self._icon_emoji,
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

        self._send(payload)

        logger.info("Product availability notification sent to Slack")


    def send_purchase_error(self, error: Exception, context: str | None) -> None:
        """Send error notification to Slack.

        Args:
            error: Exception that occurred
            context: Additional context information

        Returns:
            True if notification sent successfully, False otherwise
        """
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
            "username": self._username,
            "icon_emoji": self._icon_emoji,
            "attachments": [attachment],
        }

        self._send(payload)

        logger.info("Error notification sent to Slack")

    def send_successful_purchase(self, order_id: str, product_name: str) -> bool:
        """Send success notification to Slack.

        Args:
            order_id: Order ID of successful purchase
            product_name: Optional product name

        Returns:
            True if notification sent successfully, False otherwise
        """
        payload = {
            "username": self._username,
            "icon_emoji": self._icon_emoji,
            "attachments": [{
                "color": "good",
                "text": f":white_check_mark: Purchase successful! Order ID: {order_id}\nProduct: {product_name}",
                "footer": "Food Reminder Bot",
                "ts": int(__import__("time").time()),
            }],
        }

        self._send(payload)

        logger.info("Successful purchase notification sent to Slack")
