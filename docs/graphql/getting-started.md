# GraphQL API Documentation

## Available Tools

### Apollo Studio Integration
Apollo Studio provides powerful tools for exploring and monitoring your GraphQL API. To use Apollo Studio:

1. Visit http://localhost:5000/graphql in your browser
2. Open Apollo Studio
3. Connect to your local endpoint
4. Explore the schema, run queries, and monitor performance

### GraphQL Voyager
GraphQL Voyager provides an interactive visualization of your API schema:

1. Visit http://localhost:5000/voyager in your browser
2. Explore the relationships between types
3. Click on nodes to see detailed type information
4. Use the search function to find specific types or fields

### Self-Documenting Schema
The GraphQL schema includes comprehensive descriptions for all types and fields:

```graphql
# Example query with descriptions
query {
  service_status {  # Get current status of all backend services with visualization
    name           # The name of the service (e.g., 'gemini', 'ollama', 'transformers')
    available      # Whether the service is currently available
    status         # Human-readable status: 'online', 'degraded', or 'offline'
    response_time  # Response time in milliseconds for the last health check
  }
}
```

## Monitoring and Metrics

### Health Checks
- Endpoint: `/.well-known/apollo/server-health`
- Purpose: Check the health of the GraphQL service

### Schema Information
- Endpoint: `/graphql/schema`
- Purpose: Get the complete GraphQL schema in SDL format

### Metrics
- Endpoint: `/graphql/metrics`
- Purpose: Get Prometheus-compatible metrics for monitoring

## Best Practices

1. Use the schema descriptions to understand field purposes
2. Take advantage of GraphQL batching for multiple operations
3. Monitor query performance in Apollo Studio
4. Use the Voyager visualization to understand schema relationships
5. Enable tracing during development for performance insights

## Example Queries

```graphql
# Get service status with visualization
query GetServiceStatus {
  service_status {
    service_data
    svg_content
    last_updated
  }
}

# Process an image with effects
mutation ProcessImage($imageData: String!, $effects: ImageEffects) {
  process_image(image_data: $imageData, effects: $effects) {
    processed_image
    thumbnail
    info {
      width
      height
      format
    }
  }
}

# Send a chat message
mutation SendChatMessage($input: ChatInput!) {
  chat(input: $input) {
    response
    next_stage
    has_svg
    svg_content
  }
}
```