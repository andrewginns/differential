"""Tests for the storage manager module."""

import os
import pytest
import datetime
import yaml
from unittest.mock import patch, mock_open, MagicMock

from newsletter_generator.storage.storage_manager import (
    StorageManager,
    store_content,
    get_content,
    update_metadata,
    find_files_by_status,
    cleanup_old_files,
    list_content,
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

        # Create manager and verify it creates the directory
        _ = StorageManager(data_dir=test_dir)

        assert os.path.exists(test_dir)
        assert os.path.isdir(test_dir)

        os.rmdir(test_dir)

    def test_generate_file_path(self, storage_manager):
        """Test generating a file path for a content ID."""
        content_id = "test-content-id"
        source_type = "html"

        file_path = storage_manager._generate_file_path(content_id, source_type)

        expected_dir = os.path.join("test_data", "te", "test-content-id")
        assert file_path.startswith(expected_dir)
        assert file_path.endswith(".md")
        assert source_type in file_path

    def test_store_content(self, storage_manager):
        """Test storing content and metadata to a file."""
        content = "# Test Content\n\nThis is a test."
        metadata = {
            "url": "https://example.com",
            "source_type": "html",
            "title": "Test Title",
        }

        with (
            patch("newsletter_generator.storage.storage_manager.AtomicFileWriter.write") as mock_write,
            patch("newsletter_generator.storage.storage_manager.datetime") as mock_datetime,
            patch.object(storage_manager, "_generate_file_path") as mock_generate_path,
            patch.object(storage_manager, "cache") as mock_cache,
        ):
            mock_dt = MagicMock()
            mock_dt.isoformat.return_value = "2025-05-01T00:00:00"
            mock_datetime.datetime.now.return_value = mock_dt
            mock_datetime.timedelta = datetime.timedelta

            mock_generate_path.return_value = "test_data/te/test-content-id/html.md"
            
            with patch("uuid.uuid4") as mock_uuid:
                mock_uuid.return_value = "test-content-id"
                content_id = storage_manager.store_content(content, metadata)

                assert isinstance(content_id, str)
                assert content_id == "test-content-id"
                
                mock_cache.set.assert_any_call("test-content-id", "metadata", metadata)
                
                mock_write.assert_called_once()
                
                write_args = mock_write.call_args[0]
                assert len(write_args) == 2
                assert write_args[0] == "test_data/te/test-content-id/html.md"
                assert "---\n" in write_args[1]
                assert content in write_args[1]

    def test_store_content_missing_url(self, storage_manager):
        """Test storing content with missing URL."""
        content = "# Test Content\n\nThis is a test."
        metadata = {
            "source_type": "html",
            "title": "Test Title",
        }

        with pytest.raises(ValueError, match="Metadata must include 'url'"):
            storage_manager.store_content(content, metadata)

    def test_store_content_missing_source_type(self, storage_manager):
        """Test storing content with missing source type."""
        content = "# Test Content\n\nThis is a test."
        metadata = {
            "url": "https://example.com",
            "title": "Test Title",
        }

        with pytest.raises(ValueError, match="Metadata must include 'source_type'"):
            storage_manager.store_content(content, metadata)

    def test_get_content(self, storage_manager):
        """Test getting content from a file."""
        file_content = """---
url: https://example.com
source_type: html
title: Test Title
content_id: test-content-id
---


This is a test."""

        with (
            patch("builtins.open", mock_open(read_data=file_content)),
            patch("os.path.exists") as mock_exists,
            patch("os.listdir") as mock_listdir,
            patch.object(storage_manager, "cache") as mock_cache,
        ):
            mock_cache.get.return_value = None
            
            mock_exists.return_value = True
            mock_listdir.return_value = ["html.md"]
            
            content = storage_manager.get_content("test-content-id")

            assert content == "This is a test."
            
            mock_cache.set.assert_called_once()

    def test_get_content_no_front_matter(self, storage_manager):
        """Test getting content with no front matter."""
        file_content = "# Test Content\n\nThis is a test."

        with (
            patch("builtins.open", mock_open(read_data=file_content)),
            patch("os.path.exists") as mock_exists,
            patch("os.listdir") as mock_listdir,
            patch.object(storage_manager, "cache") as mock_cache,
        ):
            mock_cache.get.return_value = None
            
            mock_exists.return_value = True
            mock_listdir.return_value = ["html.md"]
            
            content = storage_manager.get_content("test-content-id")

            assert content == file_content

    def test_update_metadata(self, storage_manager):
        """Test updating metadata in a file."""
        with (
            patch("newsletter_generator.storage.storage_manager.AtomicFileWriter.write") as mock_write,
            patch.object(storage_manager, "read_content") as mock_read_content,
            patch.object(storage_manager, "cache") as mock_cache,
        ):
            metadata = {
                "url": "https://example.com",
                "source_type": "html",
                "title": "Test Title",
                "content_id": "test-content-id"
            }
            
            mock_read_content.return_value = (
                "# Test Content\n\nThis is a test.",
                metadata
            )

            storage_manager.update_metadata(
                "test_data/te/test-content-id/html.md", 
                {"status": "processed", "processed_at": "2025-05-01T00:00:00"}
            )

            mock_write.assert_called_once()
            
            write_args = mock_write.call_args[0]
            assert len(write_args) == 2
            assert write_args[0] == "test_data/te/test-content-id/html.md"
            assert "---\n" in write_args[1]
            assert "# Test Content\n\nThis is a test." in write_args[1]
            
            updated_metadata = metadata.copy()
            updated_metadata.update({"status": "processed", "processed_at": "2025-05-01T00:00:00"})
            mock_cache.set.assert_called_once_with("test-content-id", "metadata", updated_metadata)
            
            mock_read_content.assert_called_once_with("test_data/te/test-content-id/html.md")

    def test_find_files_by_status(self, storage_manager):
        """Test finding files with a specific status."""
        with (
            patch.object(storage_manager, "list_content") as mock_list_content,
        ):
            mock_list_content.return_value = {
                "content-id-1": {
                    "content_id": "content-id-1",
                    "source_type": "html",
                    "status": "processed",
                    "date_added": "2025-05-01T00:00:00",
                },
                "content-id-2": {
                    "content_id": "content-id-2",
                    "source_type": "pdf",
                    "status": "pending_ai",
                    "date_added": "2025-05-01T00:00:00",
                },
                "content-id-3": {
                    "content_id": "content-id-3",
                    "source_type": "html",
                    "status": "processed",
                    "date_added": "2025-04-30T00:00:00",
                },
            }

            files = storage_manager.find_files_by_status("processed")

            assert len(files) == 2
            assert os.path.join("test_data", "co", "content-id-1", "html.md") in files
            assert os.path.join("test_data", "co", "content-id-3", "html.md") in files

            files = storage_manager.find_files_by_status("pending_ai")

            assert len(files) == 1
            assert os.path.join("test_data", "co", "content-id-2", "pdf.md") in files

    def test_find_files_by_status_with_days(self, storage_manager):
        """Test finding files with a specific status and day limit."""
        with (
            patch.object(storage_manager, "list_content") as mock_list_content,
            patch("newsletter_generator.storage.storage_manager.datetime") as mock_datetime,
            patch("os.path.exists") as mock_exists,
        ):
            mock_datetime.datetime.now.return_value = datetime.datetime(2025, 5, 1)
            mock_datetime.datetime.fromisoformat = datetime.datetime.fromisoformat
            mock_datetime.timedelta = datetime.timedelta
            mock_exists.return_value = True

            mock_list_content.return_value = {
                "content-id-1": {
                    "content_id": "content-id-1",
                    "source_type": "html",
                    "status": "processed",
                    "date_added": "2025-05-01T00:00:00",
                },
                "content-id-2": {
                    "content_id": "content-id-2",
                    "source_type": "html",
                    "status": "processed",
                    "date_added": "2025-04-30T00:00:00",
                },
                "content-id-3": {
                    "content_id": "content-id-3",
                    "source_type": "html",
                    "status": "processed",
                    "date_added": "2025-04-15T00:00:00",
                },
            }

            with patch.object(storage_manager, "_generate_file_path") as mock_generate_path:
                mock_generate_path.side_effect = lambda content_id, source_type: os.path.join(
                    "test_data", content_id[:2], content_id, f"{source_type}.md"
                )
                
                files = storage_manager.find_files_by_status("processed", days=7)

                assert len(files) == 2
                assert os.path.join("test_data", "co", "content-id-1", "html.md") in files
                assert os.path.join("test_data", "co", "content-id-2", "html.md") in files
                assert os.path.join("test_data", "co", "content-id-3", "html.md") not in files

    def test_cleanup_old_files(self, storage_manager):
        """Test cleaning up old files."""
        with (
            patch.object(storage_manager, "list_content") as mock_list_content,
            patch("os.path.exists") as mock_exists,
            patch("os.path.isdir") as mock_isdir,
            patch("shutil.rmtree") as mock_rmtree,
            patch("newsletter_generator.storage.storage_manager.datetime") as mock_datetime,
            patch("newsletter_generator.storage.storage_manager.CONFIG") as mock_config,
        ):
            mock_datetime.datetime.now.return_value = datetime.datetime(2025, 5, 1)
            mock_datetime.datetime.fromisoformat = datetime.datetime.fromisoformat
            mock_datetime.timedelta = datetime.timedelta

            mock_config.get.return_value = 30  # Default TTL

            mock_list_content.return_value = {
                "content-id-1": {
                    "content_id": "content-id-1",
                    "source_type": "html",
                    "date_added": "2025-05-01T00:00:00",
                },
                "content-id-2": {
                    "content_id": "content-id-2",
                    "source_type": "html",
                    "date_added": "2025-04-30T00:00:00",
                },
                "content-id-3": {
                    "content_id": "content-id-3",
                    "source_type": "html",
                    "date_added": "2025-03-15T00:00:00",
                },
                "content-id-4": {
                    "content_id": "content-id-4",
                    "source_type": "pdf",
                    "date_added": "2025-03-15T00:00:00",
                },
            }
            
            mock_exists.return_value = True
            mock_isdir.return_value = True
            
            with patch("os.listdir") as mock_listdir, \
                 patch("os.remove") as mock_remove, \
                 patch("os.rmdir") as mock_rmdir, \
                 patch.object(storage_manager, "_generate_file_path") as mock_generate_path:
                
                mock_listdir.return_value = ["html.md", "metadata.json"]
                mock_remove.return_value = None  # Mock successful file removal
                mock_rmdir.return_value = None   # Mock successful directory removal
                mock_generate_path.side_effect = lambda content_id, source_type: os.path.join(
                    "test_data", content_id[:2], content_id, f"{source_type}.md"
                )
                
                deleted_count = storage_manager.cleanup_old_files()

                assert deleted_count == 4  # 2 files (html.md, metadata.json) for each of the 2 old content IDs
                
                mock_remove.assert_any_call(os.path.join("test_data", "co", "content-id-3", "html.md"))
                mock_remove.assert_any_call(os.path.join("test_data", "co", "content-id-3", "metadata.json"))
                mock_remove.assert_any_call(os.path.join("test_data", "co", "content-id-4", "html.md"))
                mock_remove.assert_any_call(os.path.join("test_data", "co", "content-id-4", "metadata.json"))


class TestConvenienceFunctions:
    """Test cases for the convenience functions."""

    def test_store_content_function(self):
        """Test the store_content convenience function."""
        with patch(
            "newsletter_generator.storage.storage_manager._storage_manager.store_content"
        ) as mock_store:
            mock_store.return_value = "test_content_id"

            content = "# Test Content"
            metadata = {"url": "https://example.com", "source_type": "html"}

            result = store_content(content, metadata)

            assert result == "test_content_id"
            mock_store.assert_called_once_with(content, metadata)

    def test_get_content_function(self):
        """Test the get_content convenience function."""
        with patch(
            "newsletter_generator.storage.storage_manager._storage_manager.get_content"
        ) as mock_get:
            mock_get.return_value = "# Test Content"

            content = get_content("test_content_id")

            assert content == "# Test Content"
            mock_get.assert_called_once_with("test_content_id")

    def test_update_metadata_function(self):
        """Test the update_metadata convenience function."""
        with (
            patch("newsletter_generator.storage.storage_manager._storage_manager.update_metadata") as mock_update,
            patch("newsletter_generator.storage.storage_manager._storage_manager.cache") as mock_cache,
            patch("newsletter_generator.storage.storage_manager.os.path.exists") as mock_exists,
            patch("newsletter_generator.storage.storage_manager.os.listdir") as mock_listdir,
            patch("newsletter_generator.storage.storage_manager._storage_manager._generate_file_path") as mock_generate_path,
            patch("newsletter_generator.storage.storage_manager._storage_manager.data_dir", "test_data"),
        ):
            mock_cache.get.return_value = None
            
            mock_exists.return_value = True
            mock_listdir.return_value = ["html.md"]
            
            file_path = "test_data/te/test-content-id/html.md"
            mock_generate_path.return_value = file_path
            
            update_metadata("test-content-id", {"status": "processed"})

            mock_update.assert_called_once_with(file_path, {"status": "processed"})

    def test_find_files_by_status_function(self):
        """Test the find_files_by_status convenience function."""
        with patch(
            "newsletter_generator.storage.storage_manager._storage_manager.find_files_by_status"
        ) as mock_find:
            mock_find.return_value = [
                "test_data/co/content-id-1/html.md", 
                "test_data/co/content-id-2/html.md"
            ]

            files = find_files_by_status("processed", days=7)

            assert files == [
                "test_data/co/content-id-1/html.md", 
                "test_data/co/content-id-2/html.md"
            ]
            mock_find.assert_called_once_with("processed", 7)

    def test_cleanup_old_files_function(self):
        """Test the cleanup_old_files convenience function."""
        with patch(
            "newsletter_generator.storage.storage_manager._storage_manager.cleanup_old_files"
        ) as mock_cleanup:
            mock_cleanup.return_value = 5

            deleted_count = cleanup_old_files(ttl_days=60)

            assert deleted_count == 5
            mock_cleanup.assert_called_once_with(60)


if __name__ == "__main__":
    pytest.main()
