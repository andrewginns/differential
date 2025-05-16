# Vector Search Documentation

This document explains how Differential uses vector search to enable semantic content discovery.

## Architecture

The vector search functionality is built on LightRAG, which provides efficient storage and retrieval of content embeddings. The integration between Differential's content-addressed storage and the vector database is handled by the Storage Vector Integration Layer.

```mermaid
flowchart TD
    A[Content Storage] -->|Hooks| B[Storage Vector Integration]
    B -->|Add/Update/Delete| C[LightRAG Vector DB]
    D[OpenAI API] -->|Generate Embeddings| B
    E[CLI Commands] -->|Manage Index| B
    F[User Queries] -->|Search| G[LightRAG Manager]
    G -->|Query| C
    H[LightRAG Web UI] -->|Visualize| C
    
    subgraph "Storage System"
    A
    end
    
    subgraph "Vector Search System"
    B
    C
    G
    end
    
    subgraph "User Interfaces"
    E
    F
    H
    end
```

## Integration Flow

When content is processed in Differential, it's automatically indexed in the vector database:

```mermaid
sequenceDiagram
    participant User
    participant Storage as Storage Manager
    participant Hooks as Integration Hooks
    participant Integration as Storage Vector Integration
    participant OpenAI as OpenAI API
    participant VectorDB as LightRAG Vector DB
    
    User->>Storage: Add new content
    Storage->>Storage: Store content with metadata
    Storage->>Hooks: Trigger post_save_hook
    Hooks->>Integration: sync_content(content_id)
    Integration->>Storage: Get content and metadata
    Integration->>Integration: Prepare metadata for vector DB
    Integration->>OpenAI: Generate embedding
    OpenAI-->>Integration: Return embedding
    Integration->>VectorDB: Add document with embedding
    VectorDB-->>Integration: Confirm addition
    Integration-->>Hooks: Return success
    Hooks-->>Storage: Complete hook
    Storage-->>User: Return content_id
```

## Content Update Flow

When content is updated, the vector database is automatically updated as well:

```mermaid
sequenceDiagram
    participant User
    participant Storage as Storage Manager
    participant Hooks as Integration Hooks
    participant Integration as Storage Vector Integration
    participant VectorDB as LightRAG Vector DB
    
    User->>Storage: Update content metadata
    Storage->>Storage: Update metadata in file
    Storage->>Hooks: Trigger post_update_hook
    Hooks->>Integration: sync_content(content_id)
    Integration->>Storage: Get updated content and metadata
    Integration->>Integration: Prepare metadata for vector DB
    Integration->>VectorDB: Update document
    VectorDB-->>Integration: Confirm update
    Integration-->>Hooks: Return success
    Hooks-->>Storage: Complete hook
    Storage-->>User: Confirm update
```

## Content Deletion Flow

When content is deleted, it's also removed from the vector database:

```mermaid
sequenceDiagram
    participant User
    participant Storage as Storage Manager
    participant Hooks as Integration Hooks
    participant Integration as Storage Vector Integration
    participant VectorDB as LightRAG Vector DB
    
    User->>Storage: Delete content
    Storage->>Hooks: Trigger pre_delete_hook
    Hooks->>Integration: delete_content_index(content_id)
    Integration->>VectorDB: Delete document
    VectorDB-->>Integration: Confirm deletion
    Integration-->>Hooks: Return success
    Hooks-->>Storage: Complete hook
    Storage->>Storage: Delete content file
    Storage-->>User: Confirm deletion
```

## Search Flow

Users can search for content semantically:

```mermaid
flowchart LR
    A[User Query] -->|search()| B[LightRAG Manager]
    B -->|Generate Embedding| C[OpenAI API]
    C -->|Return Embedding| B
    B -->|Query with Embedding| D[LightRAG Vector DB]
    D -->|Return Similar Documents| B
    B -->|Format Results| E[Search Results]
    E -->|Display to User| F[User Interface]
```

## Using the Vector Database

### Searching for Content

```python
from newsletter_generator.vector_db.lightrag_manager import search

# Basic search
results = search("artificial intelligence trends", limit=5)

# Search with metadata filters
results = search(
    "machine learning", 
    limit=3, 
    filter_metadata={"category": "Technology"}
)

# Process search results
for result in results:
    print(f"Document ID: {result['id']}")
    print(f"Similarity Score: {result['score']}")
    print(f"Title: {result['metadata'].get('title', 'No title')}")
    print(f"URL: {result['metadata'].get('url', 'No URL')}")
    print("---")
```

### Managing the Index via CLI

```bash
# Index all content in the storage system
uv run -m newsletter_generator.cli.vector_index index-all

# Index specific content by ID
uv run -m newsletter_generator.cli.vector_index index <content_id>

# Update specific content in the index
uv run -m newsletter_generator.cli.vector_index update <content_id>

# Delete specific content from the index
uv run -m newsletter_generator.cli.vector_index delete <content_id>
```

### Using the LightRAG Web UI

LightRAG provides a built-in web interface for exploring your content:

```bash
# Start the LightRAG web server
lightrag serve --storage-path data/vectors
```

Then open your browser to http://localhost:8000 to explore your content.

## Technical Details

### Embedding Model

By default, Differential uses OpenAI's `text-embedding-3-small` model for generating embeddings. This model produces 1536-dimensional embeddings that capture the semantic meaning of text.

### Vector Database Configuration

The LightRAG vector database is configured with the following parameters:

- **Dimension**: 1536 (matching the embedding model)
- **Metric**: Cosine similarity
- **Storage Path**: `data/vectors` (configurable)

### Metadata Transformation

When content is indexed, the following metadata fields are included:

- `title`: The title of the content
- `url`: The source URL
- `source_type`: The type of content (html, pdf, youtube)
- `date_added`: When the content was added
- `content_id`: The unique identifier for the content
- `url_hash`: The hash of the URL for deduplication
- `category`: The category of the content (from AI processing)
- `summary`: A summary of the content (from AI processing)
- `tags`: Tags associated with the content (from AI processing)
