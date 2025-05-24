# API Error Codes and Responses

Opossum Search uses standard HTTP status codes to indicate the success or failure of an API request. In case of an error, the response body will contain a JSON object with a standardized structure.

## Standard Error Response Format

When an error occurs (HTTP status code 4xx or 5xx), the response body follows this structure:

```json
{
  "success": false,
  "error": {
    "code": "error_category_code",
    "message": "A human-readable description of the error.",
    "details": [
      {
        "field": "optional_field_name",
        "message": "Specific detail about the error, often related to validation."
      }
      // ... more details if applicable
    ]
  },
  "meta": {
    "request_id": "unique-request-identifier",
    "timestamp": "YYYY-MM-DDTHH:MM:SS.ffffffZ", // UTC timestamp
    "processing_time": 0.123 // Optional: Time taken in seconds
  }
}
```

## Authentication Errors

| Code                     | HTTP Status | Description                                                     | Resolution                                                                        |
|--------------------------|-------------|-----------------------------------------------------------------|-----------------------------------------------------------------------------------|
| `invalid_api_key`        | 401         | The API key provided is invalid or doesn't exist                | Verify your API key and ensure it's properly included in the request header       |
| `expired_api_key`        | 401         | The API key has expired                                         | Renew your API key through the dashboard                                          |
| `insufficient_scope`     | 403         | The API key doesn't have permission for the requested operation | Request additional permissions or use a different API key with the required scope |
| `invalid_token`          | 401         | The authentication token is invalid or malformed                | Verify the token or request a new one                                             |
| `expired_token`          | 401         | The authentication token has expired                            | Refresh your token using the refresh token endpoint                               |
| `missing_authentication` | 401         | No authentication was provided                                  | Include an API key or Bearer token in your request                                |

## Request Validation Errors

| Code                         | HTTP Status | Description                                            | Resolution                                            |
|------------------------------|-------------|--------------------------------------------------------|-------------------------------------------------------|
| `invalid_request`            | 400         | The request body is malformed or contains invalid JSON | Check the request syntax and ensure valid JSON        |
| `missing_required_parameter` | 400         | A required parameter is missing                        | Add the missing parameter to your request             |
| `invalid_parameter`          | 400         | A parameter has an invalid value                       | Check the parameter value against the documentation   |
| `unsupported_parameter`      | 400         | A parameter is not supported for this endpoint         | Remove the unsupported parameter                      |
| `invalid_query`              | 400         | The search query is invalid or empty                   | Provide a valid search query                          |
| `invalid_filter`             | 400         | One or more filters are invalid                        | Check the filter parameters against the documentation |
| `malformed_url`              | 400         | A URL parameter is malformed                           | Ensure URLs are properly formatted and encoded        |
| `invalid_file_format`        | 400         | The uploaded file format is not supported              | Use a supported file format                           |
| `file_too_large`             | 400         | The uploaded file exceeds the size limit               | Reduce the file size or use a different file          |

## Resource Errors

| Code                      | HTTP Status | Description                                                  | Resolution                                                 |
|---------------------------|-------------|--------------------------------------------------------------|------------------------------------------------------------|
| `resource_not_found`      | 404         | The requested resource doesn't exist                         | Check the resource identifier                              |
| `resource_already_exists` | 409         | The resource you're trying to create already exists          | Use a different identifier or update the existing resource |
| `resource_conflict`       | 409         | The request conflicts with the current state of the resource | Resolve the conflict or try a different approach           |
| `resource_locked`         | 423         | The resource is locked and can't be modified                 | Wait until the resource is unlocked                        |
| `resource_gone`           | 410         | The resource was permanently removed                         | The resource is no longer available                        |

## Rate Limiting Errors

| Code                        | HTTP Status | Description                                      | Resolution                                        |
|-----------------------------|-------------|--------------------------------------------------|---------------------------------------------------|
| `rate_limit_exceeded`       | 429         | You've exceeded the rate limit for this endpoint | Reduce request frequency or upgrade your plan     |
| `quota_exceeded`            | 429         | You've exceeded your monthly quota               | Wait until your quota resets or upgrade your plan |
| `concurrent_requests_limit` | 429         | Too many concurrent requests                     | Reduce the number of parallel requests            |

## Processing Errors

| Code                     | HTTP Status | Description                                              | Resolution                                          |
|--------------------------|-------------|----------------------------------------------------------|-----------------------------------------------------|
| `processing_error`       | 422         | An error occurred while processing the request           | Check the error details for specific information    |
| `image_processing_error` | 422         | Failed to process the provided image                     | Ensure the image is valid and in a supported format |
| `svg_generation_error`   | 422         | Failed to generate the requested SVG                     | Check the input data and template                   |
| `model_error`            | 422         | The AI model encountered an issue processing the request | Try a different model or simplify your request      |
| `parsing_error`          | 422         | Failed to parse the request or response                  | Check the format of your data                       |

## Service Errors

| Code                    | HTTP Status | Description                                | Resolution                               |
|-------------------------|-------------|--------------------------------------------|------------------------------------------|
| `internal_server_error` | 500         | An unexpected error occurred on the server | Contact support if the issue persists    |
| `service_unavailable`   | 503         | The service is temporarily unavailable     | Try again later                          |
| `gateway_timeout`       | 504         | A dependent service timed out              | Try again later or simplify your request |
| `database_error`        | 500         | A database error occurred                  | Contact support if the issue persists    |
| `storage_error`         | 500         | A storage system error occurred            | Contact support if the issue persists    |
| `cache_error`           | 500         | A caching system error occurred            | Try again later                          |

## Model Service Errors

| Code                   | HTTP Status | Description                                             | Resolution                                        |
|------------------------|-------------|---------------------------------------------------------|---------------------------------------------------|
| `model_unavailable`    | 503         | The requested AI model is currently unavailable         | Try a different model or try again later          |
| `model_timeout`        | 504         | The AI model took too long to respond                   | Simplify your query or try a different model      |
| `model_overloaded`     | 503         | The AI model is currently overloaded                    | Try again later or use a different model          |
| `unsupported_model`    | 400         | The specified model is not supported                    | Use one of the supported models                   |
| `model_response_error` | 422         | The model returned an invalid or inappropriate response | Try rephrasing your query                         |
| `content_filtered`     | 422         | The content was filtered due to safety concerns         | Modify your query to comply with content policies |

## System-Specific Errors

| Code                   | HTTP Status | Description                                    | Resolution                                        |
|------------------------|-------------|------------------------------------------------|---------------------------------------------------|
| `maintenance_mode`     | 503         | The system is in maintenance mode              | Check the status page for updates                 |
| `feature_disabled`     | 403         | This feature is currently disabled             | Check the documentation or contact support        |
| `deprecated_endpoint`  | 410         | This endpoint has been deprecated              | Migrate to the recommended alternative            |
| `version_mismatch`     | 400         | API version mismatch                           | Update your client to use the correct API version |
| `region_not_supported` | 403         | This operation is not available in your region | Check the regional availability documentation     |

## Error Fields Reference

### The `details` Array

The `details` array provides more specific information about what went wrong:

```json
"details": [
  {
    "field": "name of the problematic field",
    "message": "specific issue with this field",
    "code": "specific_error_code",
    "location": "body|query|path|header",
    "value": "the invalid value (if applicable)"
  }
]
```

### Error Details Properties

| Property   | Description                                     | Example                                   |
|------------|-------------------------------------------------|-------------------------------------------|
| `field`    | The specific field that caused the error        | `"query"`, `"model"`, `"image"`           |
| `message`  | Human-readable explanation of the issue         | `"Must be at least 3 characters"`         |
| `code`     | Field-specific error code                       | `"min_length"`, `"pattern"`, `"required"` |
| `location` | Where in the request the error occurred         | `"body"`, `"query"`, `"header"`           |
| `value`    | The invalid value (may be omitted for security) | `"abc123"`                                |

## Handling Errors

### Best Practices

1. **Always check the `success` field** to determine if a request succeeded
2. **Log the `request_id`** for troubleshooting and support
3. **Implement exponential backoff** for rate limiting errors
4. **Watch for service unavailability** and implement appropriate fallbacks
5. **Parse the `details` array** for field-specific validation errors

### Retry Strategy

For transient errors (5xx, rate limits), we recommend:

1. Implement exponential backoff with jitter
2. Set maximum retry attempts (3-5 is recommended)
3. Only retry for error codes that indicate transient issues
4. Respect the `Retry-After` header if present

### Example Retry Implementation

```javascript
async function makeRequestWithRetry(endpoint, options, maxRetries = 3) {
  let retries = 0;
  
  while (retries < maxRetries) {
    try {
      const response = await fetch(endpoint, options);
      
      if (response.ok) {
        return await response.json();
      }
      
      const errorData = await response.json();
      
      // Don't retry for client errors (except rate limiting)
      if (response.status < 500 && response.status !== 429) {
        throw errorData;
      }
      
      // For rate limiting, respect the Retry-After header
      if (response.status === 429) {
        const retryAfter = response.headers.get("Retry-After");
        const waitTime = retryAfter ? parseInt(retryAfter, 10) * 1000 : (2 ** retries) * 1000;
        await new Promise(resolve => setTimeout(resolve, waitTime));
      } else {
        // Exponential backoff with jitter
        const waitTime = (2 ** retries) * 1000 + Math.random() * 1000;
        await new Promise(resolve => setTimeout(resolve, waitTime));
      }
      
      retries++;
    } catch (error) {
      if (retries === maxRetries - 1) {
        throw error;
      }
      retries++;
    }
  }
}
```

## Error Reporting

If you encounter an error that seems incorrect or requires assistance, please include:

1. The complete error response (including the `request_id`)
2. The request that triggered the error
3. Timestamp of the request
4. Any relevant context about the conditions

Submit error reports through the developer dashboard or contact support.
