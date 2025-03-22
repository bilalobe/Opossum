import logging
from typing import Optional, Any
from cachetools import TTLCache
from app.utils.infrastructure.redis_config import redis_client, check_redis_health

logger = logging.getLogger(__name__)

class CacheFactory:
    """Factory class to provide appropriate cache implementation"""
    
    def __init__(self):
        self.local_cache = TTLCache(maxsize=1000, ttl=3600)  # 1 hour TTL
        self._use_redis = check_redis_health()
        if not self._use_redis:
            logger.warning("Redis unavailable, falling back to local in-memory cache")
    
    def get(self, key: str) -> Optional[str]:
        """Get value from cache"""
        try:
            if self._use_redis:
                return redis_client.get(key)
            return self.local_cache.get(key)
        except Exception as e:
            logger.error(f"Cache get error: {str(e)}")
            self._use_redis = False
            return self.local_cache.get(key)
    
    def set(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """Set value in cache with optional expiration"""
        try:
            if self._use_redis:
                if expire:
                    return redis_client.setex(key, expire, value)
                return redis_client.set(key, value)
            
            self.local_cache[key] = value
            return True
        except Exception as e:
            logger.error(f"Cache set error: {str(e)}")
            self._use_redis = False
            self.local_cache[key] = value
            return True
    
    def delete(self, key: str) -> bool:
        """Delete value from cache"""
        try:
            if self._use_redis:
                return bool(redis_client.delete(key))
            
            if key in self.local_cache:
                del self.local_cache[key]
                return True
            return False
        except Exception as e:
            logger.error(f"Cache delete error: {str(e)}")
            self._use_redis = False
            if key in self.local_cache:
                del self.local_cache[key]
                return True
            return False
    
    def clear(self) -> bool:
        """Clear all cache entries"""
        try:
            if self._use_redis:
                return redis_client.flushdb()
            
            self.local_cache.clear()
            return True
        except Exception as e:
            logger.error(f"Cache clear error: {str(e)}")
            self._use_redis = False
            self.local_cache.clear()
            return True

# Global cache instance
cache = CacheFactory()