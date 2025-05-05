"""Tests for the logging_utils module."""

import logging
import os
import unittest
from unittest.mock import patch, MagicMock
from logging.handlers import RotatingFileHandler

from newsletter_generator.utils.logging_utils import setup_logger, get_logger


class TestLoggingUtils(unittest.TestCase):
    """Test cases for the logging_utils module."""

    def setUp(self):
        """Set up test fixtures."""
        logging.Logger.manager.loggerDict.clear()
        root = logging.getLogger()
        if root.handlers:
            for handler in root.handlers:
                root.removeHandler(handler)

    def test_setup_logger_defaults(self):
        """Test that setup_logger creates a logger with default settings."""
        with patch(
            "newsletter_generator.utils.logging_utils.CONFIG",
            {
                "LOG_FILE": "test.log",
                "LOG_LEVEL": "INFO",
                "LOG_MAX_BYTES": 1024,
                "LOG_BACKUP_COUNT": 3,
            },
        ):
            logger = setup_logger("test_logger")

            self.assertEqual(logger.name, "test_logger")
            self.assertEqual(logger.level, logging.INFO)

            self.assertEqual(len(logger.handlers), 2)  # Console and file handler

            console_handler = next(
                h
                for h in logger.handlers
                if isinstance(h, logging.StreamHandler) and not isinstance(h, RotatingFileHandler)
            )
            self.assertEqual(console_handler.level, logging.NOTSET)  # Inherits from logger

            file_handler = next(h for h in logger.handlers if isinstance(h, RotatingFileHandler))
            self.assertEqual(file_handler.level, logging.NOTSET)  # Inherits from logger
            self.assertEqual(file_handler.baseFilename, os.path.abspath("test.log"))
            self.assertEqual(file_handler.maxBytes, 1024)
            self.assertEqual(file_handler.backupCount, 3)

    def test_setup_logger_custom_settings(self):
        """Test that setup_logger respects custom settings."""
        logger = setup_logger(
            "custom_logger",
            log_file="custom.log",
            level="DEBUG",
            max_bytes=2048,
            backup_count=5,
        )

        self.assertEqual(logger.name, "custom_logger")
        self.assertEqual(logger.level, logging.DEBUG)

        self.assertEqual(len(logger.handlers), 2)  # Console and file handler

        file_handler = next(h for h in logger.handlers if isinstance(h, RotatingFileHandler))
        self.assertEqual(file_handler.baseFilename, os.path.abspath("custom.log"))
        self.assertEqual(file_handler.maxBytes, 2048)
        self.assertEqual(file_handler.backupCount, 5)

    def test_setup_logger_no_file(self):
        """Test that setup_logger works without a log file."""
        # Override CONFIG to ensure no default log file is used
        with patch("newsletter_generator.utils.logging_utils.CONFIG", {}):
            logger = setup_logger("no_file_logger", log_file=None)

            self.assertEqual(logger.name, "no_file_logger")

            self.assertEqual(len(logger.handlers), 1)
            self.assertTrue(isinstance(logger.handlers[0], logging.StreamHandler))
            self.assertFalse(isinstance(logger.handlers[0], RotatingFileHandler))

    def test_get_logger(self):
        """Test that get_logger returns a properly configured logger."""
        with patch("newsletter_generator.utils.logging_utils.setup_logger") as mock_setup:
            mock_logger = MagicMock()
            mock_setup.return_value = mock_logger

            logger = get_logger("component_name")

            mock_setup.assert_called_once_with("component_name")
            self.assertEqual(logger, mock_logger)


if __name__ == "__main__":
    unittest.main()
