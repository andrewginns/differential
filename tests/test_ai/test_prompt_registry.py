"""Tests for the prompt registry module."""

import pytest
from newsletter_generator.ai.prompts.prompt_registry import (
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
from newsletter_generator.ai.prompts.categorisation import v1 as categorisation_v1
from newsletter_generator.ai.prompts.categorisation import v2 as categorisation_v2


def test_default_versions():
    """Test that default versions are set correctly."""
    reset_to_defaults()
    
    assert get_categorisation_prompt() == categorisation_v1.prompt


def test_set_prompt_version():
    """Test setting the version for a specific prompt category."""
    reset_to_defaults()
    
    set_prompt_version("categorisation", "v2")
    
    assert get_categorisation_prompt() == categorisation_v2.prompt
    
    set_prompt_version("categorisation", "v1")
    
    assert get_categorisation_prompt() == categorisation_v1.prompt


def test_set_all_prompt_versions():
    """Test setting all prompt categories to the same version."""
    reset_to_defaults()
    
    set_all_prompt_versions("v2")
    
    assert get_categorisation_prompt() == categorisation_v2.prompt
    
    reset_to_defaults()


def test_get_prompt_module():
    """Test getting the prompt module for a specific category."""
    reset_to_defaults()
    
    module = get_prompt_module("categorisation")
    
    assert module == categorisation_v1
    
    set_prompt_version("categorisation", "v2")
    
    module = get_prompt_module("categorisation")
    
    assert module == categorisation_v2


def test_invalid_category():
    """Test that an invalid category raises a ValueError."""
    with pytest.raises(ValueError):
        set_prompt_version("invalid_category", "v1")


def test_invalid_version():
    """Test that an invalid version raises a ValueError."""
    with pytest.raises(ValueError):
        set_prompt_version("categorisation", "v3")


def test_convenience_functions():
    """Test the convenience functions for getting prompts."""
    reset_to_defaults()
    
    set_all_prompt_versions("v2")
    
    assert get_categorisation_prompt() == categorisation_v2.prompt
    
    reset_to_defaults()
