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
            output_format="markdown",
            include_links=False,
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
    @patch("newsletter_generator.ingestion.content_parser.pymupdf4llm.to_markdown")
    def test_parse_with_text(self, mock_to_markdown, mock_fitz_open):
        """Test parsing PDF content with text."""
        mock_doc = MagicMock()
        mock_fitz_open.return_value = mock_doc

        # Mock the pymupdf4llm.to_markdown function to return markdown
        mock_to_markdown.return_value = (
            "# Test Content\n\nThis is page 1 text\n\nThis is page 2 text"
        )

        parser = PDFContentParser()
        result = parser.parse(b"PDF content")

        assert "# PDF Document" in result
        assert "# Test Content" in result
        assert "This is page 1 text" in result
        assert "This is page 2 text" in result

        mock_fitz_open.assert_called_once_with(stream=b"PDF content", filetype="pdf")

    @patch("newsletter_generator.ingestion.content_parser.fitz.open")
    @patch("newsletter_generator.ingestion.content_parser.pymupdf4llm.to_markdown")
    def test_parse_with_no_text(self, mock_to_markdown, mock_fitz_open):
        """Test parsing PDF content with no text."""
        mock_doc = MagicMock()
        mock_fitz_open.return_value = mock_doc

        # Mock empty response
        mock_to_markdown.return_value = ""

        parser = PDFContentParser()
        result = parser.parse(b"PDF content")

        assert "# PDF Document" in result
        assert result.strip() == "# PDF Document"

        mock_fitz_open.assert_called_once_with(stream=b"PDF content", filetype="pdf")

    @patch("newsletter_generator.ingestion.content_parser.fitz.open")
    def test_parse_with_exception(self, mock_fitz_open):
        """Test parsing PDF content with exception."""
        mock_fitz_open.side_effect = Exception("Test exception")

        parser = PDFContentParser()

        with pytest.raises(Exception, match="Test exception"):
            parser.parse(b"PDF content")

        mock_fitz_open.assert_called_once_with(stream=b"PDF content", filetype="pdf")

    def test_remove_references_section_markdown_heading(self):
        """Test removing references section with Markdown heading format."""
        parser = PDFContentParser()
        text = "# Introduction\n\nSome content.\n\n# Results\n\nMore content.\n\n# References\n\nReference 1\nReference 2\n\n# Appendix\n\nAppendix content."

        # Print the exact string for debugging
        print(f"Original text: {repr(text)}")

        result = parser._remove_references_section(text)

        # Print the result for debugging
        print(f"Result text: {repr(result)}")

        assert "# Introduction" in result
        assert "# Results" in result
        assert "# References" not in result
        assert "Reference 1" not in result
        assert "# Appendix" not in result
        assert "Appendix content" not in result

    def test_remove_references_section_plain_text(self):
        """Test removing references section with plain text format."""
        parser = PDFContentParser()
        text = "Introduction\n\nSome content.\n\nResults\n\nMore content.\n\nReferences\n\nReference 1\nReference 2\n\nAppendix\n\nAppendix content."

        result = parser._remove_references_section(text)

        assert "Introduction" in result
        assert "Results" in result
        assert "References" not in result
        assert "Reference 1" not in result
        assert "Appendix" not in result

    def test_remove_references_section_bold_format(self):
        """Test removing references section with bold format."""
        parser = PDFContentParser()
        text = "# Introduction\n\nSome content.\n\n# Results\n\nMore content.\n\n**References**\n\nReference 1\nReference 2\n\n# Appendix\n\nAppendix content."

        result = parser._remove_references_section(text)

        assert "# Introduction" in result
        assert "# Results" in result
        assert "**References**" not in result
        assert "Reference 1" not in result
        assert "# Appendix" not in result

    def test_remove_references_section_numbered(self):
        """Test removing references section with numbered format."""
        parser = PDFContentParser()
        text = "1. Introduction\n\nSome content.\n\n2. Results\n\nMore content.\n\n3. References\n\nReference 1\nReference 2\n\n4. Appendix\n\nAppendix content."

        result = parser._remove_references_section(text)

        assert "1. Introduction" in result
        assert "2. Results" in result
        assert "3. References" not in result
        assert "Reference 1" not in result
        assert "4. Appendix" not in result

    def test_remove_references_section_with_singular_form(self):
        """Test removing reference section (singular form)."""
        parser = PDFContentParser()
        text = "# Introduction\n\nSome content.\n\n# Results\n\nMore content.\n\n# Reference\n\nReference 1\n\n# Appendix\n\nAppendix content."

        result = parser._remove_references_section(text)

        assert "# Introduction" in result
        assert "# Results" in result
        assert "# Reference" not in result
        assert "Reference 1" not in result
        assert "# Appendix" not in result

    def test_references_as_part_of_word(self):
        """Test that words containing 'reference' as part of them aren't matched."""
        parser = PDFContentParser()
        text = "# Introduction\n\nSome content with dereference.\n\n# Results\n\nThe prereference data shows...\n\n# Conclusion\n\nFinal thoughts."

        result = parser._remove_references_section(text)

        # Should remain unchanged
        assert result == text

    def test_no_references_section(self):
        """Test with no references section."""
        parser = PDFContentParser()
        text = "# Introduction\n\nSome content.\n\n# Results\n\nMore content.\n\n# Conclusion\n\nFinal thoughts."

        result = parser._remove_references_section(text)

        # Should remain unchanged
        assert result == text

    @patch("newsletter_generator.ingestion.content_parser.fitz.open")
    @patch("newsletter_generator.ingestion.content_parser.pymupdf4llm.to_markdown")
    def test_parse_with_references_removal(self, mock_to_markdown, mock_fitz_open):
        """Test that parse method calls the references section removal."""
        mock_doc = MagicMock()
        mock_fitz_open.return_value = mock_doc

        # Simulate PDF content with references section
        mock_to_markdown.return_value = (
            "# Content\n\nSome text\n\n# References\n\nReference 1\nReference 2"
        )

        parser = PDFContentParser()
        result = parser.parse(b"PDF content")

        assert "# PDF Document" in result
        assert "# Content" in result
        assert "Some text" in result
        assert "# References" not in result
        assert "Reference 1" not in result

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
