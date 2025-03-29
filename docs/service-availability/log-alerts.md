# Logging and Alerts

## Logging Strategy

| Log Category        | Purpose                                | Implementation                      | Retention |
|---------------------|----------------------------------------|-------------------------------------|-----------|
| Service Status      | Track service availability changes     | Structured JSON logs                | 30 days   |
| Rate Limit          | Monitor API usage against quotas       | Counter logs with timestamps        | 90 days   |
| Error Events        | Record service failures and exceptions | Exception details with stack traces | 14 days   |
| Recovery Actions    | Document automatic recovery attempts   | Action logs with outcomes           | 14 days   |
| Performance Metrics | Track response times and latency       | Time-series metrics                 | 180 days  |

## Log Levels

| Level    | Usage                             | Example                                               |
|----------|-----------------------------------|-------------------------------------------------------|
| DEBUG    | Detailed diagnostic information   | "Checking Gemini API availability"                    |
| INFO     | Normal operational events         | "Service status changed: Gemini API now AVAILABLE"    |
| WARNING  | Non-critical issues               | "Approaching rate limit (85% used)"                   |
| ERROR    | Runtime errors, failed operations | "Connection to Ollama failed: Connection refused"     |
| CRITICAL | System-wide failures              | "All services unavailable, switching to offline mode" |

## Logging Implementation

```python
import logging
import json
from datetime import datetime

# Configure logger
logger = logging.getLogger("service_availability")
logger.setLevel(logging.INFO)

# File handler
file_handler = logging.FileHandler("service_availability.log")
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)


class ServiceLogger:
    @staticmethod
    def log_status_change(service_name, old_status, new_status, reason=None):
        """Log a service status change with structured data"""
        log_data = {
            "event_type": "status_change",
            "timestamp": datetime.now().isoformat(),
            "service": service_name,
            "old_status": old_status,
            "new_status": new_status,
            "reason": reason
        }
        logger.info(f"Service status changed: {service_name} now {new_status}", extra={"data": json.dumps(log_data)})

        # Critical service unavailability triggers higher level log
        if new_status == "UNAVAILABLE" and service_name in ["Gemini API", "Ollama"]:
            logger.warning(f"Critical service {service_name} is now unavailable. Reason: {reason}")

    @staticmethod
    def log_rate_limit(service_name, limit_type, current_usage, total_limit):
        """Log rate limit information"""
        usage_percent = (current_usage / total_limit) * 100
        log_level = logging.INFO

        if usage_percent > 95:
            log_level = logging.ERROR
        elif usage_percent > 80:
            log_level = logging.WARNING

        log_data = {
            "event_type": "rate_limit",
            "service": service_name,
            "limit_type": limit_type,
            "usage": current_usage,
            "limit": total_limit,
            "percent": usage_percent
        }

        logger.log(log_level,
                   f"{service_name} {limit_type} usage: {usage_percent:.1f}% ({current_usage}/{total_limit})",
                   extra={"data": json.dumps(log_data)})
```

## Alert Triggers

| Trigger              | Condition                               | Severity | Response Time |
|----------------------|-----------------------------------------|----------|---------------|
| Service Unavailable  | Any primary service becomes unavailable | High     | Immediate     |
| Rate Limit Threshold | >95% of minute or daily quota consumed  | Medium   | < 5 minutes   |
| Recovery Failure     | 3+ consecutive failed recovery attempts | High     | Immediate     |
| Multiple Failovers   | >5 failovers in 24 hours                | Medium   | < 1 hour      |
| All Services Down    | No available AI services                | Critical | Immediate     |

!!! warning
Ensure that the alert triggers are configured correctly to promptly notify the operations team of any service
disruptions or potential issues.

## Notification Channels

| Channel          | Target Audience          | Alert Types             | Implementation                     |
|------------------|--------------------------|-------------------------|------------------------------------|
| Application Logs | Developers               | All events              | Structured logging with context    |
| Email Alerts     | Operations Team          | High & Critical events  | SMTP integration                   |
| UI Notifications | End Users                | Service degradation     | Browser notifications via frontend |
| Status Dashboard | All stakeholders         | Service status, outages | Real-time web dashboard            |
| Slack Channel    | Operations & Development | Medium+ severity        | Webhook integration                |

## Alert Templates

| Alert Type          | Template                                                                                      | Channel      |
|---------------------|-----------------------------------------------------------------------------------------------|--------------|
| Service Down        | "[ALERT] {service_name} is DOWN. Reason: {reason}. Failover to {fallback_service} initiated." | Email, Slack |
| Rate Limit          | "[WARNING] {service_name} approaching rate limit: {usage_percent}% of {limit_type} used."     | Logs, Slack  |
| Recovery Success    | "[INFO] {service_name} successfully recovered after {downtime} minutes of unavailability."    | Logs         |
| Client Notification | "Using alternative AI service due to temporary unavailability. Some features may be limited." | UI           |

## Log Analysis

| Analysis Type           | Purpose                        | Tools                | Frequency |
|-------------------------|--------------------------------|----------------------|-----------|
| Availability Reporting  | Calculate uptime percentages   | Custom scripts       | Daily     |
| Error Pattern Detection | Identify recurring issues      | Log parsing          | Weekly    |
| Rate Limit Forecasting  | Predict quota exhaustion       | Time-series analysis | Hourly    |
| Service Quality Metrics | Track performance degradation  | Dashboards           | Real-time |
| Audit Trail             | Security and compliance review | Log archiving        | Monthly   |