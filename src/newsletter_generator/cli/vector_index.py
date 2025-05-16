"""Command-line interface for managing the vector database index.

This module provides commands for indexing content in the vector database,
which enables semantic search and similarity-based content discovery.
"""

import argparse
import sys
from typing import List, Optional

from newsletter_generator.integration.storage_vector_integration import (
    index_all_content,
    index_content,
    update_content_index,
    delete_content_index,
)
from newsletter_generator.utils.logging_utils import get_logger

logger = get_logger("cli.vector_index")


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        args: Command-line arguments. If None, uses sys.argv.

    Returns:
        Parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description="Manage the vector database index for newsletter content"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Index all content
    index_all_parser = subparsers.add_parser(
        "index-all", help="Index all content in the storage system"
    )
    index_all_parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-indexing of all content, even if already indexed",
    )

    # Index specific content
    index_parser = subparsers.add_parser(
        "index", help="Index specific content by ID"
    )
    index_parser.add_argument(
        "content_id", help="ID of the content to index"
    )

    # Update specific content
    update_parser = subparsers.add_parser(
        "update", help="Update specific content in the index by ID"
    )
    update_parser.add_argument(
        "content_id", help="ID of the content to update"
    )

    # Delete specific content
    delete_parser = subparsers.add_parser(
        "delete", help="Delete specific content from the index by ID"
    )
    delete_parser.add_argument(
        "content_id", help="ID of the content to delete"
    )

    return parser.parse_args(args)


def main(args: Optional[List[str]] = None) -> int:
    """Run the vector index CLI.

    Args:
        args: Command-line arguments. If None, uses sys.argv.

    Returns:
        Exit code.
    """
    parsed_args = parse_args(args)

    try:
        if parsed_args.command == "index-all":
            print("Indexing all content in the vector database...")
            success_count, failure_count = index_all_content()
            print(f"Successfully indexed {success_count} items")
            if failure_count > 0:
                print(f"Failed to index {failure_count} items")
                return 1
            return 0

        elif parsed_args.command == "index":
            print(f"Indexing content {parsed_args.content_id}...")
            success = index_content(parsed_args.content_id)
            if success:
                print("Successfully indexed content")
                return 0
            else:
                print("Failed to index content")
                return 1

        elif parsed_args.command == "update":
            print(f"Updating content {parsed_args.content_id}...")
            success = update_content_index(parsed_args.content_id)
            if success:
                print("Successfully updated content")
                return 0
            else:
                print("Failed to update content")
                return 1

        elif parsed_args.command == "delete":
            print(f"Deleting content {parsed_args.content_id}...")
            success = delete_content_index(parsed_args.content_id)
            if success:
                print("Successfully deleted content")
                return 0
            else:
                print("Failed to delete content")
                return 1

        else:
            print("No command specified")
            return 1

    except Exception as e:
        print(f"Error: {e}")
        logger.error(f"Error in vector_index CLI: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
