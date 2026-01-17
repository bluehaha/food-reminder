"""Custom exceptions for the application."""


class FoodReminderError(Exception):
    """Base exception for all application errors."""

    pass


class ConfigurationError(FoodReminderError):
    """Configuration related errors."""

    pass


class CheckerError(FoodReminderError):
    """Product checking errors."""

    pass


class NotificationError(FoodReminderError):
    """Notification sending errors."""

    pass


class StateError(FoodReminderError):
    """State management errors."""

    pass


class PurchaseError(FoodReminderError):
    """Product purchase errors."""

    pass
