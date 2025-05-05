"""Tests for the ingestion orchestrator module."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio

from newsletter_generator.ingestion.orchestrator import (
    IngestionOrchestrator,
    ingest_url,
)


class TestIngestionOrchestrator:
    """Test cases for the IngestionOrchestrator class."""

    def test_determine_content_type_youtube(self):
        """Test that YouTube URLs are correctly identified."""
        orchestrator = IngestionOrchestrator()

        youtube_urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ",
            "http://www.youtube.com/watch?v=dQw4w9WgXcQ",
        ]

        for url in youtube_urls:
            assert orchestrator.determine_content_type(url) == "youtube"

    def test_determine_content_type_pdf_by_extension(self):
        """Test that PDF URLs with .pdf extension are correctly identified."""
        orchestrator = IngestionOrchestrator()

        pdf_urls = [
            "https://example.com/document.pdf",
            "http://example.com/path/to/document.pdf",
        ]

        for url in pdf_urls:
            assert orchestrator.determine_content_type(url) == "pdf"

    @patch("requests.head")
    def test_determine_content_type_pdf_by_content_type(self, mock_head):
        """Test that PDF URLs with application/pdf content type are correctly identified."""
        mock_response = MagicMock()
        mock_response.headers = {"Content-Type": "application/pdf"}
        mock_head.return_value = mock_response

        orchestrator = IngestionOrchestrator()

        url = "https://example.com/document"
        assert orchestrator.determine_content_type(url) == "pdf"

        mock_head.assert_called_once_with(url, allow_redirects=True, timeout=10)

    @patch("requests.head")
    def test_determine_content_type_html(self, mock_head):
        """Test that HTML URLs are correctly identified."""
        mock_response = MagicMock()
        mock_response.headers = {"Content-Type": "text/html"}
        mock_head.return_value = mock_response

        orchestrator = IngestionOrchestrator()

        url = "https://example.com/page"
        assert orchestrator.determine_content_type(url) == "html"

        mock_head.assert_called_once_with(url, allow_redirects=True, timeout=10)

    @patch("requests.head")
    def test_determine_content_type_request_error(self, mock_head):
        """Test that HTML is returned as fallback when request fails."""
        mock_head.side_effect = Exception("Connection error")

        orchestrator = IngestionOrchestrator()

        url = "https://example.com/page"
        assert orchestrator.determine_content_type(url) == "html"

        mock_head.assert_called_once_with(url, allow_redirects=True, timeout=10)

    @pytest.mark.asyncio
    @patch(
        "newsletter_generator.ingestion.orchestrator.IngestionOrchestrator.determine_content_type"
    )
    async def test_ingest_url_invalid_url(self, mock_determine_content_type):
        """Test that ingest_url raises ValueError for invalid URLs."""
        orchestrator = IngestionOrchestrator()

        with pytest.raises(ValueError, match="Invalid URL"):
            await orchestrator.ingest_url("not a url")

        mock_determine_content_type.assert_not_called()

    @pytest.mark.asyncio
    @patch(
        "newsletter_generator.ingestion.orchestrator.IngestionOrchestrator.determine_content_type"
    )
    async def test_ingest_url_unsupported_content_type(
        self, mock_determine_content_type
    ):
        """Test that ingest_url raises ValueError for unsupported content types."""
        mock_determine_content_type.return_value = "unsupported"

        orchestrator = IngestionOrchestrator()

        with pytest.raises(ValueError, match="Unsupported content type"):
            await orchestrator.ingest_url("https://example.com")

    @pytest.mark.asyncio
    @patch(
        "newsletter_generator.ingestion.orchestrator.IngestionOrchestrator.determine_content_type"
    )
    async def test_ingest_url_html(self, mock_determine_content_type):
        """Test that ingest_url correctly processes HTML content."""
        mock_determine_content_type.return_value = "html"

        orchestrator = IngestionOrchestrator()
        orchestrator.html_fetcher.fetch = AsyncMock(
            return_value={"markdown": "# Test", "html": "<h1>Test</h1>"}
        )
        orchestrator.html_parser.parse = MagicMock(return_value="# Parsed Test")
        orchestrator.standardiser.standardise = MagicMock(
            return_value="# Standardised Test"
        )

        content, metadata = await orchestrator.ingest_url("https://example.com")

        assert content == "# Standardised Test"
        assert metadata["url"] == "https://example.com"
        assert metadata["source_type"] == "html"
        assert metadata["status"] == "pending_ai"

        orchestrator.html_fetcher.fetch.assert_called_once_with("https://example.com")
        orchestrator.html_parser.parse.assert_called_once()
        orchestrator.standardiser.standardise.assert_called_once_with("# Parsed Test")

    @pytest.mark.asyncio
    @patch(
        "newsletter_generator.ingestion.orchestrator.IngestionOrchestrator.determine_content_type"
    )
    async def test_ingest_url_pdf(self, mock_determine_content_type):
        """Test that ingest_url correctly processes PDF content."""
        mock_determine_content_type.return_value = "pdf"

        orchestrator = IngestionOrchestrator()
        orchestrator.pdf_fetcher.fetch = AsyncMock(return_value=b"PDF content")
        orchestrator.pdf_parser.parse = MagicMock(return_value="# Parsed PDF")
        orchestrator.standardiser.standardise = MagicMock(
            return_value="# Standardised PDF"
        )

        content, metadata = await orchestrator.ingest_url("https://example.com/doc.pdf")

        assert content == "# Standardised PDF"
        assert metadata["url"] == "https://example.com/doc.pdf"
        assert metadata["source_type"] == "pdf"
        assert metadata["status"] == "pending_ai"

        orchestrator.pdf_fetcher.fetch.assert_called_once_with(
            "https://example.com/doc.pdf"
        )
        orchestrator.pdf_parser.parse.assert_called_once_with(b"PDF content")
        orchestrator.standardiser.standardise.assert_called_once_with("# Parsed PDF")

    @pytest.mark.asyncio
    @patch(
        "newsletter_generator.ingestion.orchestrator.IngestionOrchestrator.determine_content_type"
    )
    async def test_ingest_url_youtube(self, mock_determine_content_type):
        """Test that ingest_url correctly processes YouTube content."""
        mock_determine_content_type.return_value = "youtube"

        orchestrator = IngestionOrchestrator()
        orchestrator.youtube_fetcher.fetch = AsyncMock(
            return_value=[{"text": "Transcript", "start": 0}]
        )
        orchestrator.youtube_parser.parse = MagicMock(return_value="# Parsed YouTube")
        orchestrator.standardiser.standardise = MagicMock(
            return_value="# Standardised YouTube"
        )

        content, metadata = await orchestrator.ingest_url(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        )

        assert content == "# Standardised YouTube"
        assert metadata["url"] == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert metadata["source_type"] == "youtube"
        assert metadata["status"] == "pending_ai"

        orchestrator.youtube_fetcher.fetch.assert_called_once_with(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        )
        orchestrator.youtube_parser.parse.assert_called_once_with(
            [{"text": "Transcript", "start": 0}]
        )
        orchestrator.standardiser.standardise.assert_called_once_with(
            "# Parsed YouTube"
        )

    @pytest.mark.asyncio
    async def test_ingest_url_convenience_function(self):
        """Test that the ingest_url convenience function calls the orchestrator."""
        with patch(
            "newsletter_generator.ingestion.orchestrator.orchestrator.ingest_url"
        ) as mock_ingest:
            mock_ingest.return_value = ("content", {"metadata": "value"})

            result = await ingest_url("https://example.com")

            assert result == ("content", {"metadata": "value"})
            mock_ingest.assert_called_once_with("https://example.com")


if __name__ == "__main__":
    pytest.main()
