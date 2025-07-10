"""Prompt registry for the newsletter generator.

This module provides a central configuration system for managing prompt versions.
It allows switching between different versions of prompts (v1, v2, etc.) from a single location.
"""

from typing import Dict, Any, Literal, Optional

from newsletter_generator.ai.prompts.categorisation import v1 as categorisation_v1
from newsletter_generator.ai.prompts.categorisation import v2 as categorisation_v2
from newsletter_generator.ai.prompts.insights import v1 as insights_v1
from newsletter_generator.ai.prompts.insights import v2 as insights_v2
from newsletter_generator.ai.prompts.introduction import v1 as introduction_v1
from newsletter_generator.ai.prompts.introduction import v2 as introduction_v2
from newsletter_generator.ai.prompts.relevance import v1 as relevance_v1
from newsletter_generator.ai.prompts.relevance import v2 as relevance_v2
from newsletter_generator.ai.prompts.section import v1 as section_v1
from newsletter_generator.ai.prompts.section import v2 as section_v2
from newsletter_generator.ai.prompts.summary import v1 as summary_v1
from newsletter_generator.ai.prompts.summary import v2 as summary_v2
from newsletter_generator.ai.prompts.task import v1 as task_v1
from newsletter_generator.ai.prompts.task import v2 as task_v2

PromptCategory = Literal[
    "categorisation",
    "insights",
    "introduction",
    "relevance",
    "section",
    "summary",
    "task",
]

PromptVersion = Literal["v1", "v2"]

_default_versions: Dict[PromptCategory, PromptVersion] = {
    "categorisation": "v2",
    "insights": "v2",
    "introduction": "v2",
    "relevance": "v2",
    "section": "v2",
    "summary": "v2",
    "task": "v2",
}

_current_versions = _default_versions.copy()

_prompt_modules = {
    "categorisation": {
        "v1": categorisation_v1,
        "v2": categorisation_v2,
    },
    "insights": {
        "v1": insights_v1,
        "v2": insights_v2,
    },
    "introduction": {
        "v1": introduction_v1,
        "v2": introduction_v2,
    },
    "relevance": {
        "v1": relevance_v1,
        "v2": relevance_v2,
    },
    "section": {
        "v1": section_v1,
        "v2": section_v2,
    },
    "summary": {
        "v1": summary_v1,
        "v2": summary_v2,
    },
    "task": {
        "v1": task_v1,
        "v2": task_v2,
    },
}


def set_prompt_version(category: PromptCategory, version: PromptVersion) -> None:
    """Set the version for a specific prompt category.

    Args:
        category: The prompt category to configure
        version: The version to use for this category
    """
    if category not in _current_versions:
        raise ValueError(f"Unknown prompt category: {category}")
    if version not in _prompt_modules[category]:
        raise ValueError(f"Unknown version '{version}' for category '{category}'")

    _current_versions[category] = version


def set_all_prompt_versions(version: PromptVersion) -> None:
    """Set all prompt categories to use the same version.

    Args:
        version: The version to use for all categories
    """
    for category in _current_versions:
        set_prompt_version(category, version)


def reset_to_defaults() -> None:
    """Reset all prompt versions to their default values."""
    global _current_versions
    _current_versions = _default_versions.copy()


def get_prompt_module(category: PromptCategory) -> Any:
    """Get the prompt module for a specific category.

    Args:
        category: The prompt category to get

    Returns:
        The prompt module for the configured version of the category
    """
    version = _current_versions[category]
    return _prompt_modules[category][version]


def get_categorisation_prompt() -> str:
    """Get the current version of the categorisation prompt."""
    return get_prompt_module("categorisation").prompt


def get_insights_prompt() -> str:
    """Get the current version of the insights prompt."""
    return get_prompt_module("insights").prompt


def get_relevance_prompt() -> str:
    """Get the current version of the relevance prompt."""
    return get_prompt_module("relevance").prompt


def get_summary_prompt() -> str:
    """Get the current version of the summary prompt."""
    return get_prompt_module("summary").prompt


def get_introduction_prompt(max_length: int = 150) -> str:
    """Get the current version of the introduction prompt.

    Args:
        max_length: The maximum length of the introduction in words.

    Returns:
        The prompt template string.
    """
    return get_prompt_module("introduction").get_prompt(max_length)


def get_section_prompt(max_length: int = 300) -> str:
    """Get the current version of the section prompt.

    Args:
        max_length: The maximum length of the section in words.

    Returns:
        The prompt template string.
    """
    return get_prompt_module("section").get_prompt(max_length)


def get_task_category_prompt() -> str:
    """Get the current version of the task category prompt."""
    return get_prompt_module("task").category_prompt


def get_task_summary_prompt() -> str:
    """Get the current version of the task summary prompt."""
    return get_prompt_module("task").summary_prompt


def get_task_insights_prompt() -> str:
    """Get the current version of the task insights prompt."""
    return get_prompt_module("task").insights_prompt


def get_task_relevance_prompt() -> str:
    """Get the current version of the task relevance prompt."""
    return get_prompt_module("task").relevance_prompt


def get_task_section_prompt(title: str, category: str, content: str) -> str:
    """Get the current version of the task section prompt.

    Args:
        title: The title of the content
        category: The category of the content
        content: The content to process

    Returns:
        The formatted task prompt
    """
    return get_prompt_module("task").section_prompt(title, category, content)


def get_task_introduction_prompt(
    categories: list, total_items: int, content_summary: Optional[str] = None
) -> str:
    """Get the current version of the task introduction prompt.

    Args:
        categories: List of categories in the newsletter
        total_items: Total number of content items in the newsletter
        content_summary: Optional summary of newsletter content to base introduction on

    Returns:
        The formatted task prompt
    """
    return get_prompt_module("task").introduction_prompt(categories, total_items, content_summary)
