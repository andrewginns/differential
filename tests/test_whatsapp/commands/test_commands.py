"""Test script for WhatsApp webhook slash commands.

This script tests the command parsing and handling functions in webhook_receiver.py
without running the actual webhook server.
"""

import pytest
from unittest.mock import patch, AsyncMock
from typing import Dict, Any, List, Optional

from newsletter_generator.whatsapp.webhook_receiver import (
    parse_command_args,
    handle_generate_command,
    handle_help_command,
    handle_status_command,
)
from newsletter_generator.ai.processor import ModelProvider


@pytest.mark.asyncio
async def test_parse_command_args():
    """Test the command argument parsing functionality."""
    print("\n=== Testing Command Parsing ===")

    test_cases = [
        "/help",
        "/generate",
        "/generate --days 5",
        "/generate --model openai",
        "/generate --days 3 --model gemini",
        "/status --days 10",
        "/unknown --param value",
    ]

    for command_text in test_cases:
        command, args = parse_command_args(command_text)
        print(f"\nCommand: {command_text}")
        print(f"Parsed command: {command}")
        print(f"Parsed args: {args}")


@pytest.mark.asyncio
@patch("newsletter_generator.whatsapp.webhook_receiver.send_text_message")
async def test_help_command(mock_send_text_message):
    """Test the help command handler."""
    print("\n=== Testing /help Command ===")

    mock_send_text_message.return_value = True

    sender = "1234567890"
    message_id = "test_message_id"
    success = await handle_help_command(sender, message_id)

    print(f"Command handled successfully: {success}")
    print(f"Message sent: {mock_send_text_message.called}")

    args, kwargs = mock_send_text_message.call_args
    print(f"Recipient: {kwargs.get('recipient_phone')}")
    print(f"Is markdown: {kwargs.get('is_markdown')}")
    print(f"Reply to message: {kwargs.get('reply_to_message_id')}")
    print(f"Message content length: {len(kwargs.get('text', ''))}")
    print(f"Message preview: {kwargs.get('text', '')[:100]}...")


@pytest.mark.asyncio
@patch("newsletter_generator.whatsapp.webhook_receiver.send_text_message")
@patch("newsletter_generator.whatsapp.webhook_receiver.storage_manager.list_content")
async def test_status_command(mock_list_content, mock_send_text_message):
    """Test the status command handler."""
    print("\n=== Testing /status Command ===")

    mock_send_text_message.return_value = True
    mock_list_content.return_value = {
        "content1": {
            "date_added": "2023-05-15T12:00:00Z",
            "category": "Technology",
            "title": "Test Article 1",
        },
        "content2": {
            "date_added": "2023-05-16T14:30:00Z",
            "category": "Science",
            "title": "Test Article 2",
        },
        "content3": {
            "date_added": "2023-05-17T09:15:00Z",
            "category": "Technology",
            "title": "Test Article 3",
        },
    }

    sender = "1234567890"
    message_id = "test_message_id"

    for days in ["3", "7"]:
        args = {"days": days}
        print(f"\nTesting status command with args: {args}")
        success = await handle_status_command(sender, message_id, args)

        print(f"Command handled successfully: {success}")
        print(f"Message sent: {mock_send_text_message.called}")

        mock_send_text_message.reset_mock()


@pytest.mark.asyncio
@patch("newsletter_generator.whatsapp.webhook_receiver.send_text_message")
@patch("newsletter_generator.whatsapp.webhook_receiver.assemble_newsletter")
async def test_generate_command(mock_assemble_newsletter, mock_send_text_message):
    """Test the generate command handler."""
    print("\n=== Testing /generate Command ===")

    mock_send_text_message.return_value = True
    mock_assemble_newsletter.return_value = "/tmp/mock_newsletter.md"

    with open("/tmp/mock_newsletter.md", "w") as f:
        f.write(
            "# Mock Newsletter\n\nThis is a mock newsletter for testing purposes.\n\n## Technology\n\n- Test Article 1\n- Test Article 3\n\n## Science\n\n- Test Article 2\n"
        )

    sender = "1234567890"
    message_id = "test_message_id"

    test_cases = [
        {},  # Default values
        {"days": "3"},
        {"model": "openai"},
        {"days": "5", "model": "gemini"},
    ]

    for args in test_cases:
        print(f"\nTesting generate command with args: {args}")
        mock_send_text_message.reset_mock()

        success = await handle_generate_command(sender, message_id, args)

        print(f"Command handled successfully: {success}")
        print(f"Initial acknowledgment sent: {mock_send_text_message.call_count >= 1}")
        print(f"Newsletter sent: {mock_send_text_message.call_count >= 2}")

        days = int(args.get("days", "7"))
        model_provider_str = args.get("model", "gemini").lower()
        model_provider = (
            ModelProvider.OPENAI if model_provider_str == "openai" else ModelProvider.GEMINI
        )

        mock_assemble_newsletter.assert_called_with(days=days, model_provider=model_provider)
        print(f"Newsletter generated with days={days}, model_provider={model_provider}")
