"""State management for notification tracking."""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Union

from src.core.interfaces import StateStore
from src.utils.logger import get_logger

logger = get_logger(__name__)


class JsonStateStore(StateStore):
    """Stores notification state in JSON file."""

    def __init__(self, file_path: Union[Path, str]):
        """Initialize state store.

        Args:
            file_path: Path to state file
        """
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_file_exists()

    def _ensure_file_exists(self) -> None:
        """Ensure state file exists with empty dict."""
        if not self.file_path.exists():
            self._write_state({})

    def _read_state(self) -> Dict[str, str]:
        """Read state from file.

        Returns:
            State dictionary {url: timestamp}
        """
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.warning("Corrupted state file - initializing empty state")
            return {}

    def _write_state(self, state: Dict[str, str]) -> None:
        """Write state to file.

        Args:
            state: State dictionary to write
        """
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)

    def was_notified(self, product_url: str) -> bool:
        """Check if product was already notified.

        Args:
            product_url: Product URL

        Returns:
            True if already notified, False otherwise
        """
        state = self._read_state()
        return product_url in state

    def mark_notified(self, product_url: str, timestamp: Optional[datetime] = None) -> None:
        """Mark product as notified.

        Args:
            product_url: Product URL
            timestamp: Notification timestamp (defaults to now)
        """
        if timestamp is None:
            timestamp = datetime.now()

        state = self._read_state()
        state[product_url] = timestamp.isoformat()
        self._write_state(state)

        logger.info(f"Marked {product_url} as notified at {timestamp}")

    def clear_notification(self, product_url: str) -> None:
        """Clear notification record for product.

        Args:
            product_url: Product URL
        """
        state = self._read_state()
        if product_url in state:
            del state[product_url]
            self._write_state(state)
            logger.info(f"Cleared notification record for {product_url}")
