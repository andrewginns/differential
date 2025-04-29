"""AI processor module for the newsletter generator.

This module integrates OpenAI models for content processing, categorization,
and summarization of technical content.
"""

import os
from typing import Dict, Any, List, Optional, Union, Tuple

from openai import OpenAI

from newsletter_generator.utils.logging_utils import get_logger
from newsletter_generator.utils.config import CONFIG, get_openai_api_key

logger = get_logger("ai.processor")


class AIProcessor:
    """Processes content using OpenAI models.
    
    This class provides an interface to OpenAI models for content processing,
    categorization, and summarization of technical content.
    """
    
    def __init__(self):
        """Initialize the AI processor.
        
        Sets up the OpenAI client and configures the models to use.
        """
        self.openai_client = OpenAI(api_key=get_openai_api_key())
        self.llm_model = CONFIG.get("OPENAI_LLM_MODEL", "o4-mini")
        
        logger.info(f"Initialized AI processor with LLM model: {self.llm_model}")
    
    def categorize_content(self, content: str) -> Dict[str, Any]:
        """Categorize technical content into predefined categories.
        
        Args:
            content: The content to categorize.
            
        Returns:
            A dictionary containing the category information:
            {
                "primary_category": str,
                "secondary_categories": List[str],
                "tags": List[str],
                "confidence": float
            }
            
        Raises:
            Exception: If there's an error categorizing the content.
        """
        try:
            system_prompt = """
            You are a technical content categorization assistant. Your task is to analyze
            technical content and categorize it into one of the following primary categories:
            
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
            Provide a confidence score between 0.0 and 1.0 for your categorization.
            
            Return your analysis as a JSON object with the following structure:
            {
                "primary_category": "string",
                "secondary_categories": ["string", "string"],
                "tags": ["string", "string", "string", "string", "string"],
                "confidence": float
            }
            """
            
            user_prompt = f"""
            Please categorize the following technical content:
            
            {content[:4000]}  # Truncate to avoid token limits
            
            Return only the JSON object with your categorization.
            """
            
            response = self.openai_client.chat.completions.create(
                model=self.llm_model,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            result = response.choices[0].message.content
            
            import json
            categorization = json.loads(result)
            
            logger.info(f"Categorized content as {categorization['primary_category']} with confidence {categorization['confidence']}")
            
            return categorization
        except Exception as e:
            logger.error(f"Error categorizing content: {e}")
            raise
    
    def summarize_content(self, content: str, max_length: int = 200) -> str:
        """Summarize technical content.
        
        Args:
            content: The content to summarize.
            max_length: The maximum length of the summary in words.
            
        Returns:
            A summary of the content.
            
        Raises:
            Exception: If there's an error summarizing the content.
        """
        try:
            system_prompt = """
            You are a technical content summarization assistant. Your task is to create
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
            """
            
            user_prompt = f"""
            Please summarize the following technical content in no more than {max_length} words:
            
            {content[:4000]}  # Truncate to avoid token limits
            """
            
            response = self.openai_client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            summary = response.choices[0].message.content
            
            logger.info(f"Generated summary of length {len(summary.split())} words")
            
            return summary
        except Exception as e:
            logger.error(f"Error summarizing content: {e}")
            raise
    
    def generate_insights(self, content: str) -> List[str]:
        """Generate key insights from technical content.
        
        Args:
            content: The content to analyze.
            
        Returns:
            A list of key insights extracted from the content.
            
        Raises:
            Exception: If there's an error generating insights.
        """
        try:
            system_prompt = """
            You are a technical insight extraction assistant. Your task is to identify
            the most important technical insights from the content provided.
            
            Focus on:
            1. Novel technical approaches or methodologies
            2. Significant performance improvements or optimizations
            3. Innovative solutions to technical challenges
            4. Important technical trends or shifts
            5. Key technical limitations or constraints identified
            
            Return a list of 3-5 concise, specific insights that would be valuable
            to technical professionals. Each insight should be a single sentence
            that captures a specific, actionable piece of information.
            
            Format your response as a JSON array of strings.
            """
            
            user_prompt = f"""
            Please extract key technical insights from the following content:
            
            {content[:4000]}  # Truncate to avoid token limits
            
            Return only the JSON array with your insights.
            """
            
            response = self.openai_client.chat.completions.create(
                model=self.llm_model,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            result = response.choices[0].message.content
            
            import json
            response_data = json.loads(result)
            
            insights = response_data.get("insights", [])
            
            logger.info(f"Generated {len(insights)} insights from content")
            
            return insights
        except Exception as e:
            logger.error(f"Error generating insights: {e}")
            raise
    
    def evaluate_relevance(self, content: str) -> float:
        """Evaluate the technical relevance of content.
        
        Args:
            content: The content to evaluate.
            
        Returns:
            A relevance score between 0.0 and 1.0.
            
        Raises:
            Exception: If there's an error evaluating relevance.
        """
        try:
            system_prompt = """
            You are a technical content relevance evaluator. Your task is to assess
            how relevant and valuable the provided content would be to technical
            professionals in a newsletter.
            
            Consider the following factors:
            1. Technical depth and specificity
            2. Novelty and innovation
            3. Practical applicability
            4. Technical accuracy
            5. Educational value
            
            Return a single float value between 0.0 (not relevant) and 1.0 (highly relevant)
            representing your assessment of the content's relevance.
            """
            
            user_prompt = f"""
            Please evaluate the technical relevance of the following content:
            
            {content[:4000]}  # Truncate to avoid token limits
            
            Return only a single float value between 0.0 and 1.0.
            """
            
            response = self.openai_client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            result = response.choices[0].message.content.strip()
            
            import re
            match = re.search(r'(\d+\.\d+)', result)
            if match:
                relevance = float(match.group(1))
            else:
                try:
                    relevance = float(result)
                except ValueError:
                    logger.warning(f"Could not parse relevance score from: {result}, defaulting to 0.5")
                    relevance = 0.5
            
            relevance = max(0.0, min(1.0, relevance))
            
            logger.info(f"Evaluated content relevance: {relevance}")
            
            return relevance
        except Exception as e:
            logger.error(f"Error evaluating relevance: {e}")
            raise
    
    def generate_newsletter_section(
        self, 
        title: str, 
        content: str, 
        category: str, 
        max_length: int = 300
    ) -> str:
        """Generate a newsletter section for the given content.
        
        Args:
            title: The title of the content.
            content: The content to include in the newsletter.
            category: The category of the content.
            max_length: The maximum length of the section in words.
            
        Returns:
            A formatted newsletter section in Markdown.
            
        Raises:
            Exception: If there's an error generating the newsletter section.
        """
        try:
            system_prompt = """
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
            """
            
            user_prompt = f"""
            Please create a newsletter section for the following technical content:
            
            Title: {title}
            Category: {category}
            
            Content:
            {content[:4000]}  # Truncate to avoid token limits
            
            Keep your section under {max_length} words and format it in Markdown.
            """
            
            response = self.openai_client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            section = response.choices[0].message.content
            
            logger.info(f"Generated newsletter section of length {len(section.split())} words")
            
            return section
        except Exception as e:
            logger.error(f"Error generating newsletter section: {e}")
            raise



ai_processor = None

def get_ai_processor():
    """Get or create the singleton AI processor instance.
    
    Returns:
        The AIProcessor instance.
    """
    global ai_processor
    if ai_processor is None:
        try:
            ai_processor = AIProcessor()
        except Exception as e:
            logger.error(f"Error creating AIProcessor: {e}")
            raise
    return ai_processor


def categorize_content(content: str) -> Dict[str, Any]:
    """Categorize technical content into predefined categories.
    
    This is a convenience function that uses the singleton ai_processor instance.
    
    Args:
        content: The content to categorize.
        
    Returns:
        A dictionary containing the category information.
    """
    return get_ai_processor().categorize_content(content)


def summarize_content(content: str, max_length: int = 200) -> str:
    """Summarize technical content.
    
    This is a convenience function that uses the singleton ai_processor instance.
    
    Args:
        content: The content to summarize.
        max_length: The maximum length of the summary in words.
        
    Returns:
        A summary of the content.
    """
    return get_ai_processor().summarize_content(content, max_length)


def generate_insights(content: str) -> List[str]:
    """Generate key insights from technical content.
    
    This is a convenience function that uses the singleton ai_processor instance.
    
    Args:
        content: The content to analyze.
        
    Returns:
        A list of key insights extracted from the content.
    """
    return get_ai_processor().generate_insights(content)


def evaluate_relevance(content: str) -> float:
    """Evaluate the technical relevance of content.
    
    This is a convenience function that uses the singleton ai_processor instance.
    
    Args:
        content: The content to evaluate.
        
    Returns:
        A relevance score between 0.0 and 1.0.
    """
    return get_ai_processor().evaluate_relevance(content)


def generate_newsletter_section(
    title: str, 
    content: str, 
    category: str, 
    max_length: int = 300
) -> str:
    """Generate a newsletter section for the given content.
    
    This is a convenience function that uses the singleton ai_processor instance.
    
    Args:
        title: The title of the content.
        content: The content to include in the newsletter.
        category: The category of the content.
        max_length: The maximum length of the section in words.
        
    Returns:
        A formatted newsletter section in Markdown.
    """
    return get_ai_processor().generate_newsletter_section(title, content, category, max_length)
