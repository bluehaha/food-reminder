"""Configuration loader."""

from pathlib import Path
from typing import Union

import yaml

from src.config.models import Config
from src.utils.exceptions import ConfigurationError


class ConfigLoader:
    """Loads and validates configuration from YAML files."""

    @staticmethod
    def load(config_path: Union[Path, str]) -> Config:
        """Load configuration from YAML file.

        Args:
            config_path: Path to configuration file

        Returns:
            Validated Config object

        Raises:
            ConfigurationError: If config is invalid or file not found
        """
        path = Path(config_path)

        if not path.exists():
            raise ConfigurationError(f"Configuration file not found: {path}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML: {e}")

        if data is None:
            raise ConfigurationError("Configuration file is empty")

        try:
            return Config(**data)
        except Exception as e:
            raise ConfigurationError(f"Invalid configuration: {e}")
