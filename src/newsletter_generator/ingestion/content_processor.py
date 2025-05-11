"""Content processor interface and implementations for the newsletter generator.

This module provides a unified interface for processing different content types
through a common workflow of fetching, parsing, and standardising content.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple, List, Type

from newsletter_generator.utils.logging_utils import get_logger

from newsletter_generator.ingestion.content_fetcher import (
    HTMLContentFetcher,
    PDFContentFetcher,
    YouTubeContentFetcher,
)
from newsletter_generator.ingestion.content_parser import (
    HTMLContentParser,
    PDFContentParser,
    YouTubeContentParser,
)
from newsletter_generator.ingestion.content_standardiser import ContentStandardiser

logger = get_logger("ingestion.content_processor")


class ContentProcessorInterface(ABC):
    """Interface for content processors.
    
    This abstract base class defines the interface for content processors, which
    handle fetching, parsing, and standardising content from different sources.
    """
    
    @abstractmethod
    async def fetch(self, url: str) -> Any:
        """Fetch content from a URL.
        
        Args:
            url: The URL to fetch content from.
            
        Returns:
            The raw content from the URL, in a format appropriate for the content type.
            
        Raises:
            Exception: If there's an error fetching the content.
        """
        pass
    
    @abstractmethod
    def parse(self, raw_content: Any, url: str = "") -> Dict[str, Any]:
        """Parse raw content into a structured format.
        
        Args:
            raw_content: The raw content to parse.
            url: Optional URL, which may be needed for some parsing strategies.
            
        Returns:
            The parsed content.
            
        Raises:
            Exception: If there's an error parsing the content.
        """
        pass
    
    @abstractmethod
    def standardise(self, parsed_content: Dict[str, Any]) -> str:
        """Standardise parsed content into a consistent format.
        
        Args:
            parsed_content: The parsed content to standardise.
            
        Returns:
            The standardised content as a string.
            
        Raises:
            Exception: If there's an error standardising the content.
        """
        pass
    
    async def process(self, url: str) -> Tuple[str, Dict[str, Any]]:
        """Process content from a URL through the full pipeline.
        
        This method orchestrates the fetch, parse, and standardise steps.
        
        Args:
            url: The URL to process.
            
        Returns:
            A tuple containing the standardised content and metadata.
            
        Raises:
            Exception: If there's an error processing the content.
        """
        try:
            logger.info(f"Processing URL: {url}")
            
            raw_content = await self.fetch(url)
            parsed_content = self.parse(raw_content, url)
            standardised_content = self.standardise(parsed_content)
            
            metadata = {
                "url": url,
                "source_type": self.get_content_type(),
                "status": "pending_ai",
            }
            
            return standardised_content, metadata
        except Exception as e:
            logger.error(f"Error processing URL {url}: {e}")
            raise
    
    @abstractmethod
    def get_content_type(self) -> str:
        """Get the content type handled by this processor.
        
        Returns:
            The content type string (e.g., "html", "pdf", "youtube").
        """
        pass


class HTMLContentProcessor(ContentProcessorInterface):
    """Processor for HTML content."""
    
    def __init__(self):
        """Initialise the HTML content processor."""
        self.fetcher = HTMLContentFetcher()
        self.parser = HTMLContentParser()
        self.standardiser = ContentStandardiser()
    
    async def fetch(self, url: str) -> Dict[str, Any]:
        """Fetch HTML content from a URL.
        
        Args:
            url: The URL to fetch content from.
            
        Returns:
            The raw HTML content dictionary.
            
        Raises:
            Exception: If there's an error fetching the content.
        """
        return await self.fetcher.fetch(url)
    
    def parse(self, raw_content: Dict[str, Any], url: str = "") -> str:
        """Parse HTML content.
        
        Args:
            raw_content: The raw HTML content dictionary.
            url: The source URL.
            
        Returns:
            The parsed content.
            
        Raises:
            Exception: If there's an error parsing the content.
        """
        return self.parser.parse(raw_content, url)
    
    def standardise(self, parsed_content: str) -> str:
        """Standardise parsed HTML content.
        
        Args:
            parsed_content: The parsed content to standardise.
            
        Returns:
            The standardised content as a string.
            
        Raises:
            Exception: If there's an error standardising the content.
        """
        return self.standardiser.standardise(parsed_content)
    
    def get_content_type(self) -> str:
        """Get the content type handled by this processor.
        
        Returns:
            The content type string "html".
        """
        return "html"


class PDFContentProcessor(ContentProcessorInterface):
    """Processor for PDF content."""
    
    def __init__(self):
        """Initialise the PDF content processor."""
        self.fetcher = PDFContentFetcher()
        self.parser = PDFContentParser()
        self.standardiser = ContentStandardiser()
    
    async def fetch(self, url: str) -> bytes:
        """Fetch PDF content from a URL.
        
        Args:
            url: The URL to fetch content from.
            
        Returns:
            The raw PDF content as bytes.
            
        Raises:
            Exception: If there's an error fetching the content.
        """
        return await self.fetcher.fetch(url)
    
    def parse(self, raw_content: bytes, url: str = "") -> str:
        """Parse PDF content.
        
        Args:
            raw_content: The raw PDF content as bytes.
            url: The source URL (not used).
            
        Returns:
            The parsed content.
            
        Raises:
            Exception: If there's an error parsing the content.
        """
        return self.parser.parse(raw_content)
    
    def standardise(self, parsed_content: str) -> str:
        """Standardise parsed PDF content.
        
        Args:
            parsed_content: The parsed content to standardise.
            
        Returns:
            The standardised content as a string.
            
        Raises:
            Exception: If there's an error standardising the content.
        """
        return self.standardiser.standardise(parsed_content)
    
    def get_content_type(self) -> str:
        """Get the content type handled by this processor.
        
        Returns:
            The content type string "pdf".
        """
        return "pdf"


class YouTubeContentProcessor(ContentProcessorInterface):
    """Processor for YouTube content."""
    
    def __init__(self):
        """Initialise the YouTube content processor."""
        self.fetcher = YouTubeContentFetcher()
        self.parser = YouTubeContentParser()
        self.standardiser = ContentStandardiser()
    
    async def fetch(self, url: str) -> List[Dict[str, Any]]:
        """Fetch YouTube transcript.
        
        Args:
            url: The URL to fetch content from.
            
        Returns:
            The raw transcript data.
            
        Raises:
            Exception: If there's an error fetching the content.
        """
        return await self.fetcher.fetch(url)
    
    def parse(self, raw_content: List[Dict[str, Any]], url: str = "") -> str:
        """Parse YouTube transcript.
        
        Args:
            raw_content: The raw transcript data.
            url: The source URL (not used).
            
        Returns:
            The parsed content.
            
        Raises:
            Exception: If there's an error parsing the content.
        """
        return self.parser.parse(raw_content)
    
    def standardise(self, parsed_content: str) -> str:
        """Standardise parsed YouTube content.
        
        Args:
            parsed_content: The parsed content to standardise.
            
        Returns:
            The standardised content as a string.
            
        Raises:
            Exception: If there's an error standardising the content.
        """
        return self.standardiser.standardise(parsed_content)
    
    def get_content_type(self) -> str:
        """Get the content type handled by this processor.
        
        Returns:
            The content type string "youtube".
        """
        return "youtube"


class ContentProcessorFactory:
    """Factory for creating content processors based on content type."""
    
    _processors: Dict[str, Type[ContentProcessorInterface]] = {
        "html": HTMLContentProcessor,
        "pdf": PDFContentProcessor,
        "youtube": YouTubeContentProcessor,
    }
    
    @classmethod
    def get_processor(cls, content_type: str) -> ContentProcessorInterface:
        """Get a content processor for the specified content type.
        
        Args:
            content_type: The content type to get a processor for.
            
        Returns:
            A content processor instance.
            
        Raises:
            ValueError: If no processor is available for the content type.
        """
        if content_type not in cls._processors:
            raise ValueError(f"No processor available for content type: {content_type}")
        
        return cls._processors[content_type]()
    
    @classmethod
    def register_processor(cls, content_type: str, processor_cls: Type[ContentProcessorInterface]):
        """Register a new processor for a content type.
        
        Args:
            content_type: The content type to register the processor for.
            processor_cls: The processor class to register.
        """
        cls._processors[content_type] = processor_cls
