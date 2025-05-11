"""Tests for the LightRAG vector database manager module."""

import os
import pytest
from unittest.mock import patch, MagicMock

from newsletter_generator.vector_db.lightrag_manager import (
    LightRAGManager,
    add_document,
    search,
    delete_document,
    update_document,
)


@pytest.fixture
def lightrag_manager():
    """Create a LightRAG manager for testing."""
    test_data_dir = "test_vectors"

    with (
        patch("newsletter_generator.vector_db.lightrag_manager.OpenAI") as mock_openai,
        patch("newsletter_generator.vector_db.lightrag_manager.lightrag") as _,
        patch(
            "newsletter_generator.vector_db.lightrag_manager.get_openai_api_key",
            return_value="mock-api-key",
        ),
        patch.object(LightRAGManager, "_initialise_db") as mock_initialise_db,
    ):
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        mock_db = MagicMock()
        mock_initialise_db.return_value = mock_db

        manager = LightRAGManager(data_dir=test_data_dir)

        yield manager

        if os.path.exists(test_data_dir):
            os.rmdir(test_data_dir)


class TestLightRAGManager:
    """Test cases for the LightRAGManager class."""

    def test_init_creates_data_dir(self):
        """Test that the constructor creates the data directory."""
        test_dir = "test_init_vectors"

        if os.path.exists(test_dir):
            os.rmdir(test_dir)

        with (
            patch("newsletter_generator.vector_db.lightrag_manager.OpenAI"),
            patch("newsletter_generator.vector_db.lightrag_manager.lightrag"),
            patch(
                "newsletter_generator.vector_db.lightrag_manager.get_openai_api_key",
                return_value="mock-api-key",
            ),
        ):
            # Create manager and verify it creates the directory
            _ = LightRAGManager(data_dir=test_dir)

            assert os.path.exists(test_dir)
            assert os.path.isdir(test_dir)

            os.rmdir(test_dir)

    @pytest.mark.skip(reason="Requires actual LightRAG API structure")
    def test_initialise_db(self, lightrag_manager):
        """Test initialising the LightRAG database."""
        pass

    @pytest.mark.skip(reason="Requires actual LightRAG API structure")
    def test_initialise_db_error(self, lightrag_manager):
        """Test error handling when initialising the LightRAG database."""
        pass

    def test_generate_embedding(self, lightrag_manager):
        """Test generating an embedding for text."""
        mock_response = MagicMock()
        mock_data = MagicMock()
        mock_data.embedding = [0.1, 0.2, 0.3]
        mock_response.data = [mock_data]

        lightrag_manager.openai_client.embeddings.create.return_value = mock_response

        embedding = lightrag_manager._generate_embedding("Test text")

        assert embedding == [0.1, 0.2, 0.3]
        lightrag_manager.openai_client.embeddings.create.assert_called_once_with(
            model=lightrag_manager.embedding_model,
            input="Test text",
        )

    def test_generate_embedding_truncation(self, lightrag_manager):
        """Test truncation of long text when generating an embedding."""
        mock_response = MagicMock()
        mock_data = MagicMock()
        mock_data.embedding = [0.1, 0.2, 0.3]
        mock_response.data = [mock_data]

        lightrag_manager.openai_client.embeddings.create.return_value = mock_response

        long_text = "a" * 10000  # Text longer than the 8000 character limit

        embedding = lightrag_manager._generate_embedding(long_text)

        assert embedding == [0.1, 0.2, 0.3]
        lightrag_manager.openai_client.embeddings.create.assert_called_once()

        called_args = lightrag_manager.openai_client.embeddings.create.call_args[1]
        assert len(called_args["input"]) == 8000

    def test_generate_embedding_error(self, lightrag_manager):
        """Test error handling when generating an embedding."""
        lightrag_manager.openai_client.embeddings.create.side_effect = Exception("Test error")

        with pytest.raises(Exception, match="Test error"):
            lightrag_manager._generate_embedding("Test text")

    def test_add_document(self, lightrag_manager):
        """Test adding a document to the vector database."""
        with patch.object(lightrag_manager, "_generate_embedding") as mock_generate:
            mock_generate.return_value = [0.1, 0.2, 0.3]

            lightrag_manager.add_document(
                document_id="test_id",
                text="Test text",
                metadata={"key": "value"},
            )

            mock_generate.assert_called_once_with("Test text")
            lightrag_manager.db.add.assert_called_once_with(
                ids=["test_id"],
                embeddings=[[0.1, 0.2, 0.3]],
                metadatas=[{"key": "value"}],
            )

    def test_add_document_no_metadata(self, lightrag_manager):
        """Test adding a document with no metadata."""
        with patch.object(lightrag_manager, "_generate_embedding") as mock_generate:
            mock_generate.return_value = [0.1, 0.2, 0.3]

            lightrag_manager.add_document(
                document_id="test_id",
                text="Test text",
            )

            mock_generate.assert_called_once_with("Test text")
            lightrag_manager.db.add.assert_called_once_with(
                ids=["test_id"],
                embeddings=[[0.1, 0.2, 0.3]],
                metadatas=[{}],
            )

    def test_add_document_error(self, lightrag_manager):
        """Test error handling when adding a document."""
        with patch.object(lightrag_manager, "_generate_embedding") as mock_generate:
            mock_generate.return_value = [0.1, 0.2, 0.3]

            lightrag_manager.db.add.side_effect = Exception("Test error")

            with pytest.raises(Exception, match="Test error"):
                lightrag_manager.add_document(
                    document_id="test_id",
                    text="Test text",
                )

    def test_search(self, lightrag_manager):
        """Test searching for similar documents."""
        with patch.object(lightrag_manager, "_generate_embedding") as mock_generate:
            mock_generate.return_value = [0.1, 0.2, 0.3]

            mock_results = MagicMock()
            mock_results.ids = [["doc1", "doc2"]]
            mock_results.distances = [[0.9, 0.8]]
            mock_results.metadatas = [[{"key1": "value1"}, {"key2": "value2"}]]

            lightrag_manager.db.search.return_value = mock_results

            results = lightrag_manager.search(
                query="Test query",
                limit=2,
                filter_metadata={"status": "processed"},
            )

            mock_generate.assert_called_once_with("Test query")
            lightrag_manager.db.search.assert_called_once_with(
                query_embedding=[0.1, 0.2, 0.3],
                limit=2,
                filter={"status": "processed"},
            )

            assert len(results) == 2
            assert results[0]["id"] == "doc1"
            assert results[0]["score"] == 0.9
            assert results[0]["metadata"] == {"key1": "value1"}
            assert results[1]["id"] == "doc2"
            assert results[1]["score"] == 0.8
            assert results[1]["metadata"] == {"key2": "value2"}

    def test_search_no_metadata(self, lightrag_manager):
        """Test searching with no metadata in results."""
        with patch.object(lightrag_manager, "_generate_embedding") as mock_generate:
            mock_generate.return_value = [0.1, 0.2, 0.3]

            mock_results = MagicMock()
            mock_results.ids = [["doc1", "doc2"]]
            mock_results.distances = [[0.9, 0.8]]
            mock_results.metadatas = None

            lightrag_manager.db.search.return_value = mock_results

            results = lightrag_manager.search(query="Test query")

            assert len(results) == 2
            assert results[0]["metadata"] == {}
            assert results[1]["metadata"] == {}

    def test_search_error(self, lightrag_manager):
        """Test error handling when searching."""
        with patch.object(lightrag_manager, "_generate_embedding") as mock_generate:
            mock_generate.return_value = [0.1, 0.2, 0.3]

            lightrag_manager.db.search.side_effect = Exception("Test error")

            with pytest.raises(Exception, match="Test error"):
                lightrag_manager.search(query="Test query")

    def test_delete_document(self, lightrag_manager):
        """Test deleting a document from the vector database."""
        lightrag_manager.delete_document(document_id="test_id")

        lightrag_manager.db.delete.assert_called_once_with(ids=["test_id"])

    def test_delete_document_error(self, lightrag_manager):
        """Test error handling when deleting a document."""
        lightrag_manager.db.delete.side_effect = Exception("Test error")

        with pytest.raises(Exception, match="Test error"):
            lightrag_manager.delete_document(document_id="test_id")

    def test_update_document(self, lightrag_manager):
        """Test updating a document in the vector database."""
        with (
            patch.object(lightrag_manager, "delete_document") as mock_delete,
            patch.object(lightrag_manager, "add_document") as mock_add,
        ):
            lightrag_manager.update_document(
                document_id="test_id",
                text="Updated text",
                metadata={"key": "updated_value"},
            )

            mock_delete.assert_called_once_with("test_id")
            mock_add.assert_called_once_with("test_id", "Updated text", {"key": "updated_value"})

    def test_update_document_error_on_delete(self, lightrag_manager):
        """Test error handling when updating a document (delete fails)."""
        with patch.object(lightrag_manager, "delete_document") as mock_delete:
            mock_delete.side_effect = Exception("Test error")

            with pytest.raises(Exception, match="Test error"):
                lightrag_manager.update_document(
                    document_id="test_id",
                    text="Updated text",
                )

    def test_update_document_error_on_add(self, lightrag_manager):
        """Test error handling when updating a document (add fails)."""
        with (
            patch.object(lightrag_manager, "delete_document") as mock_delete,
            patch.object(lightrag_manager, "add_document") as mock_add,
        ):
            mock_add.side_effect = Exception("Test error")

            with pytest.raises(Exception, match="Test error"):
                lightrag_manager.update_document(
                    document_id="test_id",
                    text="Updated text",
                )

            mock_delete.assert_called_once_with("test_id")


class TestConvenienceFunctions:
    """Test cases for the convenience functions."""

    def test_add_document_function(self):
        """Test the add_document convenience function."""
        mock_db = MagicMock()
        with patch(
            "newsletter_generator.vector_db.lightrag_manager.get_vector_db", return_value=mock_db
        ):
            add_document(
                document_id="test_id",
                text="Test text",
                metadata={"key": "value"},
            )

            mock_db.add_document.assert_called_once_with("test_id", "Test text", {"key": "value"})

    def test_search_function(self):
        """Test the search convenience function."""
        mock_db = MagicMock()
        mock_db.search.return_value = [{"id": "doc1"}]

        with patch(
            "newsletter_generator.vector_db.lightrag_manager.get_vector_db", return_value=mock_db
        ):
            results = search(
                query="Test query",
                limit=5,
                filter_metadata={"status": "processed"},
            )

            assert results == [{"id": "doc1"}]
            mock_db.search.assert_called_once_with("Test query", 5, {"status": "processed"})

    def test_delete_document_function(self):
        """Test the delete_document convenience function."""
        mock_db = MagicMock()
        with patch(
            "newsletter_generator.vector_db.lightrag_manager.get_vector_db", return_value=mock_db
        ):
            delete_document(document_id="test_id")

            mock_db.delete_document.assert_called_once_with("test_id")

    def test_update_document_function(self):
        """Test the update_document convenience function."""
        mock_db = MagicMock()
        with patch(
            "newsletter_generator.vector_db.lightrag_manager.get_vector_db", return_value=mock_db
        ):
            update_document(
                document_id="test_id",
                text="Updated text",
                metadata={"key": "value"},
            )

            mock_db.update_document.assert_called_once_with(
                "test_id", "Updated text", {"key": "value"}
            )


@pytest.mark.skip(reason="Requires real OpenAI API key and LightRAG setup")
class TestLightRAGManagerIntegration:
    """Integration tests for the LightRAGManager class.

    These tests require a real OpenAI API key and LightRAG setup.
    They are skipped by default.
    """

    def test_real_embedding_generation(self):
        """Test generating a real embedding using OpenAI's API."""
        manager = LightRAGManager(data_dir="integration_test_vectors")

        embedding = manager._generate_embedding("This is a test sentence for embedding.")

        assert len(embedding) == 1536  # text-embedding-3-small dimension

        import shutil

        shutil.rmtree("integration_test_vectors")

    def test_real_document_lifecycle(self):
        """Test the full document lifecycle with real services."""
        manager = LightRAGManager(data_dir="integration_test_vectors")

        manager.add_document(
            document_id="test_doc_1",
            text="This is a test document about artificial intelligence.",
            metadata={"source": "test", "category": "AI"},
        )

        manager.add_document(
            document_id="test_doc_2",
            text="This document discusses machine learning algorithms.",
            metadata={"source": "test", "category": "ML"},
        )

        results = manager.search(query="What is AI?", limit=2)

        assert len(results) > 0

        manager.update_document(
            document_id="test_doc_1",
            text="Updated content about artificial intelligence and its applications.",
            metadata={"source": "test", "category": "AI", "updated": True},
        )

        manager.delete_document(document_id="test_doc_2")

        import shutil

        shutil.rmtree("integration_test_vectors")


if __name__ == "__main__":
    pytest.main()
