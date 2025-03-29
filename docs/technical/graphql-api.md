# Technical Documentation: GraphQL API

## 1. Overview

Opossum Search uses GraphQL as its primary API layer, providing a flexible, type-safe interface for clients to interact
with the system. The GraphQL implementation leverages Ariadne for schema-first development and includes advanced
features such as rate limiting, request costing, authentication, and integration with Apollo Studio.

> **Related Documentation:**
> - [GraphQL API: Getting Started](../api/getting-started.md) - User guide for integrating with the GraphQL API
> - [Service Availability: Rate Limiting](../service-availability/rate-limiting-throttling.md) - How rate limiting is
    implemented at the API level
> - [API Reference: Routes](../api/routes.md) - REST API routes that complement the GraphQL API

## 2. Schema Design

### 2.1 Core Types

The GraphQL schema defines several core types:

```graphql
type Query {
  # Status and health checking
  service_status: ServiceStatus!
  
  # Search-related queries
  search(query: String!, options: SearchOptions): SearchResult!
  
  # Utility queries
  generate_gibberish(prompt: String!): String @cost(value: 2)
}

type Mutation {
  # Interactive chat
  chat(message: String!, conversation_id: ID): ChatResponse!
    @rateLimit(limit: "50 per day, 10 per hour")
    @cost(value: 10)
    @auth(requires: USER)
  
  # Image processing
  process_image(image: Upload!, prompt: String): ImageAnalysisResult!
    @rateLimit(limit: "20 per day, 5 per hour")
    @cost(value: 15)
    @auth(requires: USER)
  
  # Service management
  force_service_check: ServiceStatus!
    @rateLimit(limit: "10 per hour")
    @auth(requires: ADMIN)
}

type ServiceStatus {
  gemini_available: Boolean!
  ollama_available: Boolean!
  transformers_available: Boolean!
  all_services_available: Boolean!
  last_checked: String!
}

type ChatResponse {
  message: String!
  conversation_id: ID!
  backend_used: String
  tokens_used: Int
}

type ImageAnalysisResult {
  description: String!
  tags: [String!]
  confidence: Float
  backend_used: String
}

type SearchResult {
  results: [SearchItem!]!
  total: Int!
  query_time_ms: Int!
}

type SearchItem {
  title: String!
  url: String
  snippet: String
  score: Float
}

input SearchOptions {
  limit: Int
  offset: Int
  filter: String
}
```

### 2.2 Schema Registration

```python
# Schema registration with Ariadne
from ariadne import load_schema_from_path, make_executable_schema
from ariadne.asgi import GraphQL

# Load schema from file
type_defs = load_schema_from_path("app/api/schema.graphql")

# Create executable schema with resolvers and directives
schema = make_executable_schema(
    type_defs,
    query_resolvers,
    mutation_resolvers,
    cost_directive,
    rate_limit_directive,
    auth_directive,
    caching_directive
)

# Create GraphQL application
graphql_app = GraphQL(
    schema,
    debug=Config.DEBUG,
    introspection=Config.GRAPHQL_GRAPHIQL,
    validation_rules=[
        cost_validation_rule,
        depth_limit_rule
    ]
)
```

## 3. Directives

### 3.1 Cost Directive

Controls query complexity and prevents resource abuse:

```python
# Cost directive implementation
from ariadne import SchemaDirectiveVisitor
from graphql import GraphQLField

class CostDirective(SchemaDirectiveVisitor):
    def visit_field_definition(self, field, object_type):
        original_resolver = field.resolve
        cost_value = self.args.get("value", 1)
        
        async def resolve_with_cost(obj, info, **kwargs):
            # Add cost to request context
            if not hasattr(info.context, "cost"):
                info.context.cost = 0
            info.context.cost += cost_value
            
            # Apply cost limit validation
            if info.context.cost > Config.GRAPHQL_COMPLEXITY_THRESHOLD:
                raise Exception(f"Query exceeded cost limit: {info.context.cost}")
                
            # Call original resolver
            return await original_resolver(obj, info, **kwargs)
            
        field.resolve = resolve_with_cost
        return field
```

### 3.2 Rate Limit Directive

Prevents API abuse by enforcing request rate limits:

```python
# Rate limit directive implementation
class RateLimitDirective(SchemaDirectiveVisitor):
    def visit_field_definition(self, field, object_type):
        original_resolver = field.resolve
        limit = self.args.get("limit", "100 per day")
        
        async def resolve_with_rate_limit(obj, info, **kwargs):
            # Get client identifier
            client_id = self._get_client_id(info.context)
            
            # Check rate limit
            limiter = RateLimiter(redis_client)
            is_limited = await limiter.is_rate_limited(client_id, limit)
            
            if is_limited:
                raise Exception("Rate limit exceeded. Try again later.")
                
            # Increment rate counter
            await limiter.increment_rate_counter(client_id, limit)
            
            # Call original resolver
            return await original_resolver(obj, info, **kwargs)
            
        field.resolve = resolve_with_rate_limit
        return field
        
    def _get_client_id(self, context):
        """Extract client identifier from request context"""
        # Try authenticated user ID first
        if hasattr(context, "user") and context.user:
            return f"user:{context.user.id}"
            
        # Fall back to IP address
        return f"ip:{context.request.client.host}"
```

### 3.3 Auth Directive

Enforces authentication requirements for protected operations:

```python
# Auth directive implementation
class AuthDirective(SchemaDirectiveVisitor):
    def visit_field_definition(self, field, object_type):
        original_resolver = field.resolve
        required_role = self.args.get("requires", "USER")
        
        async def resolve_with_auth(obj, info, **kwargs):
            # Check if user is authenticated
            if not hasattr(info.context, "user") or not info.context.user:
                raise Exception("Authentication required")
                
            # Check role if specified
            if required_role == "ADMIN" and not info.context.user.is_admin:
                raise Exception("Admin access required")
                
            # Call original resolver
            return await original_resolver(obj, info, **kwargs)
            
        field.resolve = resolve_with_auth
        return field
```

### 3.4 Caching Directive

Enables resolver-level caching for expensive operations:

```python
# Caching directive implementation
class CachingDirective(SchemaDirectiveVisitor):
    def visit_field_definition(self, field, object_type):
        original_resolver = field.resolve
        ttl = self.args.get("ttl", 60)  # Default 60 seconds
        
        async def resolve_with_caching(obj, info, **kwargs):
            # Generate cache key
            cache_key = f"graphql:cache:{info.field_name}:{hash(frozenset(kwargs.items()))}"
            
            # Check cache
            cached = await redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
                
            # Call original resolver
            result = await original_resolver(obj, info, **kwargs)
            
            # Cache result
            await redis_client.setex(
                cache_key,
                ttl,
                json.dumps(result, default=serialize_for_json)
            )
            
            return result
            
        field.resolve = resolve_with_caching
        return field
```

## 4. Query Examples

### 4.1 Service Status Check

```graphql
query CheckStatus {
  service_status {
    gemini_available
    ollama_available
    transformers_available
    all_services_available
    last_checked
  }
}
```

### 4.2 Text Chat

```graphql
mutation SendChatMessage {
  chat(
    message: "What is the natural habitat of opossums?"
    conversation_id: "conv_12345"
  ) {
    message
    conversation_id
    backend_used
    tokens_used
  }
}
```

### 4.3 Image Processing

```graphql
mutation ProcessImage($image: Upload!, $prompt: String) {
  process_image(
    image: $image
    prompt: "Describe what you see in this image"
  ) {
    description
    tags
    confidence
    backend_used
  }
}
```

### 4.4 Search Query

```graphql
query Search($query: String!, $options: SearchOptions) {
  search(
    query: "opossum diet in urban environments"
    options: {
      limit: 10
      filter: "recent"
    }
  ) {
    results {
      title
      url
      snippet
      score
    }
    total
    query_time_ms
  }
}
```

## 5. Apollo Studio Integration

### 5.1 Schema Reporting

The GraphQL API reports its schema to Apollo Studio for monitoring and exploration:

```python
# Apollo Studio integration
from ariadne.contrib.apollo import ApolloTracingExtension
from ariadne.contrib.federation import FederatedObjectType, make_federated_schema

# Setup Apollo extensions if enabled
extensions = []
if Config.APOLLO_STUDIO_ENABLED:
    extensions.append(ApolloTracingExtension)

# Create GraphQL application with Apollo integration
graphql_app = GraphQL(
    schema,
    debug=Config.DEBUG,
    introspection=Config.GRAPHQL_GRAPHIQL,
    extensions=extensions
)

# Apollo Studio configuration in settings
APOLLO_KEY = os.getenv("APOLLO_KEY")
APOLLO_GRAPH_REF = os.getenv("APOLLO_GRAPH_REF", "opossum-search@current")
APOLLO_SCHEMA_REPORTING = os.getenv("APOLLO_SCHEMA_REPORTING", "True").lower() == "true"
```

### 5.2 Performance Tracing

Apollo tracing provides performance insights:

```python
# Apollo tracing middleware
@app.middleware("http")
async def apollo_tracing_middleware(request, call_next):
    # Skip non-GraphQL requests
    if not request.url.path == Config.GRAPHQL_ENDPOINT:
        return await call_next(request)
        
    # Add Apollo tracing header
    response = await call_next(request)
    response.headers["apollo-federation-include-trace"] = (
        "ftv1" if Config.APOLLO_INCLUDE_TRACES else "false"
    )
    
    return response
```

## 6. Security and Performance

### 6.1 Depth Limiting

Prevents deeply nested queries that could consume excessive resources:

```python
# GraphQL depth limitation
from graphql import validation
from graphql.language.ast import FieldNode, FragmentSpreadNode, InlineFragmentNode

class DepthLimitRule(validation.ValidationRule):
    def __init__(self, max_depth):
        super().__init__()
        self.max_depth = max_depth
        
    def enter_operation_definition(self, node, key, parent, path, ancestors):
        self.depth_map = {}
        return node
        
    def enter_field(self, node, key, parent, path, ancestors):
        depth = self._get_depth(ancestors)
        if depth > self.max_depth:
            self.report_error(f"Query exceeds maximum depth of {self.max_depth}")
        return node
        
    def _get_depth(self, ancestors):
        # Calculate current depth based on ancestry
        depth = 0
        for ancestor in ancestors:
            if isinstance(ancestor, (FieldNode, FragmentSpreadNode, InlineFragmentNode)):
                depth += 1
        return depth

# Create depth limit rule
depth_limit_rule = DepthLimitRule(Config.GRAPHQL_DEPTH_LIMIT)
```

### 6.2 CORS Configuration

Cross-Origin Resource Sharing settings for browser security:

```python
# CORS middleware configuration
from starlette.middleware.cors import CORSMiddleware

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=Config.CORS_ALLOWED_ORIGINS,
    allow_credentials=Config.CORS_ALLOW_CREDENTIALS,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=Config.CORS_ALLOW_HEADERS,
    expose_headers=Config.CORS_EXPOSE_HEADERS
)
```

### 6.3 Response Compression

Reduces bandwidth usage for API responses:

```python
# Compression middleware
from starlette.middleware.gzip import GZipMiddleware

# Add compression middleware
app.add_middleware(
    GZipMiddleware,
    minimum_size=Config.COMPRESS_MIN_SIZE,
    compresslevel=Config.COMPRESS_LEVEL
)
```

### 6.4 API Key Authentication

Secures the GraphQL API with API key validation:

```python
# API key authentication middleware
@app.middleware("http")
async def api_key_middleware(request, call_next):
    # Skip if API key auth is disabled
    if not Config.API_KEY_REQUIRED:
        return await call_next(request)
        
    # Skip non-GraphQL requests
    if not request.url.path == Config.GRAPHQL_ENDPOINT:
        return await call_next(request)
        
    # Check for API key in headers or query parameters
    api_key = request.headers.get("x-api-key")
    if not api_key:
        # Try query parameter
        query_params = request.query_params
        api_key = query_params.get("api_key")
    
    # Validate API key
    if not api_key or api_key != Config.API_KEY:
        return JSONResponse(
            status_code=401,
            content={"error": "Invalid or missing API key"}
        )
    
    # Proceed with request
    return await call_next(request)
```

## 7. Integration with GraphQL Voyager

For schema visualization and exploration, the application includes GraphQL Voyager:

```python
# Voyager integration
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

# Setup templates for Voyager
templates = Jinja2Templates(directory="templates")

# Add Voyager endpoint
@app.get("/voyager", response_class=HTMLResponse)
async def voyager(request: Request):
    """Serve GraphQL Voyager interface"""
    if not Config.VOYAGER_ENABLED:
        return {"error": "GraphQL Voyager is disabled"}
        
    return templates.TemplateResponse(
        Config.VOYAGER_PATH,
        {"request": request, "graphql_endpoint": Config.GRAPHQL_ENDPOINT}
    )
```

## 8. Resolver Implementation

Sample resolver implementation for the core queries:

```python
# Query resolvers
query_resolvers = QueryType()

@query_resolvers.field("service_status")
async def resolve_service_status(_, info):
    """Resolve service status query"""
    service_monitor = ServiceMonitor()
    await service_monitor.check_all_services()
    
    return {
        "gemini_available": service_monitor.services["gemini"],
        "ollama_available": service_monitor.services["ollama"],
        "transformers_available": service_monitor.services["transformers"],
        "all_services_available": all(service_monitor.services.values()),
        "last_checked": datetime.datetime.now().isoformat()
    }

# Mutation resolvers
mutation_resolvers = MutationType()

@mutation_resolvers.field("chat")
async def resolve_chat(_, info, message, conversation_id=None):
    """Resolve chat mutation"""
    # Create or retrieve conversation
    if not conversation_id:
        conversation_id = str(uuid.uuid4())
    
    # Get backend
    backend = HybridModelBackend()
    
    # Generate response
    response, metadata = await backend.generate_response(
        message, 
        conversation_id=conversation_id
    )
    
    return {
        "message": response,
        "conversation_id": conversation_id,
        "backend_used": metadata.get("backend"),
        "tokens_used": metadata.get("tokens", 0)
    }
```

The GraphQL API serves as the primary interface for Opossum Search, providing a flexible, secure, and performant way for
clients to interact with the system. The schema-first approach with Ariadne enables clean separation of concerns, while
directives handle cross-cutting concerns like authentication, rate limiting, and caching.