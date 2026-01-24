"""State management for notification tracking."""

import json
from pathlib import Path

from src.core.interfaces import StateStore
from src.utils.logger import get_logger

logger = get_logger(__name__)


class JsonStateStore(StateStore):
    """Stores notification state in JSON file."""

    def __init__(self, file_path: Path | str):
        """Initialize state store.

        Args:
            file_path: Path to state file
        """
        self._file_path = Path(file_path)
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        self._state = self._read_state()

    def _read_state(self) -> dict[str, str]:
        """Read state from file.

        Returns:
            State dictionary {url: timestamp}
        """
        try:
            with open(self._file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.warning("Corrupted state file - initializing empty state")
            return {}

    def _write_state(self) -> None:
        """Write state to file.

        Args:
            state: State dictionary to write
        """
        with open(self._file_path, "w", encoding="utf-8") as f:
            json.dump(self._state, f, indent=2, ensure_ascii=False)

    def set(self, key: str, value: str) -> None:
        """Set a state value.

        Args:
            key: State key
            value: State value
        """
        self._state[key] = value
        self._write_state()

    def get(self, key: str) -> str | None:
        """Get a state value.

        Args:
            key: State key

        Returns:
            State value
        """
        return self._state.get(key)

    def delete(self, key: str) -> None:
        """Delete a state value.

        Args:
            key: State key
        """
        if key in self._state:
            del self._state[key]
            self._write_state()

    def has_key(self, key: str) -> bool:
        """Check if state has a specific key.

        Args:
            key: State key

        Returns:
            True if key exists, False otherwise
        """
        return key in self._state
