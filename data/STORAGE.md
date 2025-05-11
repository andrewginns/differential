# Content-Addressed Storage System

This document describes the content-addressed storage system used by Differential to store and retrieve processed content.

## Overview

Differential uses a content-addressed storage system to efficiently store, retrieve, and deduplicate content from various sources. This approach provides several advantages over traditional date-based storage:

- **Single source of truth**: The file system itself serves as the authoritative record
- **Predictability**: Storage paths are deterministic and derived directly from content IDs
- **Efficient lookups**: Fast retrieval without requiring separate registry files
- **Improved reliability**: Reduced risk of inconsistencies between registry and file system
- **Deduplication**: Identical content is stored only once
- **Integrity**: Content can be verified against its ID
- **Simplicity**: No separate registry or database needed

## Storage Structure

Content is stored using a content-addressed approach with the following path structure:

```
{data_dir}/{content_id[:2]}/{content_id}/{source_type}.md
```

Where:
- `data_dir`: Base directory for all stored content
- `content_id[:2]`: First two characters of the content ID (creates a two-level directory structure)
- `content_id`: Unique identifier for the content
- `source_type`: Type of content (html, pdf, youtube, etc.)

### Example

For content with ID `a1b2c3d4e5f6` and source type `html`, the path would be:

```
{data_dir}/a1/a1b2c3d4e5f6/html.md
```

### Directory Layout

The overall directory structure looks like:

```
data/
├── content/
│   ├── a1/
│   │   └── a1b2c3d4e5f6.../ (content ID directory)
│   │       ├── html.md (processed content)
│   │       └── metadata.yaml (optional metadata)
│   └── b2/
│       └── b2c3d4e5f6.../ (another content ID directory)
│           ├── pdf.md
│           └── metadata.yaml
└── newsletters/
    └── newsletter_2023-01-01.md
```

## Content Format

Each content file is stored as a Markdown file with YAML front matter containing metadata:

```markdown
---
content_id: a1b2c3d4e5f6
url: https://example.com/article
source_type: html
title: Example Article
date_added: 2025-05-10T12:34:56
url_hash: 7890abcdef
content_fingerprint: 1234567890abcdef
status: processed
processed_at: 2025-05-10T12:35:00
---

# Example Article

Article content goes here...
```

Alternatively, content and metadata can be stored separately:

### Content Files

Content is stored in Markdown format with a standardised structure:

```markdown
# Title of the Content

## Source
https://example.com/article

## Content
The actual processed content goes here...
```

### Metadata Files

Metadata can be stored separately in YAML format with information about the content:

```yaml
content_id: a1b2c3d4e5f6...
url: https://example.com/article
title: Title of the Content
source_type: webpage
date_processed: 2023-01-01T12:00:00Z
content_fingerprint: f6e5d4c3b2a1...
status: processed
```

## Deduplication Mechanism

The storage system implements two levels of deduplication:

1. **URL-based deduplication**: Prevents processing the same URL multiple times
   - URLs are normalised to remove tracking parameters
   - A URL hash index maps URL hashes to content IDs

2. **Content-based deduplication**: Prevents storing similar content from different URLs
   - Content is fingerprinted based on significant words
   - A fingerprint index maps content fingerprints to content IDs
   - Jaccard similarity is used to detect similar content

### Content Fingerprinting

Content fingerprinting works by:
1. Extracting significant words from the content
2. Creating a sorted set of these words
3. Generating a hash of the sorted words

This approach is resistant to minor changes in content while still detecting substantial similarities.

## Caching System

The storage system integrates with a unified caching interface that provides:

- **Atomic file operations**: Prevents partial updates and corruption
- **Transaction-like operations**: Ensures consistency during critical updates
- **Error recovery**: Handles common error conditions automatically

## Technical Implementation

The storage system is implemented in the following files:

- `storage_manager.py`: Core storage functionality
- `content_processing.py`: Content processing and deduplication utilities

### Storage Manager API

The `storage_manager.py` module provides a comprehensive API for interacting with the storage system:

- `store_content(url, content, metadata)`: Store content with its metadata
- `get_content(content_id)`: Retrieve content by its ID
- `list_content(days=7, status=None)`: List content processed in the last N days
- `update_metadata(content_id, metadata)`: Update metadata for existing content
- `find_files_by_status(status)`: Find all content with a specific status
- `cleanup_old_files(days=30)`: Remove content older than N days

## Error Handling

The system implements robust error handling:

- **Atomic file operations**: Uses temporary files and atomic renames
- **Comprehensive logging**: Detailed error information for troubleshooting
- **Automatic recovery**: Self-healing for common error conditions
- **Validation**: Checks for data integrity during operations

## Performance Considerations

The content-addressed storage system is optimised for:

- **Read performance**: Fast lookups by content ID
- **Write consistency**: Atomic operations prevent corruption
- **Space efficiency**: Deduplication prevents redundant storage
- **Scalability**: Two-level directory structure prevents directory bloat

## Usage Examples

### Storing Content

```python
from newsletter_generator.storage.storage_manager import store_content

metadata = {
    "title": "Example Article",
    "source_type": "webpage",
    "status": "processed"
}

content_id = store_content(
    url="https://example.com/article",
    content="# Example Article\n\nThis is the content...",
    metadata=metadata
)
```

### Retrieving Content

```python
from newsletter_generator.storage.storage_manager import get_content

content, metadata = get_content(content_id)
```

### Listing Recent Content

```python
from newsletter_generator.storage.storage_manager import list_content

# Get all processed content from the last 7 days
recent_content = list_content(days=7, status="processed")
```
