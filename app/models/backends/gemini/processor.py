"""Processing utilities for Gemini responses."""
import base64
import logging
from typing import Dict, Any, List, Optional

from app.config import Config

logger = logging.getLogger(__name__)


class GeminiResponseProcessor:
    """Processor for Gemini API responses and input preparation."""
    
    def process_image_data(self, image_data: str) -> bytes:
        """Process base64 image data for Gemini API.
        
        Args:
            image_data: Base64-encoded image data, possibly with MIME prefix
            
        Returns:
            Raw image bytes
            
        Raises:
            ValueError: If image data is invalid
        """
        # Extract base64 data if it includes a MIME prefix
        if image_data.startswith('data:image'):
            try:
                image_data = image_data.split(',')[1]
            except IndexError:
                raise ValueError("Invalid image data format")
                
        # Decode the base64 data
        try:
            decoded_image = base64.b64decode(image_data)
            return decoded_image
        except Exception as e:
            logger.error(f"Failed to decode base64 image: {e}")
            raise ValueError("Invalid base64 image data")
    
    def extract_keywords(self, text: str, max_keywords: int = 5) -> List[str]:
        """Extract keywords from response text.
        
        Args:
            text: The response text to analyze
            max_keywords: Maximum number of keywords to extract
            
        Returns:
            List of extracted keywords
        """
        # Simple keyword extraction - in a real implementation,
        # this could use NLP techniques or additional Gemini calls
        words = text.lower().split()
        stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'is', 'are', 'was'}
        keywords = [word for word in words 
                   if word not in stopwords and len(word) > 3]
        
        # Count occurrences and sort by frequency
        word_counts = {}
        for word in keywords:
            word_counts[word] = word_counts.get(word, 0) + 1
            
        sorted_keywords = sorted(word_counts.items(), 
                                key=lambda x: x[1], reverse=True)
        
        return [word for word, _ in sorted_keywords[:max_keywords]]
    
    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract entities from response text.
        
        Args:
            text: The response text to analyze
            
        Returns:
            Dictionary with entity types and values
        """
        # In a real implementation, this would use NLP or additional API calls
        # For now, just look for opossum-related terms as a simple example
        opossum_terms = ['opossum', 'marsupial', 'possum', 'didelphis', 'virginia']
        found_terms = []
        
        for term in opossum_terms:
            if term.lower() in text.lower():
                found_terms.append(term)
                
        return {
            "opossum_terms": found_terms,
            "locations": [],  # Would be populated in a real implementation
            "dates": []       # Would be populated in a real implementation
        }