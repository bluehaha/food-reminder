"""Abstract interfaces for core components."""

from abc import ABC, abstractmethod


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
