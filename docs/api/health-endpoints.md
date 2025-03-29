# Health Endpoints

## Overview

Opossum Search provides dedicated health check endpoints to monitor the status and availability of various system
components. These endpoints are essential for monitoring, alerting, and ensuring service reliability. For a list of
available API routes, see [API Routes](routes.md). For detailed information about request and response formats,
see [Request/Response Documentation](request-response.md). For error code details, see [Error Codes](error-codes.md).
Information on API usage limits can be found in [Rate Limits](rate-limits.md). To learn about real-time notifications,
refer to [Webhooks](webhooks.md).

## Base Health Endpoint

```
GET /health
```

Provides an overall status of the Opossum Search system.

**Authentication**: Not required

**Response Format**:

```json
{
  "status": "healthy",
  "version": "1.8.4",
  "timestamp": "2023-03-15T14:32:45Z",
  "components": {
    "api": "healthy",
    "models": "healthy",
    "cache": "healthy",
    "database": "healthy"
  },
  "uptime": 1209467
}
```

**Possible Status Values**:

- `healthy`: All systems operating normally
- `degraded`: System is operating with reduced capabilities
- `unhealthy`: System is experiencing significant issues

## Component-Specific Health Endpoints

### API Gateway Health

```
GET /health/api
```

Checks the health of the API gateway.

**Response Format**:

```json
{
  "status": "healthy",
  "version": "1.8.4",
  "response_time": 12,
  "load": 0.35,
  "request_rate": 453.2,
  "error_rate": 0.02
}
```

### Model Service Health

```
GET /health/models
```

Checks the availability of AI models.

**Response Format**:

```json
{
  "status": "healthy",
  "models": [
    {
      "name": "gemini",
      "status": "healthy",
      "latency": 345,
      "success_rate": 0.998,
      "last_checked": "2023-03-15T14:30:15Z"
    },
    {
      "name": "ollama",
      "status": "healthy",
      "latency": 123,
      "success_rate": 0.999,
      "last_checked": "2023-03-15T14:30:10Z"
    },
    {
      "name": "local-transformers",
      "status": "healthy",
      "latency": 78,
      "success_rate": 1.0,
      "last_checked": "2023-03-15T14:30:05Z"
    }
  ]
}
```

### Cache Health

```
GET /health/cache
```

Checks the health of the Redis cache.

**Response Format**:

```json
{
  "status": "healthy",
  "redis_version": "6.2.6",
  "latency": 2,
  "hit_rate": 0.87,
  "memory_usage": {
    "used": "1.2GB",
    "total": "4GB",
    "percentage": 30
  },
  "eviction_rate": 0.001
}
```

### Database Health

```
GET /health/database
```

Checks the health of the database.

**Response Format**:

```json
{
  "status": "healthy",
  "database_type": "PostgreSQL",
  "version": "13.4",
  "latency": 5,
  "connections": {
    "active": 12,
    "idle": 8,
    "max": 100
  },
  "last_successful_query": "2023-03-15T14:32:40Z"
}
```

### Storage Health

```
GET /health/storage
```

Checks the health of the object storage system.

**Response Format**:

```json
{
  "status": "healthy",
  "storage_type": "S3",
  "latency": 24,
  "space": {
    "used": "234GB",
    "total": "1TB",
    "percentage": 23.4
  },
  "last_successful_operation": "2023-03-15T14:31:45Z"
}
```

## Deep Health Checks

For more detailed diagnostics, use the deep health check endpoint:

```
GET /health/deep
```

This performs thorough testing of each component, including:

- Database query execution
- Cache read/write operations
- Model inference tests
- Storage operations
- Inter-service communication

**Authentication**: Required (Admin scope)

**Response Format**: Similar to the base health endpoint but with extended details for each component.

## Integration with Monitoring Systems

### Prometheus Endpoint

```
GET /metrics
```

Exposes metrics in Prometheus format for scraping.

**Authentication**: Optional (configurable)

**Sample Output**:

```
# HELP opossum_api_requests_total Total number of API requests
# TYPE opossum_api_requests_total counter
opossum_api_requests_total{method="GET",endpoint="/search"} 12453

# HELP opossum_api_request_duration_seconds Request duration in seconds
# TYPE opossum_api_request_duration_seconds histogram
opossum_api_request_duration_seconds_bucket{method="GET",endpoint="/search",le="0.1"} 8234
opossum_api_request_duration_seconds_bucket{method="GET",endpoint="/search",le="0.5"} 11021
opossum_api_request_duration_seconds_bucket{method="GET",endpoint="/search",le="1.0"} 11987
opossum_api_request_duration_seconds_bucket{method="GET",endpoint="/search",le="2.0"} 12320
opossum_api_request_duration_seconds_bucket{method="GET",endpoint="/search",le="+Inf"} 12453
opossum_api_request_duration_seconds_sum{method="GET",endpoint="/search"} 3945.7
opossum_api_request_duration_seconds_count{method="GET",endpoint="/search"} 12453

# HELP opossum_model_latency_seconds AI model inference latency in seconds
# TYPE opossum_model_latency_seconds gauge
opossum_model_latency_seconds{model="gemini"} 0.345
opossum_model_latency_seconds{model="ollama"} 0.123
opossum_model_latency_seconds{model="local-transformers"} 0.078
```

### Kubernetes Probes

The health endpoints can be used as Kubernetes probes:

#### Liveness Probe

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8080
  initialDelaySeconds: 30
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3
```

#### Readiness Probe

```yaml
readinessProbe:
  httpGet:
    path: /health/api
    port: 8080
  initialDelaySeconds: 5
  periodSeconds: 5
  timeoutSeconds: 3
  successThreshold: 1
  failureThreshold: 2
```

## Service Status Page Integration

The health endpoints can be integrated with status page providers:

### Statuspage.io Example

```
GET /health/status-page
```

Returns a status page compatible format:

```json
{
  "page": {
    "id": "opossum-search",
    "name": "Opossum Search Status",
    "url": "https://status.opossumsearch.com"
  },
  "components": [
    {
      "id": "api",
      "name": "API",
      "status": "operational"
    },
    {
      "id": "search",
      "name": "Search Service",
      "status": "operational"
    },
    {
      "id": "models",
      "name": "AI Models",
      "status": "operational"
    },
    {
      "id": "image-processing",
      "name": "Image Processing",
      "status": "operational"
    }
  ],
  "incidents": []
}
```

## Health Check Best Practices

### Monitoring Recommendations

1. **Check Frequency**: Poll the health endpoint every 30-60 seconds
2. **Alert Thresholds**: Set up alerts for:
    - Status changes from `healthy` to `degraded` or `unhealthy`
    - Component status changes
    - Latency increases beyond thresholds
    - Error rate increases
3. **Dashboard Visualization**: Create dashboards showing:
    - Overall system health over time
    - Component-specific health metrics
    - Correlation between health and user-facing metrics

### Response Codes

| HTTP Status | Meaning                                  |
|-------------|------------------------------------------|
| 200         | System is healthy                        |
| 200         | System is degraded (check response body) |
| 503         | System is unhealthy                      |
| 500         | Health check itself failed               |

## Custom Health Checks

Enterprise customers can create custom health checks through the API:

```
POST /health/custom
```

```json
{
  "name": "custom-model-check",
  "endpoint": "models",
  "check_type": "latency",
  "parameters": {
    "threshold": 500,
    "sample_size": 5
  },
  "notification_channels": [
    "email:alerts@example.com",
    "slack:channel-id"
  ],
  "schedule": "*/5 * * * *"
}
```

## Rate Limits

Health endpoints have separate rate limits to ensure availability during incidents:

| Endpoint              | Unauthenticated Requests | Authenticated Requests |
|-----------------------|--------------------------|------------------------|
| `/health`             | 60 rpm                   | 300 rpm                |
| `/health/{component}` | 20 rpm                   | 100 rpm                |
| `/health/deep`        | Not available            | 10 rpm                 |
| `/metrics`            | Not available            | 60 rpm                 |

rpm = requests per minute

## Health Data Retention

Health check data is retained according to the following schedule:

| Data Type                  | Retention Period |
|----------------------------|------------------|
| Status changes             | 90 days          |
| Component metrics          | 30 days          |
| Raw health check responses | 7 days           |
| Detailed diagnostic logs   | 3 days           |

## Maintenance Mode

During scheduled maintenance, health endpoints will indicate maintenance mode:

```json
{
  "status": "maintenance",
  "version": "1.8.4",
  "timestamp": "2023-03-15T14:32:45Z",
  "maintenance": {
    "scheduled_start": "2023-03-15T14:00:00Z",
    "scheduled_end": "2023-03-15T16:00:00Z",
    "description": "Database upgrade",
    "affected_components": ["database", "cache"]
  }
}
```
