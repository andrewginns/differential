"""Tests for the integration hooks module."""

import pytest
from unittest.mock import patch, MagicMock

from newsletter_generator.integration.hooks import (
    storage_post_save_hook,
    storage_post_update_hook,
    storage_pre_delete_hook,
)


class TestStorageHooks:
    """Test cases for the storage hooks."""

    def test_storage_post_save_hook_processed(self):
        """Test post-save hook with processed content."""
        with patch(
            "newsletter_generator.integration.hooks.sync_content"
        ) as mock_sync:
            metadata = {"status": "processed", "content_id": "test-id"}
            
            storage_post_save_hook("test-id", metadata)
            
            mock_sync.assert_called_once_with("test-id")

    def test_storage_post_save_hook_ai_processed(self):
        """Test post-save hook with AI-processed content."""
        with patch(
            "newsletter_generator.integration.hooks.sync_content"
        ) as mock_sync:
            metadata = {"ai_processed": True, "content_id": "test-id"}
            
            storage_post_save_hook("test-id", metadata)
            
            mock_sync.assert_called_once_with("test-id")

    def test_storage_post_save_hook_not_processed(self):
        """Test post-save hook with unprocessed content."""
        with patch(
            "newsletter_generator.integration.hooks.sync_content"
        ) as mock_sync:
            metadata = {"status": "pending_ai", "content_id": "test-id"}
            
            storage_post_save_hook("test-id", metadata)
            
            mock_sync.assert_not_called()

    def test_storage_post_save_hook_error(self):
        """Test post-save hook with an error."""
        with patch(
            "newsletter_generator.integration.hooks.sync_content"
        ) as mock_sync:
            mock_sync.side_effect = Exception("Test error")
            metadata = {"status": "processed", "content_id": "test-id"}
            
            # Should not raise an exception
            storage_post_save_hook("test-id", metadata)
            
            mock_sync.assert_called_once_with("test-id")

    def test_storage_post_update_hook_processed(self):
        """Test post-update hook with processed content."""
        with patch(
            "newsletter_generator.integration.hooks.sync_content"
        ) as mock_sync:
            metadata = {"status": "processed", "content_id": "test-id"}
            
            storage_post_update_hook("test-id", metadata)
            
            mock_sync.assert_called_once_with("test-id")

    def test_storage_post_update_hook_not_processed(self):
        """Test post-update hook with unprocessed content."""
        with patch(
            "newsletter_generator.integration.hooks.sync_content"
        ) as mock_sync:
            metadata = {"status": "pending_ai", "content_id": "test-id"}
            
            storage_post_update_hook("test-id", metadata)
            
            mock_sync.assert_not_called()

    def test_storage_pre_delete_hook(self):
        """Test pre-delete hook."""
        with patch(
            "newsletter_generator.integration.storage_vector_integration.delete_content_index"
        ) as mock_delete:
            storage_pre_delete_hook("test-id")
            
            mock_delete.assert_called_once_with("test-id")

    def test_storage_pre_delete_hook_error(self):
        """Test pre-delete hook with an error."""
        with patch(
            "newsletter_generator.integration.storage_vector_integration.delete_content_index"
        ) as mock_delete:
            mock_delete.side_effect = Exception("Test error")
            
            # Should not raise an exception
            storage_pre_delete_hook("test-id")
            
            mock_delete.assert_called_once_with("test-id")
