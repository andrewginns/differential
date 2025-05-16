"""Tests for the storage vector integration module."""

import os
import pytest
from unittest.mock import patch, MagicMock

from newsletter_generator.integration.storage_vector_integration import (
    StorageVectorIntegration,
    index_content,
    index_all_content,
    update_content_index,
    delete_content_index,
    sync_content,
)


@pytest.fixture
def mock_storage_manager():
    """Create a mock storage manager."""
    mock = MagicMock()
    
    # Mock content and metadata
    mock.get_content.return_value = "Test content"
    mock.list_content.return_value = {
        "test-id-1": {
            "content_id": "test-id-1",
            "title": "Test Title 1",
            "url": "https://example.com/1",
            "source_type": "html",
            "date_added": "2023-01-01T12:00:00",
            "url_hash": "hash1",
            "content_fingerprint": "fingerprint1",
            "status": "processed",
            "ai_category": "Technology",
            "ai_summary": "This is a summary",
            "ai_tags": ["tag1", "tag2"],
        },
        "test-id-2": {
            "content_id": "test-id-2",
            "title": "Test Title 2",
            "url": "https://example.com/2",
            "source_type": "pdf",
            "date_added": "2023-01-02T12:00:00",
            "url_hash": "hash2",
            "content_fingerprint": "fingerprint2",
        },
    }
    
    return mock


@pytest.fixture
def mock_vector_db():
    """Create a mock vector database."""
    mock = MagicMock()
    return mock


@pytest.fixture
def integration(mock_storage_manager, mock_vector_db):
    """Create a StorageVectorIntegration instance with mocks."""
    return StorageVectorIntegration(
        storage_manager=mock_storage_manager,
        vector_db=mock_vector_db,
    )


class TestStorageVectorIntegration:
    """Test cases for the StorageVectorIntegration class."""

    def test_prepare_metadata_for_vector_db(self, integration):
        """Test preparing metadata for the vector database."""
        metadata = {
            "content_id": "test-id",
            "title": "Test Title",
            "url": "https://example.com",
            "source_type": "html",
            "date_added": "2023-01-01T12:00:00",
            "url_hash": "hash123",
            "content_fingerprint": "fingerprint123",
            "status": "processed",
            "ai_category": "Technology",
            "ai_summary": "This is a summary",
            "ai_tags": ["tag1", "tag2"],
            "extra_field": "should not be included",
        }
        
        result = integration._prepare_metadata_for_vector_db(metadata)
        
        assert result["content_id"] == "test-id"
        assert result["title"] == "Test Title"
        assert result["url"] == "https://example.com"
        assert result["source_type"] == "html"
        assert result["date_added"] == "2023-01-01T12:00:00"
        assert result["url_hash"] == "hash123"
        assert result["category"] == "Technology"
        assert result["summary"] == "This is a summary"
        assert result["tags"] == ["tag1", "tag2"]
        assert "extra_field" not in result
        assert "content_fingerprint" not in result

    def test_index_content(self, integration, mock_storage_manager, mock_vector_db):
        """Test indexing a single content item."""
        result = integration.index_content("test-id-1")
        
        assert result is True
        mock_storage_manager.get_content.assert_called_once_with("test-id-1")
        mock_storage_manager.list_content.assert_called_once()
        mock_vector_db.add_document.assert_called_once()
        
        # Check that the document ID and text were passed correctly
        args, kwargs = mock_vector_db.add_document.call_args
        assert kwargs["document_id"] == "test-id-1"
        assert kwargs["text"] == "Test content"
        assert "metadata" in kwargs

    def test_index_content_not_found(self, integration, mock_storage_manager):
        """Test indexing a content item that doesn't exist."""
        mock_storage_manager.list_content.return_value = {}
        
        result = integration.index_content("nonexistent-id")
        
        assert result is False
        mock_storage_manager.get_content.assert_not_called()

    def test_index_all_content(self, integration, mock_storage_manager):
        """Test indexing all content."""
        with patch.object(integration, "index_content") as mock_index:
            mock_index.side_effect = [True, True]
            
            success, failure = integration.index_all_content()
            
            assert success == 2
            assert failure == 0
            assert mock_index.call_count == 2
            mock_index.assert_any_call("test-id-1")
            mock_index.assert_any_call("test-id-2")

    def test_index_all_content_with_failures(self, integration, mock_storage_manager):
        """Test indexing all content with some failures."""
        with patch.object(integration, "index_content") as mock_index:
            mock_index.side_effect = [True, False]
            
            success, failure = integration.index_all_content()
            
            assert success == 1
            assert failure == 1

    def test_update_content_index(self, integration, mock_storage_manager, mock_vector_db):
        """Test updating a content item in the vector database."""
        result = integration.update_content_index("test-id-1")
        
        assert result is True
        mock_storage_manager.get_content.assert_called_once_with("test-id-1")
        mock_storage_manager.list_content.assert_called_once()
        mock_vector_db.update_document.assert_called_once()
        
        # Check that the document ID and text were passed correctly
        args, kwargs = mock_vector_db.update_document.call_args
        assert kwargs["document_id"] == "test-id-1"
        assert kwargs["text"] == "Test content"
        assert "metadata" in kwargs

    def test_delete_content_index(self, integration, mock_vector_db):
        """Test deleting a content item from the vector database."""
        result = integration.delete_content_index("test-id-1")
        
        assert result is True
        mock_vector_db.delete_document.assert_called_once_with(document_id="test-id-1")

    def test_sync_content_update(self, integration):
        """Test syncing content that exists in the vector database."""
        with (
            patch.object(integration, "update_content_index", return_value=True) as mock_update,
            patch.object(integration, "index_content") as mock_index,
        ):
            result = integration.sync_content("test-id-1")
            
            assert result is True
            mock_update.assert_called_once_with("test-id-1")
            mock_index.assert_not_called()

    def test_sync_content_add(self, integration):
        """Test syncing content that doesn't exist in the vector database."""
        with (
            patch.object(integration, "update_content_index") as mock_update,
            patch.object(integration, "index_content", return_value=True) as mock_index,
        ):
            mock_update.side_effect = Exception("Document not found")
            
            result = integration.sync_content("test-id-1")
            
            assert result is True
            mock_update.assert_called_once_with("test-id-1")
            mock_index.assert_called_once_with("test-id-1")


class TestConvenienceFunctions:
    """Test cases for the convenience functions."""

    def test_index_content_function(self):
        """Test the index_content convenience function."""
        mock_integration = MagicMock()
        mock_integration.index_content.return_value = True
        
        with patch(
            "newsletter_generator.integration.storage_vector_integration.get_integration",
            return_value=mock_integration,
        ):
            result = index_content("test-id")
            
            assert result is True
            mock_integration.index_content.assert_called_once_with("test-id")

    def test_index_all_content_function(self):
        """Test the index_all_content convenience function."""
        mock_integration = MagicMock()
        mock_integration.index_all_content.return_value = (5, 1)
        
        with patch(
            "newsletter_generator.integration.storage_vector_integration.get_integration",
            return_value=mock_integration,
        ):
            success, failure = index_all_content()
            
            assert success == 5
            assert failure == 1
            mock_integration.index_all_content.assert_called_once()

    def test_update_content_index_function(self):
        """Test the update_content_index convenience function."""
        mock_integration = MagicMock()
        mock_integration.update_content_index.return_value = True
        
        with patch(
            "newsletter_generator.integration.storage_vector_integration.get_integration",
            return_value=mock_integration,
        ):
            result = update_content_index("test-id")
            
            assert result is True
            mock_integration.update_content_index.assert_called_once_with("test-id")

    def test_delete_content_index_function(self):
        """Test the delete_content_index convenience function."""
        mock_integration = MagicMock()
        mock_integration.delete_content_index.return_value = True
        
        with patch(
            "newsletter_generator.integration.storage_vector_integration.get_integration",
            return_value=mock_integration,
        ):
            result = delete_content_index("test-id")
            
            assert result is True
            mock_integration.delete_content_index.assert_called_once_with("test-id")

    def test_sync_content_function(self):
        """Test the sync_content convenience function."""
        mock_integration = MagicMock()
        mock_integration.sync_content.return_value = True
        
        with patch(
            "newsletter_generator.integration.storage_vector_integration.get_integration",
            return_value=mock_integration,
        ):
            result = sync_content("test-id")
            
            assert result is True
            mock_integration.sync_content.assert_called_once_with("test-id")
