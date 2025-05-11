"""Deduplication utilities for the newsletter generator.

DEPRECATED: This module is deprecated and will be removed in a future version.
Please use newsletter_generator.utils.content_processing instead.

This module provides functions for URL normalisation, content fingerprinting,
and other utilities to prevent duplicate content in the system.
"""

import warnings
from typing import Set

from newsletter_generator.utils.logging_utils import get_logger
from newsletter_generator.utils.content_processing import (
    normalise_url as cp_normalise_url,
    get_url_hash as cp_get_url_hash,
    extract_significant_words as cp_extract_significant_words,
    generate_content_fingerprint as cp_generate_content_fingerprint,
    calculate_content_similarity as cp_calculate_content_similarity,
)

logger = get_logger("utils.deduplication")

warnings.warn(
    "The deduplication module is deprecated and will be removed in a future version. "
    "Please use newsletter_generator.utils.content_processing instead.",
    DeprecationWarning,
    stacklevel=2,
)


def normalise_url(url: str) -> str:
    """Normalise URL by removing tracking parameters and standardising format.

    DEPRECATED: Use newsletter_generator.utils.content_processing.normalise_url instead.

    Args:
        url: The URL to normalise.

    Returns:
        The normalised URL string.
    """
    warnings.warn(
        "This function is deprecated. Use newsletter_generator.utils.content_processing.normalise_url instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return cp_normalise_url(url)


def get_url_hash(url: str) -> str:
    """Generate a consistent hash for a URL after normalisation.

    DEPRECATED: Use newsletter_generator.utils.content_processing.get_url_hash instead.

    Args:
        url: The URL to hash.

    Returns:
        A hexadecimal hash string of the normalised URL.
    """
    warnings.warn(
        "This function is deprecated. Use newsletter_generator.utils.content_processing.get_url_hash instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return cp_get_url_hash(url)


def extract_significant_words(text: str, min_length: int = 4, max_words: int = 1000) -> Set[str]:
    """Extract significant words from text for fingerprinting.

    DEPRECATED: Use newsletter_generator.utils.content_processing.extract_significant_words instead.

    Args:
        text: The text to extract words from.
        min_length: Minimum word length to consider significant.
        max_words: Maximum number of significant words to return.

    Returns:
        A set of significant words.
    """
    warnings.warn(
        "This function is deprecated. Use newsletter_generator.utils.content_processing.extract_significant_words instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return cp_extract_significant_words(text, min_length, max_words)


def generate_content_fingerprint(content: str, title: str = "") -> str:
    """Generate a fingerprint of content that's resistant to minor changes.

    DEPRECATED: Use newsletter_generator.utils.content_processing.generate_content_fingerprint instead.

    Args:
        content: The main content text.
        title: Optional title to include in fingerprinting.

    Returns:
        A hexadecimal hash string representing the content fingerprint.
    """
    warnings.warn(
        "This function is deprecated. Use newsletter_generator.utils.content_processing.generate_content_fingerprint instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return cp_generate_content_fingerprint(content, title)


def calculate_content_similarity(content1: str, content2: str) -> float:
    """Calculate similarity between two content strings using Jaccard similarity.

    DEPRECATED: Use newsletter_generator.utils.content_processing.calculate_content_similarity instead.

    Args:
        content1: First content string.
        content2: Second content string.

    Returns:
        Similarity score between 0.0 and 1.0.
    """
    warnings.warn(
        "This function is deprecated. Use newsletter_generator.utils.content_processing.calculate_content_similarity instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return cp_calculate_content_similarity(content1, content2)
