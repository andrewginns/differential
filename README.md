## Vector Search and Content Discovery

Differential includes a vector database integration using LightRAG that enables:

1. **Semantic Search**: Find content based on meaning, not just keywords
2. **Content Similarity**: Discover related content across different sources
3. **Content Clustering**: Group similar content for better organization
4. **Web UI for Exploration**: Use LightRAG's built-in web interface to explore content

### Using the Vector Database

The vector database is automatically populated as content is processed. You can:

1. **Search for similar content**:
   ```python
   from newsletter_generator.vector_db.lightrag_manager import search
   
   # Find content similar to a query
   results = search("artificial intelligence trends", limit=5)
   
   # Filter by metadata
   results = search(
       "machine learning", 
       limit=3, 
       filter_metadata={"category": "Technology"}
   )
   ```

2. **Manage the index via CLI**:
   ```bash
   # Index all content
   uv run -m newsletter_generator.cli.vector_index index-all
   
   # Index specific content
   uv run -m newsletter_generator.cli.vector_index index <content_id>
   ```

3. **Use LightRAG's web UI**:
   ```bash
   # Start the LightRAG web server
   lightrag serve --storage-path data/vectors
   ```
   Then open your browser to http://localhost:8000 to explore your content.

For more details on vector search capabilities, see the [Vector Search Documentation](src/newsletter_generator/vector_db/README.md).
