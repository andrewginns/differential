"""Tests for the caching module."""

import os
import json
import pytest
import tempfile
import shutil
from pathlib import Path

from newsletter_generator.utils.caching import Cache, AtomicFileWriter, with_cache


@pytest.fixture
def temp_cache_dir():
    """Create a temporary directory for testing caching."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


class TestAtomicFileWriter:
    """Test cases for the AtomicFileWriter class."""

    def test_write_atomically(self, temp_cache_dir):
        """Test writing a file atomically."""
        file_path = os.path.join(temp_cache_dir, "test.txt")
        content = "Test content"

        AtomicFileWriter.write(file_path, content)

        assert os.path.exists(file_path)
        with open(file_path, "r") as f:
            assert f.read() == content

    def test_write_atomically_existing_file(self, temp_cache_dir):
        """Test writing to an existing file atomically."""
        file_path = os.path.join(temp_cache_dir, "test.txt")
        
        with open(file_path, "w") as f:
            f.write("Initial content")
            
        new_content = "New content"
        AtomicFileWriter.write(file_path, new_content)
        
        assert os.path.exists(file_path)
        with open(file_path, "r") as f:
            assert f.read() == new_content


class TestCache:
    """Test cases for the Cache class."""

    def test_init(self, temp_cache_dir):
        """Test initializing the cache."""
        cache = Cache(temp_cache_dir)
        assert os.path.exists(temp_cache_dir)

    def test_get_cache_key(self, temp_cache_dir):
        """Test generating a cache key."""
        cache = Cache(temp_cache_dir)
        key = cache._get_cache_key("test content")
        assert isinstance(key, str)
        assert len(key) == 10

    def test_get_path(self, temp_cache_dir):
        """Test getting a cache path."""
        cache = Cache(temp_cache_dir)
        cache_id = "abcdef1234"
        name = "test"
        
        path = cache._get_path(cache_id, name)
        
        expected_path = Path(temp_cache_dir) / "ab" / "abcdef1234" / "test.json"
        assert path == expected_path

    def test_set_and_get(self, temp_cache_dir):
        """Test setting and getting a cache item."""
        cache = Cache(temp_cache_dir)
        cache_id = "test123"
        name = "test_item"
        data = {"key": "value"}
        
        cache.set(cache_id, name, data)
        result = cache.get(cache_id, name)
        
        assert result == data

    def test_has(self, temp_cache_dir):
        """Test checking if a cache item exists."""
        cache = Cache(temp_cache_dir)
        cache_id = "test123"
        name = "test_item"
        data = {"key": "value"}
        
        assert not cache.has(cache_id, name)
        
        cache.set(cache_id, name, data)
        
        assert cache.has(cache_id, name)

    def test_delete(self, temp_cache_dir):
        """Test deleting a cache item."""
        cache = Cache(temp_cache_dir)
        cache_id = "test123"
        name = "test_item"
        data = {"key": "value"}
        
        cache.set(cache_id, name, data)
        assert cache.has(cache_id, name)
        
        result = cache.delete(cache_id, name)
        
        assert result is True
        assert not cache.has(cache_id, name)

    def test_clear(self, temp_cache_dir):
        """Test clearing the cache."""
        cache = Cache(temp_cache_dir)
        
        cache.set("id1", "item1", {"key": "value1"})
        cache.set("id2", "item2", {"key": "value2"})
        cache.set("id3", "item3", {"key": "value3"})
        
        count = cache.clear()
        
        assert count == 3
        assert not cache.has("id1", "item1")
        assert not cache.has("id2", "item2")
        assert not cache.has("id3", "item3")


def test_with_cache_decorator(temp_cache_dir):
    """Test the with_cache decorator."""
    cache = Cache(temp_cache_dir)
    
    call_count = 0
    
    def id_func(arg):
        return f"test_{arg}"
    
    def original_function(arg):
        nonlocal call_count
        call_count += 1
        return {"result": arg * 2}
    
    decorated_function = with_cache(cache, id_func, "test_result")(original_function)
    
    result1 = decorated_function(5)
    assert result1 == {"result": 10}
    assert call_count == 1
    
    result2 = decorated_function(5)
    assert result2 == {"result": 10}
    assert call_count == 1  # Still 1, function not called again
    
    result3 = decorated_function(10)
    assert result3 == {"result": 20}
    assert call_count == 2
    
    # Call the original function directly
    result4 = original_function(5)
    assert result4 == {"result": 10}
    assert call_count == 3
