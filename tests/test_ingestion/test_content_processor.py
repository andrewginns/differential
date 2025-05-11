"""Tests for the content processor interface and implementations."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from newsletter_generator.ingestion.content_processor import (
    ContentProcessorInterface,
    HTMLContentProcessor,
    PDFContentProcessor,
    YouTubeContentProcessor,
    ContentProcessorFactory,
)


class TestContentProcessorInterface:
    """Test cases for the ContentProcessorInterface."""

    @pytest.mark.asyncio
    async def test_process_method(self):
        """Test that the process method orchestrates fetch, parse, and standardise."""
        class TestProcessor(ContentProcessorInterface):
            async def fetch(self, url):
                return "raw_content"
                
            def parse(self, raw_content, url=""):
                return "parsed_content"
                
            def standardise(self, parsed_content):
                return "standardised_content"
                
            def get_content_type(self):
                return "test_type"
        
        processor = TestProcessor()
        
        processor.fetch = AsyncMock(return_value="raw_content")
        processor.parse = MagicMock(return_value="parsed_content")
        processor.standardise = MagicMock(return_value="standardised_content")
        
        content, metadata = await processor.process("https://example.com")
        
        assert content == "standardised_content"
        assert metadata["url"] == "https://example.com"
        assert metadata["source_type"] == "test_type"
        assert metadata["status"] == "pending_ai"
        
        processor.fetch.assert_called_once_with("https://example.com")
        processor.parse.assert_called_once_with("raw_content", "https://example.com")
        processor.standardise.assert_called_once_with("parsed_content")

    @pytest.mark.asyncio
    async def test_process_method_error_handling(self):
        """Test that the process method handles errors properly."""
        class TestProcessor(ContentProcessorInterface):
            async def fetch(self, url):
                raise ValueError("Test error")
                
            def parse(self, raw_content, url=""):
                return "parsed_content"
                
            def standardise(self, parsed_content):
                return "standardised_content"
                
            def get_content_type(self):
                return "test_type"
        
        processor = TestProcessor()
        
        with pytest.raises(ValueError, match="Test error"):
            await processor.process("https://example.com")


class TestHTMLContentProcessor:
    """Test cases for the HTMLContentProcessor."""

    @pytest.mark.asyncio
    async def test_fetch(self):
        """Test that fetch delegates to the HTMLContentFetcher."""
        with patch("newsletter_generator.ingestion.content_processor.HTMLContentFetcher") as MockFetcher:
            mock_fetcher_instance = MockFetcher.return_value
            mock_fetcher_instance.fetch = AsyncMock(return_value={"html": "<html></html>"})
            
            processor = HTMLContentProcessor()
            result = await processor.fetch("https://example.com")
            
            assert result == {"html": "<html></html>"}
            mock_fetcher_instance.fetch.assert_called_once_with("https://example.com")
    
    def test_parse(self):
        """Test that parse delegates to the HTMLContentParser."""
        with patch("newsletter_generator.ingestion.content_processor.HTMLContentParser") as MockParser:
            mock_parser_instance = MockParser.return_value
            mock_parser_instance.parse.return_value = "parsed html"
            
            processor = HTMLContentProcessor()
            result = processor.parse({"html": "<html></html>"}, "https://example.com")
            
            assert result == "parsed html"
            mock_parser_instance.parse.assert_called_once_with({"html": "<html></html>"}, "https://example.com")
    
    def test_standardise(self):
        """Test that standardise delegates to the ContentStandardiser."""
        with patch("newsletter_generator.ingestion.content_processor.ContentStandardiser") as MockStandardiser:
            mock_standardiser_instance = MockStandardiser.return_value
            mock_standardiser_instance.standardise.return_value = "standardised html"
            
            processor = HTMLContentProcessor()
            result = processor.standardise("parsed html")
            
            assert result == "standardised html"
            mock_standardiser_instance.standardise.assert_called_once_with("parsed html")
    
    def test_get_content_type(self):
        """Test that get_content_type returns 'html'."""
        processor = HTMLContentProcessor()
        assert processor.get_content_type() == "html"


class TestPDFContentProcessor:
    """Test cases for the PDFContentProcessor."""

    @pytest.mark.asyncio
    async def test_fetch(self):
        """Test that fetch delegates to the PDFContentFetcher."""
        with patch("newsletter_generator.ingestion.content_processor.PDFContentFetcher") as MockFetcher:
            mock_fetcher_instance = MockFetcher.return_value
            mock_fetcher_instance.fetch = AsyncMock(return_value=b"pdf bytes")
            
            processor = PDFContentProcessor()
            result = await processor.fetch("https://example.com/doc.pdf")
            
            assert result == b"pdf bytes"
            mock_fetcher_instance.fetch.assert_called_once_with("https://example.com/doc.pdf")
    
    def test_parse(self):
        """Test that parse delegates to the PDFContentParser."""
        with patch("newsletter_generator.ingestion.content_processor.PDFContentParser") as MockParser:
            mock_parser_instance = MockParser.return_value
            mock_parser_instance.parse.return_value = "parsed pdf"
            
            processor = PDFContentProcessor()
            result = processor.parse(b"pdf bytes")
            
            assert result == "parsed pdf"
            mock_parser_instance.parse.assert_called_once_with(b"pdf bytes")
    
    def test_standardise(self):
        """Test that standardise delegates to the ContentStandardiser."""
        with patch("newsletter_generator.ingestion.content_processor.ContentStandardiser") as MockStandardiser:
            mock_standardiser_instance = MockStandardiser.return_value
            mock_standardiser_instance.standardise.return_value = "standardised pdf"
            
            processor = PDFContentProcessor()
            result = processor.standardise("parsed pdf")
            
            assert result == "standardised pdf"
            mock_standardiser_instance.standardise.assert_called_once_with("parsed pdf")
    
    def test_get_content_type(self):
        """Test that get_content_type returns 'pdf'."""
        processor = PDFContentProcessor()
        assert processor.get_content_type() == "pdf"


class TestYouTubeContentProcessor:
    """Test cases for the YouTubeContentProcessor."""

    @pytest.mark.asyncio
    async def test_fetch(self):
        """Test that fetch delegates to the YouTubeContentFetcher."""
        with patch("newsletter_generator.ingestion.content_processor.YouTubeContentFetcher") as MockFetcher:
            mock_fetcher_instance = MockFetcher.return_value
            mock_fetcher_instance.fetch = AsyncMock(return_value=[{"text": "transcript"}])
            
            processor = YouTubeContentProcessor()
            result = await processor.fetch("https://youtube.com/watch?v=12345")
            
            assert result == [{"text": "transcript"}]
            mock_fetcher_instance.fetch.assert_called_once_with("https://youtube.com/watch?v=12345")
    
    def test_parse(self):
        """Test that parse delegates to the YouTubeContentParser."""
        with patch("newsletter_generator.ingestion.content_processor.YouTubeContentParser") as MockParser:
            mock_parser_instance = MockParser.return_value
            mock_parser_instance.parse.return_value = "parsed transcript"
            
            processor = YouTubeContentProcessor()
            result = processor.parse([{"text": "transcript"}])
            
            assert result == "parsed transcript"
            mock_parser_instance.parse.assert_called_once_with([{"text": "transcript"}])
    
    def test_standardise(self):
        """Test that standardise delegates to the ContentStandardiser."""
        with patch("newsletter_generator.ingestion.content_processor.ContentStandardiser") as MockStandardiser:
            mock_standardiser_instance = MockStandardiser.return_value
            mock_standardiser_instance.standardise.return_value = "standardised transcript"
            
            processor = YouTubeContentProcessor()
            result = processor.standardise("parsed transcript")
            
            assert result == "standardised transcript"
            mock_standardiser_instance.standardise.assert_called_once_with("parsed transcript")
    
    def test_get_content_type(self):
        """Test that get_content_type returns 'youtube'."""
        processor = YouTubeContentProcessor()
        assert processor.get_content_type() == "youtube"


class TestContentProcessorFactory:
    """Test cases for the ContentProcessorFactory."""

    def test_get_processor_html(self):
        """Test that get_processor returns an HTMLContentProcessor for 'html'."""
        processor = ContentProcessorFactory.get_processor("html")
        assert isinstance(processor, HTMLContentProcessor)
    
    def test_get_processor_pdf(self):
        """Test that get_processor returns a PDFContentProcessor for 'pdf'."""
        processor = ContentProcessorFactory.get_processor("pdf")
        assert isinstance(processor, PDFContentProcessor)
    
    def test_get_processor_youtube(self):
        """Test that get_processor returns a YouTubeContentProcessor for 'youtube'."""
        processor = ContentProcessorFactory.get_processor("youtube")
        assert isinstance(processor, YouTubeContentProcessor)
    
    def test_get_processor_invalid(self):
        """Test that get_processor raises ValueError for invalid content types."""
        with pytest.raises(ValueError, match="No processor available for content type: invalid"):
            ContentProcessorFactory.get_processor("invalid")
    
    def test_register_processor(self):
        """Test that register_processor adds a new processor type."""
        class CustomProcessor(ContentProcessorInterface):
            async def fetch(self, url):
                return "custom raw content"
                
            def parse(self, raw_content, url=""):
                return "custom parsed content"
                
            def standardise(self, parsed_content):
                return "custom standardised content"
                
            def get_content_type(self):
                return "custom"
        
        ContentProcessorFactory.register_processor("custom", CustomProcessor)
        processor = ContentProcessorFactory.get_processor("custom")
        
        assert isinstance(processor, CustomProcessor)
        
        ContentProcessorFactory._processors.pop("custom")
