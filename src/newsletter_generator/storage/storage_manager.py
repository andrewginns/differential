"""Storage manager for the newsletter generator.

This module handles the reading and writing of processed content and associated
metadata to the local file system.
"""

import os
import datetime
import yaml
import uuid
from typing import Dict, Any, List, Optional, Tuple

from newsletter_generator.utils.logging_utils import get_logger
from newsletter_generator.utils.config import CONFIG
from newsletter_generator.utils.content_processing import (
    get_url_hash,
    generate_content_fingerprint,
    calculate_content_similarity,
)

logger = get_logger("storage.manager")


class StorageManager:
    """Manages storage of processed content and metadata.

    This class handles file operations for storing and retrieving content,
    including reading, writing, and updating Markdown files with YAML front matter.
    """

    def __init__(self, data_dir: Optional[str] = None):
        """Initialise the storage manager.

        Args:
            data_dir: The directory to store data in. If None, uses the default
                from config.
        """
        self.data_dir = data_dir or CONFIG.get("DATA_DIR", "data")

        os.makedirs(self.data_dir, exist_ok=True)

        # Initialise indices for deduplication
        self.url_hash_index = {}  # url_hash -> content_id
        self.fingerprint_index = {}  # content_fingerprint -> content_id
        self._build_deduplication_indices()

    def _build_deduplication_indices(self):
        """Build indices for URL-based and content-based deduplication."""
        try:
            all_content = self.list_content()

            for content_id, metadata in all_content.items():
                # Check for URL hash in metadata
                url = metadata.get("url", "")
                if url:
                    url_hash = metadata.get("url_hash")
                    if not url_hash:
                        # Calculate hash if not present
                        url_hash = get_url_hash(url)
                    self.url_hash_index[url_hash] = content_id

                # Check for content fingerprint in metadata
                fingerprint = metadata.get("content_fingerprint")
                if fingerprint:
                    self.fingerprint_index[fingerprint] = content_id

            logger.info(
                f"Built deduplication indices with {len(self.url_hash_index)} URLs and {len(self.fingerprint_index)} content fingerprints"
            )
        except Exception as e:
            logger.error(f"Error building deduplication indices: {e}")

    def _find_by_url_hash(self, url_hash: str) -> Optional[str]:
        """Find content ID by URL hash.

        Args:
            url_hash: The URL hash to search for.

        Returns:
            The content ID if found, None otherwise.
        """
        return self.url_hash_index.get(url_hash)

    def _find_by_content_fingerprint(self, fingerprint: str) -> Optional[str]:
        """Find content ID by content fingerprint.

        Args:
            fingerprint: The content fingerprint to search for.

        Returns:
            The content ID if found, None otherwise.
        """
        return self.fingerprint_index.get(fingerprint)

    def _calculate_similarity(self, content1: str, content2: str) -> float:
        """Calculate similarity between two content strings.

        Args:
            content1: First content string.
            content2: Second content string.

        Returns:
            Similarity score between 0.0 and 1.0.
        """
        return calculate_content_similarity(content1, content2)

    def _get_content_path(self, content_id: str, source_type: Optional[str] = None) -> str:
        """Generate a content-addressed path for a content ID.

        Args:
            content_id: The content ID.
            source_type: The content type (html, pdf, youtube). If None, returns the directory path.

        Returns:
            The path to the content file or directory.
        """
        prefix = content_id[:2]
        dir_path = os.path.join(self.data_dir, prefix, content_id)
        os.makedirs(dir_path, exist_ok=True)

        if source_type:
            return os.path.join(dir_path, f"{source_type}.md")
        return dir_path

    def _generate_file_path(self, url_or_id: str, source_type: str) -> str:
        """Generate a file path for a URL or content ID.

        Args:
            url_or_id: The URL or content ID.
            source_type: The content type (html, pdf, youtube).

        Returns:
            The file path to store the content at.
        """
        if url_or_id.startswith("http"):
            # Generate a date-based path for URLs
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            url_hash = get_url_hash(url_or_id)[:10]
            dir_path = os.path.join(self.data_dir, today)
            os.makedirs(dir_path, exist_ok=True)
            return os.path.join(dir_path, f"{source_type}_{url_hash}.md")
        else:
            return self._get_content_path(url_or_id, source_type)

    def store_content(self, content: str, metadata: Dict[str, Any]) -> str:
        """Store content and metadata with a unique content ID.

        Args:
            content: The Markdown content to store.
            metadata: The metadata to include.

        Returns:
            The content ID (which can be used to retrieve or update the content later).

        Raises:
            Exception: If there's an error storing the content.
        """
        if "url" not in metadata:
            raise ValueError("Metadata must include 'url'")

        if "source_type" not in metadata:
            raise ValueError("Metadata must include 'source_type'")

        # Check for URL-based duplicates
        url = metadata["url"]
        url_hash = get_url_hash(url)
        existing_id = self._find_by_url_hash(url_hash)

        if existing_id:
            logger.info(f"Found duplicate URL: {url} matches existing content_id: {existing_id}")
            return existing_id

        # Check for content-based duplicates
        title = metadata.get("title", "")
        content_fingerprint = generate_content_fingerprint(content, title)

        duplicate_id = self._find_by_content_fingerprint(content_fingerprint)
        if duplicate_id:
            # Double check with similarity to avoid false positives
            existing_content = self.get_content(duplicate_id)
            similarity = self._calculate_similarity(content, existing_content)

            if similarity > 0.85:  # High threshold to avoid false positives
                logger.info(
                    f"Found similar content with ID {duplicate_id}, similarity: {similarity}"
                )
                return duplicate_id

        # Generate a unique content ID
        content_id = str(uuid.uuid4())

        # Add content ID and deduplication data to metadata
        metadata["content_id"] = content_id
        metadata["url_hash"] = url_hash
        metadata["content_fingerprint"] = content_fingerprint

        if "date_added" not in metadata:
            metadata["date_added"] = datetime.datetime.now().isoformat()

        source_type = metadata["source_type"]
        file_path = self._generate_file_path(content_id, source_type)

        # Write the content to a file
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("---\n")
                yaml.dump(metadata, f, default_flow_style=False)
                f.write("---\n\n")
                f.write(content)

            logger.info(f"Stored content with ID {content_id} at {file_path}")
        except Exception as e:
            logger.error(f"Error writing content to {file_path}: {e}")
            raise

        # Update our indices
        self.url_hash_index[url_hash] = content_id
        self.fingerprint_index[content_fingerprint] = content_id

        return content_id

    def get_content(self, content_id: str) -> str:
        """Get content by content ID.

        Args:
            content_id: The content ID.

        Returns:
            The content.

        Raises:
            ValueError: If the content ID is not found.
        """
        try:
            dir_path = self._get_content_path(content_id)

            if not os.path.exists(dir_path):
                raise ValueError(f"Content ID not found: {content_id}")

            for filename in os.listdir(dir_path):
                if filename.endswith(".md"):
                    file_path = os.path.join(dir_path, filename)
                    content, _ = self.read_content(file_path)
                    return content

            raise ValueError(f"No content file found for ID: {content_id}")
        except Exception as e:
            logger.error(f"Error getting content for ID {content_id}: {e}")
            raise

    def list_content(self) -> Dict[str, Dict[str, Any]]:
        """List all content with their metadata.

        Returns:
            A dictionary mapping content IDs to metadata.
        """
        result = {}
        try:
            for prefix_dir in os.listdir(self.data_dir):
                prefix_path = os.path.join(self.data_dir, prefix_dir)

                if not os.path.isdir(prefix_path) or prefix_dir.startswith("."):
                    continue

                if len(prefix_dir) != 2:
                    continue

                for content_id_dir in os.listdir(prefix_path):
                    content_id_path = os.path.join(prefix_path, content_id_dir)

                    if not os.path.isdir(content_id_path):
                        continue

                    # Check if this looks like a content ID directory (should match the prefix)
                    if not content_id_dir.startswith(prefix_dir):
                        continue

                    for filename in os.listdir(content_id_path):
                        if filename.endswith(".md"):
                            file_path = os.path.join(content_id_path, filename)
                            try:
                                _, metadata = self.read_content(file_path)

                                # Use the directory name as the content ID
                                result[content_id_dir] = metadata

                                # Update our indices
                                url_hash = metadata.get("url_hash")
                                if url_hash:
                                    self.url_hash_index[url_hash] = content_id_dir

                                fingerprint = metadata.get("content_fingerprint")
                                if fingerprint:
                                    self.fingerprint_index[fingerprint] = content_id_dir

                                # Only need one file per content ID
                                break
                            except Exception as e:
                                logger.warning(f"Error reading metadata from {file_path}: {e}")

            logger.info(f"Listed {len(result)} content items")
            return result
        except Exception as e:
            logger.error(f"Error listing content: {e}")
            return {}

    def write_content(self, content: str, metadata: Dict[str, Any]) -> str:
        """Write content and metadata to a file.

        Args:
            content: The Markdown content to write.
            metadata: The metadata to include in the YAML front matter.

        Returns:
            The path to the written file.

        Raises:
            Exception: If there's an error writing the file.
        """
        if "source_type" not in metadata:
            raise ValueError("Metadata must include 'source_type'")

        if "content_id" not in metadata:
            raise ValueError("Metadata must include 'content_id'")

        if "ingested_at" not in metadata:
            metadata["ingested_at"] = datetime.datetime.now().isoformat()

        if "status" not in metadata:
            metadata["status"] = "pending_ai"

        content_id = metadata["content_id"]
        source_type = metadata["source_type"]
        file_path = self._get_content_path(content_id, source_type)

        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            with open(file_path, "w", encoding="utf-8") as f:
                f.write("---\n")
                yaml.dump(metadata, f, default_flow_style=False)
                f.write("---\n\n")
                f.write(content)

            logger.info(f"Wrote content to {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Error writing content to {file_path}: {e}")
            raise

    def read_content(self, file_path: str) -> Tuple[str, Dict[str, Any]]:
        """Read content and metadata from a file.

        Args:
            file_path: The path to the file to read.

        Returns:
            A tuple containing the content and metadata.

        Raises:
            Exception: If there's an error reading the file.
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            if content.startswith("---"):
                end_index = content.find("---", 3)
                if end_index != -1:
                    front_matter = content[3:end_index].strip()
                    metadata = yaml.safe_load(front_matter)

                    actual_content = content[end_index + 3 :].strip()

                    return actual_content, metadata

            logger.warning(f"No YAML front matter found in {file_path}")
            return content, {}
        except Exception as e:
            logger.error(f"Error reading content from {file_path}: {e}")
            raise

    def update_metadata(self, file_path: str, metadata_updates: Dict[str, Any]) -> None:
        """Update metadata in a file.

        Args:
            file_path: The path to the file to update.
            metadata_updates: The metadata fields to update.

        Raises:
            Exception: If there's an error updating the file.
        """
        try:
            content, metadata = self.read_content(file_path)

            metadata.update(metadata_updates)

            with open(file_path, "w", encoding="utf-8") as f:
                f.write("---\n")
                yaml.dump(metadata, f, default_flow_style=False)
                f.write("---\n\n")
                f.write(content)

            logger.info(f"Updated metadata in {file_path}")
        except Exception as e:
            logger.error(f"Error updating metadata in {file_path}: {e}")
            raise

    def find_files_by_status(self, status: str, days: Optional[int] = None) -> List[str]:
        """Find files with a specific status.

        Args:
            status: The status to filter by.
            days: If provided, only include files from the last N days.

        Returns:
            A list of file paths matching the criteria.
        """
        matching_files = []

        try:
            for item in os.listdir(self.data_dir):
                item_path = os.path.join(self.data_dir, item)
                if os.path.isdir(item_path) and item.count("-") == 2:
                    if days is not None:
                        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days)
                        cutoff_str = cutoff_date.strftime("%Y-%m-%d")
                        if item < cutoff_str:
                            continue

                    for filename in os.listdir(item_path):
                        if filename.endswith(".md"):
                            file_path = os.path.join(item_path, filename)
                            _, metadata = self.read_content(file_path)
                            if metadata.get("status") == status:
                                matching_files.append(file_path)

            logger.info(f"Found {len(matching_files)} files with status '{status}'")
            return matching_files
        except Exception as e:
            logger.error(f"Error finding files by status: {e}")
            return []

    def cleanup_old_files(self, ttl_days: Optional[int] = None) -> int:
        """Delete files older than the TTL.

        Args:
            ttl_days: The TTL in days. If None, uses the default from config.

        Returns:
            The number of files deleted.
        """
        ttl_days = ttl_days or CONFIG.get("TTL_DAYS", 60)
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=ttl_days)
        cutoff_str = cutoff_date.strftime("%Y-%m-%d")

        deleted_count = 0

        try:
            for item in os.listdir(self.data_dir):
                item_path = os.path.join(self.data_dir, item)
                if os.path.isdir(item_path) and item.count("-") == 2:
                    if item < cutoff_str:
                        dir_path = os.path.join(self.data_dir, item)
                        for filename in os.listdir(dir_path):
                            file_path = os.path.join(dir_path, filename)
                            try:
                                os.remove(file_path)
                                deleted_count += 1
                                logger.debug(f"Deleted old file: {file_path}")
                            except Exception as e:
                                logger.warning(f"Error deleting file {file_path}: {e}")

                        try:
                            os.rmdir(dir_path)
                            logger.debug(f"Deleted empty directory: {dir_path}")
                        except OSError:
                            pass

            logger.info(f"Cleaned up {deleted_count} files older than {ttl_days} days")
            return deleted_count
        except Exception as e:
            logger.error(f"Error cleaning up old files: {e}")
            return 0


# Create a singleton instance of the storage manager
_storage_manager = StorageManager()

# Convenience functions that use the singleton instance


def store_content(content: str, metadata: Dict[str, Any]) -> str:
    """Store content and metadata with a unique content ID.

    Args:
        content: The Markdown content to store.
        metadata: The metadata to include.

    Returns:
        The content ID.
    """
    return _storage_manager.store_content(content, metadata)


def get_content(content_id: str) -> str:
    """Get content by content ID.

    Args:
        content_id: The content ID.

    Returns:
        The content.
    """
    return _storage_manager.get_content(content_id)


def update_metadata(content_id: str, metadata_updates: Dict[str, Any]) -> None:
    """Update metadata for content.

    Args:
        content_id: The content ID.
        metadata_updates: The metadata fields to update.
    """
    try:
        dir_path = _storage_manager._get_content_path(content_id)

        if not os.path.exists(dir_path):
            raise ValueError(f"Content ID not found: {content_id}")

        for filename in os.listdir(dir_path):
            if filename.endswith(".md"):
                file_path = os.path.join(dir_path, filename)
                _storage_manager.update_metadata(file_path, metadata_updates)
                return

        raise ValueError(f"No content file found for ID: {content_id}")
    except Exception as e:
        logger.error(f"Error updating metadata for content ID {content_id}: {e}")
        raise


def list_content() -> Dict[str, Dict[str, Any]]:
    """List all content with their metadata.

    Returns:
        A dictionary mapping content IDs to metadata.
    """
    return _storage_manager.list_content()


def find_files_by_status(status: str, days: Optional[int] = None) -> List[str]:
    """Find files with a specific status.

    Args:
        status: The status to filter by.
        days: If provided, only include files from the last N days.

    Returns:
        A list of file paths matching the criteria.
    """
    return _storage_manager.find_files_by_status(status, days)


def cleanup_old_files(ttl_days: Optional[int] = None) -> int:
    """Delete files older than the TTL.

    Args:
        ttl_days: The TTL in days. If None, uses the default from config.

    Returns:
        The number of files deleted.
    """
    return _storage_manager.cleanup_old_files(ttl_days)
