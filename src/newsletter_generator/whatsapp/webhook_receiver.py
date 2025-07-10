"""WhatsApp webhook receiver for the newsletter generator.

This module implements a FastAPI endpoint to receive webhook notifications from
the WhatsApp Business API, extract URLs from messages, and forward them to the
ingestion orchestrator. It includes robust error handling, retry mechanisms,
and circuit breaker patterns for improved reliability.

It also supports slash commands for generating newsletters and other interactions.
"""

import re
import time
import os
import asyncio
import datetime
from typing import List, Optional, Dict, Any, Tuple, Union
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
from newsletter_generator.newsletter.assembler import assemble_newsletter
from newsletter_generator.ai.processor import ModelProvider

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


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(NetworkError),
)
async def send_text_message(
    recipient_phone: str,
    text: str,
    is_markdown: bool = False,
    reply_to_message_id: Optional[str] = None,
) -> bool:
    """Send a text message to a WhatsApp user.

    Args:
        recipient_phone: The phone number of the message recipient.
        text: The text content to send.
        is_markdown: Whether the text is formatted as markdown.
        reply_to_message_id: Optional message ID to reply to.

    Returns:
        bool: True if the message was sent successfully, False otherwise.

    Raises:
        NetworkError: If there's a network error when sending the message.
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

        MAX_MESSAGE_SIZE = 4000  # Slightly less than the limit to be safe
        message_chunks = []

        if len(text) > MAX_MESSAGE_SIZE:
            paragraphs = text.split("\n\n")
            current_chunk = ""

            for paragraph in paragraphs:
                if len(current_chunk) + len(paragraph) + 2 <= MAX_MESSAGE_SIZE:
                    if current_chunk:
                        current_chunk += "\n\n"
                    current_chunk += paragraph
                else:
                    if current_chunk:
                        message_chunks.append(current_chunk)

                    if len(paragraph) > MAX_MESSAGE_SIZE:
                        sentences = re.split(r"(?<=[.!?])\s+", paragraph)
                        current_chunk = ""

                        for sentence in sentences:
                            if len(current_chunk) + len(sentence) + 1 <= MAX_MESSAGE_SIZE:
                                if current_chunk:
                                    current_chunk += " "
                                current_chunk += sentence
                            else:
                                if current_chunk:
                                    message_chunks.append(current_chunk)

                                if len(sentence) > MAX_MESSAGE_SIZE:
                                    words = sentence.split()
                                    current_chunk = ""

                                    for word in words:
                                        if len(current_chunk) + len(word) + 1 <= MAX_MESSAGE_SIZE:
                                            if current_chunk:
                                                current_chunk += " "
                                            current_chunk += word
                                        else:
                                            message_chunks.append(current_chunk)
                                            current_chunk = word
                                else:
                                    current_chunk = sentence
                    else:
                        current_chunk = paragraph

            if current_chunk:
                message_chunks.append(current_chunk)
        else:
            message_chunks = [text]

        all_success = True
        for i, chunk in enumerate(message_chunks):
            if len(message_chunks) > 1:
                chunk = f"({i + 1}/{len(message_chunks)}) {chunk}"

            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": recipient_phone,
                "type": "text",
                "text": {"body": chunk, "preview_url": True},
            }

            if reply_to_message_id and i == 0:  # Only set context for the first message
                payload["context"] = {"message_id": reply_to_message_id}

            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status == 200:
                        response_data = await response.json()
                        logger.info(
                            f"Successfully sent message chunk {i + 1}/{len(message_chunks)} to {recipient_phone}: {response_data}"
                        )
                    else:
                        error_text = await response.text()
                        logger.error(
                            f"Failed to send message chunk {i + 1}/{len(message_chunks)} to {recipient_phone}, status {response.status}: {error_text}"
                        )
                        all_success = False

            if i < len(message_chunks) - 1:
                await asyncio.sleep(1)

        return all_success

    except aiohttp.ClientError as e:
        logger.error(f"Network error sending message to {recipient_phone}: {e}")
        raise NetworkError(f"Network error sending message: {e}")
    except Exception as e:
        logger.error(f"Error sending message to {recipient_phone}: {e}")
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


def parse_command_args(command_text: str) -> Tuple[str, Dict[str, str]]:
    """Parse command arguments from a command string.

    Args:
        command_text: The command text to parse (e.g., "/generate --days 5 --model gemini")

    Returns:
        A tuple containing the command name and a dictionary of arguments
    """
    parts = command_text.split()
    command = parts[0][1:] if parts and parts[0].startswith("/") else ""

    args = {}
    i = 1
    while i < len(parts):
        if parts[i].startswith("--"):
            arg_name = parts[i][2:]
            if i + 1 < len(parts) and not parts[i + 1].startswith("--"):
                args[arg_name] = parts[i + 1]
                i += 2
            else:
                args[arg_name] = "true"
                i += 1
        else:
            i += 1

    return command, args


async def handle_generate_command(sender: str, message_id: str, args: Dict[str, str]) -> bool:
    """Handle the /generate command to generate a newsletter.

    Args:
        sender: The phone number of the sender
        message_id: The ID of the message containing the command
        args: The parsed command arguments

    Returns:
        True if the command was handled successfully, False otherwise
    """
    try:
        days = int(args.get("days", "7"))
        model_provider_str = args.get("model", "gemini").lower()

        model_provider = (
            ModelProvider.OPENAI if model_provider_str == "openai" else ModelProvider.GEMINI
        )

        # Send acknowledgment
        await send_text_message(
            sender,
            f"Generating newsletter with content from the past {days} days using {model_provider_str} model...",
            reply_to_message_id=message_id,
        )

        # Generate the newsletter
        newsletter_path = assemble_newsletter(days=days, model_provider=model_provider)

        if newsletter_path:
            # Read the generated newsletter
            with open(newsletter_path, "r") as f:
                newsletter_content = f.read()

            # Send the newsletter
            success = await send_text_message(
                sender, f"Here's your newsletter:\n\n{newsletter_content}", is_markdown=True
            )

            return success
        else:
            await send_text_message(
                sender,
                f"No content found in the past {days} days to generate a newsletter.",
                reply_to_message_id=message_id,
            )
            return True

    except Exception as e:
        logger.error(f"Error handling /generate command: {e}")
        await send_text_message(
            sender, f"Error generating newsletter: {str(e)}", reply_to_message_id=message_id
        )
        return False


async def handle_help_command(sender: str, message_id: str) -> bool:
    """Handle the /help command to show available commands.

    Args:
        sender: The phone number of the sender
        message_id: The ID of the message containing the command

    Returns:
        True if the command was handled successfully, False otherwise
    """
    help_text = """
*Available Commands:*

*/generate* - Generate a newsletter
  Options:
  --days <number> - Number of days to look back for content (default: 7)
  --model <provider> - LLM provider to use (openai or gemini, default: gemini)
  
  Example: /generate --days 5 --model openai

*/status* - Show ingested content count for potential newsletter
  Options:
  --days <number> - Number of days to look back (default: 7)
  
  Example: /status --days 3

*/help* - Show this help message

*URL Sharing:*
Simply share URLs to ingest content for your newsletter. The system will automatically process them.
"""

    return await send_text_message(
        sender, help_text, is_markdown=True, reply_to_message_id=message_id
    )


async def handle_status_command(sender: str, message_id: str, args: Dict[str, str]) -> bool:
    """Handle the /status command to show ingested content count.

    Args:
        sender: The phone number of the sender
        message_id: The ID of the message containing the command
        args: The parsed command arguments

    Returns:
        True if the command was handled successfully, False otherwise
    """
    try:
        days = int(args.get("days", "7"))

        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days)

        all_content = storage_manager.list_content()

        recent_content = []
        for content_id, metadata in all_content.items():
            content_date_str = metadata.get("date_added", "")

            if not content_date_str:
                continue

            content_date = datetime.datetime.fromisoformat(content_date_str)

            if content_date.tzinfo is not None:
                content_date = content_date.replace(tzinfo=None)

            if content_date >= cutoff_date:
                recent_content.append((content_id, metadata))

        categories = {}
        uncategorized = 0

        for _, metadata in recent_content:
            category = metadata.get("category")
            if category:
                categories[category] = categories.get(category, 0) + 1
            else:
                uncategorized += 1

        status_message = f"*Content Status for the Past {days} Days:*\n\n"
        status_message += f"Total content items: {len(recent_content)}\n\n"

        if categories:
            status_message += "*Categories:*\n"
            for category, count in sorted(categories.items()):
                status_message += f"- {category}: {count} item{'s' if count > 1 else ''}\n"

        if uncategorized:
            status_message += f"\nUncategorized items: {uncategorized}\n"

        if not recent_content:
            status_message += "No content found in the specified time period.\n"

        status_message += "\nUse /generate to create a newsletter with this content."

        return await send_text_message(
            sender, status_message, is_markdown=True, reply_to_message_id=message_id
        )

    except Exception as e:
        logger.error(f"Error handling /status command: {e}")
        await send_text_message(
            sender, f"Error getting content status: {str(e)}", reply_to_message_id=message_id
        )
        return False


async def process_webhook(payload: Dict[str, Any]):
    """Process a webhook payload.

    Args:
        payload: The webhook payload to process.
    """
    processed_urls = []
    processed_commands = []
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

                    if text.startswith("/"):
                        logger.info(f"Received command: {text}")

                        command, args = parse_command_args(text)

                        if command == "generate":
                            success = await handle_generate_command(sender, message_id, args)
                            processed_commands.append(
                                {"command": "generate", "args": args, "success": success}
                            )

                        elif command == "help":
                            success = await handle_help_command(sender, message_id)
                            processed_commands.append({"command": "help", "success": success})

                        elif command == "status":
                            success = await handle_status_command(sender, message_id, args)
                            processed_commands.append(
                                {"command": "status", "args": args, "success": success}
                            )

                        else:
                            await send_text_message(
                                sender,
                                f"Unknown command: {command}\nUse /help to see available commands.",
                                reply_to_message_id=message_id,
                            )
                            processed_commands.append(
                                {"command": command, "success": False, "error": "Unknown command"}
                            )
                    else:
                        # Process as normal message with URLs
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
                            await send_text_message(
                                sender,
                                "I can process URLs to collect content for your newsletter or respond to commands like /generate, /status, or /help.",
                                reply_to_message_id=message_id,
                            )

        logger.info(
            f"Processed {len(processed_urls)} URLs and {len(processed_commands)} commands with {len(errors)} errors"
        )
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
