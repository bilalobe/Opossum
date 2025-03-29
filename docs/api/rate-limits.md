# Rate Limits

## Overview

To ensure optimal performance and fair usage for all users, Opossum Search implements rate limiting across all API
endpoints. This document outlines the rate limit policies, quotas, and best practices for handling rate-limiting
scenarios. For a list of available API routes, see [API Routes](routes.md). For detailed information about request and
response formats, see [Request/Response Documentation](request-response.md). For error code details,
see [Error Codes](error-codes.md). To learn about real-time notifications, refer to [Webhooks](webhooks.md). For system
status and component health, see [Health Endpoints](health-endpoints.md).

## Rate Limit Structure

Opossum Search uses a tiered rate limiting structure based on:

1. **API Key / User**: Limits per unique API key
2. **Endpoint**: Different limits for different operations
3. **IP Address**: To prevent abuse, even with valid credentials
4. **Resource Type**: Different limits for different resources (models, storage, etc.)

## Default Rate Limits

| Plan         | Requests per Minute | Concurrent Requests | Daily Quota  |
|--------------|---------------------|---------------------|--------------|
| Basic        | 60                  | 5                   | 10,000       |
| Professional | 300                 | 20                  | 50,000       |
| Enterprise   | 1,200               | 100                 | Customizable |

## Endpoint-Specific Limits

Different endpoints have different resource requirements and corresponding rate limits:

| Endpoint Category | Basic (RPM) | Professional (RPM) | Enterprise (RPM) |
|-------------------|-------------|--------------------|------------------|
| Search            | 60          | 300                | 1,200            |
| Image Analysis    | 20          | 100                | 400              |
| SVG Generation    | 30          | 150                | 600              |
| Conversation      | 40          | 200                | 800              |
| Configuration     | 15          | 60                 | 240              |
| Health/Status     | 120         | 600                | 2,400            |

RPM = Requests Per Minute

## Model-Specific Limits

Different AI models have different resource requirements:

| Model        | Basic (RPM) | Professional (RPM) | Enterprise (RPM) |
|--------------|-------------|--------------------|------------------|
| Gemini       | 30          | 150                | 600              |
| Ollama       | 60          | 300                | 1,200            |
| Local Models | 120         | 600                | 2,400            |

## Bulk Operation Limits

For bulk operations:

| Operation            | Max Items Per Request | Max Requests Per Hour |
|----------------------|-----------------------|-----------------------|
| Multi-Search         | 10                    | 100                   |
| Batch Image Analysis | 5                     | 50                    |
| Bulk SVG Generation  | 20                    | 200                   |

## Rate Limit Headers

Each API response includes rate limit information in the headers:

| Header                   | Description                                                                 |
|--------------------------|-----------------------------------------------------------------------------|
| `X-Rate-Limit-Limit`     | The rate limit ceiling for the given endpoint                               |
| `X-Rate-Limit-Remaining` | The number of requests left for the time window                             |
| `X-Rate-Limit-Reset`     | The time at which the current rate limit window resets in UTC epoch seconds |
| `X-Rate-Limit-Used`      | The number of requests made in the current time window                      |
| `X-Rate-Limit-Resource`  | The resource being rate-limited (e.g., "search", "model:gemini")            |

Example headers:

```
X-Rate-Limit-Limit: 60
X-Rate-Limit-Remaining: 45
X-Rate-Limit-Reset: 1616172903
X-Rate-Limit-Used: 15
X-Rate-Limit-Resource: search
```

## Rate Limit Response

When a rate limit is exceeded, the API responds with:

- HTTP Status Code: `429 Too Many Requests`
- Response Body:

```json
{
  "success": false,
  "error": {
    "code": "rate_limit_exceeded",
    "message": "You have exceeded the rate limit for this endpoint",
    "details": [
      {
        "limit": 60,
        "remaining": 0,
        "reset": 1616172903,
        "resource": "search"
      }
    ]
  },
  "meta": {
    "request_id": "req_8f7h6g5j4k3l2j1k"
  }
}
```

The API may also include a `Retry-After` header indicating the number of seconds to wait before retrying.

## Handling Rate Limits

### Best Practices

1. **Implement backoff strategies**:
    - Use exponential backoff with jitter
    - Respect the `Retry-After` header when provided
    - Limit maximum retry attempts

2. **Optimize request patterns**:
    - Batch requests when possible using bulk endpoints
    - Cache responses for frequently accessed data
    - Prioritize critical requests when nearing limits

3. **Monitor usage**:
    - Track rate limit headers in responses
    - Set up alerts for approaching limits
    - Use the dashboard to monitor historical usage

### Example Backoff Implementation

```javascript
async function makeRequestWithBackoff(url, options, maxRetries = 5) {
  let retries = 0;
  
  while (retries < maxRetries) {
    try {
      const response = await fetch(url, options);
      
      if (response.status !== 429) {
        return response;
      }
      
      // Handle rate limiting
      retries++;
      
      // Get retry time from header or calculate exponential backoff
      const retryAfter = response.headers.get('Retry-After');
      const waitTime = retryAfter 
        ? parseInt(retryAfter, 10) * 1000
        : Math.min(Math.pow(2, retries) * 1000 + Math.random() * 1000, 60000);
      
      console.log(`Rate limited. Retrying in ${waitTime}ms (attempt ${retries} of ${maxRetries})`);
      
      await new Promise(resolve => setTimeout(resolve, waitTime));
    } catch (error) {
      retries++;
      
      if (retries >= maxRetries) {
        throw error;
      }
      
      // Exponential backoff for network errors
      const waitTime = Math.min(Math.pow(2, retries) * 1000 + Math.random() * 1000, 60000);
      await new Promise(resolve => setTimeout(resolve, waitTime));
    }
  }
  
  throw new Error(`Failed after ${maxRetries} retries`);
}
```

## Monitoring Rate Limit Usage

The dashboard provides real-time and historical rate limit usage:

1. **Real-time Monitor**: View current usage and remaining capacity
2. **Usage Reports**: Analyze usage patterns over time
3. **Alerts**: Set up notifications for approaching limits
4. **Rate Limit Events**: Log of rate limit events

## Quota Extensions

For temporary increases in capacity:

1. **Burst Capacity**: Short-term rate limit increases for planned events
2. **Emergency Increases**: For critical scenarios
3. **Gradual Scaling**: For growing applications

Contact support for quota extension requests.

## Rate Limiting Strategies

Opossum Search implements several rate limiting algorithms:

1. **Token Bucket**: Primary algorithm for most endpoints
2. **Leaky Bucket**: For high-throughput endpoints
3. **Sliding Window**: For conversation and session-based endpoints
4. **Concurrent Request Limiting**: For resource-intensive operations

## Regional Considerations

Rate limits may vary by region due to infrastructure differences:

| Region       | Adjustment Factor |
|--------------|-------------------|
| us-east      | 1.0x (baseline)   |
| us-west      | 1.0x              |
| eu-central   | 0.9x              |
| ap-southeast | 0.8x              |

## Custom Rate Limit Plans

Enterprise customers can request custom rate limit configurations:

- Model-specific adjustments
- Endpoint-specific quotas
- Time-based quota allocation
- Reserved capacity

Contact your account manager to discuss custom rate limit plans.

## Exemptions and Whitelisting

Critical services that require exemptions from standard rate limits:

1. **Status Page Monitors**: Health checking services
2. **Authorized Partners**: Strategic integration partners
3. **Internal Services**: Opossum internal monitoring

Exemption requests require security review and approval.
