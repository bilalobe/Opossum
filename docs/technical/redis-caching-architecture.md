# Technical Documentation: Redis Caching Architecture

## 1. Overview

Opossum Search implements a sophisticated multi-level caching system using Redis to optimize performance, reduce
duplicate computation, and manage distributed state across the application. This architecture supports high throughput
while minimizing latency and external API usage.

> **Related Documentation:**
> - [Technical: Hybrid Model Selection](./hybrid-model-selection.md) - Cache integration with model selection
> - [Service Availability: Rate Limiting](../service-availability/rate-limiting-throttling.md) - Redis-based rate
    limiting implementation

## 2. Redis Configuration

```python
# Redis connection settings
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
REDIS_TTL = int(os.getenv("REDIS_TTL", "600"))  # Default TTL: 10 minutes
```

### 2.1 Connection Pool Management

```python
async def get_redis_pool():
    """Get or create Redis connection pool"""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = aioredis.ConnectionPool(
            host=Config.REDIS_HOST,
            port=Config.REDIS_PORT,
            db=Config.REDIS_DB,
            password=Config.REDIS_PASSWORD,
            max_connections=50,
            decode_responses=False
        )
    return _redis_pool

async def get_redis_client():
    """Get Redis client with connection pooling"""
    pool = await get_redis_pool()
    return aioredis.Redis(connection_pool=pool)
```

## 3. Cache Types and TTLs

### 3.1 Response Caching

Response caching stores LLM-generated responses to avoid redundant model calls for identical or similar queries.

```python
async def get_cached_response(self, query, backend_name):
    """Get cached response if available"""
    cache_key = f"response:{backend_name}:{hashlib.md5(query.encode()).hexdigest()}"
    cached = await self.redis.get(cache_key)
    
    if cached:
        self.metrics.increment("cache_hit", {"backend": backend_name})
        return json.loads(cached)
    
    self.metrics.increment("cache_miss", {"backend": backend_name})
    return None

async def cache_response(self, query, response, backend_name):
    """Cache a model response"""
    cache_key = f"response:{backend_name}:{hashlib.md5(query.encode()).hexdigest()}"
    await self.redis.setex(
        cache_key,
        Config.CACHE_TTL,  # 10 minutes default
        json.dumps(response)
    )
```

#### TTL Strategy

| Cache Type        | TTL         | Rationale                             |
|-------------------|-------------|---------------------------------------|
| Simple responses  | 600s (10m)  | High reuse value, low volatility      |
| Complex responses | 300s (5m)   | May become outdated faster            |
| Image processing  | 1800s (30m) | High computation cost, stable results |

### 3.2 Service Availability Cache

Tracks the operational status of backend services to avoid timeouts on unavailable services.

```python
async def check_service(self, service_name):
    """Check if a service is available with caching"""
    cache_key = f"service:available:{service_name}"
    
    # Check cache first
    cached = await self.redis.get(cache_key)
    if cached is not None:
        return cached == b"1"
        
    # Perform actual health check
    is_available = await self._perform_check(service_name)
    
    # Cache result with short TTL
    await self.redis.setex(
        cache_key, 
        Config.AVAILABILITY_CACHE_TTL,  # 30 seconds
        "1" if is_available else "0"
    )
    
    return is_available
```

### 3.3 Model Selection Cache

Caches model selection decisions to avoid recalculating optimal backend for similar requests.

```python
async def get_optimal_backend(self, query_type, has_image=False):
    """Get optimal backend with caching"""
    # Generate cache key
    cache_key = f"model:selection:{query_type}:{has_image}"
    
    # Check cache
    cached = await self.redis.get(cache_key)
    if cached:
        return cached.decode('utf-8')
    
    # Calculate optimal backend
    backend = await self._calculate_optimal_backend(query_type, has_image)
    
    # Cache result
    await self.redis.setex(
        cache_key,
        Config.MODEL_SELECTION_CACHE_TTL,  # 60 seconds
        backend
    )
    
    return backend
```

### 3.4 Rate Limiting

Implements token bucket algorithm for API rate limiting.

```python
async def is_rate_limited(self, client_id, limit_key="default"):
    """Check if client is rate limited"""
    # Get rate limit configuration
    limits = Config.get_rate_limits().get(limit_key, ["100 per day"])
    
    # Check each limit
    for limit in limits:
        count, period = self._parse_limit(limit)
        
        # Generate Redis key
        rate_key = f"ratelimit:{client_id}:{limit_key}:{period}"
        
        # Check current count
        current = await self.redis.get(rate_key) 
        if current and int(current) >= count:
            return True  # Rate limited
            
    return False  # Not rate limited

async def increment_rate_counter(self, client_id, limit_key="default"):
    """Increment rate counters for all applicable limits"""
    limits = Config.get_rate_limits().get(limit_key, ["100 per day"])
    
    for limit in limits:
        count, period = self._parse_limit(limit)
        seconds = self._period_to_seconds(period)
        
        rate_key = f"ratelimit:{client_id}:{limit_key}:{period}"
        
        # Increment counter and set TTL if it's new
        await self.redis.incr(rate_key)
        await self.redis.expire(rate_key, seconds, nx=True)
```

### 3.5 Performance Metrics

Stores historical performance metrics for model selection learning.

```python
async def record_performance(self, backend, metrics):
    """Record performance metrics for a backend"""
    now = int(time.time())
    
    # Store individual data point
    await self.redis.zadd(
        f"metrics:{backend}:history",
        {json.dumps(metrics): now}
    )
    
    # Trim to last N entries
    await self.redis.zremrangebyrank(
        f"metrics:{backend}:history",
        0,
        -Config.SERVICE_HISTORY_MAX_ITEMS - 1
    )
    
    # Update rolling averages
    for metric, value in metrics.items():
        # Get current average
        current = await self.redis.hget(f"metrics:{backend}:avg", metric)
        current = float(current) if current else value
        
        # Calculate new average (90% old, 10% new)
        new_avg = current * 0.9 + value * 0.1
        
        # Store updated average
        await self.redis.hset(f"metrics:{backend}:avg", metric, new_avg)
```

## 4. Cache Interaction Patterns

### 4.1 Cache-Aside Pattern

```python
async def generate_response(self, prompt, model):
    """Generate response with cache-aside pattern"""
    # Check cache first
    cache_key = f"response:{model}:{hashlib.md5(prompt.encode()).hexdigest()}"
    cached = await self.redis.get(cache_key)
    
    if cached:
        # Cache hit
        return json.loads(cached)
    
    # Cache miss - generate fresh response
    response = await self._call_llm_service(prompt, model)
    
    # Store in cache
    await self.redis.setex(cache_key, Config.CACHE_TTL, json.dumps(response))
    
    return response
```

### 4.2 Write-Through Pattern

```python
async def update_model_preference(self, user_id, model, score):
    """Update user model preference with write-through pattern"""
    # Update in-memory cache
    self.model_preferences[user_id][model] = score
    
    # Write through to Redis
    await self.redis.hset(f"user:{user_id}:preferences", model, score)
```

## 5. Monitoring and Maintenance

### 5.1 Cache Hit Ratio Monitoring

```python
async def get_cache_metrics(self):
    """Get cache hit/miss metrics"""
    hits = int(await self.redis.get("metrics:cache:hits") or 0)
    misses = int(await self.redis.get("metrics:cache:misses") or 0)
    
    total = hits + misses
    ratio = hits / total if total > 0 else 0
    
    return {
        "hits": hits,
        "misses": misses,
        "total": total,
        "ratio": ratio
    }
```

### 5.2 Cache Invalidation

```python
async def invalidate_model_cache(self, model_name=None):
    """Invalidate cache for specific model or all models"""
    if model_name:
        # Get all keys for this model
        keys = await self.redis.keys(f"response:{model_name}:*")
        if keys:
            await self.redis.delete(*keys)
    else:
        # Get all response cache keys
        keys = await self.redis.keys("response:*")
        if keys:
            await self.redis.delete(*keys)
```

## 6. Redis Memory Management

```python
# Redis memory policy in redis.conf
# maxmemory 1gb
# maxmemory-policy allkeys-lru
```

The Redis instance is configured with a memory limit and LRU eviction policy to automatically manage memory usage when
limits are reached.

## 7. Performance Considerations

### 7.1 Redis Pipeline for Batch Operations

```python
async def batch_update_metrics(self, metrics_list):
    """Update multiple metrics in a single pipeline"""
    pipeline = self.redis.pipeline()
    
    for backend, metrics in metrics_list:
        for metric, value in metrics.items():
            pipeline.hset(f"metrics:{backend}", metric, value)
    
    await pipeline.execute()
```

### 7.2 Key Expiration Strategy

Rather than running manual cleanup jobs, the system relies on Redis TTL (Time-To-Live) expirations to automatically
manage cache size and freshness. Keys are assigned appropriate TTLs based on data volatility and reuse patterns.

## 8. Redis High Availability Configuration

For production deployments, Redis is configured with:

- Redis Sentinel for automatic failover
- Periodic RDB snapshots for persistence
- Monitoring integration with system alerts

This Redis caching architecture enables Opossum Search to maintain high performance while minimizing external API usage
and providing resilience against backend service disruptions.