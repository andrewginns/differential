# WhatsApp Slash Commands Configuration Guide

This guide explains how to configure the WhatsApp Business API in the Meta Developer Portal to support the new slash commands functionality for newsletter generation.

## Overview

The WhatsApp integration has been enhanced with slash commands that allow users to:

1. `/generate` - Generate a newsletter with optional parameters
2. `/status` - Show ingested content count for potential newsletter
3. `/help` - Show available commands and usage

These commands enable users to interact with the newsletter generator directly through WhatsApp, without needing to use the command line.

## Meta Developer Portal Configuration

To enable the slash commands functionality, you need to make the following configuration changes in the Meta Developer Portal:

### 1. Update Webhook Configuration

1. Log in to the [Meta Developer Portal](https://developers.facebook.com/)
2. Navigate to your WhatsApp Business App
3. Go to **WhatsApp > Configuration**
4. Under **Webhooks**, ensure your webhook is configured with the following settings:
   - **Callback URL**: Your webhook endpoint URL (e.g., `https://your-domain.com/webhook`)
   - **Verify Token**: The same token configured in your `WHATSAPP_VERIFY_TOKEN` environment variable
   - **Subscription Fields**: Make sure the following fields are selected:
     - `messages`
     - `message_reactions`

### 2. Enable Message Templates for Responses

To send rich text responses for newsletter content, you need to configure message templates:

1. Go to **WhatsApp > Configuration > Message Templates**
2. Create a new template with the following settings:
   - **Category**: Utility
   - **Name**: `newsletter_response`
   - **Language**: Your preferred language
   - **Template Type**: Text
   - **Body**: Include a generic placeholder text like `{{1}}` that will be replaced with the actual newsletter content

### 3. Update API Permissions

Ensure your app has the necessary permissions to send messages and reactions:

1. Go to **App Settings > Permissions**
2. Make sure the following permissions are enabled:
   - `whatsapp_business_messaging`
   - `whatsapp_business_management`

### 4. Configure Rate Limits

The slash commands, especially `/generate`, can trigger multiple API calls. Configure appropriate rate limits:

1. Go to **WhatsApp > Configuration > Rate Limits**
2. Set appropriate limits for your expected usage
3. Consider increasing limits for the Business Account if you expect high usage

## Environment Variables

Update your environment variables with the following settings:

```
WHATSAPP_VERIFY_TOKEN=your_verify_token
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
WHATSAPP_API_TOKEN=your_api_token
WHATSAPP_API_VERSION=v18.0
```

## Testing the Configuration

After completing the configuration, you can test the slash commands:

1. Send a message with `/help` to your WhatsApp Business number
2. You should receive a response with the available commands and their usage
3. Test the other commands (`/generate`, `/status`) with various parameters

## Troubleshooting

If you encounter issues with the slash commands:

1. **Webhook Not Receiving Commands**:
   - Verify your webhook URL is accessible
   - Check the verify token matches your environment variable
   - Ensure the subscription fields include `messages`

2. **Commands Not Recognized**:
   - Check the logs for any parsing errors
   - Ensure the command format is correct (e.g., `/generate --days 5`)

3. **Message Sending Failures**:
   - Verify your API token is valid and has not expired
   - Check that your message templates are approved
   - Ensure you're not exceeding rate limits

## Command Reference

### `/generate` Command

Generates a newsletter with content from the past X days.

**Options**:
- `--days <number>` - Number of days to look back for content (default: 7)
- `--model <provider>` - LLM provider to use (openai or gemini, default: gemini)

**Example**: `/generate --days 5 --model openai`

### `/status` Command

Shows ingested content count for potential newsletter.

**Options**:
- `--days <number>` - Number of days to look back (default: 7)

**Example**: `/status --days 3`

### `/help` Command

Shows available commands and their usage.

**Example**: `/help`
