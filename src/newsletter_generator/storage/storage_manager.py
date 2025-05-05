"""Storage manager for the newsletter generator.

This module handles the reading and writing of processed content and associated
metadata to the local file system.
"""

import os
import hashlib
import datetime
import yaml
import uuid
from typing import Dict, Any, List, Optional, Tuple

from newsletter_generator.utils.logging_utils import get_logger
from newsletter_generator.utils.config import CONFIG
from newsletter_generator.utils.deduplication import (
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

    def _generate_file_path(self, url: str, source_type: str) -> str:
        """Generate a file path for a URL.

        Args:
            url: The source URL.
            source_type: The content type (html, pdf, youtube).

        Returns:
            The file path to store the content at.
        """
        url_hash = hashlib.md5(url.encode()).hexdigest()[:10]

        today = datetime.datetime.now().strftime("%Y-%m-%d")

        day_dir = os.path.join(self.data_dir, today)
        os.makedirs(day_dir, exist_ok=True)

        filename = f"{source_type}_{url_hash}.md"

        return os.path.join(day_dir, filename)

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

        # Write the content to a file
        file_path = self.write_content(content, metadata)

        # Map content_id to file_path in the content registry
        self._update_content_registry(content_id, file_path)

        # Update our indices
        self.url_hash_index[url_hash] = content_id
        self.fingerprint_index[content_fingerprint] = content_id

        return content_id

    def _update_content_registry(self, content_id: str, file_path: str) -> None:
        """Update the content registry with a mapping from content ID to file path.

        Args:
            content_id: The content ID.
            file_path: The path to the content file.
        """
        registry_path = os.path.join(self.data_dir, "content_registry.yaml")

        registry = {}
        if os.path.exists(registry_path):
            try:
                with open(registry_path, "r", encoding="utf-8") as f:
                    registry = yaml.safe_load(f) or {}
            except Exception as e:
                logger.error(f"Error reading content registry: {e}")

        # Check if this file path already exists in the registry
        for existing_id, existing_path in registry.items():
            if existing_path == file_path and existing_id != content_id:
                logger.warning(
                    f"Duplicate file path detected: {file_path}. Existing content ID: {existing_id}"
                )
                # Replace the old entry
                registry.pop(existing_id)
                logger.info(f"Removed duplicate entry with content ID: {existing_id}")
                break

        registry[content_id] = file_path

        try:
            with open(registry_path, "w", encoding="utf-8") as f:
                yaml.dump(registry, f, default_flow_style=False)

            logger.debug(f"Updated content registry for ID {content_id}")
        except Exception as e:
            logger.error(f"Error updating content registry: {e}")

    def get_content(self, content_id: str) -> str:
        """Get content by content ID.

        Args:
            content_id: The content ID.

        Returns:
            The content.

        Raises:
            ValueError: If the content ID is not found.
        """
        registry_path = os.path.join(self.data_dir, "content_registry.yaml")

        if not os.path.exists(registry_path):
            raise ValueError(f"Content ID not found: {content_id}")

        try:
            with open(registry_path, "r", encoding="utf-8") as f:
                registry = yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"Error reading content registry: {e}")
            raise

        if content_id not in registry:
            raise ValueError(f"Content ID not found: {content_id}")

        file_path = registry[content_id]

        content, _ = self.read_content(file_path)
        return content

    def list_content(self) -> Dict[str, Dict[str, Any]]:
        """List all content with their metadata.

        Returns:
            A dictionary mapping content IDs to metadata.
        """
        registry_path = os.path.join(self.data_dir, "content_registry.yaml")

        if not os.path.exists(registry_path):
            return {}

        try:
            with open(registry_path, "r", encoding="utf-8") as f:
                registry = yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"Error reading content registry: {e}")
            return {}

        result = {}
        for content_id, file_path in registry.items():
            try:
                _, metadata = self.read_content(file_path)
                result[content_id] = metadata
            except Exception as e:
                logger.warning(f"Error reading metadata for content ID {content_id}: {e}")

        return result

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
        if "url" not in metadata:
            raise ValueError("Metadata must include 'url'")

        if "source_type" not in metadata:
            raise ValueError("Metadata must include 'source_type'")

        if "ingested_at" not in metadata:
            metadata["ingested_at"] = datetime.datetime.now().isoformat()

        if "status" not in metadata:
            metadata["status"] = "pending_ai"

        file_path = self._generate_file_path(metadata["url"], metadata["source_type"])

        try:
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
            date_dirs = [
                d
                for d in os.listdir(self.data_dir)
                if os.path.isdir(os.path.join(self.data_dir, d))
                and d.count("-") == 2  # Simple check for date format
            ]

            date_dirs.sort(reverse=True)

            if days is not None:
                cutoff_date = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime(
                    "%Y-%m-%d"
                )
                date_dirs = [d for d in date_dirs if d >= cutoff_date]

            for date_dir in date_dirs:
                dir_path = os.path.join(self.data_dir, date_dir)
                for filename in os.listdir(dir_path):
                    if not filename.endswith(".md"):
                        continue

                    file_path = os.path.join(dir_path, filename)
                    try:
                        _, metadata = self.read_content(file_path)
                        if metadata.get("status") == status:
                            matching_files.append(file_path)
                    except Exception as e:
                        logger.warning(f"Error reading metadata from {file_path}: {e}")

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
            date_dirs = [
                d
                for d in os.listdir(self.data_dir)
                if os.path.isdir(os.path.join(self.data_dir, d))
                and d.count("-") == 2  # Simple check for date format
            ]

            for date_dir in date_dirs:
                if date_dir < cutoff_str:
                    dir_path = os.path.join(self.data_dir, date_dir)
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
    registry_path = os.path.join(_storage_manager.data_dir, "content_registry.yaml")

    if not os.path.exists(registry_path):
        raise ValueError(f"Content ID not found: {content_id}")

    try:
        with open(registry_path, "r", encoding="utf-8") as f:
            registry = yaml.safe_load(f) or {}
    except Exception as e:
        logger.error(f"Error reading content registry: {e}")
        raise

    if content_id not in registry:
        raise ValueError(f"Content ID not found: {content_id}")

    file_path = registry[content_id]

    _storage_manager.update_metadata(file_path, metadata_updates)


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
