"""Tests for the ingestion orchestrator module."""

import pytest
from unittest.mock import patch, AsyncMock

from newsletter_generator.ingestion.orchestrator import (
    IngestionOrchestrator,
    ingest_url,
)


class TestIngestionOrchestrator:
    """Test cases for the IngestionOrchestrator class."""

    @pytest.mark.asyncio
    async def test_determine_content_type_youtube(self):
        """Test that YouTube URLs are correctly identified."""
        orchestrator = IngestionOrchestrator()

        youtube_urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ",
            "http://www.youtube.com/watch?v=dQw4w9WgXcQ",
        ]

        for url in youtube_urls:
            assert await orchestrator.determine_content_type(url) == "youtube"

    @pytest.mark.asyncio
    async def test_determine_content_type_pdf_by_extension(self):
        """Test that PDF URLs with .pdf extension are correctly identified."""
        orchestrator = IngestionOrchestrator()

        pdf_urls = [
            "https://example.com/document.pdf",
            "http://example.com/path/to/document.pdf",
        ]

        for url in pdf_urls:
            assert await orchestrator.determine_content_type(url) == "pdf"

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession.head")
    async def test_determine_content_type_pdf_by_content_type(self, mock_head):
        """Test that PDF URLs with application/pdf content type are correctly identified."""
        mock_response = AsyncMock()
        mock_response.headers = {"Content-Type": "application/pdf"}
        mock_head.return_value.__aenter__.return_value = mock_response

        orchestrator = IngestionOrchestrator()

        url = "https://example.com/document"
        assert await orchestrator.determine_content_type(url) == "pdf"

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession.head")
    async def test_determine_content_type_html(self, mock_head):
        """Test that HTML URLs are correctly identified."""
        mock_response = AsyncMock()
        mock_response.headers = {"Content-Type": "text/html"}
        mock_head.return_value.__aenter__.return_value = mock_response

        orchestrator = IngestionOrchestrator()

        url = "https://example.com/page"
        assert await orchestrator.determine_content_type(url) == "html"

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession.head")
    async def test_determine_content_type_request_error(self, mock_head):
        """Test that HTML is returned as fallback when request fails."""
        mock_head.side_effect = Exception("Connection error")

        orchestrator = IngestionOrchestrator()

        url = "https://example.com/page"
        assert await orchestrator.determine_content_type(url) == "html"

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
    async def test_ingest_url_unsupported_content_type(self, mock_determine_content_type):
        """Test that ingest_url raises ValueError for unsupported content types."""
        mock_determine_content_type.return_value = "unsupported"

        orchestrator = IngestionOrchestrator()

        with pytest.raises(ValueError, match="No processor available for content type"):
            await orchestrator.ingest_url("https://example.com")

    @pytest.mark.asyncio
    @patch(
        "newsletter_generator.ingestion.orchestrator.IngestionOrchestrator.determine_content_type"
    )
    @patch("newsletter_generator.ingestion.content_processor.ContentProcessorFactory.get_processor")
    async def test_ingest_url_html(self, mock_get_processor, mock_determine_content_type):
        """Test that ingest_url correctly processes HTML content."""
        mock_determine_content_type.return_value = "html"
        
        mock_processor = AsyncMock()
        mock_processor.process.return_value = ("# Standardised Test", {
            "url": "https://example.com",
            "source_type": "html",
            "status": "pending_ai"
        })
        mock_get_processor.return_value = mock_processor

        orchestrator = IngestionOrchestrator()
        content, metadata = await orchestrator.ingest_url("https://example.com")

        assert content == "# Standardised Test"
        assert metadata["url"] == "https://example.com"
        assert metadata["source_type"] == "html"
        assert metadata["status"] == "pending_ai"

        mock_determine_content_type.assert_called_once_with("https://example.com")
        mock_get_processor.assert_called_once_with("html")
        mock_processor.process.assert_called_once_with("https://example.com")

    @pytest.mark.asyncio
    @patch(
        "newsletter_generator.ingestion.orchestrator.IngestionOrchestrator.determine_content_type"
    )
    @patch("newsletter_generator.ingestion.content_processor.ContentProcessorFactory.get_processor")
    async def test_ingest_url_pdf(self, mock_get_processor, mock_determine_content_type):
        """Test that ingest_url correctly processes PDF content."""
        mock_determine_content_type.return_value = "pdf"
        
        mock_processor = AsyncMock()
        mock_processor.process.return_value = ("# Standardised PDF", {
            "url": "https://example.com/doc.pdf",
            "source_type": "pdf",
            "status": "pending_ai"
        })
        mock_get_processor.return_value = mock_processor

        orchestrator = IngestionOrchestrator()
        content, metadata = await orchestrator.ingest_url("https://example.com/doc.pdf")

        assert content == "# Standardised PDF"
        assert metadata["url"] == "https://example.com/doc.pdf"
        assert metadata["source_type"] == "pdf"
        assert metadata["status"] == "pending_ai"

        mock_determine_content_type.assert_called_once_with("https://example.com/doc.pdf")
        mock_get_processor.assert_called_once_with("pdf")
        mock_processor.process.assert_called_once_with("https://example.com/doc.pdf")

    @pytest.mark.asyncio
    @patch(
        "newsletter_generator.ingestion.orchestrator.IngestionOrchestrator.determine_content_type"
    )
    @patch("newsletter_generator.ingestion.content_processor.ContentProcessorFactory.get_processor")
    async def test_ingest_url_youtube(self, mock_get_processor, mock_determine_content_type):
        """Test that ingest_url correctly processes YouTube content."""
        mock_determine_content_type.return_value = "youtube"
        
        mock_processor = AsyncMock()
        mock_processor.process.return_value = ("# Standardised YouTube", {
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "source_type": "youtube",
            "status": "pending_ai"
        })
        mock_get_processor.return_value = mock_processor

        orchestrator = IngestionOrchestrator()
        content, metadata = await orchestrator.ingest_url(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        )

        assert content == "# Standardised YouTube"
        assert metadata["url"] == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert metadata["source_type"] == "youtube"
        assert metadata["status"] == "pending_ai"

        mock_determine_content_type.assert_called_once_with(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        )
        mock_get_processor.assert_called_once_with("youtube")
        mock_processor.process.assert_called_once_with(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
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
