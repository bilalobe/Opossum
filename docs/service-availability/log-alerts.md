# Logging and Alerts

Effective logging and alerting are crucial for monitoring service availability and diagnosing issues promptly.

## Logging Strategy

The application uses Python's standard `logging` module, configured globally via `logging.dictConfig` during application startup (`app/__init__.py`).

| Log Category        | Purpose                                | Implementation Details                                     | Retention |
|---------------------|----------------------------------------|------------------------------------------------------------|-----------|
| **Application Logs**| General operational events, debug info | Structured JSON format (via `CustomJsonFormatter`). Includes `timestamp`, `level`, `message`, `logger`, `service_name`, `environment`, `request_id`. Console output format varies by environment (simple for dev, JSON for prod). | Configurable (e.g., file rotation, log aggregation system) |
| Service Status      | Track service availability changes     | INFO level logs via `ServiceAvailability` module. JSON format. | 30 days (example) |
| Rate Limit          | Monitor API usage against quotas       | WARNING level logs when limits approached/hit. JSON format. | 90 days (example) |
| **Error Events**    | Record service failures and exceptions | Handled by `ErrorHandler`. Logs exceptions with stack traces (ERROR/CRITICAL level). Includes error category and context. JSON format. | 14 days (example) |
| Recovery Actions    | Document automatic recovery attempts   | INFO/WARNING logs from `CircuitBreaker` (state changes) and `retry` decorator. JSON format. | 14 days (example) |
| Performance Metrics | Track response times and latency       | Handled via Prometheus metrics (see below).                | 180 days (example) |
| Security Events     | Audit security-related actions         | Dedicated 'security' logger, potentially separate handler. JSON format. See [Security Model](../technical/security-model.md#monitoring-and-incident-response). | 90+ days (example) |

## Log Levels

Standard Python log levels are used:

| Level    | Usage                             | Example                                               |
|----------|-----------------------------------|-------------------------------------------------------|
| DEBUG    | Detailed diagnostic information   | "Checking Gemini API availability", "Extracted features: {...}" |
| INFO     | Normal operational events         | "Service status changed: Gemini API now AVAILABLE", "Request processed successfully" |
| WARNING  | Non-critical issues, potential problems | "Approaching rate limit (85% used)", "Circuit breaker entering HALF_OPEN state" |
| ERROR    | Runtime errors, failed operations | "Connection to Ollama failed: Connection refused", "Error processing request: Validation Error" |
| CRITICAL | System-wide failures              | "All services unavailable, cannot process request", "Failed to initialize critical component" |

## Logging Implementation

- **Configuration**: Defined in `app/logging_config.py` and applied in `app/__init__.py`.
- **Format**: Primarily structured JSON via `python-json-logger` and a custom formatter.
- **Context**: A `RequestContextFilter` automatically injects `request_id` into logs generated during a request.
- **Handlers**: Configurable based on environment (Console, File, OTLP).

## Alert Triggers

Alerts should be configured in your monitoring system (e.g., Prometheus Alertmanager, Grafana Alerts, Datadog Monitors) based on logs and metrics. Key triggers include:

| Trigger Condition                     | Metric/Log Source                                       | Severity | Example Action                  |
|---------------------------------------|---------------------------------------------------------|----------|---------------------------------|
| Service status changes to `offline`   | `ServiceAvailability` logs / Prometheus gauge           | High     | Page on-call engineer           |
| Circuit breaker enters `OPEN` state   | `CircuitBreaker` logs / Prometheus gauge                | Medium   | Notify development team channel |
| High rate of specific error types     | `opossum_errors_total` Prometheus counter (rate)        | Medium   | Create ticket                   |
| Sustained high error rate (any type)  | `opossum_errors_total` Prometheus counter (rate)        | High     | Page on-call engineer           |
| Approaching API rate limits           | `ServiceAvailability` logs / Prometheus gauge           | Low      | Log warning                     |
| Hitting API rate limits               | `ServiceAvailability` logs / Prometheus gauge           | Medium   | Notify development team         |
| Critical log messages detected        | Log aggregation system query                            | Critical | Page on-call engineer           |
| High error handling duration          | `opossum_error_duration_seconds` Prometheus gauge       | Low      | Investigate performance         |

## Notification Channels

Configure alerts to route to appropriate channels based on severity:

- **Low**: Logging systems, internal dashboards.
- **Medium**: Team chat channels (e.g., Slack, Teams).
- **High/Critical**: Paging systems (e.g., PagerDuty, Opsgenie), dedicated alert channels.

## Prometheus Metrics

The `ErrorHandler` exposes the following metrics:

- `opossum_errors_total{error_type}`: Counter for total errors by `ErrorCategory`.
- `opossum_error_duration_seconds{error_type}`: Gauge showing the duration of the last error handling call for each `ErrorCategory`.

Additional metrics are exposed by `ServiceAvailability` (see `app/monitoring/availability.py`).

## Log Analysis

Use a log aggregation tool (e.g., ELK Stack, Splunk, Grafana Loki, Datadog Logs) to:
- Search and filter logs based on `request_id`, `service`, `level`, etc.
- Create dashboards visualizing error rates and types.
- Set up automated alerts based on log patterns.