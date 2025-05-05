#!/usr/bin/env python
"""
Command-line interface for the newsletter assembler.
"""

import argparse
import sys
from newsletter_generator.newsletter.assembler import assemble_newsletter
from newsletter_generator.ai.processor import ModelProvider


def main():
    """Main entry point for the newsletter assembler CLI."""
    parser = argparse.ArgumentParser(
        description="Generate a technical newsletter from recent content."
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Number of days to look back for content (default: 7)",
    )
    parser.add_argument(
        "--model-provider",
        type=str,
        choices=["openai", "gemini"],
        default="gemini",
        help="LLM provider to use for content processing (default: openai)",
    )

    args = parser.parse_args()

    try:
        # Map string choice to ModelProvider enum
        provider = ModelProvider.OPENAI if args.model_provider == "openai" else ModelProvider.GEMINI
        result = assemble_newsletter(days=args.days, model_provider=provider)
        if result:
            print(f"Newsletter generated successfully: {result}")
            return 0
        else:
            print(f"No content found in the past {args.days} days.")
            return 1
    except Exception as e:
        print(f"Error generating newsletter: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
