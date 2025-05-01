"""Tests for the config module."""

import os
import unittest
from unittest.mock import patch

from newsletter_generator.utils.config import get_config, get_openai_api_key, DEFAULT_CONFIG


class TestConfig(unittest.TestCase):
    """Test cases for the config module."""

    def test_get_config_defaults(self):
        """Test that get_config returns default values when no environment variables are set."""
        with patch.dict(os.environ, {}, clear=True):
            config = get_config()
            self.assertEqual(config, DEFAULT_CONFIG)

    def test_get_config_override(self):
        """Test that get_config overrides defaults with environment variables."""
        test_env = {
            "OPENAI_API_KEY": "test_key",
            "LOG_LEVEL": "DEBUG",
            "TTL_DAYS": "30",  # String that should be converted to int
        }
        with patch.dict(os.environ, test_env, clear=True):
            config = get_config()
            self.assertEqual(config["OPENAI_API_KEY"], "test_key")
            self.assertEqual(config["LOG_LEVEL"], "DEBUG")
            self.assertEqual(config["TTL_DAYS"], 30)  # Should be converted to int
            self.assertEqual(config["DATA_DIR"], DEFAULT_CONFIG["DATA_DIR"])

    def test_get_openai_api_key_from_env(self):
        """Test that get_openai_api_key returns the key from OPENAI_API_KEY env var."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}, clear=True):
            api_key = get_openai_api_key()
            self.assertEqual(api_key, "test_key")

    def test_get_openai_api_key_from_oai(self):
        """Test that get_openai_api_key returns the key from OAI env var if OPENAI_API_KEY is not set."""
        with patch.dict(os.environ, {"OAI": "test_oai_key"}, clear=True):
            api_key = get_openai_api_key()
            self.assertEqual(api_key, "test_oai_key")

    def test_get_openai_api_key_missing(self):
        """Test that get_openai_api_key raises ValueError when no key is available."""
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError):
                get_openai_api_key()


if __name__ == "__main__":
    unittest.main()
