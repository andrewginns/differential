"""Common caching utilities for the newsletter generator.

This module provides a shared interface for caching operations used by
both the content storage system and LLM output caching.
"""

import os
import json
import hashlib
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, Callable, TypeVar, Generic

from newsletter_generator.utils.logging_utils import get_logger

logger = get_logger("utils.caching")

T = TypeVar('T')


class AtomicFileWriter:
    """Writes files atomically to prevent partial updates."""

    @staticmethod
    def write(file_path: str, content: str, encoding: str = "utf-8") -> None:
        """Write content to a file atomically.

        Args:
            file_path: The path to write to.
            content: The content to write.
            encoding: The encoding to use.

        Raises:
            Exception: If there's an error writing the file.
        """
        dir_path = os.path.dirname(file_path)
        os.makedirs(dir_path, exist_ok=True)
        
        temp_path = f"{file_path}.tmp"
        try:
            with open(temp_path, "w", encoding=encoding) as f:
                f.write(content)
                
            if os.path.exists(file_path):
                os.remove(file_path)
                
            os.rename(temp_path, file_path)
            logger.debug(f"Atomically wrote file to {file_path}")
        except Exception as e:
            logger.error(f"Error writing file atomically to {file_path}: {e}")
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
            raise


class Cache(Generic[T]):
    """Generic cache implementation."""

    def __init__(self, base_dir: str):
        """Initialize the cache.

        Args:
            base_dir: Base directory for the cache.
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
    def _get_cache_key(self, content: str) -> str:
        """Generate a hash for the content to use as a cache key.

        Args:
            content: The content to hash.

        Returns:
            A short hash string for the content cache key.
        """
        return hashlib.md5(content.encode("utf-8")).hexdigest()[:10]
        
    def _get_path(self, cache_id: str, name: str) -> Path:
        """Get the path for a cache item.

        Args:
            cache_id: The cache ID.
            name: The name of the cache item.

        Returns:
            The path to the cache item.
        """
        prefix = cache_id[:2]
        cache_dir = self.base_dir / prefix / cache_id
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir / f"{name}.json"
        
    def get(self, cache_id: str, name: str) -> Optional[T]:
        """Get an item from the cache.

        Args:
            cache_id: The cache ID.
            name: The name of the cache item.

        Returns:
            The cached item, or None if not found.
        """
        path = self._get_path(cache_id, name)
        if not path.exists():
            logger.debug(f"Cache miss for {name} (ID: {cache_id})")
            return None
            
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.debug(f"Cache hit for {name} (ID: {cache_id})")
            return data
        except Exception as e:
            logger.warning(f"Error reading cache for {name} (ID: {cache_id}): {e}")
            return None
            
    def set(self, cache_id: str, name: str, data: T) -> None:
        """Set an item in the cache.

        Args:
            cache_id: The cache ID.
            name: The name of the cache item.
            data: The data to cache.
        """
        path = self._get_path(cache_id, name)
        try:
            content = json.dumps(data, indent=2)
            AtomicFileWriter.write(str(path), content)
            logger.debug(f"Cached {name} (ID: {cache_id})")
        except Exception as e:
            logger.error(f"Error writing cache for {name} (ID: {cache_id}): {e}")
            
    def has(self, cache_id: str, name: str) -> bool:
        """Check if an item exists in the cache.

        Args:
            cache_id: The cache ID.
            name: The name of the cache item.

        Returns:
            True if the item exists, False otherwise.
        """
        return self._get_path(cache_id, name).exists()
        
    def delete(self, cache_id: str, name: str) -> bool:
        """Delete an item from the cache.

        Args:
            cache_id: The cache ID.
            name: The name of the cache item.

        Returns:
            True if the item was deleted, False otherwise.
        """
        path = self._get_path(cache_id, name)
        if path.exists():
            try:
                os.remove(path)
                logger.debug(f"Deleted cache for {name} (ID: {cache_id})")
                return True
            except Exception as e:
                logger.error(f"Error deleting cache for {name} (ID: {cache_id}): {e}")
        return False
        
    def clear(self) -> int:
        """Clear all items from the cache.

        Returns:
            The number of items deleted.
        """
        count = 0
        try:
            for item in self.base_dir.glob("**/*.json"):
                try:
                    os.remove(item)
                    count += 1
                except Exception as e:
                    logger.warning(f"Error deleting cache file {item}: {e}")
            logger.info(f"Cleared {count} items from cache")
            return count
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return count


def with_cache(cache: Cache, id_func: Callable[[Any], str], name: str, force_refresh: bool = False):
    """Decorator to cache function results.

    Args:
        cache: The cache to use.
        id_func: Function to generate a cache ID from the function arguments.
        name: The name to use for the cached item.
        force_refresh: Whether to force a refresh of the cache.

    Returns:
        A decorator function.
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            cache_id = id_func(*args, **kwargs)
            
            if not force_refresh and kwargs.get('force_refresh', False) is False:
                cached = cache.get(cache_id, name)
                if cached is not None:
                    return cached
                    
            result = func(*args, **kwargs)
            
            cache.set(cache_id, name, result)
            
            return result
        return wrapper
    return decorator
