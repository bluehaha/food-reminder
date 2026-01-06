"""Unit tests for JsonStateStore."""

import json
from datetime import datetime
from pathlib import Path

import pytest

from src.core.state import JsonStateStore


@pytest.fixture
def temp_state_file(tmp_path: Path) -> Path:
    """Create a temporary state file path."""
    return tmp_path / "test_state.json"


@pytest.fixture
def state_store(temp_state_file: Path) -> JsonStateStore:
    """Create a JsonStateStore instance for testing."""
    return JsonStateStore(temp_state_file)


class TestJsonStateStore:
    """Test cases for JsonStateStore."""

    def test_initialization_creates_file(self, temp_state_file: Path) -> None:
        """Test that initialization creates the state file."""
        assert not temp_state_file.exists()

        JsonStateStore(temp_state_file)

        assert temp_state_file.exists()
        with open(temp_state_file) as f:
            data = json.load(f)
        assert data == {}

    def test_was_notified_returns_false_for_new_product(
        self, state_store: JsonStateStore
    ) -> None:
        """Test was_notified returns False for new product."""
        result = state_store.was_notified("https://example.com/product/")
        assert result is False

    def test_mark_notified_updates_state(
        self, state_store: JsonStateStore, temp_state_file: Path
    ) -> None:
        """Test mark_notified updates the state file."""
        url = "https://example.com/product/"
        timestamp = datetime(2026, 1, 4, 10, 30, 0)

        state_store.mark_notified(url, timestamp)

        # Check in-memory
        assert state_store.was_notified(url) is True

        # Check file persistence
        with open(temp_state_file) as f:
            data = json.load(f)
        assert url in data
        assert data[url] == "2026-01-04T10:30:00"

    def test_mark_notified_uses_current_time_if_not_provided(
        self, state_store: JsonStateStore
    ) -> None:
        """Test mark_notified uses current time when timestamp not provided."""
        url = "https://example.com/product/"

        state_store.mark_notified(url)

        assert state_store.was_notified(url) is True

    def test_clear_notification_removes_entry(self, state_store: JsonStateStore) -> None:
        """Test clear_notification removes the entry."""
        url = "https://example.com/product/"

        # Mark as notified first
        state_store.mark_notified(url)
        assert state_store.was_notified(url) is True

        # Clear
        state_store.clear_notification(url)
        assert state_store.was_notified(url) is False

    def test_handles_corrupted_json(self, temp_state_file: Path) -> None:
        """Test handling of corrupted JSON file."""
        # Create corrupted JSON file
        temp_state_file.parent.mkdir(parents=True, exist_ok=True)
        temp_state_file.write_text("{ invalid json }")

        # Should not raise exception, just return empty state
        state_store = JsonStateStore(temp_state_file)
        result = state_store.was_notified("https://example.com/product/")
        assert result is False

    def test_multiple_products(self, state_store: JsonStateStore) -> None:
        """Test managing state for multiple products."""
        url1 = "https://example.com/product1/"
        url2 = "https://example.com/product2/"

        state_store.mark_notified(url1)
        state_store.mark_notified(url2)

        assert state_store.was_notified(url1) is True
        assert state_store.was_notified(url2) is True

        state_store.clear_notification(url1)

        assert state_store.was_notified(url1) is False
        assert state_store.was_notified(url2) is True
