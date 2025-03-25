"""Cache infrastructure for API responses and data."""

import logging
from typing import Any, Optional

from cachetools import TTLCache, LRUCache

logger = logging.getLogger(__name__)

# Cache for API responses with TTL (Time to Live)
_api_cache = TTLCache(maxsize=1000, ttl=300)  # 5 minute TTL by default

# Cache for computed data that doesn't need to expire
_data_cache = LRUCache(maxsize=500)


def get_from_cache(key: str) -> Optional[Any]:
    """Get a value from the appropriate cache."""
    if key.startswith('api_'):
        return _api_cache.get(key)
    return _data_cache.get(key)


def add_to_cache(key: str, value: Any, ttl: Optional[int] = None) -> None:
    """
    Add a value to the cache.
    
    Args:
        key: Cache key
        value: Value to cache
        ttl: Time to live in seconds (only for API cache)
    """
    try:
        if key.startswith('api_'):
            # If TTL provided, create a new cache entry with custom TTL
            if ttl:
                temp_cache = TTLCache(maxsize=1, ttl=ttl)
                temp_cache[key] = value
                _api_cache.update(temp_cache)
            else:
                _api_cache[key] = value
        else:
            _data_cache[key] = value

        logger.debug(f"Cached {key} {'with TTL' if ttl else ''}")
    except Exception as e:
        logger.warning(f"Failed to cache {key}: {e}")


def invalidate_cache(key_prefix: str = None) -> None:
    """
    Invalidate cache entries.
    
    Args:
        key_prefix: If provided, only invalidate keys starting with this prefix
    """
    try:
        if key_prefix:
            # Clear matching keys from both caches
            _api_cache.clear()
            _data_cache.clear()
            logger.info(f"Cleared cache entries with prefix {key_prefix}")
        else:
            # Clear all caches
            _api_cache.clear()
            _data_cache.clear()
            logger.info("Cleared all cache entries")
    except Exception as e:
        logger.error(f"Failed to invalidate cache: {e}")


def get_cache_stats() -> dict:
    """Get cache statistics."""
    return {
        "api_cache": {
            "size": len(_api_cache),
            "maxsize": _api_cache.maxsize,
            "currsize": _api_cache.currsize,
            "ttl": _api_cache.ttl
        },
        "data_cache": {
            "size": len(_data_cache),
            "maxsize": _data_cache.maxsize,
            "currsize": _data_cache.currsize
        }
    }


def configure_cache(api_maxsize: int = 1000, api_ttl: int = 300,
                    data_maxsize: int = 500) -> None:
    """Configure cache parameters."""
    global _api_cache, _data_cache

    _api_cache = TTLCache(maxsize=api_maxsize, ttl=api_ttl)
    _data_cache = LRUCache(maxsize=data_maxsize)
    logger.info(f"Configured caches: API({api_maxsize}, {api_ttl}s), Data({data_maxsize})")
