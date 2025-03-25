"""DataLoader implementations for efficient data fetching.

DataLoaders help batch and cache database/API requests to avoid the N+1 query problem
in GraphQL resolvers.
"""
import logging
from functools import lru_cache
from typing import List, Dict, Any

from promise import Promise

from app.models.availability import ServiceAvailability
from app.utils.infrastructure.cache_factory import cache

logger = logging.getLogger(__name__)


class ServiceStatusLoader:
    """DataLoader for service status information."""

    def __init__(self):
        self.service_availability = ServiceAvailability()
        self.batch_load_fn = self.batch_load_services

    async def batch_load_services(self, keys: List[str]) -> Promise:
        """Batch load service status for multiple services at once."""
        logger.debug(f"Batch loading service status for: {keys}")

        # Check if we have a recent cached result
        cache_key = "service_status_batch"
        cached_result = cache.get(cache_key)

        if cached_result:
            logger.debug("Using cached service status")
            return Promise.resolve([cached_result.get(key, {}) for key in keys])

        # Otherwise, fetch fresh data
        await self.service_availability.check_all_services()
        results = {}

        for key in keys:
            if key in self.service_availability.service_status:
                results[key] = self.service_availability.service_status[key]
            else:
                results[key] = {"available": False, "status": "unknown"}

        # Cache the results for 10 seconds
        cache.set(cache_key, results, expire=10)

        # Return results in the same order as the requested keys
        return Promise.resolve([results.get(key, {}) for key in keys])


class ModelLoader:
    """DataLoader for AI model information."""

    def __init__(self):
        self.batch_load_fn = self.batch_load_models

    @lru_cache(maxsize=32)
    def get_model_config(self, model_name: str) -> Dict[str, Any]:
        """Get configuration for a model with caching."""
        from app.config import Config
        return Config.MODEL_CONFIGS.get(model_name, {})

    async def batch_load_models(self, keys: List[str]) -> Promise:
        """Batch load model configurations."""
        logger.debug(f"Batch loading model info for: {keys}")

        results = []
        for model_name in keys:
            results.append(self.get_model_config(model_name))

        return Promise.resolve(results)


# Create instances for use in resolvers
service_loader = ServiceStatusLoader()
model_loader = ModelLoader()

__all__ = ['service_loader', 'model_loader']
