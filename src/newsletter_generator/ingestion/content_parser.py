"""Content parsers for the newsletter generator.

This module provides classes for parsing content from different sources:
- HTML content using Trafilatura as a fallback for Crawl4AI
- PDF content using PyMuPDF (Fitz)
- YouTube transcripts using string manipulation
"""

from typing import Dict, Any, List, Optional, Union

import fitz  # PyMuPDF
import trafilatura

from newsletter_generator.utils.logging_utils import get_logger

logger = get_logger("ingestion.content_parser")


class HTMLContentParser:
    """Parses HTML content.
    
    This class primarily relies on Crawl4AI's built-in Markdown generation,
    with Trafilatura as a fallback or supplementary method.
    """
    
    def __init__(self):
        """Initialize the HTML content parser."""
        pass
    
    def parse(self, content: Dict[str, Any], url: str) -> str:
        """Parse HTML content.
        
        Args:
            content: The content dictionary from the HTML fetcher, containing
                'markdown', 'html', and other metadata.
            url: The source URL.
            
        Returns:
            The parsed content as Markdown.
            
        Raises:
            Exception: If there's an error parsing the content.
        """
        logger.info(f"Parsing HTML content from {url}")
        
        try:
            if content.get('markdown') and len(content['markdown']) > 100:
                logger.debug("Using Crawl4AI's Markdown output")
                return content['markdown']
            
            logger.debug("Falling back to Trafilatura for HTML parsing")
            html = content.get('html', '')
            if not html:
                raise Exception("No HTML content available for parsing")
            
            extracted_text = trafilatura.extract(
                html,
                output_format='markdown',
                include_links=True,
                include_images=True,
                include_tables=True,
            )
            
            if not extracted_text:
                logger.warning(f"Trafilatura failed to extract content from {url}")
                title = content.get('title', 'Untitled')
                return f"# {title}\n\n*Content extraction failed*"
            
            return extracted_text
        except Exception as e:
            logger.error(f"Error parsing HTML content from {url}: {e}")
            raise


class PDFContentParser:
    """Parses PDF content using PyMuPDF (Fitz).
    
    This class extracts text from PDF documents.
    """
    
    def __init__(self):
        """Initialize the PDF content parser."""
        pass
    
    def parse(self, content: bytes) -> str:
        """Parse PDF content.
        
        Args:
            content: The raw PDF content as bytes.
            
        Returns:
            The extracted text as Markdown.
            
        Raises:
            Exception: If there's an error parsing the PDF.
        """
        logger.info("Parsing PDF content")
        
        try:
            doc = fitz.open(stream=content, filetype="pdf")
            
            text_parts = []
            for page_num, page in enumerate(doc):
                text = page.get_text()
                if text.strip():
                    text_parts.append(text)
            
            doc.close()
            
            if not text_parts:
                logger.warning("No text extracted from PDF")
                return "# PDF Document\n\n*No text content could be extracted*"
            
            full_text = "\n\n".join(text_parts)
            
            markdown = f"# PDF Document\n\n{full_text}"
            
            return markdown
        except Exception as e:
            logger.error(f"Error parsing PDF content: {e}")
            raise


class YouTubeContentParser:
    """Parses YouTube transcript data.
    
    This class converts transcript segments into a coherent text.
    """
    
    def __init__(self):
        """Initialize the YouTube content parser."""
        pass
    
    def parse(self, transcript_data: List[Dict[str, Any]]) -> str:
        """Parse YouTube transcript data.
        
        Args:
            transcript_data: A list of transcript segments, each containing
                'text' and 'start' keys.
            
        Returns:
            The transcript as Markdown.
            
        Raises:
            Exception: If there's an error parsing the transcript.
        """
        logger.info("Parsing YouTube transcript")
        
        try:
            if not transcript_data:
                logger.warning("Empty transcript data")
                return "# YouTube Video Transcript\n\n*No transcript available*"
            
            text_parts = []
            for segment in transcript_data:
                text = segment.get('text', '').strip()
                if text:
                    text_parts.append(text)
            
            if not text_parts:
                logger.warning("No text extracted from transcript data")
                return "# YouTube Video Transcript\n\n*No transcript content could be extracted*"
            
            full_text = " ".join(text_parts)
            
            markdown = f"# YouTube Video Transcript\n\n{full_text}"
            
            return markdown
        except Exception as e:
            logger.error(f"Error parsing YouTube transcript: {e}")
            raise
