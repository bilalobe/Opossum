"""Request clustering for batch optimization."""
import logging
import numpy as np
from typing import List, Optional
from ..pipeline import PipelineState

logger = logging.getLogger(__name__)


class RequestClusterer:
    """Groups similar requests using text embeddings."""
    
    def __init__(self, eps: float = 0.5, min_samples: int = 2):
        self.embedder = self._initialize_embedder()
        self.eps = eps
        self.min_samples = min_samples
        
    def _initialize_embedder(self):
        """Initialize the sentence transformer model."""
        try:
            from sentence_transformers import SentenceTransformer
            return SentenceTransformer('all-MiniLM-L6-v2')
        except ImportError:
            logger.warning("SentenceTransformers not available, using fallback embedder")
            return None
            
    def cluster(self, requests: List[PipelineState]) -> np.ndarray:
        """Group similar requests based on their prompts."""
        if not self.embedder:
            return np.zeros(len(requests))
            
        try:
            from sklearn.cluster import DBSCAN
            
            # Extract prompts
            prompts = [r.prompt for r in requests]
            
            # Generate embeddings
            embeddings = self.embedder.encode(prompts)
            
            # Cluster embeddings
            clusterer = DBSCAN(eps=self.eps, min_samples=self.min_samples)
            clusters = clusterer.fit_predict(embeddings)
            
            # Log clustering results
            unique_clusters = len(set(clusters[clusters >= 0]))
            noise_points = np.sum(clusters == -1)
            logger.debug(
                f"Clustered {len(requests)} requests into {unique_clusters} clusters "
                f"with {noise_points} noise points"
            )
            
            return clusters
            
        except Exception as e:
            logger.error(f"Clustering failed: {e}")
            return np.zeros(len(requests))
            
    def get_cluster_stats(self, clusters: np.ndarray) -> dict:
        """Get statistics about the clustering results."""
        if not isinstance(clusters, np.ndarray):
            return {}
            
        return {
            "total_requests": len(clusters),
            "num_clusters": len(set(clusters[clusters >= 0])),
            "noise_points": np.sum(clusters == -1),
            "largest_cluster": max(np.bincount(clusters[clusters >= 0])) if any(clusters >= 0) else 0,
            "cluster_sizes": list(np.bincount(clusters[clusters >= 0])) if any(clusters >= 0) else []
        }