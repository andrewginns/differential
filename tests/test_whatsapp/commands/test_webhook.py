"""Test script for WhatsApp webhook commands.

This script simulates webhook payloads with different slash commands and sends them
to the webhook server for testing.
"""

import json
import aiohttp
import pytest
from typing import Dict, Any, List

WEBHOOK_PAYLOAD_TEMPLATE = {
    "object": "whatsapp_business_account",
    "entry": [
        {
            "id": "123456789",
            "changes": [
                {
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {
                            "display_phone_number": "1234567890",
                            "phone_number_id": "1234567890",
                        },
                        "contacts": [{"profile": {"name": "Test User"}, "wa_id": "9876543210"}],
                        "messages": [
                            {
                                "from": "9876543210",
                                "id": "wamid.123456789",
                                "timestamp": "1677673822",
                                "type": "text",
                                "text": {"body": "/help"},
                            }
                        ],
                    },
                    "field": "messages",
                }
            ],
        }
    ],
}


async def send_webhook_payload(url: str, command: str) -> Dict[str, Any]:
    """Send a webhook payload with the specified command.

    Args:
        url: The webhook URL to send the payload to
        command: The command to include in the message body

    Returns:
        The response from the webhook server
    """
    payload = json.loads(json.dumps(WEBHOOK_PAYLOAD_TEMPLATE))

    payload["entry"][0]["changes"][0]["value"]["messages"][0]["text"]["body"] = command

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as response:
            response_text = await response.text()
            return {"status": response.status, "text": response_text}


@pytest.fixture
def webhook_url():
    """Fixture providing a webhook URL for testing."""
    return "http://localhost:8000/webhook"


@pytest.fixture
def commands():
    """Fixture providing test commands to try."""
    return [
        "/help",
        "/generate",
        "/generate --days 3",
        "/generate --model openai",
        "/generate --days 5 --model gemini",
        "/status",
        "/status --days 3",
        "/unknown-command",
        "https://example.com",
        "Just a regular message",
    ]


@pytest.mark.asyncio
async def test_commands(webhook_url: str, commands: List[str]) -> None:
    """Test a list of commands against the webhook server.

    Args:
        webhook_url: The webhook URL to send the payloads to
        commands: List of commands to test
    """
    for command in commands:
        print(f"\n--- Testing command: {command} ---")
        try:
            response = await send_webhook_payload(webhook_url, command)
            print(f"Status: {response['status']}")
            print(f"Response: {response['text']}")
        except Exception as e:
            print(f"Error: {e}")
