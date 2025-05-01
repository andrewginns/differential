"""Tests for the storage manager module."""

import os
import pytest
import datetime
import yaml
from unittest.mock import patch, mock_open, MagicMock

from newsletter_generator.storage.storage_manager import (
    StorageManager,
    write_content,
    read_content,
    update_metadata,
    find_files_by_status,
    cleanup_old_files,
)


@pytest.fixture
def storage_manager():
    """Create a storage manager for testing."""
    test_data_dir = "test_data"
    manager = StorageManager(data_dir=test_data_dir)
    
    os.makedirs(test_data_dir, exist_ok=True)
    
    yield manager
    
    if os.path.exists(test_data_dir):
        for root, dirs, files in os.walk(test_data_dir, topdown=False):
            for file in files:
                os.remove(os.path.join(root, file))
            for dir in dirs:
                os.rmdir(os.path.join(root, dir))
        os.rmdir(test_data_dir)


class TestStorageManager:
    """Test cases for the StorageManager class."""
    
    def test_init_creates_data_dir(self):
        """Test that the constructor creates the data directory."""
        test_dir = "test_init_dir"
        
        if os.path.exists(test_dir):
            os.rmdir(test_dir)
        
        manager = StorageManager(data_dir=test_dir)
        
        assert os.path.exists(test_dir)
        assert os.path.isdir(test_dir)
        
        os.rmdir(test_dir)
    
    def test_generate_file_path(self, storage_manager):
        """Test generating a file path for a URL."""
        url = "https://example.com"
        source_type = "html"
        
        with patch("newsletter_generator.storage.storage_manager.datetime") as mock_datetime:
            mock_datetime.datetime.now.return_value = datetime.datetime(2025, 5, 1)
            mock_datetime.timedelta = datetime.timedelta
            
            file_path = storage_manager._generate_file_path(url, source_type)
            
            assert file_path.startswith(os.path.join("test_data", "2025-05-01"))
            assert file_path.endswith(".md")
            assert source_type in file_path
    
    def test_write_content(self, storage_manager):
        """Test writing content and metadata to a file."""
        content = "# Test Content\n\nThis is a test."
        metadata = {
            "url": "https://example.com",
            "source_type": "html",
            "title": "Test Title",
        }
        
        with patch("builtins.open", mock_open()) as mock_file, \
             patch("newsletter_generator.storage.storage_manager.datetime") as mock_datetime, \
             patch.object(storage_manager, "_generate_file_path") as mock_generate_path:
            
            mock_dt = MagicMock()
            mock_dt.isoformat.return_value = "2025-05-01T00:00:00"
            mock_datetime.datetime.now.return_value = mock_dt
            mock_datetime.timedelta = datetime.timedelta
            
            mock_generate_path.return_value = "test_data/2025-05-01/html_1234567890.md"
            
            file_path = storage_manager.write_content(content, metadata)
            
            assert file_path == "test_data/2025-05-01/html_1234567890.md"
            
            mock_file.assert_called_once_with(
                "test_data/2025-05-01/html_1234567890.md", "w", encoding="utf-8"
            )
            
            handle = mock_file()
            handle.write.assert_any_call("---\n")
            handle.write.assert_any_call("---\n\n")
            handle.write.assert_any_call(content)
    
    def test_write_content_missing_url(self, storage_manager):
        """Test writing content with missing URL."""
        content = "# Test Content\n\nThis is a test."
        metadata = {
            "source_type": "html",
            "title": "Test Title",
        }
        
        with pytest.raises(ValueError, match="Metadata must include 'url'"):
            storage_manager.write_content(content, metadata)
    
    def test_write_content_missing_source_type(self, storage_manager):
        """Test writing content with missing source type."""
        content = "# Test Content\n\nThis is a test."
        metadata = {
            "url": "https://example.com",
            "title": "Test Title",
        }
        
        with pytest.raises(ValueError, match="Metadata must include 'source_type'"):
            storage_manager.write_content(content, metadata)
    
    def test_read_content(self, storage_manager):
        """Test reading content and metadata from a file."""
        file_content = """---
url: https://example.com
source_type: html
title: Test Title
---


This is a test."""
        
        with patch("builtins.open", mock_open(read_data=file_content)):
            content, metadata = storage_manager.read_content("test_file.md")
            
            assert content == "This is a test."
            assert metadata["url"] == "https://example.com"
            assert metadata["source_type"] == "html"
            assert metadata["title"] == "Test Title"
    
    def test_read_content_no_front_matter(self, storage_manager):
        """Test reading content with no front matter."""
        file_content = "# Test Content\n\nThis is a test."
        
        with patch("builtins.open", mock_open(read_data=file_content)):
            content, metadata = storage_manager.read_content("test_file.md")
            
            assert content == file_content
            assert metadata == {}
    
    def test_update_metadata(self, storage_manager):
        """Test updating metadata in a file."""
        file_content = """---
url: https://example.com
source_type: html
title: Test Title
---


This is a test."""
        
        with patch("builtins.open", mock_open()) as mock_file, \
             patch.object(storage_manager, "read_content") as mock_read:
            
            mock_read.return_value = (
                "# Test Content\n\nThis is a test.",
                {
                    "url": "https://example.com",
                    "source_type": "html",
                    "title": "Test Title",
                }
            )
            
            storage_manager.update_metadata(
                "test_file.md", {"status": "processed", "processed_at": "2025-05-01T00:00:00"}
            )
            
            mock_file.assert_called_once_with("test_file.md", "w", encoding="utf-8")
            
            handle = mock_file()
            handle.write.assert_any_call("---\n")
            handle.write.assert_any_call("---\n\n")
            handle.write.assert_any_call("# Test Content\n\nThis is a test.")
            
            mock_read.assert_called_once_with("test_file.md")
    
    def test_find_files_by_status(self, storage_manager):
        """Test finding files with a specific status."""
        with patch("os.listdir") as mock_listdir, \
             patch("os.path.isdir") as mock_isdir, \
             patch.object(storage_manager, "read_content") as mock_read:
            
            mock_listdir.side_effect = lambda path: {
                "test_data": ["2025-05-01", "2025-04-30", "other"],
                os.path.join("test_data", "2025-05-01"): ["html_1.md", "pdf_2.md"],
                os.path.join("test_data", "2025-04-30"): ["html_3.md"],
            }[path]
            
            mock_isdir.side_effect = lambda path: path.endswith(("2025-05-01", "2025-04-30", "other"))
            
            mock_read.side_effect = lambda path: {
                os.path.join("test_data", "2025-05-01", "html_1.md"): (
                    "# Content 1", {"status": "processed"}
                ),
                os.path.join("test_data", "2025-05-01", "pdf_2.md"): (
                    "# Content 2", {"status": "pending_ai"}
                ),
                os.path.join("test_data", "2025-04-30", "html_3.md"): (
                    "# Content 3", {"status": "processed"}
                ),
            }[path]
            
            files = storage_manager.find_files_by_status("processed")
            
            assert len(files) == 2
            assert os.path.join("test_data", "2025-05-01", "html_1.md") in files
            assert os.path.join("test_data", "2025-04-30", "html_3.md") in files
            
            files = storage_manager.find_files_by_status("pending_ai")
            
            assert len(files) == 1
            assert os.path.join("test_data", "2025-05-01", "pdf_2.md") in files
    
    def test_find_files_by_status_with_days(self, storage_manager):
        """Test finding files with a specific status and day limit."""
        with patch("os.listdir") as mock_listdir, \
             patch("os.path.isdir") as mock_isdir, \
             patch.object(storage_manager, "read_content") as mock_read, \
             patch("newsletter_generator.storage.storage_manager.datetime") as mock_datetime:
            
            mock_datetime.datetime.now.return_value = datetime.datetime(2025, 5, 1)
            mock_datetime.timedelta = datetime.timedelta
            
            mock_listdir.side_effect = lambda path: {
                "test_data": ["2025-05-01", "2025-04-30", "2025-04-15", "other"],
                os.path.join("test_data", "2025-05-01"): ["html_1.md"],
                os.path.join("test_data", "2025-04-30"): ["html_2.md"],
                os.path.join("test_data", "2025-04-15"): ["html_3.md"],
            }[path]
            
            mock_isdir.side_effect = lambda path: path.endswith(
                ("2025-05-01", "2025-04-30", "2025-04-15", "other")
            )
            
            mock_read.side_effect = lambda path: {
                os.path.join("test_data", "2025-05-01", "html_1.md"): (
                    "# Content 1", {"status": "processed"}
                ),
                os.path.join("test_data", "2025-04-30", "html_2.md"): (
                    "# Content 2", {"status": "processed"}
                ),
                os.path.join("test_data", "2025-04-15", "html_3.md"): (
                    "# Content 3", {"status": "processed"}
                ),
            }[path]
            
            files = storage_manager.find_files_by_status("processed", days=7)
            
            assert len(files) == 2
            assert os.path.join("test_data", "2025-05-01", "html_1.md") in files
            assert os.path.join("test_data", "2025-04-30", "html_2.md") in files
            assert os.path.join("test_data", "2025-04-15", "html_3.md") not in files
    
    def test_cleanup_old_files(self, storage_manager):
        """Test cleaning up old files."""
        with patch("os.listdir") as mock_listdir, \
             patch("os.path.isdir") as mock_isdir, \
             patch("os.remove") as mock_remove, \
             patch("os.rmdir") as mock_rmdir, \
             patch("newsletter_generator.storage.storage_manager.datetime") as mock_datetime, \
             patch("newsletter_generator.storage.storage_manager.CONFIG") as mock_config:
            
            mock_datetime.datetime.now.return_value = datetime.datetime(2025, 5, 1)
            mock_datetime.timedelta = datetime.timedelta
            
            mock_config.get.return_value = 30  # Default TTL
            
            mock_listdir.side_effect = lambda path: {
                "test_data": ["2025-05-01", "2025-04-30", "2025-03-15", "other"],
                os.path.join("test_data", "2025-05-01"): ["html_1.md"],
                os.path.join("test_data", "2025-04-30"): ["html_2.md"],
                os.path.join("test_data", "2025-03-15"): ["html_3.md", "pdf_4.md"],
            }[path]
            
            mock_isdir.side_effect = lambda path: path.endswith(
                ("2025-05-01", "2025-04-30", "2025-03-15", "other")
            )
            
            deleted_count = storage_manager.cleanup_old_files()
            
            assert deleted_count == 2
            mock_remove.assert_any_call(os.path.join("test_data", "2025-03-15", "html_3.md"))
            mock_remove.assert_any_call(os.path.join("test_data", "2025-03-15", "pdf_4.md"))
            mock_rmdir.assert_called_once_with(os.path.join("test_data", "2025-03-15"))


class TestConvenienceFunctions:
    """Test cases for the convenience functions."""
    
    def test_write_content_function(self):
        """Test the write_content convenience function."""
        with patch("newsletter_generator.storage.storage_manager.storage_manager.write_content") as mock_write:
            mock_write.return_value = "test_file.md"
            
            content = "# Test Content"
            metadata = {"url": "https://example.com", "source_type": "html"}
            
            result = write_content(content, metadata)
            
            assert result == "test_file.md"
            mock_write.assert_called_once_with(content, metadata)
    
    def test_read_content_function(self):
        """Test the read_content convenience function."""
        with patch("newsletter_generator.storage.storage_manager.storage_manager.read_content") as mock_read:
            mock_read.return_value = ("# Test Content", {"url": "https://example.com"})
            
            content, metadata = read_content("test_file.md")
            
            assert content == "# Test Content"
            assert metadata["url"] == "https://example.com"
            mock_read.assert_called_once_with("test_file.md")
    
    def test_update_metadata_function(self):
        """Test the update_metadata convenience function."""
        with patch("newsletter_generator.storage.storage_manager.storage_manager.update_metadata") as mock_update:
            update_metadata("test_file.md", {"status": "processed"})
            
            mock_update.assert_called_once_with("test_file.md", {"status": "processed"})
    
    def test_find_files_by_status_function(self):
        """Test the find_files_by_status convenience function."""
        with patch("newsletter_generator.storage.storage_manager.storage_manager.find_files_by_status") as mock_find:
            mock_find.return_value = ["file1.md", "file2.md"]
            
            files = find_files_by_status("processed", days=7)
            
            assert files == ["file1.md", "file2.md"]
            mock_find.assert_called_once_with("processed", 7)
    
    def test_cleanup_old_files_function(self):
        """Test the cleanup_old_files convenience function."""
        with patch("newsletter_generator.storage.storage_manager.storage_manager.cleanup_old_files") as mock_cleanup:
            mock_cleanup.return_value = 5
            
            deleted_count = cleanup_old_files(ttl_days=60)
            
            assert deleted_count == 5
            mock_cleanup.assert_called_once_with(60)


if __name__ == "__main__":
    pytest.main()
