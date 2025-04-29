"""Content standardizer for the newsletter generator.

This module provides a class for standardizing content from different sources
into a consistent Markdown format.
"""

import re
from typing import Optional

from newsletter_generator.utils.logging_utils import get_logger

logger = get_logger("ingestion.content_standardizer")


class ContentStandardizer:
    """Standardizes content into a consistent Markdown format.
    
    This class ensures that content from different sources (HTML, PDF, YouTube)
    is formatted consistently as Markdown.
    """
    
    def __init__(self):
        """Initialize the content standardizer."""
        pass
    
    def standardize(self, content: str) -> str:
        """Standardize content into a consistent Markdown format.
        
        Args:
            content: The content to standardize, already in basic Markdown format.
            
        Returns:
            The standardized content as Markdown.
        """
        logger.info("Standardizing content")
        
        if not content:
            logger.warning("Empty content provided for standardization")
            return "# Empty Content\n\n*No content was provided*"
        
        try:
            standardized = re.sub(r'\n{3,}', '\n\n', content)
            
            standardized = re.sub(r'([^\n])(#+ )', r'\1\n\n\2', standardized)
            standardized = re.sub(r'(#+ .+?)(\n[^#\n])', r'\1\n\2', standardized)
            
            standardized = re.sub(r'([^\n])(\n[*-] )', r'\1\n\2', standardized)
            
            standardized = re.sub(r'([^\n])(\n```)', r'\1\n\2', standardized)
            standardized = re.sub(r'(```\n)([^\n])', r'\1\n\2', standardized)
            
            standardized = re.sub(r'([^\n])(\n> )', r'\1\n\2', standardized)
            
            if not standardized.strip().startswith('#'):
                title = "Extracted Content"
                standardized = f"# {title}\n\n{standardized}"
            
            if not standardized.endswith('\n'):
                standardized += '\n'
            
            logger.debug("Content standardization completed")
            return standardized
        except Exception as e:
            logger.error(f"Error standardizing content: {e}")
            return content
