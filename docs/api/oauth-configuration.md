# OAuth 2.0 Configuration

## Overview

Opossum Search supports OAuth 2.0 authentication for secure user authorization. This document explains how to configure and use OAuth 2.0 in your applications.

## Prerequisites

- A registered OAuth application (client ID and secret)
- HTTPS enabled for your redirect URI
- Valid API credentials

## OAuth Flow Configuration

### 1. Authorization Request

```
GET /oauth/authorize
```

**Required Parameters:**
- `client_id` - Your OAuth client ID
- `redirect_uri` - URL to return to after authorization
- `response_type` - Must be "code"
- `scope` - Space-separated list of requested permissions

**Optional Parameters:**
- `state` - Random string to prevent CSRF attacks
- `prompt` - "none", "login", or "consent"

**Example Request:**
```
https://api.opossumsearch.com/oauth/authorize?
  client_id=your_client_id&
  redirect_uri=https://your-app.com/callback&
  response_type=code&
  scope=read write&
  state=random_state_string
```

### 2. Token Exchange

```
POST /oauth/token
```

**Required Parameters:**
- `grant_type` - Must be "authorization_code"
- `code` - The authorization code received
- `redirect_uri` - Same URI used in authorization
- `client_id` - Your OAuth client ID
- `client_secret` - Your OAuth client secret

**Example Request:**
```bash
curl -X POST https://api.opossumsearch.com/oauth/token \
  -d grant_type=authorization_code \
  -d code=received_auth_code \
  -d redirect_uri=https://your-app.com/callback \
  -d client_id=your_client_id \
  -d client_secret=your_client_secret
```

**Example Response:**
```json
{
  "access_token": "access_token_value",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "refresh_token_value",
  "scope": "read write"
}
```

### 3. Token Refresh

```
POST /oauth/token
```

**Required Parameters:**
- `grant_type` - Must be "refresh_token"
- `refresh_token` - The refresh token
- `client_id` - Your OAuth client ID
- `client_secret` - Your OAuth client secret

**Example Request:**
```bash
curl -X POST https://api.opossumsearch.com/oauth/token \
  -d grant_type=refresh_token \
  -d refresh_token=refresh_token_value \
  -d client_id=your_client_id \
  -d client_secret=your_client_secret
```

## Scopes

| Scope | Description |
|-------|-------------|
| read | Read-only access to public data |
| write | Ability to modify data |
| admin | Administrative access (requires approval) |

## Security Considerations

1. Always use HTTPS for all OAuth endpoints
2. Validate the state parameter to prevent CSRF
3. Store tokens securely (encrypted at rest)
4. Never expose client secrets in client-side code
5. Implement token rotation for long-lived sessions

## Error Handling

### Common Error Responses

| Error Code | Description | Resolution |
|------------|-------------|------------|
| invalid_request | Missing required parameter | Check request parameters |
| invalid_client | Invalid client credentials | Verify client ID and secret |
| invalid_grant | Invalid authorization code | Request new authorization |
| invalid_scope | Requested scope not valid | Check scope permissions |

### Example Error Response:
```json
{
  "error": "invalid_request",
  "error_description": "Missing required parameter: grant_type",
  "error_uri": "https://api.opossumsearch.com/docs/oauth-errors#invalid_request"
}
```

## Implementation Examples

### JavaScript/Node.js
```javascript
const config = {
  clientId: 'your_client_id',
  clientSecret: 'your_client_secret',
  redirectUri: 'https://your-app.com/callback'
};

// Authorization URL construction
const authUrl = `https://api.opossumsearch.com/oauth/authorize?
  client_id=${config.clientId}&
  redirect_uri=${encodeURIComponent(config.redirectUri)}&
  response_type=code&
  scope=read%20write`;

// Token exchange
async function exchangeCode(code) {
  const response = await fetch('https://api.opossumsearch.com/oauth/token', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: new URLSearchParams({
      grant_type: 'authorization_code',
      code,
      redirect_uri: config.redirectUri,
      client_id: config.clientId,
      client_secret: config.clientSecret,
    }),
  });
  return response.json();
}
```

### Python
```python
import requests

config = {
    'client_id': 'your_client_id',
    'client_secret': 'your_client_secret',
    'redirect_uri': 'https://your-app.com/callback'
}

# Authorization URL construction
auth_url = (
    'https://api.opossumsearch.com/oauth/authorize?'
    f'client_id={config["client_id"]}&'
    f'redirect_uri={quote(config["redirect_uri"])}&'
    'response_type=code&'
    'scope=read%20write'
)

# Token exchange
def exchange_code(code):
    response = requests.post(
        'https://api.opossumsearch.com/oauth/token',
        data={
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': config['redirect_uri'],
            'client_id': config['client_id'],
            'client_secret': config['client_secret'],
        }
    )
    return response.json()