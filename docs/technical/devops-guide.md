# Technical Documentation: Deployment & Operations Guide

## 1. Deployment Overview

This guide outlines the processes and best practices for deploying, configuring, monitoring, and maintaining Opossum
Search in various environments.

## 2. Environment Setup

### 2.1 System Requirements

| Component | Minimum | Recommended           | Notes                                        |
|-----------|---------|-----------------------|----------------------------------------------|
| CPU       | 2 cores | 4+ cores              | 8+ cores for high-volume production          |
| RAM       | 8GB     | 16GB                  | 32GB+ for multiple local models              |
| Storage   | 5GB     | 20GB                  | SSD recommended for model loading            |
| Network   | 10Mbps  | 100Mbps+              | Reliable connection for external APIs        |
| GPU       | None    | NVIDIA with 8GB+ VRAM | For [Ollama](https://ollama.ai/) performance |

### 2.2 Software Dependencies

```bash
# Install system dependencies
sudo apt-get update
sudo apt-get install -y \
    [python3.11](https://docs.python.org/3.11/) \
    python3.11-dev \
    python3-pip \
    python3-venv \
    redis-server # [Redis](https://redis.io/) in-memory data structure store
    imagemagick # [ImageMagick](https://imagemagick.org/index.php) for image processing
    libmagickwand-dev
    build-essential

# Install NVIDIA drivers and CUDA toolkit (for GPU support)
# Skip this section if not using GPU
sudo apt-get install -y nvidia-driver-535 nvidia-cuda-toolkit
```

### 2.3 Environment Configurations

| Environment   | Description                 | Use Case                                    |
|---------------|-----------------------------|---------------------------------------------|
| `development` | Local setup for developers  | Feature development, testing                |
| `staging`     | Production-like environment | Integration testing, pre-release validation |
| `production`  | Live deployment             | End-user service                            |

## 3. Installation Procedures

### 3.1 Docker-based Deployment (Recommended)

```bash
# Clone repository
git clone https://github.com/yourusername/opossum-search.git
cd opossum-search

# Setup environment file
cp .env.example .env
# Edit .env file with appropriate settings

# Start with Docker Compose
docker-compose up -d
```

#### Docker Compose File

```yaml
# docker-compose.yml
version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - REDIS_HOST=redis
      - ENV=production
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318/v1/traces
    depends_on:
      - redis
      - ollama
      - otel-collector
    volumes:
      - ./models:/app/models
      - ./config:/app/config

  redis:
    image: redis:7.0-alpine
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes
    volumes:
      - redis-data:/data

  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama-models:/root/.ollama
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

  otel-collector:
    image: otel/opentelemetry-collector:0.97.0
    command: ["--config=/etc/otel-config.yaml"]
    volumes:
      - ./otel-config.yaml:/etc/otel-config.yaml
    ports:
      - "4318:4318"
      - "9464:9464"

  jaeger:
    image: jaegertracing/all-in-one:latest
    ports:
      - "16686:16686"
      - "14250:14250"

volumes:
  redis-data:
  ollama-models:
```

### 3.2 Kubernetes Deployment

```yaml
# app-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: opossum-search
spec:
  replicas: 3
  selector:
    matchLabels:
      app: opossum-search
  template:
    metadata:
      labels:
        app: opossum-search
    spec:
      containers:
      - name: opossum-search
        image: opossum-search:latest
        ports:
        - containerPort: 8000
        env:
        - name: REDIS_HOST
          value: redis-service
        - name: ENV
          value: production
        - name: GEMINI_API_KEY
          valueFrom:
            secretKeyRef:
              name: api-keys
              key: gemini-api-key
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
```

### 3.3 Manual Installation

```bash
# Clone repository
git clone https://github.com/yourusername/opossum-search.git
cd opossum-search

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env file with appropriate settings

# Run application
python -m app
```

## 4. Configuration Management

Effective configuration is crucial for adapting Opossum Search to different environments (`development`, `staging`, `production`). Configuration is primarily managed through environment variables and Python configuration files (`config/*.py`).

### 4.1 Environment Variables

| Variable                      | Purpose                                              | Example                      |
|-------------------------------|------------------------------------------------------|------------------------------|
| `ENV`                         | Deployment environment                               | `production`                 |
| `DEBUG`                       | Enable debug mode                                    | `False`                      |
| `GEMINI_API_KEY`              | API key for [Gemini](https://ai.google.dev/)         | `your-api-key`               |
| `REDIS_HOST`                  | [Redis](https://redis.io/) server hostname           | `redis`                      |
| `REDIS_PORT`                  | [Redis](https://redis.io/) server port               | `6379`                       |
| `REDIS_PASSWORD`              | [Redis](https://redis.io/) password                  | `secure-password`            |
| `OLLAMA_BASE_URL`             | [Ollama](https://ollama.ai/) server URL              | `http://ollama:11434`        |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | [OpenTelemetry](https://opentelemetry.io/) collector | `http://otel-collector:4318` |
| `FLASK_APP`                   | Flask application entry point                        | `app.py`                     |
| `FLASK_ENV`                   | Flask environment                                    | `production`                 |
| `DATABASE_URL`                | Database connection URL                              | `postgres://user:password@host/db` |
| `SECRET_KEY`                  | Secret key for Flask application                     | `your-secret-key`            |
| `LOG_LEVEL`                   | Logging level                                        | `INFO`                       |
| `OTEL_ENABLED`                | Enable OpenTelemetry                                 | `True`                       |
| `OTEL_SERVICE_NAME`           | OpenTelemetry service name                           | `opossum-search`             |

### 4.2 Configuration Files

Environment-specific Python files (e.g., `config/development.py`, `config/production.py`) inherit from a base `Config` class and override settings.

**Key Configuration Settings:**

- **Logging:**
    - `LOG_LEVEL`: Sets the logging level (e.g., 'DEBUG', 'INFO', 'WARNING').
- **OpenTelemetry:**
    - `OTEL_ENABLED`: Boolean to enable/disable OpenTelemetry integration.
    - `OTEL_SERVICE_NAME`: Name reported to the OTLP collector.
    - `OTEL_EXPORTER_OTLP_ENDPOINT`: URL of the OTLP collector.
- **Circuit Breaker Settings:**
    - `CIRCUIT_BREAKER_FAILURE_THRESHOLD`: Default failure count before opening (e.g., 5).
    - `CIRCUIT_BREAKER_RESET_TIMEOUT`: Default seconds before attempting recovery (e.g., 60).
    - `[SERVICE_NAME]_CIRCUIT_BREAKER_ENABLED`: Boolean to enable/disable breaker for 'gemini', 'ollama', 'transformers'. Defaults to `True` for external, `False` for local `transformers`.
    - `[SERVICE_NAME]_FAILURE_THRESHOLD`: Service-specific failure threshold override.
    - `[SERVICE_NAME]_RESET_TIMEOUT`: Service-specific reset timeout override.
- **Retry Policy Settings:**
    - `DEFAULT_MAX_RETRIES`: Default maximum retry attempts for services (e.g., 3).
    - `DEFAULT_RETRY_DELAY`: Default base delay (seconds) between retries (e.g., 1.0).
    - `[SERVICE_NAME]_MAX_RETRIES`: Service-specific max retries override (e.g., 'gemini', 'ollama'). Defaults to 0 for `transformers`.
    - `[SERVICE_NAME]_RETRY_DELAY`: Service-specific base delay override.
- **API Keys & Endpoints:**
    - `GEMINI_API_KEY`, `OLLAMA_HEALTH_URL`, etc.
- **Rate Limits:**
    - `GEMINI_DAILY_LIMIT`, `GEMINI_RPM_LIMIT`, etc.
- **Model Settings:**
    - `MAX_TOKENS`, `TEMPERATURE`, `TOP_P`, `TOP_K`.
    - `USE_QUANTIZED_MODELS`, `MODEL_PRECISION`, `QUANTIZED_MODEL_DIR`.
- **Other:**
    - `REQUEST_TIMEOUT`, `TRANSFORMERS_WORKERS`, `AVAILABILITY_CHECK_INTERVAL`.

Refer to `app/config.py` for the full list and default values.

### 4.3 Secrets Management

API keys and other sensitive credentials should **never** be hardcoded in configuration files. Use environment variables or a dedicated secrets management system (like HashiCorp Vault, AWS Secrets Manager, etc.) accessed during application startup. The `Config` class typically reads these from the environment.

```bash
# Create Kubernetes secrets
kubectl create secret generic api-keys \
  --from-literal=gemini-api-key=your-gemini-api-key \
  --from-literal=redis-password=your-redis-password
```

## 5. Scaling Strategies

### 5.1 Horizontal Scaling

```yaml
# Kubernetes HPA configuration
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: opossum-search-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: opossum-search
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### 5.2 Redis Scaling

#### Single Instance Configuration

```conf
# redis.conf for single instance
maxmemory 1gb
maxmemory-policy allkeys-lru
appendonly yes
```

#### Redis Sentinel Configuration

```conf
# sentinel.conf
sentinel monitor mymaster redis-master 6379 2
sentinel down-after-milliseconds mymaster 5000
sentinel failover-timeout mymaster 60000
sentinel parallel-syncs mymaster 1
```

### 5.3 Model Optimization for Scale

```python
# Example model optimization settings for scaled deployments
MODEL_CONFIGS = {
    "gemini-thinking": {
        "api_name": "gemini-1.5-pro",
        "max_tokens": 1024,
        "temperature": 0.7,
        "top_p": 0.95,
    },
    "gemma": {
        "top_k": 40,
        "temperature": 0.8,
        "response_format": {"type": "text"},
    },
    "transformers": {
        "transformers_name": "google/gemma-2b",
        "max_length": 512,
        "device_map": "auto",  # Automatically select best device
    }
}
```

## 6. Monitoring and Alerting

### 6.1 Health Checks

```python
# app/api/health.py
@app.get("/health")
async def health_check():
    """System health check"""
    status = {
        "status": "ok",
        "version": Config.VERSION,
        "timestamp": datetime.datetime.now().isoformat(),
        "services": {}
    }
    
    # Check Redis
    try:
        redis_ping = await redis_client.ping()
        status["services"]["redis"] = "ok" if redis_ping else "error"
    except Exception as e:
        status["services"]["redis"] = f"error: {str(e)}"
    
    # Check Ollama
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{Config.OLLAMA_BASE_URL}/api/tags")
            status["services"]["ollama"] = "ok" if response.status_code == 200 else "error"
    except Exception as e:
        status["services"]["ollama"] = f"error: {str(e)}"
    
    # Check model availability
    service_monitor = ServiceMonitor()
    await service_monitor.check_all_services()
    status["services"]["model_backends"] = {
        k: "available" if v else "unavailable"
        for k, v in service_monitor.services.items()
    }
    
    # Set overall status
    if any(v != "ok" and not v.startswith("available") 
           for v in [*status["services"].values(), *status["services"]["model_backends"].values()]):
        status["status"] = "degraded"
        
    return status
```

### 6.2 Prometheus Metrics

```python
# app/monitoring/metrics.py
from prometheus_client import Counter, Histogram, Gauge

# Define metrics
REQUESTS_TOTAL = Counter(
    "opossum_requests_total", 
    "Total number of requests",
    ["method", "endpoint"]
)

RESPONSE_TIME = Histogram(
    "opossum_response_time_seconds",
    "Response time in seconds",
    ["method", "endpoint"]
)

MODEL_USAGE = Counter(
    "opossum_model_usage_total",
    "Total model usage count",
    ["model_name"]
)

CACHE_HITS = Counter(
    "opossum_cache_hits_total",
    "Total cache hits",
    ["cache_type"]
)

CACHE_MISSES = Counter(
    "opossum_cache_misses_total",
    "Total cache misses",
    ["cache_type"]
)

SERVICE_AVAILABILITY = Gauge(
    "opossum_service_availability",
    "Service availability status (1=available, 0=unavailable)",
    ["service_name"]
)
```

### 6.3 Alerting Configuration

```yaml
# prometheus/alert-rules.yml
groups:
- name: opossum-alerts
  rules:
  - alert: HighErrorRate
    expr: rate(opossum_requests_total{status="error"}[5m]) / rate(opossum_requests_total[5m]) > 0.05
    for: 2m
    labels:
      severity: critical
    annotations:
      summary: "High error rate detected"
      description: "Error rate is above 5% for the last 2 minutes"

  - alert: ServiceUnavailable
    expr: opossum_service_availability == 0
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "Service unavailable"
      description: "{{ $labels.service_name }} has been unavailable for 5 minutes"

  - alert: HighResponseTime
    expr: histogram_quantile(0.95, rate(opossum_response_time_seconds_bucket[5m])) > 2
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High response time"
      description: "95th percentile response time is above 2 seconds for 5 minutes"
```

## 7. Backup and Recovery

### 7.1 Redis Backup

```bash
# Automated Redis backup script
#!/bin/bash
BACKUP_DIR="/backups/redis"
TIMESTAMP=$(date +%Y%m%d%H%M%S)
BACKUP_FILE="$BACKUP_DIR/redis-$TIMESTAMP.rdb"

# Ensure backup directory exists
mkdir -p $BACKUP_DIR

# Trigger Redis save
redis-cli save

# Copy RDB file
cp /var/lib/redis/dump.rdb $BACKUP_FILE

# Compress backup
gzip $BACKUP_FILE

# Keep last 7 days of backups
find $BACKUP_DIR -name "redis-*.rdb.gz" -mtime +7 -delete
```

### 7.2 Application State Backup

```python
# app/management/backup.py
async def export_system_state():
    """Export critical system state"""
    state = {
        "timestamp": datetime.datetime.now().isoformat(),
        "version": Config.VERSION,
        "service_status": {},
        "model_weights": {},
        "cache_stats": {}
    }
    
    # Get service availability
    service_monitor = ServiceMonitor()
    await service_monitor.check_all_services()
    state["service_status"] = service_monitor.services
    
    # Get model selection weights
    backend = HybridModelBackend()
    state["model_weights"] = backend.get_model_weights()
    
    # Get cache statistics
    cache_stats = await redis_client.info("stats")
    state["cache_stats"] = {
        "hits": cache_stats.get("keyspace_hits", 0),
        "misses": cache_stats.get("keyspace_misses", 0),
        "keys": await redis_client.dbsize()
    }
    
    # Export to file
    export_path = f"backups/state-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.json"
    with open(export_path, "w") as f:
        json.dump(state, f, indent=2)
        
    return export_path
```

### 7.3 Recovery Procedures

```bash
# Redis recovery
#!/bin/bash
BACKUP_FILE=$1

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 backup-file.rdb.gz"
    exit 1
fi

# Stop Redis
sudo systemctl stop redis-server

# Decompress backup if needed
if [[ $BACKUP_FILE == *.gz ]]; then
    gunzip -c $BACKUP_FILE > /tmp/dump.rdb
    BACKUP_FILE="/tmp/dump.rdb"
fi

# Replace Redis data file
sudo cp $BACKUP_FILE /var/lib/redis/dump.rdb
sudo chown redis:redis /var/lib/redis/dump.rdb

# Start Redis
sudo systemctl start redis-server

# Verify Redis is running
redis-cli ping
```

## 8. Maintenance Procedures

### 8.1 Model Updates

```bash
# Update Ollama models script
#!/bin/bash
MODELS=("gemma:latest" "llava:latest" "all-minilm:latest")

for MODEL in "${MODELS[@]}"; do
    echo "Updating $MODEL..."
    ollama pull $MODEL
done

# Verify models
ollama list
```

### 8.2 Dependency Updates

```bash
# Update dependencies
pip install --upgrade -r requirements.txt

# Check for security vulnerabilities
pip-audit
```

### 8.3 Performance Tuning

```python
# Example memory optimization settings
import torch

def optimize_for_environment():
    """Apply optimal settings based on environment"""
    total_memory = torch.cuda.get_device_properties(0).total_memory if torch.cuda.is_available() else 0
    
    if torch.cuda.is_available():
        if total_memory > 8 * (1024**3):  # More than 8GB VRAM
            return {
                "device_map": "auto",
                "load_in_8bit": False,
                "torch_dtype": torch.float16
            }
        else:  # Less than 8GB VRAM
            return {
                "device_map": "auto",
                "load_in_8bit": True,
                "torch_dtype": torch.float16
            }
    else:  # CPU only
        return {
            "device_map": {"": "cpu"},
            "low_cpu_mem_usage": True
        }
```

## 9. Troubleshooting Common Issues

### 9.1 Service Unavailability

| Issue                                            | Diagnosis                                              | Resolution                                                           |
|--------------------------------------------------|--------------------------------------------------------|----------------------------------------------------------------------|
| [Gemini API](https://ai.google.dev/) unavailable | Check API key validity and rate limits                 | Verify API key and check Google Cloud console for quota              |
| [Ollama](https://ollama.ai/) service down        | Check logs with `docker logs ollama`                   | Restart service and verify model availability                        |
| [Redis](https://redis.io/) connection error      | Check [Redis](https://redis.io/) logs and connectivity | Verify [Redis](https://redis.io/) is running and properly configured |

### 9.2 Performance Issues

| Issue                 | Diagnosis                                       | Resolution                                               |
|-----------------------|-------------------------------------------------|----------------------------------------------------------|
| High response time    | Check request concurrency and model performance | Scale horizontally and optimize model selection weights  |
| Memory leaks          | Monitor memory usage over time                  | Implement proper garbage collection and restart services |
| Slow image processing | Check image size and transformation pipeline    | Optimize image processing parameters and caching         |

### 9.3 Debug Commands

```bash
# Check service health
curl http://localhost:8000/health

# View service logs
docker logs opossum-search-app

# Check Redis performance
redis-cli info stats

# Monitor API performance
curl http://localhost:8000/metrics

# Test model availability
curl -X POST http://localhost:11434/api/generate -d '{
  "model": "gemma",
  "prompt": "Hello",
  "stream": false
}'
```

## 10. Security Considerations

### 10.1 API Key Rotation

```bash
# Rotate API keys in Kubernetes
kubectl create secret generic api-keys \
  --from-literal=gemini-api-key=new-gemini-api-key \
  --from-literal=redis-password=new-redis-password \
  --dry-run=client -o yaml | kubectl apply -f -

# Restart pods to apply new keys
kubectl rollout restart deployment opossum-search
```

### 10.2 SSL Configuration

```yaml
# ingress.yaml for TLS
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: opossum-search-ingress
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
  - hosts:
    - api.opossum-search.com
    secretName: opossum-search-tls
  rules:
  - host: api.opossum-search.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: opossum-search-service
            port:
              number: 8000
```

This Deployment & Operations Guide provides comprehensive instructions for deploying, configuring, monitoring, and
maintaining the Opossum Search platform across various environments. Follow these best practices to ensure reliable
operation and optimal performance of your deployment.