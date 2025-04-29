"""Logging utilities for the newsletter generator.

This module provides a centralized logging configuration and utility functions
for consistent logging across the application.
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from typing import Optional

from .config import CONFIG


def setup_logger(
    name: str,
    log_file: Optional[str] = None,
    level: Optional[str] = None,
    max_bytes: Optional[int] = None,
    backup_count: Optional[int] = None,
) -> logging.Logger:
    """Set up and configure a logger.

    Args:
        name: The name of the logger, typically the component name.
        log_file: Path to the log file. If None, uses the default from config.
        level: The logging level. If None, uses the default from config.
        max_bytes: Maximum size of log file before rotation. If None, uses the default from config.
        backup_count: Number of backup log files to keep. If None, uses the default from config.

    Returns:
        A configured logger instance.
    """
    # Use the default log file from config if log_file is not explicitly set to None
    if log_file is None and "LOG_FILE" in CONFIG:
        log_file = CONFIG.get("LOG_FILE")

    level_name = level or CONFIG.get("LOG_LEVEL", "INFO")
    max_bytes = max_bytes or CONFIG.get("LOG_MAX_BYTES", 10485760)  # Default 10MB
    backup_count = backup_count or CONFIG.get("LOG_BACKUP_COUNT", 5)

    level = getattr(logging, level_name.upper(), logging.INFO)

    logger = logging.getLogger(name)
    logger.setLevel(level)

    if logger.handlers:
        logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Only add a file handler if log_file is specified and not None
    if log_file:
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)

        file_handler = RotatingFileHandler(
            log_file, maxBytes=max_bytes, backupCount=backup_count
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(component_name: str) -> logging.Logger:
    """Get a logger for a specific component.

    This is the main function that should be used by components to get their logger.

    Args:
        component_name: The name of the component requesting the logger.

    Returns:
        A configured logger instance.
    """
    return setup_logger(component_name)


logger = get_logger("utils")
