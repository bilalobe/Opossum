# Error Handling and Recovery

## Error Detection and Classification

| Error Type                | Detection Method                      | Priority | Example                                 |
|---------------------------|---------------------------------------|----------|-----------------------------------------|
| API Connection Failure    | Request timeout or HTTP error         | High     | Gemini API unreachable                  |
| Rate Limit Reached        | HTTP 429 or quota tracking            | High     | Gemini API quota exceeded               |
| Authentication Failure    | HTTP 401/403 response                 | High     | Invalid or expired API key              |
| Local Service Unreachable | Socket connection failure             | Medium   | Ollama service not running              |
| Model Loading Failure     | Exception during model initialization | Medium   | Insufficient resources for Transformers |
| Slow Response             | Response time exceeding threshold     | Low      | Degraded performance warning            |

## Failover Strategy

| From Service               | To Service                                    | Trigger         | Transition Time |
|----------------------------|-----------------------------------------------|-----------------|-----------------|
| Gemini API → Ollama        | Connection failure, rate limit, or auth error | Immediate       | < 2s            |
| Ollama → Transformers      | Connection failure or initialization error    | Immediate       | < 5s            |
| Any → Client-side Fallback | All server services unavailable               | After 3 retries | < 10s           |

!!! important
The failover strategy ensures that the Opossum Search application remains functional even when individual services
experience outages.

## Recovery Procedures

| Service      | Automatic Recovery                                              | Manual Recovery Steps                                                                                                                         |
|--------------|-----------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------|
| Gemini API   | Periodic availability checks to detect when service is restored | 1. Verify API key validity<br>2. Check quota status<br>3. Test connectivity to API endpoint<br>4. Update API configuration if needed          |
| Ollama       | Restart attempt after 60s of unavailability                     | 1. Check local service process<br>2. Restart Ollama service<br>3. Verify model availability<br>4. Check GPU utilization if performance issues |
| Transformers | Model reloading attempt if initialization fails                 | 1. Verify model files exist<br>2. Check available RAM<br>3. Consider loading smaller model variant<br>4. Update model files if corrupted      |

## Error Communication

| Audience   | Error Information                                           | Delivery Method                                                   |
|------------|-------------------------------------------------------------|-------------------------------------------------------------------|
| End Users  | General error with degraded capability notice               | UI message: "Using alternative model due to service availability" |
| Developers | Detailed error including exception trace and service status | Application logs with ERROR level                                 |
| Operations | Service status changes and recovery attempts                | Logs and monitoring alerts                                        |

## Resilience Mechanisms

| Mechanism              | Purpose                                                   | Implementation                            |
|------------------------|-----------------------------------------------------------|-------------------------------------------|
| Circuit Breaker        | Prevent repeated calls to failing services                | Exponential backoff with jitter           |
| Request Caching        | Serve previous responses during outages                   | In-memory cache with TTL                  |
| Client-side Fallback   | Provide degraded functionality when server is unavailable | JavaScript simulation mode in UI          |
| Service Prioritization | Route requests to highest capability available service    | Service ranking with availability checks  |
| Graceful Degradation   | Maintain core functionality with limited capabilities     | Feature flags based on available services |

## Recovery Monitoring

| Recovery Metric            | Measurement                              | Threshold          | Action                          |
|----------------------------|------------------------------------------|--------------------|---------------------------------|
| Recovery Time              | Time from failure to service restoration | > RTO              | Alert operations team           |
| Failed Recovery Attempts   | Count of unsuccessful recovery attempts  | > 3                | Escalate to manual intervention |
| Failover Frequency         | Number of failovers in 24h period        | > 5                | Investigate root cause          |
| Performance After Recovery | Response time compared to baseline       | > 150% of baseline | Flag for optimization           |

### Circuit Breaker Pattern

Opossum implements a robust circuit breaker pattern to prevent cascading failures when services become unresponsive. The
centralized implementation provides:

- **Failure threshold detection**: Configurable limits for consecutive failures
- **Rate-based detection**: Optional percentage-based failure detection for high-volume services
- **Automatic recovery**: Half-open state testing to detect when services recover
- **Prometheus metrics**: Comprehensive monitoring of circuit state changes
- **Named instances**: Service-specific circuit breakers with individual configurations

Circuit breakers are managed centrally by the ErrorHandler and can be configured through environment variables:

| Configuration Parameter             | Description                     | Default           |
|-------------------------------------|---------------------------------|-------------------|
| `CIRCUIT_BREAKER_FAILURE_THRESHOLD` | Default failure count threshold | 5                 |
| `CIRCUIT_BREAKER_RESET_TIMEOUT`     | Default seconds before retry    | 60                |
| `{SERVICE}_FAILURE_THRESHOLD`       | Service-specific threshold      | Default threshold |
| `{SERVICE}_RESET_TIMEOUT`           | Service-specific timeout        | Default timeout   |

When a circuit opens, requests will be routed to fallback mechanisms or return appropriate error responses to clients.