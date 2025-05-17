# Newsletter Generator - LLM Processing

This module handles the LLM-powered processing of technical content for the newsletter generator. It uses PydanticAI to interface with LLM models (OpenAI and Gemini) for content processing.

## Newsletter Generation Process

1. **Content Categorisation**
   - Analyses technical content and categorises it into primary and secondary categories
   - Assigns relevant tags to each piece of content
   - Provides a confidence score for categorisation

2. **Technical Relevance Evaluation**
   - Assesses how relevant the content is for technical professionals
   - Evaluates technical depth, novelty, practical applicability, and educational value
   - Generates a relevance score between 0.0 and 1.0

3. **Insight Extraction**
   - Identifies 3-5 key technical insights from the content
   - Focuses on novel approaches, performance improvements, innovative solutions, and emerging trends
   - Presents insights as concise, actionable information

4. **Content Summarisation**
   - Creates concise, informative summaries of technical content
   - Highlights main technical concepts, key features, and potential applications
   - Maintains technical accuracy while removing marketing language

5. **Newsletter Section Generation**
   - Formats content into engaging newsletter sections
   - Includes catchy introductions, concise summaries, and calls to action
   - Outputs properly formatted Markdown with appropriate headings and formatting

6. **Newsletter Introduction Generation**
   - Creates an engaging introduction for the entire newsletter
   - Highlights key themes and categories across all content
   - Sets the tone and encourages readers to explore the different sections

## Checkpointing and Fault Tolerance

Each step of the newsletter generation process is automatically saved to disk in a dedicated subfolder:

- All outputs are stored in a folder structure: `newsletter_cache/<cache_id>/`
- Each processing step saves its result to a separate JSON file (e.g., `categorisation.json`, `insights.json`)
- If a process fails midway, it can be resumed by using the same `cache_id` in subsequent calls
- The system automatically uses cached results unless `force_refresh=True` is specified

This provides fault tolerance against:
- API failures when communicating with LLM providers
- Process interruptions
- Application crashes

### Cache IDs

Each piece of content is assigned a unique `cache_id`:
- Automatically generated as an MD5 hash of the content (by default)
- Can be manually specified for better tracking and organisation
- All outputs for a specific content are stored in its dedicated folder

### Logging and Monitoring

The system provides detailed logging about cache operations and processing status:

- **Cache Operations**:
  - `✅ CACHE HIT`: When cached data is successfully found and loaded
  - `❓ CACHE MISS`: When no cached data exists for a requested step
  - `🔄 CACHE BYPASS`: When caching is explicitly bypassed with `force_refresh=True`
  - `💾 CACHE SAVED`: When data is successfully saved to cache
  - `❌ CACHE ERROR`: When there's an error loading from or saving to cache

- **Processing Status**:
  - `🔍 PROCESSING`: When a processing step begins with an LLM
  - `✅ COMPLETED`: When a processing step completes successfully
  - `❌ ERROR`: When a processing step fails

These detailed logs help monitor the system's performance and quickly identify any issues that may arise during newsletter generation.

## Usage

The module provides both an `AIProcessor` class and convenience functions for direct use:

```python
from newsletter_generator.ai.processor import (
    categorise_content,
    summarise_content,
    generate_insights,
    evaluate_relevance,
    generate_newsletter_section,
    generate_newsletter_introduction
)

# Process an article with automatic checkpointing
cache_id = "tech_news_2023_06_15"  # Optional custom ID
category_info = categorise_content(article_text, cache_id=cache_id)
relevance = evaluate_relevance(article_text, cache_id=cache_id)
insights = generate_insights(article_text, cache_id=cache_id)
summary = summarise_content(article_text, max_length=200, cache_id=cache_id)
section = generate_newsletter_section(
    article_title, 
    article_text, 
    category_info["primary_category"],
    max_length=300,
    cache_id=cache_id
)

# Generate an introduction for the entire newsletter
introduction = generate_newsletter_introduction(
    categories=["AI", "Frontend", "Cloud Computing"],
    total_items=12,
    content_summary="Summary of the newsletter content",
    max_length=150,
    cache_id="newsletter_2023_06_15"
)

# Force regeneration of a specific step
insights = generate_insights(article_text, cache_id=cache_id, force_refresh=True)
```

## Configuration

The default model provider can be set in the application configuration:

```
MODEL_PROVIDER=gemini  # or openai
```

You can also explicitly specify the provider and output directory when getting the AI processor:

```python
from newsletter_generator.ai.processor import get_ai_processor, ModelProvider

processor = get_ai_processor(
    provider=ModelProvider.OPENAI,
    output_dir="custom_newsletter_output"
)
```

# AI Module

This module contains components for integrating with Large Language Models (LLMs) for processing newsletter content.

## Components

- `processor.py`: The main interface for interacting with LLMs, providing functions for categorisation, summarisation, and content generation.

## Prompts Management

The `prompts` package contains versioned prompt templates for different AI agents, organized by functionality. Each prompt type is maintained in its own directory with versioned implementations.

### Directory Structure

```
prompts/
├── __init__.py
├── categorisation/
│   ├── __init__.py
│   ├── v1.py
│   └── v2.py (when new versions are added)
├── insights/
├── introduction/
├── relevance/ 
├── section/
├── summary/
└── task/
```

### Versioning Strategy

Each prompt category follows a consistent versioning approach:

1. **Version-based Files**: Each version of a prompt is stored in its own Python file (e.g., `v1.py`, `v2.py`)
2. **Consistent Interface**: All versions maintain the same interface - either exposing a `prompt` variable or a function like `get_prompt()`
3. **Independent Evolution**: Versions evolve independently, allowing for experimentation without affecting production code
4. **Clear Documentation**: Each version file includes docstrings explaining its purpose and any changes from previous versions

### Importing Prompts

Prompts are imported by specifying the exact version needed:

```python
# Import specific prompt versions
from newsletter_generator.ai.prompts.categorisation import v1 as categorisation

# Use in code
agent = Agent(
    model, 
    system_prompt=categorisation.prompt
)

# For prompts that require customization
from newsletter_generator.ai.prompts.section import v1 as section

agent = Agent(
    model,
    system_prompt=section.get_prompt(max_length=300)
)
```

### Benefits of Versioning

This versioning approach provides several advantages:

1. **Stability**: Production code can rely on specific prompt versions that are known to work well
2. **Experimentation**: New prompt versions can be developed and tested without disrupting existing functionality
3. **Evaluation**: Different prompt versions can be benchmarked against each other to measure improvements
4. **History**: The evolution of prompts is preserved, documenting the refinement process
5. **Rollback**: If a new prompt version performs poorly, the system can easily revert to a previous version

### Creating New Prompt Versions

To create a new version of a prompt:

1. Create a new file (e.g., `v2.py`) in the appropriate subdirectory
2. Implement the same interface as the previous version
3. Document the changes and improvements in the file's docstring
4. Import the new version where needed: `from newsletter_generator.ai.prompts.categorisation import v2 as categorisation`

This structured approach to prompt management ensures that the system can evolve while maintaining reliability and providing clear documentation of prompt engineering decisions.
