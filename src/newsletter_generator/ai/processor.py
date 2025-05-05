"""AI processor module for the newsletter generator.

This module integrates PydanticAI for content processing, categorisation,
and summarisation of technical content with support for multiple LLM providers.
"""

import os
import json
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Tuple, Literal
from enum import Enum

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.models.gemini import GeminiModel

from newsletter_generator.utils.logging_utils import get_logger
from newsletter_generator.utils.config import (
    CONFIG,
)
import logfire

# Configure Logfire
logfire.configure(
    send_to_logfire="if-token-present",
    service_name="differential-newsletter",
    scrubbing=False,
)
logfire.instrument_pydantic_ai()

logger = get_logger("ai.processor")


class ModelProvider(str, Enum):
    """Enum for supported model providers."""

    OPENAI = "openai"
    GEMINI = "gemini"


class CategoryOutput(BaseModel):
    """Pydantic model for categorisation output."""

    primary_category: str = Field(description="The primary category of the content")
    secondary_categories: List[str] = Field(
        description="Secondary categories if applicable", max_items=3
    )
    tags: List[str] = Field(description="Relevant tags", max_items=5)
    confidence: float = Field(
        description="Confidence score between 0.0 and 1.0", ge=0.0, le=1.0
    )


class InsightsOutput(BaseModel):
    """Pydantic model for insights output."""

    insights: List[str] = Field(
        description="Key technical insights extracted from the content",
        min_items=3,
        max_items=5,
    )


class RelevanceOutput(BaseModel):
    """Pydantic model for relevance evaluation."""

    relevance_score: float = Field(
        description="Relevance score between 0.0 and 1.0", ge=0.0, le=1.0
    )


class AIProcessor:
    """Processes content using PydanticAI with support for multiple LLM models.

    This class provides an interface to LLM models for content processing,
    categorisation, and summarisation of technical content.
    """

    def __init__(
        self,
        provider: ModelProvider = ModelProvider.GEMINI,
        output_dir: str = "newsletter_cache",
    ):
        """Initialise the AI processor.

        Sets up the PydanticAI agents with the appropriate models.

        Args:
            provider: The model provider to use (OpenAI or Gemini)
            output_dir: Base directory to store newsletter outputs
        """
        self.provider = provider
        self.output_dir = output_dir

        # Define the models
        self.openai_model = OpenAIModel("o4-mini")
        self.gemini_model = GeminiModel(
            "gemini-2.5-pro-preview-03-25", provider="google-vertex"
        )

        # Set the current model based on provider
        self.current_model = self._get_model_for_provider(provider)

        # Create agents for different tasks
        self.categorisation_agent = Agent(
            self.current_model,
            name="Categorisation Agent",
            output_type=CategoryOutput,
            system_prompt="""
            You are a technical content categorisation assistant. Your task is to analyse
            technical content and categorise it into one of the following primary categories:
            
            - Frontend Development
            - Backend Development
            - DevOps
            - Data Science
            - Machine Learning
            - Artificial Intelligence
            - Cloud Computing
            - Security
            - Blockchain
            - Mobile Development
            - IoT
            - Other
            
            Also provide up to 3 secondary categories if applicable, and up to 5 relevant tags.
            Provide a confidence score between 0.0 and 1.0 for your categorisation.
            """,
        )
        self.categorisation_agent.instrument_all()

        self.insights_agent = Agent(
            self.current_model,
            name="Insights Agent",
            output_type=InsightsOutput,
            system_prompt="""
            You are a technical insight extraction assistant. Your task is to identify
            the most important technical insights from the content provided.
            
            Focus on:
            1. Novel technical approaches or methodologies
            2. Significant performance improvements or optimisations
            3. Innovative solutions to technical challenges
            4. Important technical trends or shifts
            5. Key technical limitations or constraints identified
            
            Return a list of 3-5 concise, specific insights that would be valuable
            to technical professionals. Each insight should be a single sentence
            that captures a specific, actionable piece of information.
            """,
        )

        self.relevance_agent = Agent(
            self.current_model,
            name="Relevance Agent",
            output_type=RelevanceOutput,
            system_prompt="""
            You are a technical content relevance evaluator. Your task is to assess
            how relevant and valuable the provided content would be to technical
            professionals in a newsletter.
            
            Consider the following factors:
            1. Technical depth and specificity
            2. Novelty and innovation
            3. Practical applicability
            4. Technical accuracy
            5. Educational value
            
            Return a relevance score between 0.0 (not relevant) and 1.0 (highly relevant)
            representing your assessment of the content's relevance.
            """,
        )

        logger.info(f"Initialised AI processor with provider: {provider}")

    def _get_model_for_provider(self, provider: ModelProvider):
        """Get the appropriate model for the given provider.

        Args:
            provider: The model provider to use

        Returns:
            The corresponding model instance
        """
        if provider == ModelProvider.OPENAI:
            return self.openai_model
        elif provider == ModelProvider.GEMINI:
            return self.gemini_model
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    def set_provider(self, provider: ModelProvider):
        """Change the model provider.

        Args:
            provider: The model provider to use
        """
        self.provider = provider
        self.current_model = self._get_model_for_provider(provider)

        # Update all agents to use the new model
        self.categorisation_agent.model = self.current_model
        self.insights_agent.model = self.current_model
        self.relevance_agent.model = self.current_model

        logger.info(f"Switched AI processor to provider: {provider}")

    def _get_content_hash(self, content: str) -> str:
        """Generate a hash for the content to use in filenames.

        Args:
            content: The content to hash

        Returns:
            A short hash string for the content
        """
        return hashlib.md5(content.encode("utf-8")).hexdigest()[:10]

    def _get_newsletter_dir(self, newsletter_id: str) -> Path:
        """Get the directory for storing newsletter outputs.

        Args:
            newsletter_id: Unique identifier for the newsletter

        Returns:
            Path object for the newsletter directory
        """
        newsletter_dir = Path(self.output_dir) / newsletter_id
        newsletter_dir.mkdir(parents=True, exist_ok=True)
        return newsletter_dir

    def _check_cache(
        self, file_path: Path, step_name: str, newsletter_id: str
    ) -> Optional[Dict[str, Any]]:
        """Check if cached output exists and load it.

        Args:
            file_path: Path to the cached file
            step_name: Name of the processing step
            newsletter_id: ID of the newsletter

        Returns:
            The cached data if it exists, None otherwise
        """
        if file_path.exists():
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
                logger.info(
                    f"✅ CACHE HIT: Found cached {step_name} data for newsletter '{newsletter_id}' at {file_path}"
                )
                return data
            except Exception as e:
                logger.warning(
                    f"❌ CACHE ERROR: Failed to load {step_name} cache from {file_path}: {e}"
                )
                return None

        logger.info(
            f"❓ CACHE MISS: No cached {step_name} data found for newsletter '{newsletter_id}'"
        )
        return None

    def _save_to_cache(
        self, file_path: Path, data: Any, step_name: str, newsletter_id: str
    ) -> None:
        """Save data to cache file.

        Args:
            file_path: Path to save the cache file
            data: Data to cache
            step_name: Name of the processing step
            newsletter_id: ID of the newsletter
        """
        try:
            with open(file_path, "w") as f:
                json.dump(data, f, indent=2)
            logger.info(
                f"💾 CACHE SAVED: {step_name} data for newsletter '{newsletter_id}' saved to {file_path}"
            )
        except Exception as e:
            logger.error(
                f"❌ CACHE ERROR: Failed to save {step_name} data to {file_path}: {e}"
            )

    def categorise_content(
        self,
        content: str,
        newsletter_id: Optional[str] = None,
        force_refresh: bool = False,
        word_limit: int = CONFIG.get("MAX_CATEGORORISATION_TOKENS", 1000),
    ) -> Dict[str, Any]:
        """Categorise technical content into predefined categories.

        Args:
            content: The content to categorise.
            newsletter_id: Optional ID for the newsletter (defaults to content hash)
            force_refresh: If True, ignore cached results and reprocess
            word_limit: The maximum number of words to use for categorisation
        Returns:
            A dictionary containing the category information:
            {
                "primary_category": str,
                "secondary_categories": List[str],
                "tags": List[str],
                "confidence": float
            }

        Raises:
            Exception: If there's an error categorising the content.
        """
        try:
            # Generate newsletter ID if not provided
            if newsletter_id is None:
                newsletter_id = self._get_content_hash(content)
                logger.info(
                    f"Generated newsletter ID: {newsletter_id} (based on content hash)"
                )

            # Set up output directory
            newsletter_dir = self._get_newsletter_dir(newsletter_id)
            cache_file = newsletter_dir / "categorisation.json"

            # Check cache first if not forcing refresh
            if not force_refresh:
                cached_data = self._check_cache(
                    cache_file, "categorisation", newsletter_id
                )
                if cached_data:
                    return cached_data
            else:
                logger.info(
                    f"🔄 CACHE BYPASS: Force refreshing categorisation for newsletter '{newsletter_id}'"
                )

            logger.info(
                f"🔍 PROCESSING: Categorising content for newsletter '{newsletter_id}' using {self.provider} model"
            )
            result = self.categorisation_agent.run_sync(
                f"Please categorise the following technical content: {content[:word_limit]}"
            )

            categorisation = result.output.model_dump()

            logger.info(
                f"✅ COMPLETED: Content categorised as '{categorisation['primary_category']}' with confidence {categorisation['confidence']}"
            )

            # Save result to cache
            self._save_to_cache(
                cache_file, categorisation, "categorisation", newsletter_id
            )

            return categorisation
        except Exception as e:
            logger.error(
                f"❌ ERROR: Failed to categorise content for newsletter '{newsletter_id}': {e}"
            )
            raise

    def summarise_content(
        self,
        content: str,
        max_length: int = 200,
        newsletter_id: Optional[str] = None,
        force_refresh: bool = False,
    ) -> str:
        """Summarise technical content.

        Args:
            content: The content to summarise.
            max_length: The maximum length of the summary in words.
            newsletter_id: Optional ID for the newsletter (defaults to content hash)
            force_refresh: If True, ignore cached results and reprocess

        Returns:
            A summary of the content.

        Raises:
            Exception: If there's an error summarising the content.
        """
        try:
            # Generate newsletter ID if not provided
            if newsletter_id is None:
                newsletter_id = self._get_content_hash(content)
                logger.info(
                    f"Generated newsletter ID: {newsletter_id} (based on content hash)"
                )

            # Set up output directory
            newsletter_dir = self._get_newsletter_dir(newsletter_id)
            cache_file = newsletter_dir / "summary.json"

            # Check cache first if not forcing refresh
            if not force_refresh:
                cached_data = self._check_cache(cache_file, "summary", newsletter_id)
                if cached_data and "summary" in cached_data:
                    return cached_data["summary"]
            else:
                logger.info(
                    f"🔄 CACHE BYPASS: Force refreshing summary for newsletter '{newsletter_id}'"
                )

            # Create a summarisation agent on demand with a custom system prompt
            summarisation_agent = Agent(
                self.current_model,
                name="Summarisation Agent",
                system_prompt=f"""
                You are a technical content summarisation assistant. Your task is to create
                concise, informative summaries of technical content that capture the key
                points while maintaining technical accuracy.
                
                Focus on:
                1. The main technical concepts or innovations discussed
                2. Key features or capabilities mentioned
                3. Potential applications or implications
                4. Any notable results or metrics
                
                Avoid:
                1. Marketing language or hype
                2. Redundant information
                3. Overly basic explanations of well-known concepts
                
                Keep your summary clear, factual, and technically precise.
                Your summary should be no more than {max_length} words.
                """,
            )

            logger.info(
                f"🔍 PROCESSING: Summarising content for newsletter '{newsletter_id}' using {self.provider} model"
            )
            result = summarisation_agent.run_sync(
                f"Please summarise the following technical content: {content}"
            )

            summary = result.output

            logger.info(
                f"✅ COMPLETED: Generated summary of {len(summary.split())} words for newsletter '{newsletter_id}'"
            )

            # Save result to cache
            self._save_to_cache(
                cache_file,
                {"summary": summary, "max_length": max_length},
                "summary",
                newsletter_id,
            )

            return summary
        except Exception as e:
            logger.error(
                f"❌ ERROR: Failed to summarise content for newsletter '{newsletter_id}': {e}"
            )
            raise

    def generate_insights(
        self,
        content: str,
        newsletter_id: Optional[str] = None,
        force_refresh: bool = False,
    ) -> List[str]:
        """Generate key insights from technical content.

        Args:
            content: The content to analyse.
            newsletter_id: Optional ID for the newsletter (defaults to content hash)
            force_refresh: If True, ignore cached results and reprocess

        Returns:
            A list of key insights extracted from the content.

        Raises:
            Exception: If there's an error generating insights.
        """
        try:
            # Generate newsletter ID if not provided
            if newsletter_id is None:
                newsletter_id = self._get_content_hash(content)
                logger.info(
                    f"Generated newsletter ID: {newsletter_id} (based on content hash)"
                )

            # Set up output directory
            newsletter_dir = self._get_newsletter_dir(newsletter_id)
            cache_file = newsletter_dir / "insights.json"

            # Check cache first if not forcing refresh
            if not force_refresh:
                cached_data = self._check_cache(cache_file, "insights", newsletter_id)
                if cached_data and "insights" in cached_data:
                    return cached_data["insights"]
            else:
                logger.info(
                    f"🔄 CACHE BYPASS: Force refreshing insights for newsletter '{newsletter_id}'"
                )

            logger.info(
                f"🔍 PROCESSING: Extracting insights for newsletter '{newsletter_id}' using {self.provider} model"
            )
            result = self.insights_agent.run_sync(
                f"Please extract key technical insights from the following content: {content}"
            )

            insights = result.output.insights

            logger.info(
                f"✅ COMPLETED: Generated {len(insights)} insights for newsletter '{newsletter_id}'"
            )

            # Save result to cache
            self._save_to_cache(
                cache_file, {"insights": insights}, "insights", newsletter_id
            )

            return insights
        except Exception as e:
            logger.error(
                f"❌ ERROR: Failed to generate insights for newsletter '{newsletter_id}': {e}"
            )
            raise

    def evaluate_relevance(
        self,
        content: str,
        newsletter_id: Optional[str] = None,
        force_refresh: bool = False,
    ) -> float:
        """Evaluate the technical relevance of content.

        Args:
            content: The content to evaluate.
            newsletter_id: Optional ID for the newsletter (defaults to content hash)
            force_refresh: If True, ignore cached results and reprocess

        Returns:
            A relevance score between 0.0 and 1.0.

        Raises:
            Exception: If there's an error evaluating relevance.
        """
        try:
            # Generate newsletter ID if not provided
            if newsletter_id is None:
                newsletter_id = self._get_content_hash(content)
                logger.info(
                    f"Generated newsletter ID: {newsletter_id} (based on content hash)"
                )

            # Set up output directory
            newsletter_dir = self._get_newsletter_dir(newsletter_id)
            cache_file = newsletter_dir / "relevance.json"

            # Check cache first if not forcing refresh
            if not force_refresh:
                cached_data = self._check_cache(cache_file, "relevance", newsletter_id)
                if cached_data and "relevance_score" in cached_data:
                    return cached_data["relevance_score"]
            else:
                logger.info(
                    f"🔄 CACHE BYPASS: Force refreshing relevance score for newsletter '{newsletter_id}'"
                )

            logger.info(
                f"🔍 PROCESSING: Evaluating relevance for newsletter '{newsletter_id}' using {self.provider} model"
            )
            result = self.relevance_agent.run_sync(
                f"Please evaluate the technical relevance of the following content: {content}"
            )

            relevance = result.output.relevance_score

            logger.info(
                f"✅ COMPLETED: Evaluated content relevance for newsletter '{newsletter_id}': {relevance}"
            )

            # Save result to cache
            self._save_to_cache(
                cache_file, {"relevance_score": relevance}, "relevance", newsletter_id
            )

            return relevance
        except Exception as e:
            logger.error(
                f"❌ ERROR: Failed to evaluate relevance for newsletter '{newsletter_id}': {e}"
            )
            raise

    def generate_newsletter_section(
        self,
        title: str,
        content: str,
        category: str,
        max_length: int = 300,
        newsletter_id: Optional[str] = None,
        force_refresh: bool = False,
    ) -> str:
        """Generate a newsletter section for the given content.

        Args:
            title: The title of the content.
            content: The content to include in the newsletter.
            category: The category of the content.
            max_length: The maximum length of the section in words.
            newsletter_id: Optional ID for the newsletter (defaults to content hash)
            force_refresh: If True, ignore cached results and reprocess

        Returns:
            A formatted newsletter section in Markdown.

        Raises:
            Exception: If there's an error generating the newsletter section.
        """
        try:
            # Generate newsletter ID if not provided
            if newsletter_id is None:
                newsletter_id = self._get_content_hash(content)
                logger.info(
                    f"Generated newsletter ID: {newsletter_id} (based on content hash)"
                )

            # Set up output directory
            newsletter_dir = self._get_newsletter_dir(newsletter_id)
            cache_file = newsletter_dir / "newsletter_section.json"

            # Check cache first if not forcing refresh
            if not force_refresh:
                cached_data = self._check_cache(
                    cache_file, "newsletter section", newsletter_id
                )
                if cached_data and "section" in cached_data:
                    return cached_data["section"]
            else:
                logger.info(
                    f"🔄 CACHE BYPASS: Force refreshing newsletter section for '{newsletter_id}'"
                )

            # Create a newsletter section agent on demand with a custom system prompt
            newsletter_section_agent = Agent(
                self.current_model,
                name="Section Creation Agent",
                system_prompt=f"""
                You are a technical newsletter section writer. Your task is to create
                engaging, informative newsletter sections from technical content.
                
                Your section should include:
                1. A brief, catchy introduction that highlights why this content is interesting
                2. A concise summary of the key technical points
                3. Any notable implications or applications
                4. A brief conclusion or call to action
                
                Format your response in Markdown, with appropriate headings, bullet points,
                and emphasis where needed. Make it engaging for technical professionals
                while maintaining technical accuracy.
                
                Your section should be under {max_length} words.
                """,
            )

            logger.info(
                f"🔍 PROCESSING: Generating newsletter section for '{newsletter_id}' using {self.provider} model"
            )
            result = newsletter_section_agent.run_sync(
                f"""
                Please create a newsletter section for the following technical content:
                
                Title: {title}
                Category: {category}
                
                Content:
                {content}
                """
            )

            section = result.output

            logger.info(
                f"✅ COMPLETED: Generated newsletter section of {len(section.split())} words for '{newsletter_id}'"
            )

            # Save result to cache
            self._save_to_cache(
                cache_file,
                {
                    "section": section,
                    "title": title,
                    "category": category,
                    "max_length": max_length,
                },
                "newsletter section",
                newsletter_id,
            )

            return section
        except Exception as e:
            logger.error(
                f"❌ ERROR: Failed to generate newsletter section for '{newsletter_id}': {e}"
            )
            raise

    def generate_newsletter_introduction(
        self,
        categories: List[str],
        total_items: int,
        content_summary: Optional[str] = None,
        max_length: int = 150,
        newsletter_id: Optional[str] = None,
        force_refresh: bool = False,
    ) -> str:
        """Generate an introduction for the newsletter.

        Args:
            categories: List of categories in the newsletter.
            total_items: Total number of content items in the newsletter.
            content_summary: Optional summary of newsletter content to base introduction on.
            max_length: The maximum length of the introduction in words.
            newsletter_id: Optional ID for the newsletter (defaults to content hash)
            force_refresh: If True, ignore cached results and reprocess

        Returns:
            A formatted newsletter introduction in plain text.

        Raises:
            Exception: If there's an error generating the newsletter introduction.
        """
        try:
            # Generate newsletter ID if not provided
            if newsletter_id is None:
                content_to_hash = f"{','.join(categories)}_{total_items}"
                newsletter_id = self._get_content_hash(content_to_hash)
                logger.info(
                    f"Generated newsletter ID: {newsletter_id} (based on content hash)"
                )

            # Set up output directory
            newsletter_dir = self._get_newsletter_dir(newsletter_id)
            cache_file = newsletter_dir / "newsletter_introduction.json"

            # Check cache first if not forcing refresh
            if not force_refresh:
                cached_data = self._check_cache(
                    cache_file, "newsletter introduction", newsletter_id
                )
                if cached_data and "introduction" in cached_data:
                    return cached_data["introduction"]
            else:
                logger.info(
                    f"🔄 CACHE BYPASS: Force refreshing newsletter introduction for '{newsletter_id}'"
                )

            # Create a newsletter introduction agent on demand with a custom system prompt
            newsletter_introduction_agent = Agent(
                self.current_model,
                name="Introduction Agent",
                system_prompt=f"""
                You are a technical newsletter introduction writer. Your task is to create
                engaging, informative introductions for technical newsletters.
                
                Your introduction should:
                1. Welcome readers and set the tone for the newsletter
                2. Highlight key themes or notable items from this week
                3. Briefly mention the diversity of content available
                4. Encourage readers to explore the different sections
                
                Keep your introduction concise, professional, and focused on technical content.
                Write in a friendly but authoritative tone appropriate for a professional audience.
                
                Your introduction should be under {max_length} words.
                """,
            )

            # Create the prompt based on available content
            if content_summary:
                prompt = f"""
                This week's technical newsletter includes {total_items} items across {len(categories)} categories:
                {", ".join(categories)}.
                
                Based on the following newsletter content summary, please generate an engaging introduction that 
                highlights key themes and important items from this week's content.
                
                CONTENT SUMMARY:
                {content_summary}
                """
            else:
                prompt = f"""
                This week's technical newsletter includes {total_items} items across {len(categories)} categories:
                {", ".join(categories)}.
                
                Please generate an engaging introduction for a technical newsletter that highlights
                the diversity of content and encourages readers to explore the different sections.
                """

            logger.info(
                f"🔍 PROCESSING: Generating newsletter introduction for '{newsletter_id}' using {self.provider} model"
            )
            result = newsletter_introduction_agent.run_sync(prompt)

            introduction = result.output

            logger.info(
                f"✅ COMPLETED: Generated newsletter introduction of {len(introduction.split())} words for '{newsletter_id}'"
            )

            # Save result to cache
            self._save_to_cache(
                cache_file,
                {
                    "introduction": introduction,
                    "categories": categories,
                    "total_items": total_items,
                    "max_length": max_length,
                },
                "newsletter introduction",
                newsletter_id,
            )

            return introduction
        except Exception as e:
            logger.error(
                f"❌ ERROR: Failed to generate newsletter introduction for '{newsletter_id}': {e}"
            )
            raise


ai_processor = None


def get_ai_processor(
    provider: Optional[ModelProvider] = None, output_dir: str = "newsletter_cache"
):
    """Get or create the singleton AI processor instance.

    Args:
        provider: Optional model provider to use (OpenAI or Gemini)
        output_dir: Base directory to store newsletter outputs

    Returns:
        The AIProcessor instance.
    """
    global ai_processor
    if ai_processor is None:
        try:
            # Use the provider parameter if specified, otherwise use config
            if provider is None:
                config_provider = CONFIG.get("MODEL_PROVIDER", "openai").lower()
                provider = (
                    ModelProvider.GEMINI
                    if config_provider == "gemini"
                    else ModelProvider.OPENAI
                )

            ai_processor = AIProcessor(provider=provider, output_dir=output_dir)
        except Exception as e:
            logger.error(f"Error creating AIProcessor: {e}")
            raise
    elif provider is not None and provider != ai_processor.provider:
        # If provider is specified and different from current provider, switch
        ai_processor.set_provider(provider)
        logger.info(f"Switched AIProcessor to provider: {provider}")
    return ai_processor


def categorise_content(
    content: str, newsletter_id: Optional[str] = None, force_refresh: bool = False
) -> Dict[str, Any]:
    """Categorise technical content into predefined categories.

    This is a convenience function that uses the singleton ai_processor instance.

    Args:
        content: The content to categorise.
        newsletter_id: Optional ID for the newsletter (defaults to content hash)
        force_refresh: If True, ignore cached results and reprocess

    Returns:
        A dictionary containing the category information.
    """
    return get_ai_processor().categorise_content(
        content, newsletter_id=newsletter_id, force_refresh=force_refresh
    )


def summarise_content(
    content: str,
    max_length: int = 200,
    newsletter_id: Optional[str] = None,
    force_refresh: bool = False,
) -> str:
    """Summarise technical content.

    This is a convenience function that uses the singleton ai_processor instance.

    Args:
        content: The content to summarise.
        max_length: The maximum length of the summary in words.
        newsletter_id: Optional ID for the newsletter (defaults to content hash)
        force_refresh: If True, ignore cached results and reprocess

    Returns:
        A summary of the content.
    """
    return get_ai_processor().summarise_content(
        content, max_length, newsletter_id=newsletter_id, force_refresh=force_refresh
    )


def generate_insights(
    content: str, newsletter_id: Optional[str] = None, force_refresh: bool = False
) -> List[str]:
    """Generate key insights from technical content.

    This is a convenience function that uses the singleton ai_processor instance.

    Args:
        content: The content to analyse.
        newsletter_id: Optional ID for the newsletter (defaults to content hash)
        force_refresh: If True, ignore cached results and reprocess

    Returns:
        A list of key insights extracted from the content.
    """
    return get_ai_processor().generate_insights(
        content, newsletter_id=newsletter_id, force_refresh=force_refresh
    )


def evaluate_relevance(
    content: str, newsletter_id: Optional[str] = None, force_refresh: bool = False
) -> float:
    """Evaluate the technical relevance of content.

    This is a convenience function that uses the singleton ai_processor instance.

    Args:
        content: The content to evaluate.
        newsletter_id: Optional ID for the newsletter (defaults to content hash)
        force_refresh: If True, ignore cached results and reprocess

    Returns:
        A relevance score between 0.0 and 1.0.
    """
    return get_ai_processor().evaluate_relevance(
        content, newsletter_id=newsletter_id, force_refresh=force_refresh
    )


def generate_newsletter_section(
    title: str,
    content: str,
    category: str,
    max_length: int = 300,
    newsletter_id: Optional[str] = None,
    force_refresh: bool = False,
) -> str:
    """Generate a newsletter section for the given content.

    This is a convenience function that uses the singleton ai_processor instance.

    Args:
        title: The title of the content.
        content: The content to include in the newsletter.
        category: The category of the content.
        max_length: The maximum length of the section in words.
        newsletter_id: Optional ID for the newsletter (defaults to content hash)
        force_refresh: If True, ignore cached results and reprocess

    Returns:
        A formatted newsletter section in Markdown.
    """
    return get_ai_processor().generate_newsletter_section(
        title,
        content,
        category,
        max_length,
        newsletter_id=newsletter_id,
        force_refresh=force_refresh,
    )


def generate_newsletter_introduction(
    categories: List[str],
    total_items: int,
    content_summary: Optional[str] = None,
    max_length: int = 150,
    newsletter_id: Optional[str] = None,
    force_refresh: bool = False,
) -> str:
    """Generate an introduction for the newsletter.

    This is a convenience function that uses the singleton ai_processor instance.

    Args:
        categories: List of categories in the newsletter.
        total_items: Total number of content items in the newsletter.
        content_summary: Optional summary of newsletter content to base introduction on.
        max_length: The maximum length of the introduction in words.
        newsletter_id: Optional ID for the newsletter (defaults to content hash)
        force_refresh: If True, ignore cached results and reprocess

    Returns:
        A formatted newsletter introduction in plain text.
    """
    return get_ai_processor().generate_newsletter_introduction(
        categories,
        total_items,
        content_summary=content_summary,
        max_length=max_length,
        newsletter_id=newsletter_id,
        force_refresh=force_refresh,
    )
