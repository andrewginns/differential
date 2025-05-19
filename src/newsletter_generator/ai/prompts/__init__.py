"""Prompt management for the newsletter generator AI.

This package contains versioned prompt templates for the different AI agents.

For direct imports of specific versions:
    from newsletter_generator.ai.prompts.categorisation import v1 as categorisation

For centralized version management (recommended):
    from newsletter_generator.ai.prompts.prompt_registry import get_prompt_module
    categorisation = get_prompt_module("categorisation")
    
    from newsletter_generator.ai.prompts.prompt_registry import get_categorisation_prompt
    prompt = get_categorisation_prompt()
    
    from newsletter_generator.ai.prompts.prompt_registry import set_prompt_version
    set_prompt_version("categorisation", "v2")
    
    from newsletter_generator.ai.prompts.prompt_registry import set_all_prompt_versions
    set_all_prompt_versions("v2")
"""

from newsletter_generator.ai.prompts.prompt_registry import (  # noqa: F401
    set_prompt_version,
    set_all_prompt_versions,
    reset_to_defaults,
    get_prompt_module,
    get_categorisation_prompt,
    get_insights_prompt,
    get_relevance_prompt,
    get_summary_prompt,
    get_introduction_prompt,
    get_section_prompt,
    get_task_category_prompt,
    get_task_summary_prompt,
    get_task_insights_prompt,
    get_task_relevance_prompt,
    get_task_section_prompt,
    get_task_introduction_prompt,
)
