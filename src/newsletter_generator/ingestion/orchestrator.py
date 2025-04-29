"""Ingestion orchestrator for the newsletter generator.

This module orchestrates the ingestion process for URLs, determining content type
and routing to appropriate fetchers, parsers, and standardizers.
"""

import re
import asyncio
from typing import Dict, Any, Optional, Tuple
from urllib.parse import urlparse

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
import aiohttp
import requests

from newsletter_generator.utils.logging_utils import get_logger

logger = get_logger("ingestion.orchestrator")


class IngestionOrchestrator:
    """Orchestrates the ingestion process for URLs.

    This class determines the content type of a URL, routes it to the appropriate
    content fetcher, parser, and standardizer, and manages the overall ingestion
    process including retries.
    """

    def __init__(self):
        """Initialize the ingestion orchestrator."""
        from newsletter_generator.ingestion.content_fetcher import (
            HTMLContentFetcher,
            PDFContentFetcher,
            YouTubeContentFetcher,
        )
        from newsletter_generator.ingestion.content_parser import (
            HTMLContentParser,
            PDFContentParser,
            YouTubeContentParser,
        )
        from newsletter_generator.ingestion.content_standardizer import (
            ContentStandardizer,
        )

        self.html_fetcher = HTMLContentFetcher()
        self.pdf_fetcher = PDFContentFetcher()
        self.youtube_fetcher = YouTubeContentFetcher()

        self.html_parser = HTMLContentParser()
        self.pdf_parser = PDFContentParser()
        self.youtube_parser = YouTubeContentParser()

        self.standardizer = ContentStandardizer()

    async def determine_content_type(self, url: str) -> str:
        """Determine the content type of a URL asynchronously.

        Args:
            url: The URL to check.

        Returns:
            The content type: 'html', 'pdf', or 'youtube'.

        Raises:
            ValueError: If the content type cannot be determined.
        """
        youtube_patterns = [
            r"(?:https?:\/\/)?(?:www\.)?youtube\.com\/watch\?v=([a-zA-Z0-9_-]+)",
            r"(?:https?:\/\/)?(?:www\.)?youtu\.be\/([a-zA-Z0-9_-]+)",
        ]

        for pattern in youtube_patterns:
            if re.match(pattern, url):
                return "youtube"

        if url.lower().endswith(".pdf"):
            return "pdf"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.head(
                    url, allow_redirects=True, timeout=10
                ) as response:
                    content_type = response.headers.get("Content-Type", "").lower()

                    if "application/pdf" in content_type:
                        return "pdf"
                    elif any(
                        html_type in content_type
                        for html_type in ["text/html", "application/xhtml+xml"]
                    ):
                        return "html"
        except Exception as e:
            logger.warning(f"Error determining content type for {url}: {e}")
            return "html"

        return "html"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, ConnectionError)),
        reraise=True,
    )
    async def ingest_url(self, url: str) -> Tuple[str, Dict[str, Any]]:
        """Ingest content from a URL.

        Args:
            url: The URL to ingest.

        Returns:
            A tuple containing the standardized Markdown content and metadata.

        Raises:
            ValueError: If the URL is invalid or the content type is unsupported.
            aiohttp.ClientError: If there's an error fetching the content.
        """
        logger.info(f"Ingesting URL: {url}")

        try:
            result = urlparse(url)
            if not all([result.scheme, result.netloc]):
                raise ValueError(f"Invalid URL: {url}")
        except Exception as e:
            logger.error(f"Invalid URL {url}: {e}")
            raise ValueError(f"Invalid URL: {url}")

        content_type = await self.determine_content_type(url)
        logger.info(f"Determined content type for {url}: {content_type}")

        raw_content = None
        if content_type == "html":
            raw_content = await self.html_fetcher.fetch(url)
        elif content_type == "pdf":
            raw_content = await self.pdf_fetcher.fetch(url)
        elif content_type == "youtube":
            raw_content = await self.youtube_fetcher.fetch(url)
        else:
            raise ValueError(f"Unsupported content type: {content_type}")

        parsed_content = None
        if content_type == "html":
            parsed_content = self.html_parser.parse(raw_content, url)
        elif content_type == "pdf":
            parsed_content = self.pdf_parser.parse(raw_content)
        elif content_type == "youtube":
            parsed_content = self.youtube_parser.parse(raw_content)

        standardized_content = self.standardizer.standardize(parsed_content)

        metadata = {
            "url": url,
            "source_type": content_type,
            "status": "pending_ai",
        }

        return standardized_content, metadata


# Create a singleton instance
orchestrator = IngestionOrchestrator()


async def ingest_url(url: str) -> Tuple[str, Dict[str, Any]]:
    """Ingest content from a URL.

    This is a convenience function that uses the singleton orchestrator instance.

    Args:
        url: The URL to ingest.

    Returns:
        A tuple containing the standardized Markdown content and metadata.
    """
    return await orchestrator.ingest_url(url)
