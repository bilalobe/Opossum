"""Request clustering for batch optimization."""

import logging
import numpy as np
from typing import List, Any, Optional
from sklearn.cluster import DBSCAN

logger = logging.getLogger(__name__)

class RequestClusterer:
    """Groups similar requests using text embeddings."""
    
    def __init__(self):
        """Initialize request clusterer."""
        self.embedder = self._initialize_embedder()
        self.clusterer = DBSCAN(eps=0.5, min_samples=2)
        
    def _initialize_embedder(self):
        """Initialize sentence embedder."""
        try:
            from sentence_transformers import SentenceTransformer
            return SentenceTransformer('all-MiniLM-L6-v2')
        except ImportError:
            logger.warning("SentenceTransformers not available, using fallback embedder")
            return None
            
    def cluster(self, requests: List[Any]) -> np.ndarray:
        """Cluster requests based on prompt similarity.
        
        Args:
            requests: List of PipelineState objects
            
        Returns:
            Array of cluster assignments (same length as requests)
        """
        if not self.embedder:
            return np.zeros(len(requests))
            
        try:
            # Extract prompts
            prompts = [getattr(r, 'prompt', '') for r in requests]
            if not prompts:
                return np.zeros(len(requests))
                
            # Generate embeddings
            embeddings = self.embedder.encode(prompts)
            
            # Cluster embeddings
            labels = self.clusterer.fit_predict(embeddings)
            
            return labels
            
        except Exception as e:
            logger.error(f"Clustering failed: {e}")
            return np.zeros(len(requests))