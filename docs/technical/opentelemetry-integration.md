# Technical Documentation: OpenTelemetry Integration

## 1. Overview

Opossum Search implements comprehensive observability using OpenTelemetry to monitor application performance, track
request flows, and diagnose issues across its distributed architecture. This integration enables detailed visibility
into system behavior, performance bottlenecks, and service dependencies.

## 2. OpenTelemetry Configuration

```python
# OpenTelemetry Configuration
OTEL_EXPORTER_OTLP_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318/v1/traces")
OTEL_SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "opossum-search")
OTEL_ENABLED = os.getenv("OTEL_ENABLED", "True").lower() == "true"
```

### 2.1 Initialization

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv.resource import ResourceAttributes

def initialize_telemetry():
    """Initialize OpenTelemetry for distributed tracing"""
    if not Config.OTEL_ENABLED:
        return
    
    # Create resource information
    resource = Resource.create({
        ResourceAttributes.SERVICE_NAME: Config.OTEL_SERVICE_NAME,
        ResourceAttributes.SERVICE_VERSION: "1.0.0",
        "environment": Config.ENV
    })
    
    # Set up tracer provider
    provider = TracerProvider(resource=resource)
    
    # Create OTLP exporter
    otlp_exporter = OTLPSpanExporter(endpoint=Config.OTEL_EXPORTER_OTLP_ENDPOINT)
    span_processor = BatchSpanProcessor(otlp_exporter)
    provider.add_span_processor(span_processor)
    
    # Set global tracer provider
    trace.set_tracer_provider(provider)
    
    # Create global tracer
    return trace.get_tracer(__name__)
```

## 3. Tracing Request Flow

### 3.1 GraphQL Request Tracing

```python
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# Instrument FastAPI application
def instrument_fastapi(app):
    """Instrument FastAPI with OpenTelemetry"""
    if Config.OTEL_ENABLED:
        FastAPIInstrumentor.instrument_app(
            app,
            excluded_urls="/health,/metrics",
            tracer_provider=trace.get_tracer_provider()
        )
```

### 3.2 Model Backend Tracing

```python
async def generate_response(self, prompt, model_name):
    """Generate response with OpenTelemetry tracing"""
    tracer = trace.get_tracer(__name__)
    
    with tracer.start_as_current_span(
        "model.generate", 
        attributes={
            "prompt.length": len(prompt),
            "model.name": model_name
        }
    ) as span:
        try:
            # Record start time
            start_time = time.time()
            
            # Call model backend
            response = await self._call_model_backend(prompt, model_name)
            
            # Calculate and record duration
            duration = time.time() - start_time
            span.set_attribute("duration_seconds", duration)
            span.set_attribute("response.length", len(response))
            
            return response
        except Exception as e:
            # Record error information
            span.record_exception(e)
            span.set_status(trace.StatusCode.ERROR, str(e))
            raise
```

## 4. Custom Metrics and Events

### 4.1 Service Availability Monitoring

```python
async def check_service(self, service_name):
    """Check service availability with metrics recording"""
    tracer = trace.get_tracer(__name__)
    
    with tracer.start_as_current_span(
        "service.check", 
        attributes={"service.name": service_name}
    ) as span:
        # Record check attempt
        span.add_event("check_started")
        
        try:
            # Perform actual check
            is_available = await self._perform_actual_check(service_name)
            
            # Record result
            span.set_attribute("service.available", is_available)
            span.add_event(
                "check_completed", 
                {"result": "available" if is_available else "unavailable"}
            )
            
            return is_available
        except Exception as e:
            # Record error
            span.record_exception(e)
            span.set_status(trace.StatusCode.ERROR, str(e))
            span.add_event("check_failed", {"error": str(e)})
            return False
```

### 4.2 Cache Hit/Miss Monitoring

```python
async def get_cached_item(self, key):
    """Get cached item with telemetry"""
    tracer = trace.get_tracer(__name__)
    
    with tracer.start_as_current_span(
        "cache.get", 
        attributes={"cache.key": key}
    ) as span:
        # Try to get from cache
        value = await self.redis_client.get(key)
        
        # Record hit/miss
        hit = value is not None
        span.set_attribute("cache.hit", hit)
        
        # Record in aggregated metrics
        if hit:
            await self.redis_client.incr("metrics:cache:hits")
        else:
            await self.redis_client.incr("metrics:cache:misses")
        
        return value
```

## 5. Custom Context Propagation

```python
from opentelemetry.context import Context, get_current
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

class ContextCarrier:
    """Carries context between async tasks"""
    def __init__(self):
        self.context = {}
    
    def get(self, key, default=None):
        return self.context.get(key, default)
    
    def set(self, key, value):
        self.context[key] = value

def extract_context_for_background_task():
    """Extract current context to pass to background task"""
    carrier = ContextCarrier()
    propagator = TraceContextTextMapPropagator()
    propagator.inject(carrier, get_current())
    return carrier

async def run_in_background(func, *args, parent_context=None, **kwargs):
    """Run function in background with parent trace context"""
    if parent_context and Config.OTEL_ENABLED:
        propagator = TraceContextTextMapPropagator()
        context = propagator.extract(parent_context)
        token = context.attach()
        try:
            return await func(*args, **kwargs)
        finally:
            context.detach(token)
    else:
        return await func(*args, **kwargs)
```

## 6. External Service Integration

### 6.1 Ollama API Tracing

```python
async def generate_ollama_response(self, prompt, model):
    """Trace Ollama API requests"""
    tracer = trace.get_tracer(__name__)
    
    with tracer.start_as_current_span(
        "ollama.generate", 
        attributes={
            "prompt.length": len(prompt),
            "model.name": model
        }
    ) as span:
        try:
            # Create request
            url = f"{Config.OLLAMA_BASE_URL}/api/generate"
            payload = {
                "prompt": prompt,
                "model": model,
                "stream": False
            }
            
            # Add request details to span
            span.set_attribute("http.url", url)
            span.set_attribute("http.method", "POST")
            
            # Send request
            start_time = time.time()
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=60.0)
            
            # Add response details
            span.set_attribute("http.status_code", response.status_code)
            span.set_attribute("http.response_time", time.time() - start_time)
            
            # Handle response
            if response.status_code == 200:
                data = response.json()
                return data.get("response", "")
            else:
                error_msg = f"Ollama API error: {response.status_code}"
                span.set_status(trace.StatusCode.ERROR, error_msg)
                raise Exception(error_msg)
                
        except Exception as e:
            span.record_exception(e)
            span.set_status(trace.StatusCode.ERROR, str(e))
            raise
```

### 6.2 Gemini API Tracing

```python
async def generate_gemini_response(self, prompt, image_data=None):
    """Trace Gemini API requests"""
    tracer = trace.get_tracer(__name__)
    
    with tracer.start_as_current_span(
        "gemini.generate", 
        attributes={
            "prompt.length": len(prompt),
            "has_image": image_data is not None
        }
    ) as span:
        try:
            # Initialize Gemini client
            gemini_client = AsyncGeminiClient(api_key=Config.GEMINI_API_KEY)
            model = Config.MODEL_CONFIGS["gemini-thinking"]["api_name"]
            
            # Add request details to span
            span.set_attribute("model.name", model)
            
            # Prepare content parts
            content_parts = [{"text": prompt}]
            if image_data:
                # Add image to content parts
                span.set_attribute("image.size", len(image_data))
                content_parts.append({
                    "inline_data": {
                        "mime_type": "image/jpeg",
                        "data": base64.b64encode(image_data).decode('utf-8')
                    }
                })
            
            # Generate response
            start_time = time.time()
            response = await gemini_client.generate_content(
                model=model,
                contents=[{"parts": content_parts}]
            )
            
            # Record performance metrics
            duration = time.time() - start_time
            span.set_attribute("duration_seconds", duration)
            
            # Extract response text
            if response and response.candidates:
                result = response.candidates[0].content.parts[0].text
                span.set_attribute("response.length", len(result))
                return result
            else:
                span.set_status(trace.StatusCode.ERROR, "Empty response from Gemini")
                return "No response generated"
                
        except Exception as e:
            span.record_exception(e)
            span.set_status(trace.StatusCode.ERROR, str(e))
            raise
```

## 7. Visualization and Monitoring

```python
# Visualization endpoints
@app.get("/metrics")
async def metrics():
    """Expose metrics for Prometheus scraping"""
    if not Config.OTEL_ENABLED:
        return {"error": "OpenTelemetry is disabled"}
    
    return Response(
        content=generate_latest().decode("utf-8"),
        media_type="text/plain"
    )

@app.get("/traces/recent")
async def recent_traces():
    """Get recent traces for UI display"""
    # This would typically be handled by a trace visualization tool like Jaeger
    # This endpoint just provides basic info for quick debugging
    
    recent = await redis_client.lrange("traces:recent", 0, 9)
    return [json.loads(trace) for trace in recent]
```

## 8. Deployment Configuration

For production deployments, OpenTelemetry traces are sent to a collector service that can export to various backends:

```yaml
# docker-compose excerpt for OpenTelemetry collector
services:
  otel-collector:
    image: otel/opentelemetry-collector:0.97.0
    command: ["--config=/etc/otel-config.yaml"]
    volumes:
      - ./otel-config.yaml:/etc/otel-config.yaml
    ports:
      - "4318:4318"  # OTLP HTTP receiver
      - "9464:9464"  # Prometheus exporter

  # Visualization with Jaeger
  jaeger:
    image: jaegertracing/all-in-one:latest
    ports:
      - "16686:16686"  # Jaeger UI
      - "14250:14250"  # Receive from collector
```

### 8.1 Collector Configuration

```yaml
# otel-config.yaml
receivers:
  otlp:
    protocols:
      http:
        endpoint: 0.0.0.0:4318

processors:
  batch:
    timeout: 1s
    send_batch_size: 1024

exporters:
  jaeger:
    endpoint: jaeger:14250
    tls:
      insecure: true
  prometheus:
    endpoint: 0.0.0.0:9464
    namespace: opossum
  logging:
    loglevel: info

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch]
      exporters: [jaeger, logging]
    metrics:
      receivers: [otlp]
      processors: [batch]
      exporters: [prometheus, logging]
```

The OpenTelemetry integration provides comprehensive observability for Opossum Search, enabling performance monitoring,
troubleshooting, and service dependency tracking across the distributed architecture.