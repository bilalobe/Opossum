# Availability Monitoring

## Monitoring Strategy

| Component            | Strategy           | Implementation                             |
|----------------------|--------------------|--------------------------------------------|
| Service Availability | Active polling     | Asynchronous health checks to all services |
| Rate Limit Tracking  | Counter-based      | In-memory tracking with time-based resets  |
| Status Changes       | Event-based        | Status change detection and logging        |
| Failure Detection    | Exception handling | Request timeouts and error catching        |

## Check Frequency and Scheduling

| Service      | Check Frequency        | Caching Duration | Trigger Mechanism      |
|--------------|------------------------|------------------|------------------------|
| Gemini API   | Every 30 seconds (max) | 30 seconds       | On-demand with caching |
| Ollama       | Every 30 seconds (max) | 30 seconds       | On-demand with caching |
| Transformers | Every 30 seconds (max) | 30 seconds       | On-demand with caching |
| All Services | On application startup | N/A              | Initialization check   |

## Metrics Collection

| Metric                  | Collection Method         | Storage              | Purpose                   |
|-------------------------|---------------------------|----------------------|---------------------------|
| Service Status          | Boolean availability flag | In-memory dictionary | Service selection         |
| Last Check Timestamp    | Datetime object           | In-memory dictionary | Throttling checks         |
| Gemini Daily Usage      | Counter with daily reset  | In-memory counter    | Rate limit compliance     |
| Gemini Per-Minute Usage | Counter with minute reset | In-memory counter    | Rate limit compliance     |
| Service Transitions     | Event logging             | Application logs     | Diagnostics and reporting |

## Monitoring Tools

| Tool               | Purpose                                       | Integration                    |
|--------------------|-----------------------------------------------|--------------------------------|
| Standard Logging   | Record availability events and transitions    | Python logging module          |
| Health Check API   | Internal HTTP endpoint for status monitoring  | Flask route handler            |
| Exception Tracking | Capture and report service check failures     | Try-except blocks with logging |
| Status Dashboard   | Visual representation of service availability | Admin interface (planned)      |

## Implementation Details

The monitoring system uses concurrent asynchronous checks to efficiently assess service availability:

```python
class ServiceAvailability:
    def __init__(self):
        self.services_status = {
            "gemini": {"available": False, "last_checked": None},
            "ollama": {"available": False, "last_checked": None},
            "transformers": {"available": False, "last_checked": None}
        }
        self.check_interval = 30  # seconds
        
    async def check_all_services(self):
        """Check availability of all configured services"""
        logger.debug("Beginning availability check for all services")

        # Run all checks concurrently
        await asyncio.gather(
            self.check_ollama_availability(),
            self.check_gemini_availability(),
            self.check_transformers_availability()
        )
        
    async def check_gemini_availability(self):
        """Check if Gemini API is available"""
        try:
            # Implement a lightweight request to Gemini API
            # Record result in services_status dictionary
            current_time = datetime.now()
            if self.services_status["gemini"]["last_checked"] is None or \
               (current_time - self.services_status["gemini"]["last_checked"]).seconds > self.check_interval:
                # Perform actual check here
                self.services_status["gemini"]["available"] = True  # Set based on check result
                self.services_status["gemini"]["last_checked"] = current_time
                logger.info("Gemini API is available")
        except Exception as e:
            self.services_status["gemini"]["available"] = False
            self.services_status["gemini"]["last_checked"] = datetime.now()
            logger.error(f"Gemini API check failed: {str(e)}")
            
    # Similar methods for check_ollama_availability and check_transformers_availability
```

## Availability Reporting

| Report               | Frequency | Contents                                            | Distribution           |
|----------------------|-----------|-----------------------------------------------------|------------------------|
| Status Change Alerts | Real-time | Service, previous status, new status, reason        | Logs                   |
| Availability Summary | Daily     | Uptime percentages, outage periods, failover counts | Logs, email (planned)  |
| Rate Limit Reports   | Daily     | API usage statistics, remaining quota               | Logs                   |
| Service Health Check | On-demand | Current status of all services                      | API endpoint (planned) |

!!! note
    Regularly review the Availability Summary reports to identify trends and potential issues with service availability.