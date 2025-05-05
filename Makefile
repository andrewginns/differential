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

registry-cleanup:
	uv run -m newsletter_generator.utils.registry_manager clean

registry-validate:
	uv run -m newsletter_generator.utils.registry_manager validate

registry-build:
	uv run -m newsletter_generator.utils.registry_manager build

test:
	uv run pytest

