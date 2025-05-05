"""Test script for the ingestion pipeline.

This script allows testing the ingestion pipeline with a sample URL
without requiring the WhatsApp webhook.
"""

import asyncio
import argparse
from typing import List
import pytest

from newsletter_generator.utils.logging_utils import get_logger
from newsletter_generator.utils.config import CONFIG
from newsletter_generator.ingestion.orchestrator import ingest_url
from newsletter_generator.storage import storage_manager

logger = get_logger("ingestion.test")


@pytest.mark.skip(reason="This is a utility function for manual testing, not an automated test")
async def test_ingest_url(url: str) -> None:
    """Test ingesting a single URL.

    Args:
        url: The URL to ingest.
    """
    logger.info(f"Testing ingestion with URL: {url}")

    try:
        # Process the URL through the ingestion pipeline
        content, metadata = await ingest_url(url)

        # Add additional metadata
        metadata.update(
            {
                "date_added": CONFIG.get_iso_timestamp(),
                "source": "test_script",
            }
        )

        # Store the content in the storage manager
        content_id = storage_manager.store_content(content, metadata)

        logger.info(f"Successfully processed and stored URL: {url}")
        logger.info(f"Content ID: {content_id}")
        logger.info(f"Content type: {metadata['source_type']}")
        logger.info(f"Content length: {len(content)} characters")

        print(f"Successfully processed URL: {url}")
        print(f"Content ID: {content_id}")
        print(f"Content type: {metadata['source_type']}")
        print(f"Content length: {len(content)} characters")

    except Exception as e:
        logger.error(f"Error processing URL {url}: {e}")
        print(f"Error: {e}")


@pytest.mark.skip(reason="This is a utility function for manual testing, not an automated test")
async def test_ingest_multiple_urls(urls: List[str]) -> None:
    """Test ingesting multiple URLs.

    Args:
        urls: The URLs to ingest.
    """
    for url in urls:
        await test_ingest_url(url)


def main():
    """Main entry point for the test script."""
    parser = argparse.ArgumentParser(description="Test the ingestion pipeline with URLs.")
    parser.add_argument("urls", nargs="+", help="URLs to ingest")

    args = parser.parse_args()

    asyncio.run(test_ingest_multiple_urls(args.urls))


if __name__ == "__main__":
    main()
