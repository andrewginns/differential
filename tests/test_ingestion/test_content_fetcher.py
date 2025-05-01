"""Tests for the content fetcher module."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio

from newsletter_generator.ingestion.content_fetcher import (
    HTMLContentFetcher,
    PDFContentFetcher,
    YouTubeContentFetcher,
)


class TestHTMLContentFetcher:
    """Test cases for the HTMLContentFetcher class."""

    @pytest.mark.asyncio
    @patch("newsletter_generator.ingestion.content_fetcher.AsyncWebCrawler")
    async def test_fetch_success(self, mock_crawler_class):
        """Test successful HTML content fetching."""
        mock_crawler = AsyncMock()
        mock_crawler_class.return_value = mock_crawler

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.markdown = "# Test Markdown"
        mock_result.html = "<h1>Test HTML</h1>"
        mock_result.title = "Test Title"

        mock_crawler.arun.return_value = mock_result

        fetcher = HTMLContentFetcher()
        result = await fetcher.fetch("https://example.com")

        assert result["markdown"] == "# Test Markdown"
        assert result["html"] == "<h1>Test HTML</h1>"
        assert result["title"] == "Test Title"
        assert result["url"] == "https://example.com"

        mock_crawler_class.assert_called_once()
        mock_crawler.arun.assert_called_once()
        mock_crawler.stop.assert_called_once()

    @pytest.mark.asyncio
    @patch("newsletter_generator.ingestion.content_fetcher.AsyncWebCrawler")
    async def test_fetch_failure(self, mock_crawler_class):
        """Test HTML content fetching failure."""
        mock_crawler = AsyncMock()
        mock_crawler_class.return_value = mock_crawler

        mock_result = MagicMock()
        mock_result.success = False
        mock_result.error_message = "Crawl failed"

        mock_crawler.arun.return_value = mock_result

        fetcher = HTMLContentFetcher()

        with pytest.raises(Exception, match="Failed to fetch HTML content"):
            await fetcher.fetch("https://example.com")

        mock_crawler_class.assert_called_once()
        mock_crawler.arun.assert_called_once()
        mock_crawler.stop.assert_called_once()

    @pytest.mark.asyncio
    @patch("newsletter_generator.ingestion.content_fetcher.AsyncWebCrawler")
    async def test_fetch_exception(self, mock_crawler_class):
        """Test HTML content fetching with exception."""
        mock_crawler = AsyncMock()
        mock_crawler_class.return_value = mock_crawler

        mock_crawler.arun.side_effect = Exception("Test exception")

        fetcher = HTMLContentFetcher()

        with pytest.raises(Exception):
            await fetcher.fetch("https://example.com")

        mock_crawler_class.assert_called_once()
        mock_crawler.arun.assert_called_once()


class TestPDFContentFetcher:
    """Test cases for the PDFContentFetcher class."""

    @pytest.mark.asyncio
    @patch("newsletter_generator.ingestion.content_fetcher.requests.get")
    async def test_fetch_success(self, mock_requests_get):
        """Test successful PDF content fetching."""
        mock_response = MagicMock()
        mock_response.headers = {"Content-Type": "application/pdf"}
        mock_response.content = b"PDF content"
        mock_requests_get.return_value = mock_response

        fetcher = PDFContentFetcher()
        result = await fetcher.fetch("https://example.com/doc.pdf")

        assert result == b"PDF content"
        mock_requests_get.assert_called_once_with(
            "https://example.com/doc.pdf", timeout=30
        )

    @pytest.mark.asyncio
    @patch("newsletter_generator.ingestion.content_fetcher.requests.get")
    async def test_fetch_non_pdf_content_type(self, mock_requests_get):
        """Test PDF content fetching with non-PDF content type."""
        mock_response = MagicMock()
        mock_response.headers = {"Content-Type": "text/plain"}
        mock_response.content = b"Not a PDF"
        mock_requests_get.return_value = mock_response

        fetcher = PDFContentFetcher()
        result = await fetcher.fetch("https://example.com/doc.txt")

        assert result == b"Not a PDF"
        mock_requests_get.assert_called_once_with(
            "https://example.com/doc.txt", timeout=30
        )

    @pytest.mark.asyncio
    @patch("newsletter_generator.ingestion.content_fetcher.requests.get")
    async def test_fetch_http_error(self, mock_requests_get):
        """Test PDF content fetching with HTTP error."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("HTTP error")
        mock_requests_get.return_value = mock_response

        fetcher = PDFContentFetcher()

        with pytest.raises(Exception):
            await fetcher.fetch("https://example.com/doc.pdf")

        mock_requests_get.assert_called_once_with(
            "https://example.com/doc.pdf", timeout=30
        )


class TestYouTubeContentFetcher:
    """Test cases for the YouTubeContentFetcher class."""

    def test_extract_video_id_watch_url(self):
        """Test extracting video ID from watch URL."""
        fetcher = YouTubeContentFetcher()
        video_id = fetcher._extract_video_id(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        )
        assert video_id == "dQw4w9WgXcQ"

    def test_extract_video_id_short_url(self):
        """Test extracting video ID from short URL."""
        fetcher = YouTubeContentFetcher()
        video_id = fetcher._extract_video_id("https://youtu.be/dQw4w9WgXcQ")
        assert video_id == "dQw4w9WgXcQ"

    def test_extract_video_id_invalid_url(self):
        """Test extracting video ID from invalid URL."""
        fetcher = YouTubeContentFetcher()
        with pytest.raises(ValueError, match="Could not extract video ID"):
            fetcher._extract_video_id("https://example.com")

    @pytest.mark.asyncio
    @patch(
        "newsletter_generator.ingestion.content_fetcher.YouTubeTranscriptApi.list_transcripts"
    )
    async def test_fetch_success(self, mock_list_transcripts):
        """Test successful YouTube transcript fetching."""
        mock_transcript_list = MagicMock()
        mock_transcript = MagicMock()
        mock_transcript_data = [{"text": "Test transcript", "start": 0}]

        mock_transcript_list.find_transcript.return_value = mock_transcript
        mock_transcript.fetch.return_value = mock_transcript_data
        mock_list_transcripts.return_value = mock_transcript_list

        fetcher = YouTubeContentFetcher()
        result = await fetcher.fetch("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

        assert result == mock_transcript_data
        mock_list_transcripts.assert_called_once_with("dQw4w9WgXcQ")

    @pytest.mark.asyncio
    @patch(
        "newsletter_generator.ingestion.content_fetcher.YouTubeTranscriptApi.list_transcripts"
    )
    async def test_fetch_generated_transcript(self, mock_list_transcripts):
        """Test YouTube transcript fetching with generated transcript."""
        mock_transcript_list = MagicMock()
        mock_transcript = MagicMock()
        mock_transcript_data = [{"text": "Test transcript", "start": 0}]

        mock_transcript_list.find_transcript.side_effect = Exception("No transcript")
        mock_transcript_list.find_generated_transcript.return_value = mock_transcript
        mock_transcript.fetch.return_value = mock_transcript_data
        mock_list_transcripts.return_value = mock_transcript_list

        fetcher = YouTubeContentFetcher()
        result = await fetcher.fetch("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

        assert result == mock_transcript_data
        mock_list_transcripts.assert_called_once_with("dQw4w9WgXcQ")

    @pytest.mark.asyncio
    @patch(
        "newsletter_generator.ingestion.content_fetcher.YouTubeTranscriptApi.list_transcripts"
    )
    async def test_fetch_transcripts_disabled(self, mock_list_transcripts):
        """Test YouTube transcript fetching with transcripts disabled."""
        from youtube_transcript_api import TranscriptsDisabled

        mock_list_transcripts.side_effect = TranscriptsDisabled("Transcripts disabled")

        fetcher = YouTubeContentFetcher()
        with pytest.raises(Exception, match="Transcripts are disabled"):
            await fetcher.fetch("https://www.youtube.com/watch?v=dQw4w9WgXcQ")


if __name__ == "__main__":
    pytest.main()
