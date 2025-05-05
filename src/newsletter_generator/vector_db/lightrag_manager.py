"""LightRAG vector database manager for the newsletter generator.

This module integrates LightRAG for vector database functionality, providing
efficient storage and retrieval of content embeddings.
"""

import os
from typing import Dict, Any, List, Optional, Union, Tuple

import numpy as np
from openai import OpenAI
import lightrag

from newsletter_generator.utils.logging_utils import get_logger
from newsletter_generator.utils.config import CONFIG, get_openai_api_key

logger = get_logger("vector_db.lightrag_manager")


class LightRAGManager:
    """Manages vector database operations using LightRAG.
    
    This class provides an interface to the LightRAG vector database for
    storing, retrieving, and searching content embeddings.
    """
    
    def __init__(self, data_dir: Optional[str] = None):
        """Initialise the LightRAG manager.
        
        Args:
            data_dir: The directory to store vector database files. If None,
                uses the default from config.
        """
        self.data_dir = data_dir or os.path.join(CONFIG.get("DATA_DIR", "data"), "vectors")
        self.embedding_model = CONFIG.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
        
        os.makedirs(self.data_dir, exist_ok=True)
        
        self.openai_client = OpenAI(api_key=get_openai_api_key())
        
        self.db = self._initialise_db()
        
        logger.info(f"Initialised LightRAG manager with data directory: {self.data_dir}")
    
    def _initialise_db(self) -> Any:
        """Initialise the LightRAG database.
        
        Returns:
            The initialised LightRAG database instance.
        """
        try:
            db = lightrag.VectorDB(
                storage_path=self.data_dir,
                dimension=1536,  # Dimension for text-embedding-3-small
                metric="cosine",
            )
            return db
        except Exception as e:
            logger.error(f"Error initialising LightRAG database: {e}")
            raise
    
    def _generate_embedding(self, text: str) -> List[float]:
        """Generate an embedding for text using OpenAI's API.
        
        Args:
            text: The text to generate an embedding for.
            
        Returns:
            The embedding as a list of floats.
            
        Raises:
            Exception: If there's an error generating the embedding.
        """
        try:
            max_chars = 8000  # Approximate limit
            if len(text) > max_chars:
                logger.warning(f"Truncating text from {len(text)} to {max_chars} characters")
                text = text[:max_chars]
            
            response = self.openai_client.embeddings.create(
                model=self.embedding_model,
                input=text,
            )
            
            embedding = response.data[0].embedding
            return embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise
    
    def add_document(
        self, document_id: str, text: str, metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add a document to the vector database.
        
        Args:
            document_id: A unique identifier for the document.
            text: The text content of the document.
            metadata: Optional metadata to store with the document.
            
        Raises:
            Exception: If there's an error adding the document.
        """
        try:
            embedding = self._generate_embedding(text)
            
            self.db.add(
                ids=[document_id],
                embeddings=[embedding],
                metadatas=[metadata or {}],
            )
            
            logger.info(f"Added document {document_id} to vector database")
        except Exception as e:
            logger.error(f"Error adding document {document_id} to vector database: {e}")
            raise
    
    def search(
        self, query: str, limit: int = 5, filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar documents in the vector database.
        
        Args:
            query: The query text to search for.
            limit: The maximum number of results to return.
            filter_metadata: Optional metadata filter to apply to the search.
            
        Returns:
            A list of dictionaries containing document IDs, scores, and metadata.
            
        Raises:
            Exception: If there's an error searching the database.
        """
        try:
            query_embedding = self._generate_embedding(query)
            
            results = self.db.search(
                query_embedding=query_embedding,
                limit=limit,
                filter=filter_metadata,
            )
            
            formatted_results = []
            for i, (doc_id, score) in enumerate(zip(results.ids[0], results.distances[0])):
                formatted_results.append({
                    "id": doc_id,
                    "score": score,
                    "metadata": results.metadatas[0][i] if results.metadatas else {},
                })
            
            logger.info(f"Found {len(formatted_results)} results for query: {query[:50]}...")
            return formatted_results
        except Exception as e:
            logger.error(f"Error searching vector database: {e}")
            raise
    
    def delete_document(self, document_id: str) -> None:
        """Delete a document from the vector database.
        
        Args:
            document_id: The ID of the document to delete.
            
        Raises:
            Exception: If there's an error deleting the document.
        """
        try:
            self.db.delete(ids=[document_id])
            logger.info(f"Deleted document {document_id} from vector database")
        except Exception as e:
            logger.error(f"Error deleting document {document_id} from vector database: {e}")
            raise
    
    def update_document(
        self, document_id: str, text: str, metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Update a document in the vector database.
        
        Args:
            document_id: The ID of the document to update.
            text: The new text content of the document.
            metadata: Optional new metadata for the document.
            
        Raises:
            Exception: If there's an error updating the document.
        """
        try:
            self.delete_document(document_id)
            
            self.add_document(document_id, text, metadata)
            
            logger.info(f"Updated document {document_id} in vector database")
        except Exception as e:
            logger.error(f"Error updating document {document_id} in vector database: {e}")
            raise


vector_db = None

def get_vector_db():
    """Get or create the singleton vector database instance.
    
    Returns:
        The LightRAGManager instance.
    """
    global vector_db
    if vector_db is None:
        try:
            vector_db = LightRAGManager()
        except Exception as e:
            logger.error(f"Error creating LightRAGManager: {e}")
            raise
    return vector_db


def add_document(
    document_id: str, text: str, metadata: Optional[Dict[str, Any]] = None
) -> None:
    """Add a document to the vector database.
    
    This is a convenience function that uses the singleton vector_db instance.
    
    Args:
        document_id: A unique identifier for the document.
        text: The text content of the document.
        metadata: Optional metadata to store with the document.
    """
    return get_vector_db().add_document(document_id, text, metadata)


def search(
    query: str, limit: int = 5, filter_metadata: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """Search for similar documents in the vector database.
    
    This is a convenience function that uses the singleton vector_db instance.
    
    Args:
        query: The query text to search for.
        limit: The maximum number of results to return.
        filter_metadata: Optional metadata filter to apply to the search.
        
    Returns:
        A list of dictionaries containing document IDs, scores, and metadata.
    """
    return get_vector_db().search(query, limit, filter_metadata)


def delete_document(document_id: str) -> None:
    """Delete a document from the vector database.
    
    This is a convenience function that uses the singleton vector_db instance.
    
    Args:
        document_id: The ID of the document to delete.
    """
    return get_vector_db().delete_document(document_id)


def update_document(
    document_id: str, text: str, metadata: Optional[Dict[str, Any]] = None
) -> None:
    """Update a document in the vector database.
    
    This is a convenience function that uses the singleton vector_db instance.
    
    Args:
        document_id: The ID of the document to update.
        text: The new text content of the document.
        metadata: Optional new metadata for the document.
    """
    return get_vector_db().update_document(document_id, text, metadata)
