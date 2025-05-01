"""Tests for the content parser module."""

import pytest
from unittest.mock import patch, MagicMock

from newsletter_generator.ingestion.content_parser import (
    HTMLContentParser,
    PDFContentParser,
    YouTubeContentParser,
)


class TestHTMLContentParser:
    """Test cases for the HTMLContentParser class."""
    
    def test_parse_with_markdown(self):
        """Test parsing HTML content with Markdown already available."""
        parser = HTMLContentParser()
        
        content = {
            "markdown": "# Test Markdown\n\nThis is a test.",
            "html": "<h1>Test HTML</h1><p>This is a test.</p>",
            "title": "Test Title",
        }
        
        result = parser.parse(content, "https://example.com")
        
        assert "# Test Title" in result
    
    @patch("newsletter_generator.ingestion.content_parser.trafilatura.extract")
    def test_parse_with_trafilatura_fallback(self, mock_extract):
        """Test parsing HTML content with Trafilatura fallback."""
        mock_extract.return_value = "# Extracted with Trafilatura\n\nThis is a test."
        
        parser = HTMLContentParser()
        
        content = {
            "markdown": "",  # Empty markdown
            "html": "<h1>Test HTML</h1><p>This is a test.</p>",
            "title": "Test Title",
        }
        
        result = parser.parse(content, "https://example.com")
        
        assert result == "# Extracted with Trafilatura\n\nThis is a test."
        mock_extract.assert_called_once_with(
            "<h1>Test HTML</h1><p>This is a test.</p>",
            output_format='markdown',
            include_links=True,
            include_images=True,
            include_tables=True,
        )
    
    @patch("newsletter_generator.ingestion.content_parser.trafilatura.extract")
    def test_parse_with_trafilatura_failure(self, mock_extract):
        """Test parsing HTML content with Trafilatura failure."""
        mock_extract.return_value = None
        
        parser = HTMLContentParser()
        
        content = {
            "markdown": "",  # Empty markdown
            "html": "<h1>Test HTML</h1><p>This is a test.</p>",
            "title": "Test Title",
        }
        
        result = parser.parse(content, "https://example.com")
        
        assert "# Test Title" in result
        assert "*Content extraction failed*" in result
        mock_extract.assert_called_once()
    
    def test_parse_with_no_html(self):
        """Test parsing HTML content with no HTML available."""
        parser = HTMLContentParser()
        
        content = {
            "markdown": "",  # Empty markdown
            "html": "",  # Empty HTML
            "title": "Test Title",
        }
        
        with pytest.raises(Exception, match="No HTML content available"):
            parser.parse(content, "https://example.com")


class TestPDFContentParser:
    """Test cases for the PDFContentParser class."""
    
    @patch("newsletter_generator.ingestion.content_parser.fitz.open")
    def test_parse_with_text(self, mock_fitz_open):
        """Test parsing PDF content with text."""
        mock_doc = MagicMock()
        mock_page1 = MagicMock()
        mock_page2 = MagicMock()
        
        mock_page1.get_text.return_value = "Page 1 text"
        mock_page2.get_text.return_value = "Page 2 text"
        
        mock_doc.__iter__.return_value = [mock_page1, mock_page2]
        mock_fitz_open.return_value = mock_doc
        
        parser = PDFContentParser()
        result = parser.parse(b"PDF content")
        
        assert "# PDF Document" in result
        assert "Page 1 text" in result
        assert "Page 2 text" in result
        
        mock_fitz_open.assert_called_once_with(stream=b"PDF content", filetype="pdf")
        mock_doc.close.assert_called_once()
    
    @patch("newsletter_generator.ingestion.content_parser.fitz.open")
    def test_parse_with_no_text(self, mock_fitz_open):
        """Test parsing PDF content with no text."""
        mock_doc = MagicMock()
        mock_page = MagicMock()
        
        mock_page.get_text.return_value = ""  # Empty text
        
        mock_doc.__iter__.return_value = [mock_page]
        mock_fitz_open.return_value = mock_doc
        
        parser = PDFContentParser()
        result = parser.parse(b"PDF content")
        
        assert "# PDF Document" in result
        assert "*No text content could be extracted*" in result
        
        mock_fitz_open.assert_called_once_with(stream=b"PDF content", filetype="pdf")
        mock_doc.close.assert_called_once()
    
    @patch("newsletter_generator.ingestion.content_parser.fitz.open")
    def test_parse_with_exception(self, mock_fitz_open):
        """Test parsing PDF content with exception."""
        mock_fitz_open.side_effect = Exception("Test exception")
        
        parser = PDFContentParser()
        
        with pytest.raises(Exception, match="Test exception"):
            parser.parse(b"PDF content")
        
        mock_fitz_open.assert_called_once_with(stream=b"PDF content", filetype="pdf")


class TestYouTubeContentParser:
    """Test cases for the YouTubeContentParser class."""
    
    def test_parse_with_transcript(self):
        """Test parsing YouTube transcript data."""
        parser = YouTubeContentParser()
        
        transcript_data = [
            {"text": "This is the first part.", "start": 0},
            {"text": "This is the second part.", "start": 5},
            {"text": "This is the third part.", "start": 10},
        ]
        
        result = parser.parse(transcript_data)
        
        assert "# YouTube Video Transcript" in result
        assert "This is the first part. This is the second part. This is the third part." in result
    
    def test_parse_with_empty_transcript(self):
        """Test parsing empty YouTube transcript data."""
        parser = YouTubeContentParser()
        
        transcript_data = []
        
        result = parser.parse(transcript_data)
        
        assert "# YouTube Video Transcript" in result
        assert "*No transcript available*" in result
    
    def test_parse_with_empty_text(self):
        """Test parsing YouTube transcript data with empty text."""
        parser = YouTubeContentParser()
        
        transcript_data = [
            {"text": "", "start": 0},
            {"text": "  ", "start": 5},  # Whitespace only
        ]
        
        result = parser.parse(transcript_data)
        
        assert "# YouTube Video Transcript" in result
        assert "*No transcript content could be extracted*" in result
    
    def test_parse_with_invalid_data(self):
        """Test parsing YouTube transcript data with invalid structure."""
        parser = YouTubeContentParser()
        
        transcript_data = [{"invalid_key": "value"}]  # Missing 'text' key
        
        result = parser.parse(transcript_data)
        
        assert "# YouTube Video Transcript" in result
        assert "*No transcript content could be extracted*" in result


if __name__ == "__main__":
    pytest.main()
