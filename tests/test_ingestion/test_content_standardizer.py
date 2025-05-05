"""Tests for the content standardiser module."""

import pytest
from unittest.mock import patch

from newsletter_generator.ingestion.content_standardiser import ContentStandardiser


class TestContentStandardiser:
    """Test cases for the ContentStandardiser class."""

    def test_standardise_with_valid_content(self):
        """Test standardising valid content."""
        standardiser = ContentStandardiser()

        content = "# Test Content\n\nThis is a test paragraph.\n\nThis is another paragraph."
        expected = content + "\n"  # Account for added newline

        result = standardiser.standardise(content)

        assert result == expected

    def test_standardise_with_empty_content(self):
        """Test standardising empty content."""
        standardiser = ContentStandardiser()

        content = ""

        result = standardiser.standardise(content)

        assert "# Empty Content" in result
        assert "*No content was provided*" in result

    def test_standardise_with_excessive_newlines(self):
        """Test standardising content with excessive newlines."""
        standardiser = ContentStandardiser()

        content = "# Test Content\n\n\n\n\nThis has too many newlines."
        expected = "# Test Content\n\nThis has too many newlines.\n"

        result = standardiser.standardise(content)

        assert result == expected

    def test_standardise_with_missing_newlines_before_headers(self):
        """Test standardising content with missing newlines before headers."""
        standardiser = ContentStandardiser()

        content = "# Main Header\nThis is text.## Subheader\nMore text."
        expected = "# Main Header\n\nThis is text.\n\n## Subheader\n\nMore text.\n"

        result = standardiser.standardise(content)

        assert result == expected

    def test_standardise_with_missing_newlines_before_lists(self):
        """Test standardising content with missing newlines before lists."""
        standardiser = ContentStandardiser()

        content = "# List Test\nThis is text.\n- Item 1\n- Item 2"
        expected = "# List Test\n\nThis is text.\n\n- Item 1\n\n- Item 2\n"

        result = standardiser.standardise(content)

        assert result == expected

    def test_standardise_with_missing_newlines_before_code_blocks(self):
        """Test standardising content with missing newlines before code blocks."""
        standardiser = ContentStandardiser()

        content = "# Code Test\nThis is text.```python\nprint('hello')\n```"

        result = standardiser.standardise(content)

        assert "# Code Test" in result
        assert "This is text." in result
        assert "```python" in result
        assert "print('hello')" in result

    def test_standardise_with_missing_newlines_before_blockquotes(self):
        """Test standardising content with missing newlines before blockquotes."""
        standardiser = ContentStandardiser()

        content = "# Quote Test\nThis is text.\n> This is a quote"
        expected = "# Quote Test\n\nThis is text.\n\n> This is a quote\n"

        result = standardiser.standardise(content)

        assert result == expected

    def test_standardise_with_no_header(self):
        """Test standardising content with no header."""
        standardiser = ContentStandardiser()

        content = "This content has no header."
        expected = "# Extracted Content\n\nThis content has no header.\n"

        result = standardiser.standardise(content)

        assert result == expected

    def test_standardise_with_exception(self):
        """Test standardising content with an exception."""
        standardiser = ContentStandardiser()

        with patch("newsletter_generator.ingestion.content_standardiser.re.sub") as mock_sub:
            mock_sub.side_effect = Exception("Test exception")

            content = "# Test Content\n\nThis should raise an exception."

            result = standardiser.standardise(content)

            assert result == content


if __name__ == "__main__":
    pytest.main()
