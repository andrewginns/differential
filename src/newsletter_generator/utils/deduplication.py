"""Deduplication utilities for the newsletter generator.

This module provides functions for URL normalisation, content fingerprinting,
and other utilities to prevent duplicate content in the system.
"""

import hashlib
from typing import List, Set
from urllib.parse import urlparse, parse_qs, urlencode, ParseResult

from newsletter_generator.utils.logging_utils import get_logger

logger = get_logger("utils.deduplication")

def normalise_url(url: str) -> str:
    """Normalise URL by removing tracking parameters and standardising format.
    
    Args:
        url: The URL to normalise.
        
    Returns:
        The normalised URL string.
    """
    try:
        parsed = urlparse(url)
        
        # Extract base parameters and filter out tracking parameters
        query_params = parse_qs(parsed.query)
        filtered_params = {k: v for k, v in query_params.items() if k not in [
            'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
            'source', 'ref', 'fbclid', 'gclid', 'ocid', 'mc_cid', 'mc_eid'
        ]}
        
        # Rebuild query string
        new_query = urlencode(filtered_params, doseq=True) if filtered_params else ''
        
        # Rebuild URL with normalised components
        normalised = ParseResult(
            scheme=parsed.scheme.lower(),
            netloc=parsed.netloc.lower(),
            path=parsed.path,
            params=parsed.params,
            query=new_query,
            fragment=''  # Remove fragments like #section
        ).geturl()
        
        return normalised
    except Exception as e:
        logger.warning(f"Error normalising URL {url}: {e}")
        return url

def get_url_hash(url: str) -> str:
    """Generate a consistent hash for a URL after normalisation.
    
    Args:
        url: The URL to hash.
        
    Returns:
        A hexadecimal hash string of the normalised URL.
    """
    normalised_url = normalise_url(url)
    return hashlib.sha256(normalised_url.encode()).hexdigest()

def extract_significant_words(text: str, min_length: int = 4, max_words: int = 1000) -> Set[str]:
    """Extract significant words from text for fingerprinting.
    
    Args:
        text: The text to extract words from.
        min_length: Minimum word length to consider significant.
        max_words: Maximum number of significant words to return.
        
    Returns:
        A set of significant words.
    """
    # Simple tokenisation by splitting on whitespace
    words = text.split()
    
    # Filter out short words and common stopwords
    stopwords = {"and", "the", "for", "with", "this", "that", "from", "what", "have", "been"}
    significant = {w.lower() for w in words 
                  if len(w) >= min_length and w.lower() not in stopwords}
    
    # Return up to max_words most significant words
    return set(sorted(significant)[:max_words])

def generate_content_fingerprint(content: str, title: str = "") -> str:
    """Generate a fingerprint of content that's resistant to minor changes.
    
    Args:
        content: The main content text.
        title: Optional title to include in fingerprinting.
        
    Returns:
        A hexadecimal hash string representing the content fingerprint.
    """
    try:
        # Normalise content
        combined_text = (title + " " + content).lower()
        
        # Extract significant words
        significant_words = extract_significant_words(combined_text)
        
        # Create a stable fingerprint
        words_str = " ".join(sorted(significant_words))
        return hashlib.sha256(words_str.encode()).hexdigest()
    except Exception as e:
        logger.warning(f"Error generating content fingerprint: {e}")
        # Fallback to simple hash of full content
        return hashlib.sha256((title + content).encode()).hexdigest()

def calculate_content_similarity(content1: str, content2: str) -> float:
    """Calculate similarity between two content strings using Jaccard similarity.
    
    Args:
        content1: First content string.
        content2: Second content string.
        
    Returns:
        Similarity score between 0.0 and 1.0.
    """
    try:
        # Extract significant words from both contents
        words1 = extract_significant_words(content1.lower())
        words2 = extract_significant_words(content2.lower())
        
        # Calculate Jaccard similarity
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        if union == 0:
            return 0.0
            
        return intersection / union
    except Exception as e:
        logger.warning(f"Error calculating content similarity: {e}")
        return 0.0 