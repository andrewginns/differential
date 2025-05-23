install:
	uv sync
	uv run crawl4ai-setup

tunnel:
	ngrok http 8081
	echo "Tunnel created, webhook url should be $(ngrok_url)/webhook"
	echo "Start the server with 'make server'. Then add the webhook url to https://developers.facebook.com/apps/YOU_APP_ID/whatsapp-business/wa-settings/?business_id=YOUR_BUSINESS_ID"

server:
	uv run src/newsletter_generator/whatsapp/webhook_receiver.py

newsletter:
	uv run -m newsletter_generator.newsletter

test:
	uv run pytest

lint:
	uv run ruff check .

format:
	uv run ruff format .

