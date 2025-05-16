"""Integration hooks for the newsletter generator.

This module provides hooks that can be used to integrate different components
of the newsletter generator system, such as automatically indexing content
in the vector database when it's added to storage.
"""

from typing import Dict, Any, Optional

from newsletter_generator.utils.logging_utils import get_logger
from newsletter_generator.integration.storage_vector_integration import sync_content

logger = get_logger("integration.hooks")


def storage_post_save_hook(content_id: str, metadata: Dict[str, Any]) -> None:
    """Hook that runs after content is saved to storage.

    This hook automatically indexes the content in the vector database.

    Args:
        content_id: The ID of the saved content.
        metadata: The metadata of the saved content.
    """
    try:
        # Only index content that has been processed by AI
        if metadata.get("status") == "processed" or metadata.get("ai_processed", False):
            logger.info(f"Indexing content {content_id} in vector database")
            sync_content(content_id)
        else:
            logger.debug(
                f"Skipping vector indexing for content {content_id} (not AI processed)"
            )
    except Exception as e:
        logger.error(f"Error in storage_post_save_hook for content {content_id}: {e}")


def storage_post_update_hook(content_id: str, metadata: Dict[str, Any]) -> None:
    """Hook that runs after content metadata is updated in storage.

    This hook updates the content in the vector database if needed.

    Args:
        content_id: The ID of the updated content.
        metadata: The updated metadata.
    """
    try:
        # Only update index if content has been processed by AI
        if metadata.get("status") == "processed" or metadata.get("ai_processed", False):
            logger.info(f"Updating content {content_id} in vector database")
            sync_content(content_id)
        else:
            logger.debug(
                f"Skipping vector update for content {content_id} (not AI processed)"
            )
    except Exception as e:
        logger.error(f"Error in storage_post_update_hook for content {content_id}: {e}")


def storage_pre_delete_hook(content_id: str) -> None:
    """Hook that runs before content is deleted from storage.

    This hook deletes the content from the vector database.

    Args:
        content_id: The ID of the content to be deleted.
    """
    try:
        from newsletter_generator.integration.storage_vector_integration import delete_content_index

        logger.info(f"Deleting content {content_id} from vector database")
        delete_content_index(content_id)
    except Exception as e:
        logger.error(f"Error in storage_pre_delete_hook for content {content_id}: {e}")
