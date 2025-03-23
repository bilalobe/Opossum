# Rate Limiting and Throttling

> **Related Documentation:**
> - [Technical: GraphQL API](../technical/graphql-api.md) - Implementation of rate limiting in GraphQL directives
> - [API Reference: Rate Limits](../api/rate-limits.md) - Detailed API rate limit reference documentation
> - [Infrastructure: Redis Integration](../infrastructure/redis-integration.md) - Redis-based rate limit tracking implementation

## Rate Limit Policies

| Service      | Rate Limit Type | Quota                | Reset Period | Priority Handling                        |
|--------------|-----------------|----------------------|--------------|------------------------------------------|
| Gemini API   | API Calls       | 60 per minute        | Minute       | High-value queries prioritized           |
| Gemini API   | Daily Usage     | 60,000 per day       | 24 hours     | Resource allocation based on time of day |
| Ollama       | Local Resource  | CPU/GPU dependent    | N/A          | Queue-based with timeout                 |
| Transformers | Local Resource  | Memory/CPU dependent | N/A          | Simplified models for high load          |

## Detection Mechanisms

| Limit Type          | Detection Method  | Response Code         | Handling Strategy                         |
|---------------------|-------------------|-----------------------|-------------------------------------------|
| Pre-emptive         | Counter tracking  | N/A                   | Redirect before limit reached             |
| Reactive            | HTTP 429 response | 429 Too Many Requests | Immediate failover to alternative service |
| Quota Exceeded      | HTTP 403 response | 403 Forbidden         | Temporary service downgrade               |
| Resource Exhaustion | Exception/timeout | Various               | Scale down model complexity               |

## Request Management

| Approach               | Implementation                       | Benefit                                |
|------------------------|--------------------------------------|----------------------------------------|
| Request Queuing        | In-memory FIFO queue with priority   | Prevents request loss during high load |
| Request Coalescing     | Combine similar requests             | Reduces total API calls                |
| Request Prioritization | User interaction > Background tasks  | Maintains responsive UX                |
| Adaptive TTL           | Dynamic cache lifetime based on load | Reduces API calls during peak          |

## Throttling Implementation

```python
# filepath: c:\Users\beb\PycharmProjects\Opossum\docs\service-availability\rate-limiting-throttling.md
class RateLimitManager:
    def __init__(self):
        self.minute_usage = 0
        self.daily_usage = 0
        self.last_minute_reset = datetime.now()
        self.last_daily_reset = datetime.now()
        self.request_queue = asyncio.Queue()
        
    async def track_request(self):
        """Track a new request against rate limits"""
        current_time = datetime.now()
        
        # Reset counters if needed
        if (current_time - self.last_minute_reset).seconds >= 60:
            self.minute_usage = 0
            self.last_minute_reset = current_time
            
        if (current_time - self.last_daily_reset).days >= 1:
            self.daily_usage = 0
            self.last_daily_reset = current_time
            
        # Increment counters
        self.minute_usage += 1
        self.daily_usage += 1
        
    async def can_process_request(self):
        """Check if request can be processed within rate limits"""
        return self.minute_usage < 58  # Buffer of 2 requests
        
    async def process_or_queue(self, request_func, *args):
        """Process request or queue it based on rate limits"""
        if await self.can_process_request():
            await self.track_request()
            return await request_func(*args)
        else:
            # Queue the request or fail over
            return await self.handle_rate_limit(*args)
```

## Client-Side Adaptation

| Condition           | Client Behavior               | User Experience                        |
|---------------------|-------------------------------|----------------------------------------|
| Server Rate Limited | Switch to fallback simulation | "Using simplified mode temporarily"    |
| Approaching Limits  | Batch requests                | Normal with slight delay               |
| Normal Operation    | Direct API access             | Full functionality                     |
| Extended Outage     | Local-only operation          | Reduced capabilities with notification |

## Balance and Optimization Strategies

| Strategy                    | Implementation                     | Effect                                            |
|-----------------------------|------------------------------------|---------------------------------------------------|
| Time-of-day Allocation      | Reserve quota for peak hours       | Consistent availability during business hours     |
| Request Complexity Analysis | Measure token count before sending | Route complex queries to appropriate backend      |
| Adaptive Backoff            | Exponential delay with jitter      | Graceful recovery during service degradation      |
| Quota Forecasting           | Predictive usage modeling          | Proactive service switching before limits reached |

## Monitoring and Alerts

| Metric          | Threshold     | Alert Type | Recipient               |
|-----------------|---------------|------------|-------------------------|
| Minute Usage    | >80% of limit | Warning    | Logs                    |
| Minute Usage    | >95% of limit | Critical   | Operations Team         |
| Daily Usage     | >90% of limit | Warning    | Operations Team         |
| Queue Size      | >20 requests  | Warning    | Logs                    |
| Queue Size      | >50 requests  | Critical   | Operations Team         |
| Queue Wait Time | >5 seconds    | Warning    | Logs, User Notification |