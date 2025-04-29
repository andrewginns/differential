# Newsletter Generator

An automated system for generating weekly technical newsletters from shared URLs.

## Features
- Ingests content from URLs shared in WhatsApp
- Processes web pages, PDFs, and YouTube videos
- Uses AI to categorize and summarize content
- Assembles a weekly newsletter in Markdown format

## Setup
1. Clone the repository
2. Install dependencies: `uv sync`

## Configuration
Create a `.env` file with the following variables:
```
OPENAI_API_KEY=your_openai_api_key
WHATSAPP_VERIFY_TOKEN=your_secure_random_token
```

### Generating a WhatsApp Verify Token
The WHATSAPP_VERIFY_TOKEN is a secure string used to verify webhook requests from Meta:

1. Create a secure random string. For example, using Python:
   ```
   python -c "import secrets; print(secrets.token_hex(16))"
   ```
2. Add this token to your `.env` file as WHATSAPP_VERIFY_TOKEN
3. Use the same token in the Meta Developer Portal webhook configuration

## Local Development with ngrok
To test WhatsApp webhooks during local development:

1. Install ngrok:
   ```
   uv add ngrok
   ```
   Or download from https://ngrok.com/download

2. Start the webhook server:
   ```
   uv run src/newsletter_generator/whatsapp/webhook_receiver.py
   ```

3. In a separate terminal, create a tunnel to your local server:
   ```
   ngrok http 8000
   ```

4. Copy the HTTPS URL from ngrok output (e.g., https://a1b2c3d4.ngrok.io)

5. Configure your webhook in the Meta Developer Portal:
   - Callback URL: `https://a1b2c3d4.ngrok.io/webhook`
   - Verify Token: The same token from your `.env` file
   - Subscribe to: `messages`

6. Meta will send a verification request to confirm your endpoint is working

Note: The ngrok URL changes each time you restart ngrok unless you have a paid plan.

## Usage

1. Start the WhatsApp webhook server:
   ```
   uv run src/newsletter_generator/whatsapp/webhook_receiver.py
   ```

2. Tunnel local server using ngrok (in a separate terminal):
   ```
   ngrok http 8000
   ```

3. Share URLs in your WhatsApp group. The system will:
   - Receive URLs via WhatsApp webhook
   - Automatically extract and validate URLs from messages
   - Determine content type (HTML, PDF, YouTube)
   - Fetch and process content based on its type
   - Store processed content with metadata in the filesystem

4. Generate a weekly newsletter:
   ```
   # Generate using last 7 days of content (default)
   uv run -m newsletter_generator.newsletter.assembler

   # Or specify custom number of days
   uv run -m newsletter_generator.newsletter.assembler --days 5
   ```

5. Find generated newsletters in the `data/newsletters` directory.

## How It Works

### Ingestion Pipeline

1. **URL Reception**: URLs are received through the WhatsApp webhook.
2. **Content Type Detection**: System automatically detects if the URL is a webpage, PDF, or YouTube video.
3. **Content Fetching**: Content is fetched from the source using specialized fetchers for each content type.
4. **Content Parsing**: Raw content is parsed and converted to a structured format.
5. **Content Standardization**: All content is standardized to a uniform format for storage.
6. **Storage**: Processed content is stored with relevant metadata for later use.

### Newsletter Generation

1. **Content Collection**: The system collects all content ingested in the last week.
2. **AI Processing**: Content is categorized and summarized using AI.
3. **Content Organization**: Content is organized by category.
4. **Newsletter Assembly**: A markdown document is assembled with all processed content.

## Customizing the Newsletter

You can customize the newsletter generation by modifying the following:

- Content categorization: Update AI prompts in the `ai/processor.py` file
- Newsletter template: Modify the `assemble_newsletter` method in `newsletter/assembler.py`
- Content sources: Currently supports web pages, PDFs, and YouTube videos

## Troubleshooting

- Check the log file `newsletter_generator.log` for detailed information
- Ensure your WhatsApp webhook is properly configured in the Meta Developer Portal
- Verify that your `.env` file contains the required API keys and tokens
- If URLs are not being processed, check the connection between the webhook and the ingestion pipeline

## Testing the Ingestion Pipeline

You can test the ingestion pipeline directly without setting up the WhatsApp webhook:

```
# Test with a single URL
uv run src/newsletter_generator/ingestion/test_ingest.py https://example.com

# Test with multiple URLs
uv run src/newsletter_generator/ingestion/test_ingest.py https://example.com https://youtube.com/watch?v=12345 https://example.org/document.pdf
```

This allows you to:
- Verify the ingestion pipeline is working correctly
- Test different content types (HTML, PDF, YouTube)
- Debug issues with content fetching and processing

