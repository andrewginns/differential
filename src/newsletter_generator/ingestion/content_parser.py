"""Content parsers for the newsletter generator.

This module provides classes for parsing content from different sources:
- HTML content using Trafilatura as a fallback for Crawl4AI
- PDF content using PyMuPDF (Fitz)
- YouTube transcripts using youtube-transcript-api
"""

from typing import Dict, Any

import fitz  # PyMuPDF
import pymupdf4llm
import trafilatura
import re

from newsletter_generator.utils.logging_utils import get_logger

logger = get_logger("ingestion.content_parser")


class HTMLContentParser:
    """Parses HTML content.

    This class primarily relies on Crawl4AI's built-in Markdown generation,
    with Trafilatura as a fallback or supplementary method.
    """

    def __init__(self):
        """Initialise the HTML content parser."""
        pass

    def parse(self, content: Dict[str, Any], url: str) -> str:
        """Parse HTML content.

        Args:
            content: The content dictionary from the HTML fetcher, containing
                'markdown', 'html', and other metadata.
            url: The source URL.

        Returns:
            The parsed content as Markdown.

        Raises:
            Exception: If there's an error parsing the content.
        """
        logger.info(f"Parsing HTML content from {url}")

        try:
            if content.get("markdown") and len(content["markdown"]) > 100:
                logger.debug("Using Crawl4AI's Markdown output")
                return content["markdown"]

            logger.debug("Falling back to Trafilatura for HTML parsing")
            html = content.get("html", "")
            if not html:
                raise Exception("No HTML content available for parsing")

            extracted_text = trafilatura.extract(
                html,
                output_format="markdown",
                include_links=False,
                include_images=True,
                include_tables=True,
            )

            if not extracted_text:
                logger.warning(f"Trafilatura failed to extract content from {url}")
                title = content.get("title", "Untitled")
                return f"# {title}\n\n*Content extraction failed*"

            return extracted_text
        except Exception as e:
            logger.error(f"Error parsing HTML content from {url}: {e}")
            raise


class PDFContentParser:
    """Parses PDF content using PyMuPDF (Fitz).

    This class extracts text from PDF documents.
    """

    def __init__(self):
        """Initialise the PDF content parser."""
        pass

    def _remove_references_section(self, markdown_text: str) -> str:
        """Remove references section and all content after it.

        Args:
            markdown_text: The markdown text to process

        Returns:
            Processed markdown text with references section removed
        """
        # Various patterns to match reference sections with exact matches
        # for common references section formats
        patterns = [
            # Markdown headings
            r"(?m)^# References$",  # Level 1 heading
            r"(?m)^## References$",  # Level 2 heading
            r"(?m)^### References$",  # Level 3 heading
            r"(?m)^# Reference$",  # Singular form
            r"(?m)^## Reference$",  # Level 2 singular
            r"(?m)^### Reference$",  # Level 3 singular
            # Plain text
            r"(?m)^References$",  # Plain text on its own line
            r"(?m)^Reference$",  # Singular form
            # Bold formatting
            r"(?m)^\*\*References\*\*$",  # Bold format
            r"(?m)^\*\*Reference\*\*$",  # Bold singular
            r"(?m)^__References__$",  # Alternate bold
            r"(?m)^__Reference__$",  # Alternate bold singular
            # Numbered sections
            r"(?m)^\d+\.\s*References$",  # e.g., "5. References"
            r"(?m)^\d+\.\s*Reference$",  # Singular form
        ]

        # Find the earliest match of any pattern
        min_index = len(markdown_text)
        for pattern in patterns:
            matches = list(re.finditer(pattern, markdown_text))
            if matches:
                for match in matches:
                    logger.debug(
                        f"References section found: '{match.group()}' at position {match.start()}"
                    )
                    min_index = min(min_index, match.start())

        # If we found a reference section, return text up to that point
        if min_index < len(markdown_text):
            logger.info(f"References section found and removed at position {min_index}")
            return markdown_text[:min_index].strip()

        logger.debug("No references section found")
        return markdown_text

    def parse(self, content: bytes) -> str:
        """Parse PDF content.

        Args:
            content: The raw PDF content as bytes.

        Returns:
            The extracted text as Markdown.

        Raises:
            Exception: If there's an error parsing the PDF.
        """
        logger.info("Parsing PDF content")

        try:
            doc = fitz.open(stream=content, filetype="pdf")
            # Extract Markdown using LLM-centric approach
            full_text = pymupdf4llm.to_markdown(doc)
            # Remove references section and everything after it
            processed_text = self._remove_references_section(full_text)
            # Format as Markdown with title
            markdown = f"# PDF Document\n\n{processed_text}"

            return markdown
        except Exception as e:
            logger.error(f"Error parsing PDF content: {e}")
            raise


class YouTubeContentParser:
    """Parses YouTube transcript data.

    This class extracts transcripts from YouTube videos given a URL or video ID
    using the youtube-transcript-api library and formats them as Markdown.
    """

    def _extract_video_id(self, url_or_id: str) -> str | None:
        """Extracts the video ID from various YouTube URL formats or returns the ID itself.

        Handles URLs like:
        - https://www.youtube.com/watch?v=VIDEO_ID
        - https://youtu.be/VIDEO_ID
        - https://www.youtube.com/embed/VIDEO_ID
        - https://m.youtube.com/watch?v=VIDEO_ID
        - VIDEO_ID (if passed directly)

        Args:
            url_or_id: A YouTube video URL or a potential video ID string.

        Returns:
            The extracted video ID string, or None if no valid ID is found.
        """
        # Regex to find the video ID from various YouTube URL patterns
        # Covers standard, mobile, short URLs, and embed URLs
        patterns = [
            r"(?:v=|\/)([0-9A-Za-z_-]{11}).*",  # Standard '?v=' or '/'. Must be 11 chars.
            r"^([0-9A-Za-z_-]{11})$",  # Direct video ID
        ]

        for pattern in patterns:
            match = re.search(pattern, url_or_id)
            if match:
                # Return the first captured group if it's 11 characters long
                potential_id = match.group(1)
                if len(potential_id) == 11:
                    return potential_id

        # Basic check if the input itself might be a valid ID (11 chars, specific characters)
        if re.fullmatch(r"[0-9A-Za-z_-]{11}", url_or_id):
            return url_or_id

        return None  # Return None if no valid ID pattern is matched

    def parse(self, transcript_data) -> str:
        """Parses YouTube transcript data into formatted Markdown.

        Args:
            transcript_data: A list of FetchedTranscriptSnippet objects from the YouTube Transcript API.

        Returns:
            The transcript formatted as a Markdown string with timestamps.
        """
        logger.info("Parsing YouTube transcript data")

        try:
            # Check if the transcript has content
            if not transcript_data:
                logger.warning("Empty transcript data received")
                return "# YouTube Video Transcript\n\n*No transcript available*"

            # Format transcript with timestamps
            formatted_lines = []
            plain_text_segments = []
            has_valid_content = False

            for segment in transcript_data:
                try:
                    if hasattr(segment, "text"):
                        text = segment.text.strip()
                        start_time = segment.start
                    else:
                        text = segment.get("text", "").strip()
                        start_time = segment.get("start", 0)

                    # Skip empty segments
                    if not text:
                        continue

                    has_valid_content = True
                    plain_text_segments.append(text)

                    # Convert start time to MM:SS format
                    minutes, seconds = divmod(int(start_time), 60)
                    timestamp = f"[{minutes:02d}:{seconds:02d}]"

                    # Add formatted line with timestamp
                    formatted_lines.append(f"{timestamp} {text}")
                except (AttributeError, KeyError, TypeError):
                    continue

            if not has_valid_content:
                logger.warning("No valid transcript content could be extracted")
                return "# YouTube Video Transcript\n\n*No transcript content could be extracted*"

            # Join all lines with newlines between them
            transcript_text = "\n".join(formatted_lines)

            plain_text = " ".join(plain_text_segments)

            # Format as Markdown
            markdown = "# YouTube Video Transcript\n\n"
            markdown += transcript_text
            markdown += f"\n\n{plain_text}"

            return markdown

        except Exception as e:
            logger.error(f"Error parsing YouTube transcript: {e}")
            raise
