"""Cache configuration and settings."""

from datetime import timedelta
from typing import TypeVar

# Type variable for cache value types
T = TypeVar('T')

# Default cache settings
DEFAULT_TTL = timedelta(minutes=10)
DEFAULT_MAX_SIZE = 100
DEFAULT_PRUNE_SIZE = 75  # When pruning, keep this many items

# Image processing specific cache settings
IMAGE_CACHE_TTL = timedelta(minutes=5)
IMAGE_CACHE_MAX_SIZE = 50
IMAGE_MAX_DIMENSION = 4096

# Service response cache settings
SERVICE_CACHE_TTL = timedelta(seconds=30)
SERVICE_CACHE_MAX_SIZE = 200

# Metrics cache settings
METRICS_CACHE_TTL = timedelta(seconds=10)
METRICS_CACHE_MAX_SIZE = 50


class CacheConfig:
    """Cache configuration container."""

    def __init__(self, ttl: timedelta = DEFAULT_TTL, max_size: int = DEFAULT_MAX_SIZE):
        self.ttl = ttl
        self.max_size = max_size
        self.prune_size = min(max_size, DEFAULT_PRUNE_SIZE)

    @classmethod
    def for_images(cls) -> 'CacheConfig':
        """Get cache config optimized for image processing."""
        return cls(ttl=IMAGE_CACHE_TTL, max_size=IMAGE_CACHE_MAX_SIZE)

    @classmethod
    def for_services(cls) -> 'CacheConfig':
        """Get cache config optimized for service responses."""
        return cls(ttl=SERVICE_CACHE_TTL, max_size=SERVICE_CACHE_MAX_SIZE)

    @classmethod
    def for_metrics(cls) -> 'CacheConfig':
        """Get cache config optimized for metrics data."""
        return cls(ttl=METRICS_CACHE_TTL, max_size=METRICS_CACHE_MAX_SIZE)
