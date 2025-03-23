# Optimization Strategies

This document outlines key optimization opportunities for the Opossum Search platform across various components. These strategies enhance performance, reliability, and resource efficiency without compromising the system's hybrid architecture.

## Model Selection Optimization

### Weighted Selection Caching

```python
# Cache model selection decisions in Redis
async def get_optimal_backend(self, query_type, has_image=False):
    # Generate cache key from request parameters
    cache_key = f"model_selection:{query_type}:{has_image}"
    
    # Check cache first
    cached_result = await self.redis_client.get(cache_key)
    if cached_result:
        return cached_result.decode('utf-8')
    
    # Calculate optimal backend when not cached
    selected_backend = await self._calculate_backend_scores(query_type, has_image)
    
    # Cache result for future requests
    await self.redis_client.setex(
        cache_key, 
        Config.MODEL_SELECTION_CACHE_TTL, 
        selected_backend
    )
    
    return selected_backend
```

### Fast Path Selection

```python
# Implement fast paths for common scenarios
def get_fast_path(self, query_type, has_image=False):
    """Fast selection paths to avoid full scoring calculation"""
    # Multimodal requests prioritize Gemini when available
    if has_image and self.services.is_gemini_available:
        return "gemini-thinking"
        
    # Simple greetings use lightweight models
    if query_type == "greeting" and self.services.is_ollama_available:
        return "gemma"
        
    # Complex reasoning favors Gemini
    if query_type == "reasoning" and self.services.is_gemini_available:
        return "gemini-thinking"
    
    # Fall through to standard weighted selection
    return None
```

## Redis Caching Strategies

### Multi-Level Response Caching

```python
async def get_cached_response(self, query, context):
    """Implement multi-level caching with context awareness"""
    # Try exact match (highest priority, short TTL)
    exact_key = f"response:exact:{hashlib.md5(query.encode()).hexdigest()}"
    exact_match = await self.redis.get(exact_key)
    if exact_match:
        return json.loads(exact_match)
    
    # For non-critical contexts, try semantic matching (longer TTL)
    if context != "critical_response":
        embedding = await self.get_embedding(query)
        similar_queries = await self.find_similar_queries(embedding)
        
        for similar_key in similar_queries:
            cached = await self.redis.get(f"response:exact:{similar_key}")
            if cached:
                return json.loads(cached)
    
    # Cache miss - will need to generate new response
    return None
```

### Availability Cache Refresh

```python
class ServiceMonitor:
    async def start_refresh_task(self):
        """Start background refresh of service availability"""
        async def _refresh_loop():
            while True:
                try:
                    # Check all services
                    await self.check_all_services()
                    
                    # Update Redis cache with latest status
                    for service, status in self.services.items():
                        await self.redis.setex(
                            f"service:status:{service}",
                            Config.AVAILABILITY_CACHE_TTL,
                            "1" if status else "0"
                        )
                    
                    # Wait before next check
                    await asyncio.sleep(Config.AVAILABILITY_CHECK_INTERVAL)
                except Exception as e:
                    logger.error(f"Error in availability refresh: {e}")
                    await asyncio.sleep(5)  # Shorter retry on error
        
        self.refresh_task = asyncio.create_task(_refresh_loop())
        return self.refresh_task
```

## Parallel Processing

### Concurrent Service Checks

```python
async def check_all_services(self):
    """Check all services concurrently"""
    tasks = [
        self.check_service("gemini"),
        self.check_service("ollama"),
        self.check_service("transformers")
    ]
    
    # Use gather to run all checks in parallel
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Process results, handling any exceptions
    status_updates = {}
    for i, result in enumerate(results):
        service_name = ["gemini", "ollama", "transformers"][i]
        
        if isinstance(result, Exception):
            logger.error(f"Error checking {service_name}: {result}")
            status_updates[service_name] = False
        else:
            status_updates[service_name] = result
    
    # Update global service status
    self.update_service_status(status_updates)
```

### Parallel Image Processing

```python
async def process_image(self, image_data, target_size=512):
    """Process image with parallel operations"""
    async def resize_image():
        with wand.image.Image(blob=image_data) as img:
            img.resize(target_size, target_size)
            return img.make_blob()
    
    async def extract_metadata():
        with wand.image.Image(blob=image_data) as img:
            return {
                "format": img.format,
                "width": img.width,
                "height": img.height,
                "colorspace": str(img.colorspace),
                "depth": img.depth
            }
    
    async def create_thumbnail():
        with wand.image.Image(blob=image_data) as img:
            img.resize(128, 128)
            return img.make_blob(format='webp')
    
    # Run all processing tasks concurrently
    resized, metadata, thumbnail = await asyncio.gather(
        resize_image(),
        extract_metadata(),
        create_thumbnail()
    )
    
    return {
        "processed": resized,
        "metadata": metadata,
        "thumbnail": thumbnail
    }
```

## Memory Optimization

### Efficient Transformers Loading

```python
def initialize_transformers_model():
    """Load transformers model with optimal memory settings"""
    model_name = Config.MODEL_CONFIGS["gemma"]["transformers_name"]
    
    # Configure quantization based on available hardware
    if torch.cuda.is_available():
        # Use 8-bit quantization on GPU
        return AutoModelForCausalLM.from_pretrained(
            model_name,
            device_map="auto",
            load_in_8bit=True,
            torch_dtype=torch.float16
        )
    else:
        # CPU optimization
        return AutoModelForCausalLM.from_pretrained(
            model_name,
            device_map={"": "cpu"},
            low_cpu_mem_usage=True
        )
```

### Connection Pooling

```python
class HttpClientPool:
    """Manage persistent HTTP connections for external services"""
    def __init__(self):
        # Shared connection pools by service
        self.clients = {
            "ollama": httpx.AsyncClient(
                base_url=Config.OLLAMA_BASE_URL,
                timeout=30.0,
                limits=httpx.Limits(max_connections=20),
                http2=True
            ),
            "telemetry": httpx.AsyncClient(
                base_url=Config.OTEL_EXPORTER_OTLP_ENDPOINT,
                timeout=5.0,
                limits=httpx.Limits(max_connections=5)
            )
        }
    
    def get_client(self, service_name):
        """Get client for specific service"""
        return self.clients.get(service_name)
    
    async def close_all(self):
        """Close all connections when shutting down"""
        for client in self.clients.values():
            await client.aclose()
```

## API Optimization

### Rate Limiting & Queueing

```python
class GeminiRequestQueue:
    """Queue for rate-limited Gemini API requests"""
    def __init__(self):
        self.queue = asyncio.Queue()
        self.worker_task = None
        self.daily_tokens = 0
        self.daily_requests = 0
        self.tokens_lock = asyncio.Lock()
    
    async def start_worker(self):
        """Process queued requests at controlled rate"""
        async def _worker():
            while True:
                # Get next request from queue
                request_data, future = await self.queue.get()
                try:
                    # Process with rate limiting
                    result = await self._process_request(request_data)
                    future.set_result(result)
                except Exception as e:
                    future.set_exception(e)
                finally:
                    # Rate limit - ensure minimum time between requests
                    await asyncio.sleep(60 / Config.GEMINI_RPM_LIMIT)
                    self.queue.task_done()
        
        self.worker_task = asyncio.create_task(_worker())
    
    async def enqueue_request(self, request_data):
        """Add request to processing queue"""
        # Check daily limits
        async with self.tokens_lock:
            if self.daily_requests >= Config.GEMINI_DAILY_LIMIT:
                raise Exception("Daily request limit exceeded")
        
        # Create future for async result
        future = asyncio.Future()
        await self.queue.put((request_data, future))
        return await future
```

### Smart Retries

```python
async def request_with_retry(self, func, *args, max_retries=3, **kwargs):
    """Generic retry wrapper with exponential backoff"""
    retry = 0
    last_exception = None
    
    while retry <= max_retries:
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            retry += 1
            
            # Don't retry certain errors
            if isinstance(e, (AuthenticationError, RateLimitExceeded)):
                raise
                
            # Calculate exponential backoff with jitter
            backoff = min(30, 0.5 * (2 ** (retry - 1)) * (1 + random.random()))
            logger.warning(f"Attempt {retry}/{max_retries} failed: {e}. Retrying in {backoff:.2f}s")
            await asyncio.sleep(backoff)
    
    # All retries failed
    logger.error(f"All {max_retries} retry attempts failed")
    raise last_exception
```

## Monitoring & Diagnostics

### Performance Tracing

```python
async def process_query(self, query, context=None):
    """Process user query with performance tracking"""
    with tracer.start_as_current_span("process_query") as span:
        # Add context to span
        span.set_attribute("query.length", len(query))
        span.set_attribute("query.context", context or "none")
        
        start_time = time.time()
        
        # Get optimal backend
        backend_start = time.time()
        backend = await self.get_optimal_backend(query, context)
        backend_time = time.time() - backend_start
        span.set_attribute("backend.selection.time_ms", backend_time * 1000)
        span.set_attribute("backend.selected", backend)
        
        # Generate response
        generate_start = time.time()
        response = await self.generate_response(query, backend)
        generate_time = time.time() - generate_start
        span.set_attribute("response.generation.time_ms", generate_time * 1000)
        
        # Record total processing time
        total_time = time.time() - start_time
        span.set_attribute("query.total_time_ms", total_time * 1000)
        
        return response
```

### Adaptive Quality Control

```python
async def monitor_response_quality(self, query, response, backend):
    """Track response quality metrics for adaptive improvement"""
    # Calculate basic metrics
    response_length = len(response)
    query_length = len(query)
    ratio = response_length / max(1, query_length)
    
    # Calculate response time
    response_time = self.response_times.get(backend, [])
    if response_time:
        avg_time = sum(response_time) / len(response_time)
    else:
        avg_time = 0
    
    # Update quality metrics in Redis
    await self.redis.hset(
        f"quality:backend:{backend}",
        mapping={
            "avg_response_ratio": (self.quality_metrics.get("ratio", 0) + ratio) / 2,
            "avg_response_time": avg_time,
            "total_requests": self.quality_metrics.get("requests", 0) + 1
        }
    )
    
    # If quality falling below threshold, adjust selection weights
    if ratio < 0.5 and avg_time > 2.0:
        # Reduce preference for this backend
        await self.adjust_backend_weights(backend, factor=0.8)
```

## Configuration Management

### Environment-Based Settings

```python
# Example production settings for .env file
FLASK_ENV=production
API_KEY_REQUIRED=true
GRAPHQL_GRAPHIQL=false
VOYAGER_ENABLED=false
GEMINI_DAILY_LIMIT=1000
REDIS_PASSWORD=secure_password_here
CACHE_TTL=3600
CORS_ALLOWED_ORIGINS=https://app.example.com,https://studio.apollographql.com
```

By implementing these optimizations, you'll significantly enhance your system's performance and reliability while maintaining its flexible architecture.