# Content-Addressed Storage System

This document describes the content-addressed storage system used by Differential to store and retrieve processed content.

## Overview

Differential uses a content-addressed storage system to efficiently store, retrieve, and deduplicate content from various sources. This approach provides several advantages over traditional date-based storage:

- **Single source of truth**: The file system itself serves as the authoritative record
- **Predictable paths**: Content locations can be derived directly from content IDs
- **Efficient lookups**: Fast retrieval without requiring separate registry files
- **Improved reliability**: Reduced risk of inconsistencies between registry and file system

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

## Deduplication Mechanism

The storage system implements two levels of deduplication:

1. **URL-based deduplication**: Prevents processing the same URL multiple times
   - URLs are normalised to remove tracking parameters
   - A URL hash index maps URL hashes to content IDs

2. **Content-based deduplication**: Prevents storing similar content from different URLs
   - Content is fingerprinted based on significant words
   - A fingerprint index maps content fingerprints to content IDs
   - Jaccard similarity is used to detect similar content

## Caching System

The storage system integrates with a unified caching interface that provides:

- **Atomic file operations**: Prevents partial updates and corruption
- **Transaction-like operations**: Ensures consistency during critical updates
- **Error recovery**: Handles common error conditions automatically

## Technical Implementation

The storage system is implemented in the following files:

- `storage_manager.py`: Core storage functionality
- `caching.py`: Unified caching interface

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
