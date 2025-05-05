"""Content fetchers for the newsletter generator.

This module provides classes for fetching content from different sources:
- HTML content using Crawl4AI
- PDF content using requests
- YouTube transcripts using youtube-transcript-api
"""

import asyncio
from typing import Dict, Any, List, Optional, Union, Tuple

import requests
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled

from newsletter_generator.utils.logging_utils import get_logger

logger = get_logger("ingestion.content_fetcher")


class HTMLContentFetcher:
    """Fetches HTML content from URLs using Crawl4AI.

    This class uses Crawl4AI's AsyncWebCrawler to navigate to URLs and
    retrieve the main content as Markdown.
    """

    def __init__(self):
        """Initialise the HTML content fetcher."""
        self.browser_config = BrowserConfig(
            headless=True,
            ignore_https_errors=True,
        )
        self.crawler_config = CrawlerRunConfig(
            page_timeout=60000,  # 60 seconds
            delay_before_return_html=5.0,  # 5 seconds
        )

    async def fetch(self, url: str) -> Dict[str, Any]:
        """Fetch HTML content from a URL.

        Args:
            url: The URL to fetch content from.

        Returns:
            A dictionary containing the fetched content and metadata.

        Raises:
            Exception: If there's an error fetching the content.
        """
        logger.info(f"Fetching HTML content from {url}")

        try:
            # Create the crawler
            crawler = AsyncWebCrawler(
                config=self.browser_config,
            )

            # Start the crawler explicitly
            await crawler.start()

            try:
                # Run the crawler to get the result
                result = await crawler.arun(
                    url=url,
                    config=self.crawler_config,
                )

                if not result.success:
                    logger.error(
                        f"Failed to fetch HTML content from {url}: {result.error_message}"
                    )
                    raise Exception(
                        f"Failed to fetch HTML content: {result.error_message}"
                    )

                # Log the available attributes for debugging
                logger.debug(f"Available attributes in CrawlResult: {dir(result)}")

                # Get the markdown content - recent versions use a dedicated markdown attribute
                markdown_content = ""
                if hasattr(result, "markdown"):
                    if isinstance(result.markdown, str):
                        markdown_content = result.markdown
                    elif hasattr(result.markdown, "raw_markdown"):
                        markdown_content = result.markdown.raw_markdown
                    elif hasattr(result.markdown, "fit_markdown"):
                        markdown_content = result.markdown.fit_markdown

                # Get HTML content - may be under cleaned_html or html attribute
                html_content = ""
                if hasattr(result, "cleaned_html"):
                    html_content = result.cleaned_html
                elif hasattr(result, "html"):
                    html_content = result.html

                # Extract title - could be in metadata or elsewhere
                title = url  # Default to URL if no title is found
                if hasattr(result, "metadata") and hasattr(result.metadata, "title"):
                    title = result.metadata.title

                return {
                    "markdown": markdown_content,
                    "html": html_content,
                    "title": title,
                    "url": url,
                }
            finally:
                # Make sure to close the crawler in the finally block
                await crawler.close()
        except Exception as e:
            logger.error(f"Error fetching HTML content from {url}: {e}")
            raise


class PDFContentFetcher:
    """Fetches PDF content from URLs using requests.

    This class uses the requests library to download PDF files.
    """

    def __init__(self):
        """Initialise the PDF content fetcher."""
        pass

    async def fetch(self, url: str) -> bytes:
        """Fetch PDF content from a URL.

        Args:
            url: The URL to fetch content from.

        Returns:
            The raw PDF content as bytes.

        Raises:
            Exception: If there's an error fetching the content or if the content
                is not a PDF.
        """
        logger.info(f"Fetching PDF content from {url}")

        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, lambda: requests.get(url, timeout=30)
            )

            response.raise_for_status()

            content_type = response.headers.get("Content-Type", "").lower()
            if "application/pdf" not in content_type:
                logger.warning(
                    f"Content from {url} is not a PDF (Content-Type: {content_type}). "
                    "Proceeding anyway."
                )

            return response.content
        except Exception as e:
            logger.error(f"Error fetching PDF content from {url}: {e}")
            raise


class YouTubeContentFetcher:
    """Fetches YouTube transcripts using youtube-transcript-api.

    This class uses the YouTubeTranscriptApi to fetch transcripts for YouTube videos.
    """

    def __init__(self):
        """Initialise the YouTube content fetcher."""
        pass

    def _extract_video_id(self, url: str) -> str:
        """Extract the video ID from a YouTube URL.

        Args:
            url: The YouTube URL.

        Returns:
            The video ID.

        Raises:
            ValueError: If the video ID cannot be extracted.
        """
        import re

        patterns = [
            r"(?:https?:\/\/)?(?:www\.)?youtube\.com\/watch\?v=([a-zA-Z0-9_-]+)",
            r"(?:https?:\/\/)?(?:www\.)?youtu\.be\/([a-zA-Z0-9_-]+)",
        ]

        for pattern in patterns:
            match = re.match(pattern, url)
            if match:
                return match.group(1)

        raise ValueError(f"Could not extract video ID from YouTube URL: {url}")

    async def fetch(self, url: str) -> List[Dict[str, Any]]:
        """Fetch transcript for a YouTube video.

        Args:
            url: The YouTube URL.

        Returns:
            A list of transcript segments, each containing 'text' and 'start' keys.

        Raises:
            Exception: If there's an error fetching the transcript.
        """
        logger.info(f"Fetching YouTube transcript from {url}")

        try:
            video_id = self._extract_video_id(url)
            logger.debug(f"Extracted video ID: {video_id}")

            loop = asyncio.get_event_loop()
            transcript_list = await loop.run_in_executor(
                None, lambda: YouTubeTranscriptApi.list_transcripts(video_id)
            )

            try:
                transcript = transcript_list.find_transcript(["en"])
            except Exception:
                try:
                    transcript = transcript_list.find_generated_transcript(["en"])
                except Exception:
                    transcript = transcript_list.find_transcript(
                        ["en", "es", "fr", "de"]
                    )

            transcript_data = await loop.run_in_executor(
                None, lambda: transcript.fetch()
            )

            return transcript_data
        except TranscriptsDisabled:
            logger.error(f"Transcripts are disabled for video: {url}")
            raise Exception(f"Transcripts are disabled for this YouTube video")
        except Exception as e:
            logger.error(f"Error fetching YouTube transcript from {url}: {e}")
            raise
