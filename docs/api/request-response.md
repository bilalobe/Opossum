# Request and Response Formats

## Overview

This document details the standard request and response formats used across the Opossum Search API, including headers,
body structures, and status codes. For a list of available API routes, see [API Routes](routes.md). For error code
details, see [Error Codes](error-codes.md). Information on API usage limits can be found
in [Rate Limits](rate-limits.md). To learn about real-time notifications, refer to [Webhooks](webhooks.md). For system
status and component health, see [Health Endpoints](health-endpoints.md).

## Common Headers

### Request Headers

| Header             | Description                                                   | Required                            |
|--------------------|---------------------------------------------------------------|-------------------------------------|
| `Content-Type`     | The format of the request body (usually `application/json`)   | Yes (for requests with bodies)      |
| `Accept`           | The format the client can accept (usually `application/json`) | No (defaults to `application/json`) |
| `X-API-Key`        | API key for authentication                                    | Yes (unless using Bearer)           |
| `Authorization`    | Bearer token for authentication (`Bearer <token>`)            | Yes (unless using API key)          |
| `X-Request-ID`     | Unique ID for tracking the request                            | No (created if not provided)        |
| `X-Correlation-ID` | ID for tracking related requests                              | No                                  |
| `User-Agent`       | Client application identifier                                 | No                                  |

### Response Headers

| Header                   | Description                                          |
|--------------------------|------------------------------------------------------|
| `Content-Type`           | Format of response body (usually `application/json`) |
| `X-Request-ID`           | Mirrors the request ID (or generated)                |
| `X-Rate-Limit-Limit`     | Rate limit ceiling for the endpoint                  |
| `X-Rate-Limit-Remaining` | Number of requests left for the time window          |
| `X-Rate-Limit-Reset`     | Seconds until the rate limit resets                  |
| `X-Processing-Time`      | Time in milliseconds to process the request          |
| `X-Cache-Status`         | Cache status (`HIT`, `MISS`, `STALE`, `SKIP`)        |
| `X-Version`              | API version                                          |

## Standard Response Format

All API responses follow a consistent structure:

```json
{
  "success": true,
  "data": { ... },
  "meta": {
    "request_id": "req_8f7h6g5j4k3l2j1k",
    "processing_time": 123,
    "model_used": "gemini"
  }
}
```

For errors:

```json
{
  "success": false,
  "error": {
    "code": "invalid_request",
    "message": "The request was invalid",
    "details": [ ... ]
  },
  "meta": {
    "request_id": "req_8f7h6g5j4k3l2j1k",
    "processing_time": 45
  }
}
```

## HTTP Status Codes

| Code | Description                                                       |
|------|-------------------------------------------------------------------|
| 200  | OK - The request succeeded                                        |
| 201  | Created - A new resource was created                              |
| 202  | Accepted - The request was accepted for processing                |
| 204  | No Content - The request succeeded but returns no content         |
| 400  | Bad Request - The request could not be understood                 |
| 401  | Unauthorized - Authentication failed                              |
| 403  | Forbidden - Authentication succeeded but insufficient permissions |
| 404  | Not Found - The requested resource does not exist                 |
| 409  | Conflict - The request conflicts with the current state           |
| 422  | Unprocessable Entity - Validation errors                          |
| 429  | Too Many Requests - Rate limit exceeded                           |
| 500  | Internal Server Error - Something went wrong on the server        |
| 503  | Service Unavailable - The service is temporarily unavailable      |
| 504  | Gateway Timeout - A dependent service timed out                   |

## Pagination

For endpoints that return collections, pagination is applied:

### Request Parameters

| Parameter | Description                                 | Default |
|-----------|---------------------------------------------|---------|
| `limit`   | Number of items per page                    | 20      |
| `offset`  | Number of items to skip                     | 0       |
| `cursor`  | Opaque cursor for more efficient pagination | -       |

### Paginated Response

```json
{
  "success": true,
  "data": [ ... ],
  "meta": {
    "pagination": {
      "total": 243,
      "limit": 20,
      "offset": 40,
      "next_cursor": "Y3Vyc29yOjYw",
      "prev_cursor": "Y3Vyc29yOjIw"
    },
    "request_id": "req_8f7h6g5j4k3l2j1k"
  }
}
```

## Search Request Format

### Basic Search

```json
{
  "query": "opossum behavior",
  "options": {
    "model": "gemini",
    "mode": "balanced",
    "limit": 10
  },
  "filters": {
    "date_range": {
      "from": "2023-01-01",
      "to": "2023-12-31"
    },
    "content_type": ["article", "research"]
  },
  "context": {
    "user_location": "North America",
    "previous_searches": ["marsupial species"]
  }
}
```

### Image Analysis

```json
{
  "image_url": "https://example.com/images/opossum.jpg",
  "options": {
    "detail_level": "high",
    "analysis_type": "object_detection"
  }
}
```

## Response Examples

### Search Response

```json
{
  "success": true,
  "data": {
    "results": [
      {
        "title": "North American Opossum Behavior Patterns",
        "snippet": "The opossum is known for its defensive behavior of 'playing dead' when threatened...",
        "source": "Wildlife Journal",
        "relevance_score": 0.92,
        "url": "https://example.com/articles/opossum-behavior"
      },
      // Additional results...
    ],
    "suggested_queries": [
      "opossum diet",
      "opossum habitat"
    ],
    "knowledge_graph": {
      "entity": "Virginia opossum",
      "attributes": {
        "scientific_name": "Didelphis virginiana",
        "lifespan": "2-4 years",
        "diet": "Omnivore"
      }
    }
  },
  "meta": {
    "processing_time": 156,
    "model_used": "gemini",
    "request_id": "req_8f7h6g5j4k3l2j1k",
    "cache_status": "MISS"
  }
}
```

### Image Analysis Response

```json
{
  "success": true,
  "data": {
    "objects_detected": [
      {
        "label": "opossum",
        "confidence": 0.97,
        "bounding_box": {
          "x": 23,
          "y": 45,
          "width": 200,
          "height": 150
        }
      },
      {
        "label": "tree",
        "confidence": 0.85,
        "bounding_box": {
          "x": 300,
          "y": 10,
          "width": 100,
          "height": 400
        }
      }
    ],
    "scene_description": "An opossum climbing on a tree at night",
    "tags": ["wildlife", "nocturnal", "marsupial", "forest"]
  },
  "meta": {
    "processing_time": 345,
    "model_used": "gemini-vision",
    "request_id": "req_9g8h7j6k5l4k3j2h",
    "image_dimensions": {
      "width": 1024,
      "height": 768
    }
  }
}
```

### Error Response Example

```json
{
  "success": false,
  "error": {
    "code": "invalid_parameter",
    "message": "Invalid value for parameter 'model'",
    "details": [
      {
        "field": "model",
        "message": "Model 'gpt-5' is not available. Available models: gemini, ollama, local"
      }
    ]
  },
  "meta": {
    "request_id": "req_5d6f7g8h9j0k1l2m",
    "processing_time": 12
  }
}
```

## Versioning

The API is versioned using URL path. The current version is `v1`.

## CORS

The API supports Cross-Origin Resource Sharing (CORS) for browser applications:

| Header                         | Value                                                                  |
|--------------------------------|------------------------------------------------------------------------|
| `Access-Control-Allow-Origin`  | `*` or configured domains                                              |
| `Access-Control-Allow-Methods` | `GET, POST, PUT, PATCH, DELETE, OPTIONS`                               |
| `Access-Control-Allow-Headers` | `Origin, Content-Type, Accept, Authorization, X-API-Key, X-Request-ID` |
| `Access-Control-Max-Age`       | `86400` (24 hours)                                                     |

## Request Timeouts

| Operation       | Timeout    |
|-----------------|------------|
| Standard search | 10 seconds |
| Image analysis  | 30 seconds |
| SVG generation  | 15 seconds |
| Bulk operations | 60 seconds |

Requests exceeding these timeouts will receive a `504 Gateway Timeout` response.
