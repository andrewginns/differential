"""WhatsApp webhook receiver for the newsletter generator.

This module implements a FastAPI endpoint to receive webhook notifications from
the WhatsApp Business API, extract URLs from messages, and forward them to the
ingestion orchestrator.
"""

import re
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse

from fastapi import FastAPI, Request, HTTPException, Depends, Query
from pydantic import BaseModel, Field

from newsletter_generator.utils.logging_utils import get_logger
from newsletter_generator.utils.config import CONFIG
from newsletter_generator.ingestion.orchestrator import ingest_url
from newsletter_generator.storage import storage_manager

logger = get_logger("whatsapp.webhook")

app = FastAPI(title="Newsletter Generator WhatsApp Webhook")


class WhatsAppMessage(BaseModel):
    """Model for WhatsApp message data."""

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


@app.post("/webhook")
async def receive_webhook(request: Request):
    """Receive webhook notifications from WhatsApp Business API.

    This endpoint handles incoming messages from WhatsApp, extracts URLs,
    and forwards them to the ingestion orchestrator.

    Args:
        request: The FastAPI request object containing the webhook payload.

    Returns:
        A success response.
    """
    try:
        payload = await request.json()
        logger.debug(f"Received webhook payload: {payload}")

        if "object" not in payload or payload["object"] != "whatsapp_business_account":
            logger.info("Received non-message webhook notification")
            return {"status": "success"}

        if "entry" not in payload or not payload["entry"]:
            logger.warning("No entries in webhook payload")
            return {"status": "success"}

        processed_urls = []

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

                    urls = extract_urls(text)

                    if urls:
                        logger.info(f"Extracted {len(urls)} URLs from message: {urls}")

                        for url in urls:
                            logger.info(f"Processing URL: {url}")
                            try:
                                # Process the URL through the ingestion pipeline
                                content, metadata = await ingest_url(url)

                                # Add additional metadata
                                metadata.update(
                                    {
                                        "date_added": CONFIG.get_iso_timestamp(),
                                        "source": "whatsapp",
                                        "sender": sender,
                                        "message_id": message_id,
                                    }
                                )

                                # Store the content in the storage manager
                                content_id = storage_manager.store_content(
                                    content, metadata
                                )

                                logger.info(
                                    f"Successfully processed and stored URL: {url} with content_id: {content_id}"
                                )
                                processed_urls.append(url)
                            except Exception as e:
                                logger.error(f"Error processing URL {url}: {e}")
                    else:
                        logger.info("No URLs found in message")

        return {
            "status": "success",
            "processed_urls": processed_urls,
            "total_processed": len(processed_urls),
        }
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
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    run_webhook_server()
