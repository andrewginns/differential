"""Storage System Integration Layer for Differential.

This module integrates the content-addressed storage system with the LightRAG
vector database, enabling automatic indexing of content for vector search.
"""

import os
from typing import Dict, Any, List, Optional, Tuple

from newsletter_generator.storage.storage_manager import (
    StorageManager,
    list_content,
    get_content,
)
from newsletter_generator.vector_db.lightrag_manager import (
    LightRAGManager,
    add_document,
    update_document,
    delete_document,
)
from newsletter_generator.utils.logging_utils import get_logger

logger = get_logger("integration.storage_vector")


class StorageVectorIntegration:
    """Integration layer between content-addressed storage and vector database.

    This class provides functionality to:
    1. Index existing content in the vector database
    2. Automatically index new content as it's added
    3. Update vector entries when content is updated
    4. Delete vector entries when content is deleted
    """

    def __init__(
        self,
        storage_manager: Optional[StorageManager] = None,
        vector_db: Optional[LightRAGManager] = None,
    ):
        """Initialize the integration layer.

        Args:
            storage_manager: Optional StorageManager instance. If None, uses the singleton.
            vector_db: Optional LightRAGManager instance. If None, uses the singleton.
        """
        from newsletter_generator.storage.storage_manager import _storage_manager
        from newsletter_generator.vector_db.lightrag_manager import get_vector_db

        self.storage_manager = storage_manager or _storage_manager
        self.vector_db = vector_db or get_vector_db()

        logger.info("Initialized StorageVectorIntegration")

    def _prepare_metadata_for_vector_db(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare metadata for storage in the vector database.

        Args:
            metadata: The original metadata from the content storage.

        Returns:
            A dictionary with metadata formatted for the vector database.
        """
        # Copy only the fields we want to include in the vector database
        vector_metadata = {
            "title": metadata.get("title", ""),
            "url": metadata.get("url", ""),
            "source_type": metadata.get("source_type", ""),
            "date_added": metadata.get("date_added", ""),
            "content_id": metadata.get("content_id", ""),
            "url_hash": metadata.get("url_hash", ""),
            "category": metadata.get("category", ""),
            "summary": metadata.get("summary", ""),
            "tags": metadata.get("tags", []),
        }

        # Add any AI-generated fields if they exist
        if "ai_processed" in metadata:
            vector_metadata["ai_processed"] = metadata["ai_processed"]
        if "ai_category" in metadata:
            vector_metadata["category"] = metadata["ai_category"]
        if "ai_summary" in metadata:
            vector_metadata["summary"] = metadata["ai_summary"]
        if "ai_tags" in metadata:
            vector_metadata["tags"] = metadata["ai_tags"]

        return vector_metadata

    def index_content(self, content_id: str) -> bool:
        """Index a single content item in the vector database.

        Args:
            content_id: The ID of the content to index.

        Returns:
            True if indexing was successful, False otherwise.
        """
        try:
            # Get content and metadata from storage
            content = self.storage_manager.get_content(content_id)
            
            # Get all content metadata to find the one matching our ID
            all_content = self.storage_manager.list_content()
            if content_id not in all_content:
                logger.error(f"Content ID {content_id} not found in storage")
                return False
                
            metadata = all_content[content_id]
            
            # Prepare metadata for vector database
            vector_metadata = self._prepare_metadata_for_vector_db(metadata)
            
            # Add to vector database
            add_document(
                document_id=content_id,
                text=content,
                metadata=vector_metadata,
            )
            
            logger.info(f"Indexed content {content_id} in vector database")
            return True
        except Exception as e:
            logger.error(f"Error indexing content {content_id}: {e}")
            return False

    def index_all_content(self) -> Tuple[int, int]:
        """Index all content in the storage system.

        Returns:
            A tuple of (success_count, failure_count).
        """
        success_count = 0
        failure_count = 0
        
        try:
            all_content = list_content()
            total_count = len(all_content)
            
            logger.info(f"Indexing {total_count} content items in vector database")
            
            for content_id in all_content:
                if self.index_content(content_id):
                    success_count += 1
                else:
                    failure_count += 1
                    
            logger.info(
                f"Indexed {success_count} content items successfully, {failure_count} failed"
            )
            return success_count, failure_count
        except Exception as e:
            logger.error(f"Error indexing all content: {e}")
            return success_count, failure_count

    def update_content_index(self, content_id: str) -> bool:
        """Update a content item in the vector database.

        Args:
            content_id: The ID of the content to update.

        Returns:
            True if update was successful, False otherwise.
        """
        try:
            # Get content and metadata from storage
            content = self.storage_manager.get_content(content_id)
            
            # Get all content metadata to find the one matching our ID
            all_content = self.storage_manager.list_content()
            if content_id not in all_content:
                logger.error(f"Content ID {content_id} not found in storage")
                return False
                
            metadata = all_content[content_id]
            
            # Prepare metadata for vector database
            vector_metadata = self._prepare_metadata_for_vector_db(metadata)
            
            # Update in vector database
            update_document(
                document_id=content_id,
                text=content,
                metadata=vector_metadata,
            )
            
            logger.info(f"Updated content {content_id} in vector database")
            return True
        except Exception as e:
            logger.error(f"Error updating content {content_id} in vector database: {e}")
            return False

    def delete_content_index(self, content_id: str) -> bool:
        """Delete a content item from the vector database.

        Args:
            content_id: The ID of the content to delete.

        Returns:
            True if deletion was successful, False otherwise.
        """
        try:
            delete_document(document_id=content_id)
            logger.info(f"Deleted content {content_id} from vector database")
            return True
        except Exception as e:
            logger.error(f"Error deleting content {content_id} from vector database: {e}")
            return False

    def sync_content(self, content_id: str) -> bool:
        """Sync a content item between storage and vector database.

        This will add the content if it doesn't exist in the vector database,
        or update it if it does.

        Args:
            content_id: The ID of the content to sync.

        Returns:
            True if sync was successful, False otherwise.
        """
        try:
            # First try to update, which will fail if the document doesn't exist
            try:
                return self.update_content_index(content_id)
            except Exception:
                # If update fails, try to add the document
                return self.index_content(content_id)
        except Exception as e:
            logger.error(f"Error syncing content {content_id}: {e}")
            return False


# Create a singleton instance
_integration = None


def get_integration() -> StorageVectorIntegration:
    """Get or create the singleton integration instance.

    Returns:
        The StorageVectorIntegration instance.
    """
    global _integration
    if _integration is None:
        try:
            _integration = StorageVectorIntegration()
        except Exception as e:
            logger.error(f"Error creating StorageVectorIntegration: {e}")
            raise
    return _integration


# Convenience functions that use the singleton instance

def index_content(content_id: str) -> bool:
    """Index a single content item in the vector database.

    Args:
        content_id: The ID of the content to index.

    Returns:
        True if indexing was successful, False otherwise.
    """
    return get_integration().index_content(content_id)


def index_all_content() -> Tuple[int, int]:
    """Index all content in the storage system.

    Returns:
        A tuple of (success_count, failure_count).
    """
    return get_integration().index_all_content()


def update_content_index(content_id: str) -> bool:
    """Update a content item in the vector database.

    Args:
        content_id: The ID of the content to update.

    Returns:
        True if update was successful, False otherwise.
    """
    return get_integration().update_content_index(content_id)


def delete_content_index(content_id: str) -> bool:
    """Delete a content item from the vector database.

    Args:
        content_id: The ID of the content to delete.

    Returns:
        True if deletion was successful, False otherwise.
    """
    return get_integration().delete_content_index(content_id)


def sync_content(content_id: str) -> bool:
    """Sync a content item between storage and vector database.

    Args:
        content_id: The ID of the content to sync.

    Returns:
        True if sync was successful, False otherwise.
    """
    return get_integration().sync_content(content_id)
