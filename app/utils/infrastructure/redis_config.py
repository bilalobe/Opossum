import logging

import redis

from app.config import Config

logger = logging.getLogger(__name__)

# Redis connection pool
redis_pool = redis.ConnectionPool(
    host=getattr(Config, 'REDIS_HOST', 'localhost'),
    port=getattr(Config, 'REDIS_PORT', 6379),
    db=getattr(Config, 'REDIS_DB', 0),
    decode_responses=True
)

# Redis client instance
redis_client = redis.Redis(connection_pool=redis_pool)


def get_redis_cache(key):
    """Get value from Redis cache"""
    return redis_client.get(key)


def set_redis_cache(key, value, expire=None):
    """Set value in Redis cache with optional expiration"""
    if expire:
        redis_client.setex(key, expire, value)
    else:
        redis_client.set(key, value)


def delete_redis_cache(key):
    """Delete value from Redis cache"""
    redis_client.delete(key)


def check_redis_health():
    """Check Redis connection health"""
    try:
        redis_client.ping()
        return True
    except redis.ConnectionError as e:
        logger.error(f"Redis connection error: {str(e)}")
        return False


def clear_redis_cache():
    """Clear all keys in Redis cache"""
    try:
        redis_client.flushdb()
        return True
    except redis.RedisError as e:
        logger.error(f"Error clearing Redis cache: {str(e)}")
        return False
