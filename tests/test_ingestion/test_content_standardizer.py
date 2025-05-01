"""Tests for the content standardizer module."""

import pytest
from unittest.mock import patch, MagicMock

from newsletter_generator.ingestion.content_standardizer import ContentStandardizer


class TestContentStandardizer:
    """Test cases for the ContentStandardizer class."""
    
    def test_standardize_with_valid_content(self):
        """Test standardizing valid content."""
        standardizer = ContentStandardizer()
        
        content = "# Test Content\n\nThis is a test paragraph.\n\nThis is another paragraph."
        expected = content + "\n"  # Account for added newline
        
        result = standardizer.standardize(content)
        
        assert result == expected
    
    def test_standardize_with_empty_content(self):
        """Test standardizing empty content."""
        standardizer = ContentStandardizer()
        
        content = ""
        
        result = standardizer.standardize(content)
        
        assert "# Empty Content" in result
        assert "*No content was provided*" in result
    
    def test_standardize_with_excessive_newlines(self):
        """Test standardizing content with excessive newlines."""
        standardizer = ContentStandardizer()
        
        content = "# Test Content\n\n\n\n\nThis has too many newlines."
        expected = "# Test Content\n\nThis has too many newlines.\n"
        
        result = standardizer.standardize(content)
        
        assert result == expected
    
    def test_standardize_with_missing_newlines_before_headers(self):
        """Test standardizing content with missing newlines before headers."""
        standardizer = ContentStandardizer()
        
        content = "# Main Header\nThis is text.## Subheader\nMore text."
        expected = "# Main Header\n\nThis is text.\n\n## Subheader\n\nMore text.\n"
        
        result = standardizer.standardize(content)
        
        assert result == expected
    
    def test_standardize_with_missing_newlines_before_lists(self):
        """Test standardizing content with missing newlines before lists."""
        standardizer = ContentStandardizer()
        
        content = "# List Test\nThis is text.\n- Item 1\n- Item 2"
        expected = "# List Test\n\nThis is text.\n\n- Item 1\n\n- Item 2\n"
        
        result = standardizer.standardize(content)
        
        assert result == expected
    
    def test_standardize_with_missing_newlines_before_code_blocks(self):
        """Test standardizing content with missing newlines before code blocks."""
        standardizer = ContentStandardizer()
        
        content = "# Code Test\nThis is text.```python\nprint('hello')\n```"
        
        result = standardizer.standardize(content)
        
        assert "# Code Test" in result
        assert "This is text." in result
        assert "```python" in result
        assert "print('hello')" in result
    
    def test_standardize_with_missing_newlines_before_blockquotes(self):
        """Test standardizing content with missing newlines before blockquotes."""
        standardizer = ContentStandardizer()
        
        content = "# Quote Test\nThis is text.\n> This is a quote"
        expected = "# Quote Test\n\nThis is text.\n\n> This is a quote\n"
        
        result = standardizer.standardize(content)
        
        assert result == expected
    
    def test_standardize_with_no_header(self):
        """Test standardizing content with no header."""
        standardizer = ContentStandardizer()
        
        content = "This content has no header."
        expected = "# Extracted Content\n\nThis content has no header.\n"
        
        result = standardizer.standardize(content)
        
        assert result == expected
    
    def test_standardize_with_exception(self):
        """Test standardizing content with an exception."""
        standardizer = ContentStandardizer()
        
        with patch("newsletter_generator.ingestion.content_standardizer.re.sub") as mock_sub:
            mock_sub.side_effect = Exception("Test exception")
            
            content = "# Test Content\n\nThis should raise an exception."
            
            result = standardizer.standardize(content)
            
            assert result == content


if __name__ == "__main__":
    pytest.main()
