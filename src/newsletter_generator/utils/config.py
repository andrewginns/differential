"""Configuration module for the newsletter generator.

This module handles loading and accessing configuration values from environment
variables and default settings.
"""

import os
import datetime
from typing import Dict, Any, Optional

from dotenv import load_dotenv

load_dotenv()

DEFAULT_CONFIG = {
    "OPENAI_API_KEY": None,  # Must be provided in environment
    "OPENAI_LLM_MODEL": "o4-mini",
    "OPENAI_EMBEDDING_MODEL": "text-embedding-3-small",
    "GEMINI_API_KEY": None,  # Must be provided in environment if using Gemini
    "MODEL_PROVIDER": "openai",  # Default model provider (openai or gemini)
    "DATA_DIR": "data",
    "NEWSLETTER_DIR": "newsletters",
    "TTL_DAYS": 60,  # Time-to-live for stored content in days
    "LOG_LEVEL": "INFO",
    "LOG_FILE": "newsletter_generator.log",
    "LOG_MAX_BYTES": 10 * 1024 * 1024,  # 10 MB
    "LOG_BACKUP_COUNT": 5,
    "WEBHOOK_PORT": 8000,
    "WEBHOOK_PATH": "/webhook",
    # WhatsApp Business API configuration
    "WHATSAPP_VERIFY_TOKEN": None,  # Must be provided in environment
}


def get_config() -> Dict[str, Any]:
    """Get the application configuration.

    Loads configuration from environment variables, falling back to default values
    when not specified.

    Returns:
        Dict[str, Any]: The configuration dictionary.
    """
    config = DEFAULT_CONFIG.copy()

    for key in config:
        env_value = os.getenv(key)
        if env_value is not None:
            if isinstance(config[key], int) and env_value.isdigit():
                config[key] = int(env_value)
            else:
                config[key] = env_value

    return config


def get_openai_api_key() -> str:
    """Get the OpenAI API key.

    Returns:
        str: The OpenAI API key.

    Raises:
        ValueError: If the OpenAI API key is not set.
    """
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OAI")
    if not api_key:
        raise ValueError(
            "OpenAI API key not found. Please set the OPENAI_API_KEY or OAI environment variable."
        )
    return api_key


def get_gemini_api_key() -> str:
    """Get the Gemini API key.

    Returns:
        str: The Gemini API key.

    Raises:
        ValueError: If the Gemini API key is not set.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "Gemini API key not found. Please set the GEMINI_API_KEY environment variable."
        )
    return api_key


class ConfigDict(dict):
    """Extended dictionary class that adds utility methods to the configuration."""

    def get_iso_timestamp(self) -> str:
        """Get the current timestamp in ISO format.

        Returns:
            str: The current UTC timestamp in ISO format.
        """
        return datetime.datetime.now(datetime.timezone.utc).isoformat()


# Convert the regular dictionary to our extended ConfigDict
config_dict = get_config()
CONFIG = ConfigDict(config_dict)
