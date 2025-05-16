"""WhatsApp webhook receiver for the newsletter generator.

This module implements a FastAPI endpoint to receive webhook notifications from
the WhatsApp Business API, extract URLs from messages, and forward them to the
ingestion orchestrator. It includes robust error handling, retry mechanisms,
and circuit breaker patterns for improved reliability.
"""

import re
import time
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse
from functools import wraps

from fastapi import FastAPI, Request, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field, ConfigDict
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
import aiohttp

from newsletter_generator.utils.logging_utils import get_logger
from newsletter_generator.utils.config import CONFIG
from newsletter_generator.ingestion.orchestrator import ingest_url
from newsletter_generator.storage import storage_manager
from newsletter_generator.whatsapp.webhook_errors import (
    ValidationError,
    ProcessingError,
    TransientError,
    NetworkError,
    CircuitBreakerError,
)

logger = get_logger("whatsapp.webhook")

app = FastAPI(title="Newsletter Generator WhatsApp Webhook")


class CircuitBreaker:
    """Simple circuit breaker implementation."""

    def __init__(self, failure_threshold: int = 5, reset_timeout: int = 60):
        """Initialize the circuit breaker.

        Args:
            failure_threshold: Number of failures before opening the circuit.
            reset_timeout: Time in seconds before trying to close the circuit again.
        """
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.last_failure_time = 0
        self.state = "closed"  # closed, open, half-open

    def record_failure(self):
        """Record a failure and potentially open the circuit."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning("Circuit breaker opened due to multiple failures")

    def record_success(self):
        """Record a success and potentially close the circuit."""
        if self.state == "half-open":
            self.state = "closed"
            self.failure_count = 0
            logger.info("Circuit breaker closed after successful operation")

    def can_execute(self) -> bool:
        """Check if the operation can be executed.

        Returns:
            True if the operation can be executed, False otherwise.
        """
        if self.state == "closed":
            return True

        if self.state == "open":
            if time.time() - self.last_failure_time > self.reset_timeout:
                self.state = "half-open"
                logger.info("Circuit breaker transitioned to half-open state")
                return True
            return False

        return True


ingestion_circuit_breaker = CircuitBreaker()


def circuit_breaker_decorator(func):
    """Decorator that applies circuit breaker pattern to a function.

    Args:
        func: The function to decorate.

    Returns:
        The decorated function.
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        if not ingestion_circuit_breaker.can_execute():
            raise CircuitBreakerError("Circuit breaker is open")

        try:
            result = await func(*args, **kwargs)
            ingestion_circuit_breaker.record_success()
            return result
        except TransientError:
            ingestion_circuit_breaker.record_failure()
            raise

    return wrapper


class WhatsAppMessage(BaseModel):
    """Model for WhatsApp message data."""

    model_config = ConfigDict()

    message_id: str = Field(..., alias="id")
    text: Optional[str] = None
    timestamp: str
    from_number: str = Field(..., alias="from")


def is_valid_url(url: str) -> bool:
    """Check if a string is a valid URL.

    Args:
        url: The string to check.

    Returns:
        True if the string is a valid HTTP or HTTPS URL, False otherwise.
    """
    try:
        result = urlparse(url)
        return all([result.scheme in ("http", "https"), result.netloc])
    except Exception as e:
        logger.error(f"Error validating URL {url}: {e}")
        return False


def extract_urls(text: str) -> List[str]:
    """Extract URLs from text.

    Args:
        text: The text to extract URLs from.

    Returns:
        A list of valid URLs found in the text.
    """
    if not text:
        return []

    url_pattern = r'https?://[^\s<>"]+|www\.[^\s<>"]+\.[^\s<>"]{2,}'
    potential_urls = re.findall(url_pattern, text)

    valid_urls = []
    for url in potential_urls:
        if url[-1] in [".", ",", ":", ";", "!", "?"]:
            url = url[:-1]

        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        if is_valid_url(url):
            valid_urls.append(url)

    return valid_urls


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(NetworkError),
)
async def send_message_reaction(message_id: str, sender_phone: str, emoji: str = "✅") -> bool:
    """Send a reaction to a WhatsApp message.

    Args:
        message_id: The ID of the message to react to.
        sender_phone: The phone number of the message sender.
        emoji: The emoji to use as a reaction, defaults to checkmark.

    Returns:
        bool: True if the reaction was sent successfully, False otherwise.

    Raises:
        NetworkError: If there's a network error when sending the reaction.
    """
    try:
        phone_number_id = CONFIG.get("WHATSAPP_PHONE_NUMBER_ID")
        api_token = CONFIG.get("WHATSAPP_API_TOKEN")
        api_version = CONFIG.get("WHATSAPP_API_VERSION", "v18.0")

        if not phone_number_id or not api_token:
            logger.error("Missing WhatsApp API configuration")
            return False

        url = f"https://graph.facebook.com/{api_version}/{phone_number_id}/messages"

        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_token}"}

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": sender_phone,
            "type": "reaction",
            "reaction": {"message_id": message_id, "emoji": emoji},
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    response_data = await response.json()
                    logger.info(
                        f"Successfully sent reaction to message {message_id}: {response_data}"
                    )
                    return True
                else:
                    error_text = await response.text()
                    logger.error(
                        f"Failed to send reaction to message {message_id}, status {response.status}: {error_text}"
                    )
                    return False

    except aiohttp.ClientError as e:
        logger.error(f"Network error sending reaction to message {message_id}: {e}")
        raise NetworkError(f"Network error sending reaction: {e}")
    except Exception as e:
        logger.error(f"Error sending reaction to message {message_id}: {e}")
        return False


@app.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(..., alias="hub.mode"),
    hub_challenge: str = Query(..., alias="hub.challenge"),
    hub_verify_token: str = Query(..., alias="hub.verify_token"),
):
    """Verify the webhook for WhatsApp Business API.

    This endpoint handles the verification handshake required by Meta.

    Args:
        hub_mode: The mode of the verification request.
        hub_challenge: The challenge string to be returned.
        hub_verify_token: The verification token to validate.

    Returns:
        The challenge string if verification is successful.

    Raises:
        HTTPException: If verification fails.
    """
    verify_token = CONFIG.get("WHATSAPP_VERIFY_TOKEN", "default_token")

    if hub_mode == "subscribe" and hub_verify_token == verify_token:
        logger.info("Webhook verified successfully")
        return int(hub_challenge)

    logger.error(f"Webhook verification failed: {hub_mode=}, {hub_verify_token=}")
    raise HTTPException(status_code=403, detail="Verification failed")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(TransientError),
)
@circuit_breaker_decorator
async def process_url(url: str, message_metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Process a URL extracted from a webhook.

    Args:
        url: The URL to process.
        message_metadata: Metadata about the message containing the URL.

    Returns:
        A dictionary with processing results.

    Raises:
        TransientError: If there's a temporary error that might resolve with a retry.
        ProcessingError: If there's an error processing the URL.
    """
    logger.info(f"Processing URL: {url}")

    try:
        # Process the URL through the ingestion pipeline
        content, metadata = await ingest_url(url)

        # Add additional metadata
        metadata.update(message_metadata)

        # Store the content in the storage manager
        content_id = storage_manager.store_content(content, metadata)

        logger.info(f"Successfully processed and stored URL: {url} with content_id: {content_id}")

        return {"url": url, "content_id": content_id, "status": "success"}
    except aiohttp.ClientError as e:
        logger.warning(f"Network error processing URL {url}: {e}")
        raise NetworkError(f"Network error: {e}")
    except ConnectionError as e:
        logger.warning(f"Connection error processing URL {url}: {e}")
        raise NetworkError(f"Connection error: {e}")
    except Exception as e:
        logger.error(f"Error processing URL {url}: {e}")
        raise ProcessingError(f"Error processing URL: {e}")


async def process_webhook(payload: Dict[str, Any]):
    """Process a webhook payload.

    Args:
        payload: The webhook payload to process.
    """
    processed_urls = []
    errors = []

    try:
        for entry in payload["entry"]:
            if "changes" not in entry or not entry["changes"]:
                continue

            for change in entry["changes"]:
                if "value" not in change or "messages" not in change["value"]:
                    continue

                for message in change["value"]["messages"]:
                    if message["type"] != "text" or "text" not in message:
                        continue

                    text = message["text"].get("body", "")
                    sender = message.get("from", "unknown")
                    message_id = message.get("id", "unknown")

                    # Send acknowledgment reaction to the received message
                    try:
                        reaction_sent = await send_message_reaction(message_id, sender)
                        if reaction_sent:
                            logger.info(f"Sent acknowledgment reaction to message {message_id}")
                        else:
                            logger.warning(
                                f"Failed to send acknowledgment reaction to message {message_id}"
                            )
                    except Exception as e:
                        logger.error(f"Error sending reaction to message {message_id}: {e}")

                    message_metadata = {
                        "date_added": CONFIG.get_iso_timestamp(),
                        "source": "whatsapp",
                        "sender": sender,
                        "message_id": message_id,
                    }

                    urls = extract_urls(text)

                    if urls:
                        logger.info(f"Extracted {len(urls)} URLs from message: {urls}")

                        for url in urls:
                            try:
                                result = await process_url(url, message_metadata)
                                processed_urls.append(result)
                            except (TransientError, ProcessingError) as e:
                                logger.error(f"Error processing URL {url}: {e}")
                                errors.append({"url": url, "error": str(e)})
                    else:
                        logger.info("No URLs found in message")

        logger.info(f"Processed {len(processed_urls)} URLs with {len(errors)} errors")
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")


@app.post("/webhook")
async def receive_webhook(request: Request, background_tasks: BackgroundTasks):
    """Receive webhook notifications from WhatsApp Business API.

    This endpoint handles incoming messages from WhatsApp, extracts URLs,
    and forwards them to the ingestion orchestrator.

    Args:
        request: The FastAPI request object containing the webhook payload.
        background_tasks: FastAPI BackgroundTasks for processing webhooks in the background.

    Returns:
        A success response.
    """
    try:
        payload = await request.json()
        logger.debug(f"Received webhook payload: {payload}")

        if "object" not in payload:
            raise ValidationError("Missing 'object' in webhook payload")

        if payload["object"] != "whatsapp_business_account":
            logger.info("Received non-message webhook notification")
            return {"status": "success"}

        if "entry" not in payload or not payload["entry"]:
            logger.warning("No entries in webhook payload")
            return {"status": "success"}

        # Process the webhook in the background
        background_tasks.add_task(process_webhook, payload)

        return {"status": "success", "message": "Webhook received and being processed"}
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        return {"status": "error", "message": str(e)}
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return {"status": "error", "message": str(e)}


def run_webhook_server():
    """Run the webhook server.

    This function is the entry point for running the webhook server.
    """
    import uvicorn

    port = CONFIG.get("WEBHOOK_PORT", 8000)
    webhook_path = CONFIG.get("WEBHOOK_PATH", "/webhook")

    logger.info(f"Starting webhook server on port {port} with path {webhook_path}")
    logger.info("Webhook server configured with robust error handling and circuit breaker")
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    run_webhook_server()
