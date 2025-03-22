"""Service-specific DataLoader implementations."""
import logging
from promise import Promise

from app.models.availability import ServiceAvailability 
from app.utils.infrastructure.cache_factory import cache

logger = logging.getLogger(__name__)

class ServiceLoader:
    """DataLoader for service status information."""
    
    def __init__(self):
        self.service_availability = ServiceAvailability()
        
    async def load_many(self, keys):
        """Load multiple service statuses in one batch."""
        cache_key = "service_status_batch"
        cached_result = cache.get(cache_key)
        
        if cached_result:
            logger.debug("Using cached service status")
            return [cached_result.get(key, {}) for key in keys]
        
        # Fetch fresh data
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
        return [results.get(key, {}) for key in keys]
    
    async def load(self, key):
        """Load a single service status."""
        results = await self.load_many([key])
        return results[0]
    
    def clear(self):
        """Clear the cache."""
        cache.delete("service_status_batch")
        
# Create an instance to use in resolvers
service_loader = ServiceLoader()

__all__ = ['service_loader']