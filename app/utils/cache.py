from cachetools import TTLCache
from app.config import Config

# Initialize cache with settings from config
response_cache = TTLCache(maxsize=Config.CACHE_MAXSIZE, ttl=Config.CACHE_TTL)

def get_from_cache(key):
    """Get a value from the cache if it exists"""
    return response_cache.get(key)

def add_to_cache(key, value):
    """Add a value to the cache with the given key"""
    response_cache[key] = value
    return value