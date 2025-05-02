"""Newsletter assembler module for the newsletter generator.

This module is responsible for assembling the weekly technical newsletter
by collecting content, organizing it by categories, and generating the
final Markdown document.
"""

import os
import datetime
from typing import Dict, Any, List, Optional, Union, Tuple

from newsletter_generator.utils.logging_utils import get_logger
from newsletter_generator.utils.config import CONFIG
from newsletter_generator.storage import storage_manager
from newsletter_generator.ai import processor
from newsletter_generator.vector_db import lightrag_manager

logger = get_logger("newsletter.assembler")


class NewsletterAssembler:
    """Assembles the weekly technical newsletter.

    This class is responsible for collecting content, organizing it by categories,
    and generating the final newsletter in Markdown format.
    """

    def __init__(self, output_dir: Optional[str] = None):
        """Initialize the newsletter assembler.

        Args:
            output_dir: The directory to save the generated newsletters.
                If None, uses the default from config.
        """
        self.output_dir = output_dir or os.path.join(
            CONFIG.get("DATA_DIR", "data"), "newsletters"
        )

        os.makedirs(self.output_dir, exist_ok=True)

        logger.info(
            f"Initialized newsletter assembler with output directory: {self.output_dir}"
        )

    def collect_weekly_content(self, days: int = 7) -> List[Dict[str, Any]]:
        """Collect content from the past week.

        Args:
            days: The number of days to look back for content.

        Returns:
            A list of content items with their metadata.
        """
        try:
            # Create a naive datetime for cutoff
            cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days)

            all_content = storage_manager.list_content()

            weekly_content = []
            for content_id, metadata in all_content.items():
                # Parse the date from metadata
                content_date_str = metadata.get("date_added", "")

                # Handle timezone-aware datetimes by making them naive
                content_date = datetime.datetime.fromisoformat(content_date_str)

                # Make timezone-aware datetime naive for comparison
                if content_date.tzinfo is not None:
                    content_date = content_date.replace(tzinfo=None)

                if content_date >= cutoff_date:
                    content_text = storage_manager.get_content(content_id)

                    weekly_content.append(
                        {"id": content_id, "text": content_text, "metadata": metadata}
                    )

            logger.info(
                f"Collected {len(weekly_content)} content items from the past {days} days"
            )

            return weekly_content
        except Exception as e:
            logger.error(f"Error collecting weekly content: {e}")
            raise

    def organize_by_category(
        self, content_items: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Organize content items by category.

        Args:
            content_items: A list of content items with their metadata.

        Returns:
            A dictionary mapping categories to lists of content items.
        """
        try:
            categorized_content = {}

            for item in content_items:
                if "category" not in item["metadata"]:
                    categorization = processor.categorize_content(item["text"])
                    category = categorization["primary_category"]

                    item["metadata"]["category"] = category
                    item["metadata"]["secondary_categories"] = categorization[
                        "secondary_categories"
                    ]
                    item["metadata"]["tags"] = categorization["tags"]

                    storage_manager.update_metadata(item["id"], item["metadata"])
                else:
                    category = item["metadata"]["category"]

                if category not in categorized_content:
                    categorized_content[category] = []

                categorized_content[category].append(item)

            logger.info(f"Organized content into {len(categorized_content)} categories")

            return categorized_content
        except Exception as e:
            logger.error(f"Error organizing content by category: {e}")
            raise

    def generate_introduction(
        self,
        categorized_content: Dict[str, List[Dict[str, Any]]],
        category_sections: Optional[Dict[str, str]] = None,
    ) -> str:
        """Generate an introduction for the newsletter.

        Args:
            categorized_content: A dictionary mapping categories to lists of content items.
            category_sections: A dictionary mapping categories to their generated section content.
                If provided, will be used to generate a more accurate introduction based on actual content.

        Returns:
            The generated introduction in Markdown format.
        """
        try:
            categories = list(categorized_content.keys())
            total_items = sum(len(items) for items in categorized_content.values())

            # Prepare content summary if we have category sections
            content_summary = None
            if category_sections:
                # Create a summary of the actual content
                all_sections_text = "\n".join(category_sections.values())
                content_summary = processor.summarize_content(
                    all_sections_text, max_length=500
                )

            # Use the dedicated newsletter introduction function
            newsletter_introduction = processor.generate_newsletter_introduction(
                categories=categories,
                total_items=total_items,
                content_summary=content_summary,
                max_length=150,
            )

            formatted_intro = f"""

*{datetime.datetime.now().strftime("%B %d, %Y")}*

{newsletter_introduction}

"""

            for category in sorted(categories):
                item_count = len(categorized_content[category])
                formatted_intro += f"- [{category}](#{''.join(category.lower().split())}) ({item_count} item{'s' if item_count > 1 else ''})\n"

            logger.info("Generated newsletter introduction")

            return formatted_intro
        except Exception as e:
            logger.error(f"Error generating introduction: {e}")
            raise

    def generate_category_section(
        self, category: str, items: List[Dict[str, Any]]
    ) -> str:
        """Generate a section for a specific category.

        Args:
            category: The category name.
            items: The list of content items in this category.

        Returns:
            The generated section in Markdown format.
        """
        try:
            sorted_items = sorted(
                items,
                key=lambda x: (
                    -float(x["metadata"].get("relevance", 0)),
                    x["metadata"].get("date_added", ""),
                ),
            )

            section = f"\n\n## {category}\n\n"

            for item in sorted_items:
                title = item["metadata"].get("title", "Untitled")
                url = item["metadata"].get("url", "")

                if "summary" not in item["metadata"]:
                    summary = processor.summarize_content(item["text"], max_length=100)
                    item["metadata"]["summary"] = summary
                    storage_manager.update_metadata(item["id"], item["metadata"])
                else:
                    summary = item["metadata"]["summary"]

                content_section = processor.generate_newsletter_section(
                    title=title, content=item["text"], category=category, max_length=200
                )

                section += f"{content_section}\n\n"

                if url:
                    section += f"[Read more]({url})\n\n"

                section += "---\n\n"

            logger.info(
                f"Generated section for category '{category}' with {len(items)} items"
            )

            return section
        except Exception as e:
            logger.error(f"Error generating category section: {e}")
            raise

    def assemble_newsletter(self, days: int = 7, model_provider=None) -> str:
        """Assemble the weekly newsletter.

        Args:
            days: The number of days to look back for content.
            model_provider: The AI model provider to use (OpenAI or Gemini).

        Returns:
            The path to the generated newsletter file.
        """
        try:
            # Initialize the processor with the specified provider
            if model_provider is not None:
                processor.get_ai_processor(provider=model_provider)

            content_items = self.collect_weekly_content(days=days)

            if not content_items:
                logger.warning(f"No content found in the past {days} days")
                return None

            categorized_content = self.organize_by_category(content_items)

            # Generate category sections first
            category_sections = {}
            for category, items in sorted(categorized_content.items()):
                section = self.generate_category_section(category, items)
                category_sections[category] = section

            # Generate introduction after all content has been processed
            newsletter = self.generate_introduction(
                categorized_content, category_sections
            )

            # Add all category sections to the newsletter
            for category, section in category_sections.items():
                newsletter += section

            newsletter += f"\n\n---\n\n*This newsletter was automatically generated on {datetime.datetime.now().strftime('%B %d, %Y')}.*"

            date_str = datetime.datetime.now().strftime("%Y-%m-%d")
            filename = f"newsletter_{date_str}.md"
            filepath = os.path.join(self.output_dir, filename)

            with open(filepath, "w") as f:
                f.write(newsletter)

            logger.info(f"Generated newsletter saved to {filepath}")

            return filepath
        except Exception as e:
            logger.error(f"Error assembling newsletter: {e}")
            raise

    def generate_related_content_section(
        self, content_id: str, max_items: int = 3
    ) -> str:
        """Generate a 'Related Content' section for a specific content item.

        Args:
            content_id: The ID of the content item.
            max_items: The maximum number of related items to include.

        Returns:
            The generated section in Markdown format.
        """
        try:
            content = storage_manager.get_content(content_id)
            metadata = storage_manager.get_metadata(content_id)

            related_items = lightrag_manager.search(
                query=content,
                limit=max_items + 1,  # +1 to account for the item itself
                filter_metadata={
                    "content_id": {"$ne": content_id}
                },  # Exclude the item itself
            )

            if not related_items:
                return ""

            section = "\n\n### Related Content\n\n"

            for item in related_items[:max_items]:
                related_id = item["id"]
                related_metadata = storage_manager.get_metadata(related_id)

                title = related_metadata.get("title", "Untitled")
                url = related_metadata.get("url", "")

                section += f"- [{title}]({url})\n"

            logger.info(
                f"Generated related content section for {content_id} with {len(related_items[:max_items])} items"
            )

            return section
        except Exception as e:
            logger.error(f"Error generating related content section: {e}")
            raise


newsletter_assembler = None


def get_newsletter_assembler():
    """Get or create the singleton newsletter assembler instance.

    Returns:
        The NewsletterAssembler instance.
    """
    global newsletter_assembler
    if newsletter_assembler is None:
        try:
            newsletter_assembler = NewsletterAssembler()
        except Exception as e:
            logger.error(f"Error creating NewsletterAssembler: {e}")
            raise
    return newsletter_assembler


def collect_weekly_content(days: int = 7) -> List[Dict[str, Any]]:
    """Collect content from the past week.

    This is a convenience function that uses the singleton newsletter_assembler instance.

    Args:
        days: The number of days to look back for content.

    Returns:
        A list of content items with their metadata.
    """
    return get_newsletter_assembler().collect_weekly_content(days=days)


def organize_by_category(
    content_items: List[Dict[str, Any]],
) -> Dict[str, List[Dict[str, Any]]]:
    """Organize content items by category.

    This is a convenience function that uses the singleton newsletter_assembler instance.

    Args:
        content_items: A list of content items with their metadata.

    Returns:
        A dictionary mapping categories to lists of content items.
    """
    return get_newsletter_assembler().organize_by_category(content_items)


def generate_introduction(categorized_content: Dict[str, List[Dict[str, Any]]]) -> str:
    """Generate an introduction for the newsletter.

    This is a convenience function that uses the singleton newsletter_assembler instance.

    Args:
        categorized_content: A dictionary mapping categories to lists of content items.

    Returns:
        The generated introduction in Markdown format.
    """
    return get_newsletter_assembler().generate_introduction(categorized_content)


def generate_category_section(category: str, items: List[Dict[str, Any]]) -> str:
    """Generate a section for a specific category.

    This is a convenience function that uses the singleton newsletter_assembler instance.

    Args:
        category: The category name.
        items: The list of content items in this category.

    Returns:
        The generated section in Markdown format.
    """
    return get_newsletter_assembler().generate_category_section(category, items)


def assemble_newsletter(days: int = 7, model_provider=None) -> str:
    """Assemble the weekly newsletter.

    This is a convenience function that uses the singleton newsletter_assembler instance.

    Args:
        days: The number of days to look back for content.
        model_provider: The AI model provider to use (OpenAI or Gemini).

    Returns:
        The path to the generated newsletter file.
    """
    return get_newsletter_assembler().assemble_newsletter(
        days=days, model_provider=model_provider
    )


def generate_related_content_section(content_id: str, max_items: int = 3) -> str:
    """Generate a 'Related Content' section for a specific content item.

    This is a convenience function that uses the singleton newsletter_assembler instance.

    Args:
        content_id: The ID of the content item.
        max_items: The maximum number of related items to include.

    Returns:
        The generated section in Markdown format.
    """
    return get_newsletter_assembler().generate_related_content_section(
        content_id=content_id, max_items=max_items
    )
