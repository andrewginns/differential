"""Tests for the WhatsApp webhook receiver module."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from newsletter_generator.whatsapp.webhook_receiver import (
    app,
    is_valid_url,
    extract_urls,
)


class TestURLFunctions:
    """Test cases for URL validation and extraction functions."""

    def test_is_valid_url_with_valid_urls(self):
        """Test that is_valid_url returns True for valid URLs."""
        valid_urls = [
            "https://example.com",
            "http://example.com/path",
            "https://subdomain.example.com/path?query=value",
            "http://example.com/path#fragment",
        ]
        for url in valid_urls:
            assert is_valid_url(url) is True, f"URL should be valid: {url}"

    def test_is_valid_url_with_invalid_urls(self):
        """Test that is_valid_url returns False for invalid URLs."""
        invalid_urls = [
            "",
            "not a url",
            "ftp://example.com",  # Not http or https
            "http://",  # Missing netloc
            "example.com",  # Missing scheme
        ]
        for url in invalid_urls:
            assert is_valid_url(url) is False, f"URL should be invalid: {url}"

    def test_extract_urls_with_no_urls(self):
        """Test that extract_urls returns an empty list when no URLs are present."""
        texts_with_no_urls = [
            "",
            "This is a text with no URLs",
            "example.com",  # Not a valid URL without scheme
        ]
        for text in texts_with_no_urls:
            assert extract_urls(text) == [], f"No URLs should be extracted from: {text}"

    def test_extract_urls_with_urls(self):
        """Test that extract_urls correctly extracts URLs from text."""
        text_with_urls = (
            "Check out https://example.com and http://another-example.com/path "
            "and www.example.org for more information."
        )
        expected_urls = [
            "https://example.com",
            "http://another-example.com/path",
            "https://www.example.org",
        ]
        assert sorted(extract_urls(text_with_urls)) == sorted(expected_urls)

    def test_extract_urls_with_mixed_content(self):
        """Test that extract_urls correctly handles mixed content."""
        text = "Visit https://example.com. This is not a URL: example. But www.example.org is."
        expected_urls = ["https://example.com", "https://www.example.org"]
        assert sorted(extract_urls(text)) == sorted(expected_urls)


class TestWebhookEndpoints:
    """Test cases for webhook endpoints."""

    client = TestClient(app)

    def test_verify_webhook_success(self):
        """Test successful webhook verification."""
        with patch(
            "newsletter_generator.whatsapp.webhook_receiver.CONFIG",
            {"WHATSAPP_VERIFY_TOKEN": "test_token"},
        ):
            response = self.client.get(
                "/webhook?hub.mode=subscribe&hub.challenge=1234&hub.verify_token=test_token"
            )
            assert response.status_code == 200
            assert response.json() == 1234

    def test_verify_webhook_failure_wrong_token(self):
        """Test webhook verification failure due to wrong token."""
        with patch(
            "newsletter_generator.whatsapp.webhook_receiver.CONFIG",
            {"WHATSAPP_VERIFY_TOKEN": "test_token"},
        ):
            response = self.client.get(
                "/webhook?hub.mode=subscribe&hub.challenge=1234&hub.verify_token=wrong_token"
            )
            assert response.status_code == 403
            assert "Verification failed" in response.text

    def test_verify_webhook_failure_wrong_mode(self):
        """Test webhook verification failure due to wrong mode."""
        with patch(
            "newsletter_generator.whatsapp.webhook_receiver.CONFIG",
            {"WHATSAPP_VERIFY_TOKEN": "test_token"},
        ):
            response = self.client.get(
                "/webhook?hub.mode=wrong_mode&hub.challenge=1234&hub.verify_token=test_token"
            )
            assert response.status_code == 403
            assert "Verification failed" in response.text

    @patch("newsletter_generator.whatsapp.webhook_receiver.logger")
    def test_receive_webhook_with_valid_message(self, mock_logger):
        """Test receiving a valid webhook message with URLs."""
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "123456789",
                    "changes": [
                        {
                            "value": {
                                "messages": [
                                    {
                                        "id": "wamid.123456789",
                                        "type": "text",
                                        "text": {"body": "Check out https://example.com"},
                                        "from": "1234567890",
                                    }
                                ]
                            }
                        }
                    ],
                }
            ],
        }

        response = self.client.post("/webhook", json=payload)
        assert response.status_code == 200
        response_json = response.json()
        assert response_json["status"] == "success"
        assert "processed_urls" in response_json
        assert "total_processed" in response_json

        mock_logger.info.assert_any_call("Extracted 1 URLs from message: ['https://example.com']")
        mock_logger.info.assert_any_call("Processing URL: https://example.com")

    @patch("newsletter_generator.whatsapp.webhook_receiver.logger")
    def test_receive_webhook_with_no_urls(self, mock_logger):
        """Test receiving a webhook message with no URLs."""
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "123456789",
                    "changes": [
                        {
                            "value": {
                                "messages": [
                                    {
                                        "id": "wamid.123456789",
                                        "type": "text",
                                        "text": {"body": "This message has no URLs"},
                                        "from": "1234567890",
                                    }
                                ]
                            }
                        }
                    ],
                }
            ],
        }

        response = self.client.post("/webhook", json=payload)
        assert response.status_code == 200
        response_json = response.json()
        assert response_json["status"] == "success"
        assert "processed_urls" in response_json
        assert "total_processed" in response_json
        assert response_json["total_processed"] == 0

        mock_logger.info.assert_any_call("No URLs found in message")

    def test_receive_webhook_with_non_message_object(self):
        """Test receiving a webhook with a non-message object."""
        payload = {"object": "not_whatsapp", "entry": []}

        response = self.client.post("/webhook", json=payload)
        assert response.status_code == 200
        assert response.json() == {"status": "success"}

    def test_receive_webhook_with_empty_entry(self):
        """Test receiving a webhook with an empty entry list."""
        payload = {"object": "whatsapp_business_account", "entry": []}

        response = self.client.post("/webhook", json=payload)
        assert response.status_code == 200
        assert response.json() == {"status": "success"}

    def test_receive_webhook_with_non_text_message(self):
        """Test receiving a webhook with a non-text message."""
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "123456789",
                    "changes": [
                        {
                            "value": {
                                "messages": [
                                    {"id": "wamid.123456789", "type": "image", "from": "1234567890"}
                                ]
                            }
                        }
                    ],
                }
            ],
        }

        response = self.client.post("/webhook", json=payload)
        assert response.status_code == 200
        response_json = response.json()
        assert response_json["status"] == "success"
        assert "processed_urls" in response_json
        assert "total_processed" in response_json


if __name__ == "__main__":
    pytest.main()
