"""Tests for the newsletter assembler module."""

import os
import datetime
from unittest.mock import patch, MagicMock, mock_open
import pytest

from newsletter_generator.newsletter.assembler import (
    NewsletterAssembler,
    get_newsletter_assembler,
    collect_weekly_content,
    organize_by_category,
    generate_introduction,
    generate_category_section,
    assemble_newsletter,
    generate_related_content_section,
)


@pytest.fixture
def newsletter_assembler():
    """Fixture for creating a newsletter assembler with mocked dependencies."""
    with patch("newsletter_generator.newsletter.assembler.storage_manager") as mock_storage, \
         patch("newsletter_generator.newsletter.assembler.processor") as mock_processor, \
         patch("newsletter_generator.newsletter.assembler.lightrag_manager") as mock_lightrag, \
         patch("newsletter_generator.newsletter.assembler.os.makedirs") as mock_makedirs:
        
        assembler = NewsletterAssembler(output_dir="/test/newsletters")
        
        mock_storage.list_content.return_value = {}
        mock_storage.get_content.return_value = "Test content"
        mock_storage.get_metadata.return_value = {"title": "Test Title", "url": "https://example.com"}
        
        mock_processor.categorize_content.return_value = {
            "primary_category": "Test Category",
            "secondary_categories": ["Other Category"],
            "tags": ["test", "example"]
        }
        mock_processor.summarize_content.return_value = "This is a test summary."
        mock_processor.generate_newsletter_section.return_value = "# Test Section\n\nThis is a test section."
        
        mock_lightrag.search.return_value = []
        
        yield assembler


class TestNewsletterAssembler:
    """Test cases for the NewsletterAssembler class."""
    
    def test_init(self, newsletter_assembler):
        """Test initializing the newsletter assembler."""
        assert newsletter_assembler.output_dir == "/test/newsletters"
    
    @patch("newsletter_generator.newsletter.assembler.datetime")
    def test_collect_weekly_content_empty(self, mock_datetime, newsletter_assembler):
        """Test collecting weekly content when no content is available."""
        mock_now = MagicMock()
        mock_now.strftime.return_value = "2025-05-01"
        mock_datetime.datetime.now.return_value = mock_now
        mock_datetime.datetime.fromisoformat.return_value = mock_now
        mock_datetime.timedelta.return_value = datetime.timedelta(days=7)
        
        result = newsletter_assembler.collect_weekly_content()
        
        assert result == []
    
    @patch("newsletter_generator.newsletter.assembler.datetime")
    def test_collect_weekly_content(self, mock_datetime, newsletter_assembler):
        """Test collecting weekly content."""
        now = datetime.datetime(2025, 5, 1, 12, 0, 0)
        cutoff_date = now - datetime.timedelta(days=7)
        
        mock_datetime.datetime.now.return_value = now
        mock_datetime.timedelta.return_value = datetime.timedelta(days=7)
        
        def mock_fromisoformat(date_str):
            if date_str == "2025-04-30T12:00:00":
                return datetime.datetime(2025, 4, 30, 12, 0, 0)
            elif date_str == "2025-04-29T12:00:00":
                return datetime.datetime(2025, 4, 29, 12, 0, 0)
            else:
                return datetime.datetime(2025, 4, 20, 12, 0, 0)  # Old content
        
        mock_datetime.datetime.fromisoformat.side_effect = mock_fromisoformat
        
        with patch("newsletter_generator.newsletter.assembler.storage_manager") as mock_storage:
            mock_storage.list_content.return_value = {
                "content1": {"date_added": "2025-04-30T12:00:00", "title": "Test 1"},
                "content2": {"date_added": "2025-04-29T12:00:00", "title": "Test 2"},
                "content3": {"date_added": "2025-04-20T12:00:00", "title": "Old Content"},
            }
            mock_storage.get_content.return_value = "Test content"
            
            result = newsletter_assembler.collect_weekly_content()
            
            assert len(result) == 2
            assert result[0]["id"] == "content1"
            assert result[1]["id"] == "content2"
            assert "content3" not in [item["id"] for item in result]
    
    def test_organize_by_category_with_existing_categories(self, newsletter_assembler):
        """Test organizing content by category when categories already exist."""
        content_items = [
            {
                "id": "content1",
                "text": "Test content 1",
                "metadata": {"category": "Category A", "title": "Test 1"}
            },
            {
                "id": "content2",
                "text": "Test content 2",
                "metadata": {"category": "Category B", "title": "Test 2"}
            },
            {
                "id": "content3",
                "text": "Test content 3",
                "metadata": {"category": "Category A", "title": "Test 3"}
            },
        ]
        
        result = newsletter_assembler.organize_by_category(content_items)
        
        assert len(result) == 2
        assert "Category A" in result
        assert "Category B" in result
        assert len(result["Category A"]) == 2
        assert len(result["Category B"]) == 1
    
    def test_organize_by_category_with_missing_categories(self, newsletter_assembler):
        """Test organizing content by category when categories need to be determined."""
        content_items = [
            {
                "id": "content1",
                "text": "Test content 1",
                "metadata": {"title": "Test 1"}
            },
            {
                "id": "content2",
                "text": "Test content 2",
                "metadata": {"category": "Category B", "title": "Test 2"}
            },
        ]
        
        with patch("newsletter_generator.newsletter.assembler.processor") as mock_processor, \
             patch("newsletter_generator.newsletter.assembler.storage_manager") as mock_storage:
            
            mock_processor.categorize_content.return_value = {
                "primary_category": "Category A",
                "secondary_categories": ["Other Category"],
                "tags": ["test", "example"]
            }
            
            result = newsletter_assembler.organize_by_category(content_items)
            
            assert len(result) == 2
            assert "Category A" in result
            assert "Category B" in result
            
            mock_storage.update_metadata.assert_called_once_with(
                "content1",
                {
                    "title": "Test 1",
                    "category": "Category A",
                    "secondary_categories": ["Other Category"],
                    "tags": ["test", "example"]
                }
            )
    
    @patch("newsletter_generator.newsletter.assembler.datetime")
    def test_generate_introduction(self, mock_datetime, newsletter_assembler):
        """Test generating the newsletter introduction."""
        mock_now = MagicMock()
        mock_now.strftime.return_value = "May 01, 2025"
        mock_datetime.datetime.now.return_value = mock_now
        
        categorized_content = {
            "Category A": [{"id": "content1"}, {"id": "content2"}],
            "Category B": [{"id": "content3"}],
        }
        
        with patch("newsletter_generator.newsletter.assembler.processor") as mock_processor:
            mock_processor.summarize_content.return_value = "This is a test introduction."
            
            result = newsletter_assembler.generate_introduction(categorized_content)
            
            assert "*May 01, 2025*" in result
            assert "This is a test introduction." in result
            assert "- [Category A](#categorya) (2 items)" in result
            assert "- [Category B](#categoryb) (1 item)" in result
    
    def test_generate_category_section(self, newsletter_assembler):
        """Test generating a category section."""
        items = [
            {
                "id": "content1",
                "text": "Test content 1",
                "metadata": {
                    "title": "Test 1",
                    "url": "https://example.com/1",
                    "relevance": "0.8",
                    "date_added": "2025-04-30T12:00:00",
                    "summary": "Existing summary 1"
                }
            },
            {
                "id": "content2",
                "text": "Test content 2",
                "metadata": {
                    "title": "Test 2",
                    "url": "https://example.com/2",
                    "relevance": "0.9",
                    "date_added": "2025-04-29T12:00:00"
                }
            },
        ]
        
        with patch("newsletter_generator.newsletter.assembler.processor") as mock_processor, \
             patch("newsletter_generator.newsletter.assembler.storage_manager") as mock_storage:
            
            mock_processor.summarize_content.return_value = "This is a generated summary."
            mock_processor.generate_newsletter_section.return_value = "# Test Section\n\nThis is a test section."
            
            result = newsletter_assembler.generate_category_section("Test Category", items)
            
            assert "## Test Category" in result
            assert "# Test Section" in result
            assert "This is a test section." in result
            assert "[Read more](https://example.com/1)" in result
            assert "[Read more](https://example.com/2)" in result
            
            mock_processor.summarize_content.assert_called_once_with("Test content 2", max_length=100)
            mock_storage.update_metadata.assert_called_once_with(
                "content2",
                {
                    "title": "Test 2",
                    "url": "https://example.com/2",
                    "relevance": "0.9",
                    "date_added": "2025-04-29T12:00:00",
                    "summary": "This is a generated summary."
                }
            )
    
    @patch("newsletter_generator.newsletter.assembler.datetime")
    @patch("builtins.open", new_callable=mock_open)
    def test_assemble_newsletter(self, mock_file, mock_datetime, newsletter_assembler):
        """Test assembling the complete newsletter."""
        mock_now = MagicMock()
        mock_now.strftime.side_effect = lambda fmt: "2025-05-01" if fmt == "%Y-%m-%d" else "May 01, 2025"
        mock_datetime.datetime.now.return_value = mock_now
        
        with patch.object(newsletter_assembler, "collect_weekly_content") as mock_collect, \
             patch.object(newsletter_assembler, "organize_by_category") as mock_organize, \
             patch.object(newsletter_assembler, "generate_introduction") as mock_intro, \
             patch.object(newsletter_assembler, "generate_category_section") as mock_section:
            
            mock_collect.return_value = [{"id": "content1"}, {"id": "content2"}]
            mock_organize.return_value = {
                "Category A": [{"id": "content1"}],
                "Category B": [{"id": "content2"}],
            }
            mock_intro.return_value = "# Test Introduction"
            mock_section.side_effect = lambda cat, items: f"## {cat}\n\nTest section for {cat}"
            
            result = newsletter_assembler.assemble_newsletter()
            
            assert result == "/test/newsletters/newsletter_2025-05-01.md"
            
            mock_file.assert_called_once_with("/test/newsletters/newsletter_2025-05-01.md", "w")
            mock_file().write.assert_called_once()
            written_content = mock_file().write.call_args[0][0]
            
            assert "# Test Introduction" in written_content
            assert "## Category A" in written_content
            assert "## Category B" in written_content
            assert "Test section for Category A" in written_content
            assert "Test section for Category B" in written_content
            assert "*This newsletter was automatically generated on May 01, 2025.*" in written_content
    
    def test_assemble_newsletter_no_content(self, newsletter_assembler):
        """Test assembling the newsletter when no content is available."""
        with patch.object(newsletter_assembler, "collect_weekly_content") as mock_collect:
            mock_collect.return_value = []
            
            result = newsletter_assembler.assemble_newsletter()
            
            assert result is None
    
    def test_generate_related_content_section(self, newsletter_assembler):
        """Test generating a related content section."""
        with patch("newsletter_generator.newsletter.assembler.storage_manager") as mock_storage, \
             patch("newsletter_generator.newsletter.assembler.lightrag_manager") as mock_lightrag:
            
            mock_storage.get_content.return_value = "Test content"
            mock_storage.get_metadata.side_effect = lambda content_id: {
                "content1": {"title": "Main Content", "url": "https://example.com/1"},
                "content2": {"title": "Related 1", "url": "https://example.com/2"},
                "content3": {"title": "Related 2", "url": "https://example.com/3"},
            }[content_id]
            
            mock_lightrag.search.return_value = [
                {"id": "content2", "score": 0.9},
                {"id": "content3", "score": 0.8},
            ]
            
            result = newsletter_assembler.generate_related_content_section("content1", max_items=2)
            
            assert "### Related Content" in result
            assert "- [Related 1](https://example.com/2)" in result
            assert "- [Related 2](https://example.com/3)" in result
            
            mock_lightrag.search.assert_called_once_with(
                query="Test content",
                limit=3,
                filter_metadata={"content_id": {"$ne": "content1"}}
            )
    
    def test_generate_related_content_section_no_results(self, newsletter_assembler):
        """Test generating a related content section when no related content is found."""
        with patch("newsletter_generator.newsletter.assembler.storage_manager") as mock_storage, \
             patch("newsletter_generator.newsletter.assembler.lightrag_manager") as mock_lightrag:
            
            mock_storage.get_content.return_value = "Test content"
            mock_storage.get_metadata.return_value = {"title": "Main Content", "url": "https://example.com/1"}
            
            mock_lightrag.search.return_value = []
            
            result = newsletter_assembler.generate_related_content_section("content1")
            
            assert result == ""


class TestConvenienceFunctions:
    """Test cases for the convenience functions."""
    
    def test_get_newsletter_assembler(self):
        """Test getting the singleton newsletter assembler instance."""
        with patch("newsletter_generator.newsletter.assembler.NewsletterAssembler") as mock_assembler_class:
            import newsletter_generator.newsletter.assembler
            newsletter_generator.newsletter.assembler.newsletter_assembler = None
            
            assembler1 = get_newsletter_assembler()
            mock_assembler_class.assert_called_once()
            
            mock_assembler_class.reset_mock()
            assembler2 = get_newsletter_assembler()
            mock_assembler_class.assert_not_called()
            
            assert assembler1 == assembler2
    
    def test_collect_weekly_content_function(self):
        """Test the collect_weekly_content convenience function."""
        with patch("newsletter_generator.newsletter.assembler.get_newsletter_assembler") as mock_get_assembler:
            mock_assembler = MagicMock()
            mock_get_assembler.return_value = mock_assembler
            
            collect_weekly_content(days=14)
            
            mock_assembler.collect_weekly_content.assert_called_once_with(days=14)
    
    def test_organize_by_category_function(self):
        """Test the organize_by_category convenience function."""
        with patch("newsletter_generator.newsletter.assembler.get_newsletter_assembler") as mock_get_assembler:
            mock_assembler = MagicMock()
            mock_get_assembler.return_value = mock_assembler
            
            content_items = [{"id": "content1"}]
            organize_by_category(content_items)
            
            mock_assembler.organize_by_category.assert_called_once_with(content_items)
    
    def test_generate_introduction_function(self):
        """Test the generate_introduction convenience function."""
        with patch("newsletter_generator.newsletter.assembler.get_newsletter_assembler") as mock_get_assembler:
            mock_assembler = MagicMock()
            mock_get_assembler.return_value = mock_assembler
            
            categorized_content = {"Category A": [{"id": "content1"}]}
            generate_introduction(categorized_content)
            
            mock_assembler.generate_introduction.assert_called_once_with(categorized_content)
    
    def test_generate_category_section_function(self):
        """Test the generate_category_section convenience function."""
        with patch("newsletter_generator.newsletter.assembler.get_newsletter_assembler") as mock_get_assembler:
            mock_assembler = MagicMock()
            mock_get_assembler.return_value = mock_assembler
            
            items = [{"id": "content1"}]
            generate_category_section("Test Category", items)
            
            mock_assembler.generate_category_section.assert_called_once_with("Test Category", items)
    
    def test_assemble_newsletter_function(self):
        """Test the assemble_newsletter convenience function."""
        with patch("newsletter_generator.newsletter.assembler.get_newsletter_assembler") as mock_get_assembler:
            mock_assembler = MagicMock()
            mock_get_assembler.return_value = mock_assembler
            
            assemble_newsletter(days=14)
            
            mock_assembler.assemble_newsletter.assert_called_once_with(days=14)
    
    def test_generate_related_content_section_function(self):
        """Test the generate_related_content_section convenience function."""
        with patch("newsletter_generator.newsletter.assembler.get_newsletter_assembler") as mock_get_assembler:
            mock_assembler = MagicMock()
            mock_get_assembler.return_value = mock_assembler
            
            generate_related_content_section("content1", max_items=5)
            
            mock_assembler.generate_related_content_section.assert_called_once_with(content_id="content1", max_items=5)


@pytest.mark.skip(reason="Integration tests requiring real dependencies")
class TestNewsletterAssemblerIntegration:
    """Integration tests for the NewsletterAssembler class.
    
    These tests require real dependencies and are skipped by default.
    """
    
    @pytest.fixture
    def real_assembler(self):
        """Fixture for creating a real newsletter assembler."""
        import tempfile
        test_dir = tempfile.mkdtemp()
        
        assembler = NewsletterAssembler(output_dir=test_dir)
        yield assembler
        
        import shutil
        shutil.rmtree(test_dir)
    
    def test_real_newsletter_assembly(self, real_assembler):
        """Test assembling a real newsletter with actual dependencies."""
        pass


if __name__ == "__main__":
    pytest.main()
