"""Logging configuration."""

import logging
import sys
from typing import Optional

# Global flag to track if logging has been configured
_logging_configured = False


def configure_logging(level: str = "INFO") -> None:
    """Configure logging for the entire application.

    This should be called once at the application entry point.
    It sets up a single handler on the root logger and configures
    all loggers to propagate to it.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    global _logging_configured

    if _logging_configured:
        # If already configured, just update the level
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, level.upper()))
        for handler in root_logger.handlers:
            handler.setLevel(getattr(logging, level.upper()))
        return

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    # Remove any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create a single handler for the root logger
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, level.upper()))

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)

    # Add handler to root logger
    root_logger.addHandler(handler)

    _logging_configured = True


def get_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """Get configured logger.

    Args:
        name: Logger name (usually __name__)
        level: Log level (deprecated, use configure_logging instead)

    Returns:
        Configured logger that propagates to root logger
    """
    logger = logging.getLogger(name)

    # If level is specified, set it (but this is not recommended)
    if level:
        logger.setLevel(getattr(logging, level.upper()))

    return logger
