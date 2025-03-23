# API Routes Documentation

For detailed information about request and response formats, see [Request/Response Documentation](request-response.md). For error code details, see [Error Codes](error-codes.md). Information on API usage limits can be found in [Rate Limits](rate-limits.md). To learn about real-time notifications, refer to [Webhooks](webhooks.md). For system status and component health, see [Health Endpoints](health-endpoints.md).

## Base URL

All API endpoints _will_ be available at:

```
https://api.opossumsearch.com/v1
```

## Authentication

Most endpoints require authentication via one of these methods:
- API key (passed as `X-API-Key` header)
- Bearer token (passed as `Authorization: Bearer <token>` header)
- OAuth 2.0 (for user-authenticated requests)

See [Authentication](getting-started.md#authentication) for detailed instructions.

## Core Search Endpoints

### Search

```
GET /search
```

Performs a search using specified parameters.

**Query Parameters:**
- `q` (required): The search query text
- `model` (optional): Specific model to use ("gemini", "ollama", etc.)
- `mode` (optional): Search mode ("accurate", "creative", "balanced")
- `limit` (optional): Maximum number of results (default: 10)
- `include_images` (optional): Whether to allow image results (default: false)

**Example Request:**
```
GET /search?q=how%20do%20opossums%20sleep&model=gemini&mode=accurate&limit=5
```

### Multi-Search

```
POST /multi-search
```

Performs multiple searches in a single request.

**Request Body:**
```json
{
  "searches": [
    {
      "q": "opossum diet",
      "model": "gemini"
    },
    {
      "q": "opossum habitat",
      "model": "ollama"
    }
  ],
  "common": {
    "mode": "balanced",
    "limit": 3
  }
}
```

### Image Analysis

```
POST /analyze-image
```

Analyzes the content of an image.

**Request Body:**
- Multipart form with `image` field containing the image file
- Additional parameters as form fields

**Example Request:**
```
POST /analyze-image
Content-Type: multipart/form-data; boundary=----WebKitFormBoundary7MA4YWxkTrZu0gW

------WebKitFormBoundary7MA4YWxkTrZu0gW
Content-Disposition: form-data; name="image"; filename="opossum.jpg"
Content-Type: image/jpeg

(binary image data)
------WebKitFormBoundary7MA4YWxkTrZu0gW
Content-Disposition: form-data; name="detail_level"

high
------WebKitFormBoundary7MA4YWxkTrZu0gW--
```

## Conversation Management

### Start Conversation

```
POST /conversation
```

Starts a new conversation session.

**Request Body:**
```json
{
  "initial_message": "Tell me about opossums",
  "settings": {
    "model": "gemini",
    "mode": "creative"
  }
}
```

### Continue Conversation

```
POST /conversation/{conversation_id}/message
```

Adds a message to an existing conversation.

**Request Body:**
```json
{
  "message": "How long do they live?",
  "context": {
    "location": "North America"
  }
}
```

### List Conversations

```
GET /conversations
```

Lists all conversations for the authenticated user.

**Query Parameters:**
- `limit` (optional): Maximum number of conversations (default: 20)
- `offset` (optional): Pagination offset (default: 0)
- `status` (optional): Filter by status ("active", "archived")

## SVG Generation

### Generate Visualization

```
POST /generate-svg
```

Generates an SVG visualization based on provided data.

**Request Body:**
```json
{
  "visualization_type": "data_chart",
  "data": [
    {"label": "Jan", "value": 10},
    {"label": "Feb", "value": 15},
    {"label": "Mar", "value": 8}
  ],
  "options": {
    "width": 800,
    "height": 400,
    "colors": ["#1f77b4", "#ff7f0e", "#2ca02c"]
  }
}
```

### Get SVG Template

```
GET /svg-templates/{template_id}
```

Retrieves a specific SVG template.

## System Configuration

### Get Configuration

```
GET /config
```

Retrieves current system configuration (admin only).

### Update Configuration

```
PATCH /config
```

Updates system configuration parameters (admin only).

**Request Body:**
```json
{
  "cache": {
    "ttl": 3600,
    "max_size": "2GB"
  },
  "models": {
    "default": "gemini"
  }
}
```

## Health and Status

### System Status

```
GET /status
```

Returns overall system status and health.

### Component Health

```
GET /health/{component}
```

Returns health information for a specific component.

Valid components: `api`, `models`, `cache`, `database`, `all`

## Model Management

### List Available Models

```
GET /models
```

Lists all available AI models with capabilities.

### Model Details

```
GET /models/{model_id}
```

Returns detailed information about a specific model.

### Model Performance

```
GET /models/{model_id}/performance
```

Returns performance metrics for a specific model.
