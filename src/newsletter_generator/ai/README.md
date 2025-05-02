# Newsletter Generator - AI Processing

This module handles the AI-powered processing of technical content for the newsletter generator. It uses PydanticAI to interface with LLM models (OpenAI and Gemini) for content processing.

## Newsletter Generation Process

1. **Content Categorization**
   - Analyzes technical content and categorizes it into primary and secondary categories
   - Assigns relevant tags to each piece of content
   - Provides a confidence score for categorization

2. **Technical Relevance Evaluation**
   - Assesses how relevant the content is for technical professionals
   - Evaluates technical depth, novelty, practical applicability, and educational value
   - Generates a relevance score between 0.0 and 1.0

3. **Insight Extraction**
   - Identifies 3-5 key technical insights from the content
   - Focuses on novel approaches, performance improvements, innovative solutions, and emerging trends
   - Presents insights as concise, actionable information

4. **Content Summarization**
   - Creates concise, informative summaries of technical content
   - Highlights main technical concepts, key features, and potential applications
   - Maintains technical accuracy while removing marketing language

5. **Newsletter Section Generation**
   - Formats content into engaging newsletter sections
   - Includes catchy introductions, concise summaries, and calls to action
   - Outputs properly formatted Markdown with appropriate headings and formatting

## Checkpointing and Fault Tolerance

Each step of the newsletter generation process is automatically saved to disk in a dedicated subfolder:

- All outputs are stored in a folder structure: `newsletter_output/<newsletter_id>/`
- Each processing step saves its result to a separate JSON file (e.g., `categorization.json`, `insights.json`)
- If a process fails midway, it can be resumed by using the same `newsletter_id` in subsequent calls
- The system automatically uses cached results unless `force_refresh=True` is specified

This provides fault tolerance against:
- API failures when communicating with LLM providers
- Process interruptions
- Application crashes

### Newsletter IDs

Each piece of content is assigned a unique `newsletter_id`:
- Automatically generated as an MD5 hash of the content (by default)
- Can be manually specified for better tracking and organization
- All outputs for a specific newsletter are stored in its dedicated folder

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
    categorize_content,
    summarize_content,
    generate_insights,
    evaluate_relevance,
    generate_newsletter_section
)

# Process an article with automatic checkpointing
newsletter_id = "tech_news_2023_06_15"  # Optional custom ID
category_info = categorize_content(article_text, newsletter_id=newsletter_id)
relevance = evaluate_relevance(article_text, newsletter_id=newsletter_id)
insights = generate_insights(article_text, newsletter_id=newsletter_id)
summary = summarize_content(article_text, max_length=200, newsletter_id=newsletter_id)
section = generate_newsletter_section(
    article_title, 
    article_text, 
    category_info["primary_category"],
    newsletter_id=newsletter_id
)

# Force regeneration of a specific step
insights = generate_insights(article_text, newsletter_id=newsletter_id, force_refresh=True)
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