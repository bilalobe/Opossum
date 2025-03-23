# Webhooks

## Overview

Opossum Search provides webhooks to notify your application about events as they happen. This document covers webhook configuration, event types, payload format, and best practices for processing webhook events. For a list of available API routes, see [API Routes](routes.md). For detailed information about request and response formats, see [Request/Response Documentation](request-response.md). For error code details, see [Error Codes](error-codes.md). Information on API usage limits can be found in [Rate Limits](rate-limits.md). For system status and component health, see [Health Endpoints](health-endpoints.md).

## What are Webhooks?

Webhooks are HTTP callbacks that allow Opossum Search to send real-time notifications to your application when specific events occur. Rather than polling the API for updates, your application can receive automatic notifications.

## Webhook Events

Opossum Search supports the following webhook event types:

| Event Type | Description |
|------------|-------------|
| `search.completed` | A search operation has completed |
| `analysis.completed` | An image or content analysis has completed |
| `conversation.updated` | A conversation has been updated with new messages |
| `model.status_changed` | An AI model's status has changed (online/offline) |
| `system.status_changed` | The system status has changed |
| `job.completed` | A long-running job has completed |
| `error.threshold_exceeded` | Error rate has exceeded configured threshold |
| `cache.invalidated` | Cache for specified resources has been invalidated |
| `quota.threshold_reached` | Usage quota has reached a configured threshold |
| `user.action_required` | User action is required (e.g., payment, verification) |

## Setting Up Webhooks

### Dashboard Configuration

1. Navigate to the Opossum Search Developer Dashboard
2. Go to **Settings** > **Webhooks**
3. Click **Add Endpoint**
4. Configure your webhook:
   - Endpoint URL: Your server's URL to receive webhook events
   - Events: Select which events to subscribe to
   - Secret: Generate a secret to verify webhook payloads
   - Description: Optional description for your reference

### API Configuration

You can also configure webhooks programmatically:

```
POST /webhooks
```

Request body:

```json
{
  "url": "https://example.com/webhooks/opossum",
  "events": ["search.completed", "model.status_changed"],
  "description": "Production webhook for search notifications",
  "active": true,
  "version": "v1"
}
```

## Webhook Payload Format

All webhook payloads follow this standard format:

```json
{
  "id": "evt_8f7h6g5j4k3l2j1k",
  "created": "2023-03-15T14:32:45Z",
  "type": "search.completed",
  "data": {
    // Event-specific data
  },
  "account": "acc_1234567890",
  "api_version": "v1"
}
```

### Event-Specific Payloads

#### `search.completed`

```json
{
  "id": "evt_8f7h6g5j4k3l2j1k",
  "created": "2023-03-15T14:32:45Z",
  "type": "search.completed",
  "data": {
    "search_id": "srch_1234567890",
    "query": "opossum behavior",
    "status": "completed",
    "duration_ms": 432,
    "result_count": 15,
    "model_used": "gemini",
    "cache_hit": false
  },
  "account": "acc_1234567890",
  "api_version": "v1"
}
```

#### `model.status_changed`

```json
{
  "id": "evt_8f7h6g5j4k3l2j1k",
  "created": "2023-03-15T14:32:45Z",
  "type": "model.status_changed",
  "data": {
    "model": "gemini",
    "previous_status": "online",
    "current_status": "degraded",
    "reason": "increased_latency",
    "estimated_recovery": "2023-03-15T15:00:00Z"
  },
  "account": "acc_1234567890",
  "api_version": "v1"
}
```

## Webhook Signature Verification

For security, all webhooks include a signature header that you should verify:

1. Opossum Search signs the payload using HMAC-SHA256 with your webhook secret
2. The signature is included in the `X-Opossum-Signature` header
3. Verify this signature to ensure the webhook is authentic

### Example Verification (Node.js)

```javascript
const crypto = require('crypto');

function verifyWebhookSignature(payload, header, secret) {
  const signature = crypto
    .createHmac('sha256', secret)
    .update(payload)
    .digest('hex');
  
  return crypto.timingSafeEqual(
    Buffer.from(signature),
    Buffer.from(header)
  );
}

// In your webhook handler
app.post('/webhooks/opossum', (req, res) => {
  const payload = JSON.stringify(req.body);
  const signature = req.headers['x-opossum-signature'];
  const webhookSecret = process.env.OPOSSUM_WEBHOOK_SECRET;
  
  if (!verifyWebhookSignature(payload, signature, webhookSecret)) {
    return res.status(401).send('Invalid signature');
  }
  
  // Process the webhook
  const event = req.body;
  
  // Handle different event types
  switch (event.type) {
    case 'search.completed':
      handleSearchCompleted(event.data);
      break;
    // Handle other event types
  }
  
  res.status(200).send('Webhook received');
});
```

## Webhook Best Practices

### Security

1. **Always verify signatures**: Validate the `X-Opossum-Signature` header
2. **Use HTTPS endpoints**: Ensure webhook URLs use HTTPS
3. **Rotate webhook secrets**: Periodically update your webhook secrets
4. **Implement IP filtering**: Optionally restrict to Opossum Search IP ranges

### Reliability

1. **Return 2xx quickly**: Respond with a 2xx status code as soon as possible
2. **Process asynchronously**: Handle webhook logic outside the request-response cycle
3. **Implement idempotency**: Handle duplicate webhook deliveries gracefully
4. **Store raw payloads**: Save raw webhook data before processing

### Monitoring

1. **Log webhook receipts**: Keep records of all received webhooks
2. **Track processing success**: Monitor webhook processing success rates
3. **Set up alerts**: Create alerts for webhook delivery failures
4. **Check webhook dashboard**: Use the Opossum Search dashboard to view delivery stats

## Webhook Delivery

### Retry Policy

If your endpoint returns a non-2xx response, Opossum Search will retry with this schedule:

1. Initial retry: 5 seconds
2. Second retry: 30 seconds
3. Third retry: 5 minutes
4. Fourth retry: 30 minutes
5. Fifth retry: 2 hours
6. Final retry: 5 hours

After all retry attempts fail, the webhook will be marked as failed in the dashboard.

### Testing Webhooks

The dashboard provides a "Test Webhook" feature to send sample events to your endpoint:

1. Go to **Settings** > **Webhooks**
2. Select a configured webhook
3. Click **Test Webhook**
4. Choose an event type
5. Send the test event

You can also use the API to test webhooks:

```
POST /webhooks/{webhook_id}/test
```

```json
{
  "event_type": "search.completed"
}
```

## Webhook Logs

The dashboard provides logs of all webhook delivery attempts:

1. Event ID
2. Timestamp
3. Destination URL
4. Response status
5. Response time
6. Retry count

Logs are retained for 30 days.

## Managing Webhooks

### Listing Webhooks

```
GET /webhooks
```

### Updating a Webhook

```
PATCH /webhooks/{webhook_id}
```

```json
{
  "events": ["search.completed", "analysis.completed"],
  "active": false
}
```

### Deleting a Webhook

```
DELETE /webhooks/{webhook_id}
```

## Webhook Quotas and Limits

| Plan | Max Webhook Endpoints | Max Events per Minute | Event Retention |
|------|----------------------|---------------------|-----------------|
| Basic | 5 | 60 | 7 days |
| Professional | 20 | 300 | 30 days |
| Enterprise | 100 | 1,200 | 90 days |

## Troubleshooting

Common webhook issues and solutions:

### Webhook Not Receiving Events

1. Check the webhook's status in the dashboard
2. Verify the endpoint URL is correct and accessible
3. Ensure your server accepts POST requests
4. Check that you're subscribed to the expected events

### Failed Signature Verification

1. Confirm you're using the correct webhook secret
2. Ensure you're validating against the raw request body
3. Check for any body parsing middleware that might modify the payload

### Events Missing or Delayed

1. Check webhook logs for delivery failures
2. Verify your endpoint responds with 2xx status codes
3. Check for rate limiting on your server
4. Ensure your server can handle concurrent webhook requests
