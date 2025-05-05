"""Content standardiser for the newsletter generator.

This module provides a class for standardising content from different sources
into a consistent Markdown format.
"""

import re
from typing import Optional

from newsletter_generator.utils.logging_utils import get_logger

logger = get_logger("ingestion.content_standardiser")


class ContentStandardiser:
    """Standardises content into a consistent Markdown format.
    
    This class ensures that content from different sources (HTML, PDF, YouTube)
    is formatted consistently as Markdown.
    """
    
    def __init__(self):
        """Initialise the content standardiser."""
        pass
    
    def standardise(self, content: str) -> str:
        """Standardise content into a consistent Markdown format.
        
        Args:
            content: The content to standardise, already in basic Markdown format.
            
        Returns:
            The standardised content as Markdown.
        """
        logger.info("Standardising content")
        
        if not content:
            logger.warning("Empty content provided for standardisation")
            return "# Empty Content\n\n*No content was provided*"
        
        try:
            standardised = re.sub(r'\n{3,}', '\n\n', content)
            
            standardised = re.sub(r'([^\n])(#+ )', r'\1\n\n\2', standardised)
            standardised = re.sub(r'(#+ .+?)(\n[^#\n])', r'\1\n\2', standardised)
            
            standardised = re.sub(r'([^\n])(\n[*-] )', r'\1\n\2', standardised)
            
            standardised = re.sub(r'([^\n])(\n```)', r'\1\n\2', standardised)
            standardised = re.sub(r'(```\n)([^\n])', r'\1\n\2', standardised)
            
            standardised = re.sub(r'([^\n])(\n> )', r'\1\n\2', standardised)
            
            if not standardised.strip().startswith('#'):
                title = "Extracted Content"
                standardised = f"# {title}\n\n{standardised}"
            
            if not standardised.endswith('\n'):
                standardised += '\n'
            
            logger.debug("Content standardisation completed")
            return standardised
        except Exception as e:
            logger.error(f"Error standardising content: {e}")
            return content
