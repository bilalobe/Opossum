# Opossum Search

Opossum Search is an adaptive chat interface with multiple AI backend services, automatic failover capabilities, and service availability monitoring. The interface features a unique, AI-powered dynamic background that generates opossum-themed gibberish text with emojis in a mesmerizing snake-like pattern.

## Features

- 🤖 Multiple AI model backends (Gemini, Ollama, Transformers)
- 🔄 Automatic failover between services based on availability
- 📊 Real-time service status monitoring and visualization
- 🖼️ Image processing capabilities
- 🎨 SVG generation from text descriptions via Chat2SVG
- 📱 Responsive web interface
- 📝 Topic detection and context-aware conversations
- 🎨 Dynamic NLP-powered background with snake-like text animation
- 🦝 Opossum-themed content generation
- 😊 Contextual emoji integration
- ✨ Special highlighting for opossum-related terms
- 🔌 GraphQL API for integration with other services

## Architecture

The system uses a tiered fallback architecture:

1. **Primary Service**: Google's Gemini API (cloud-based)
2. **Secondary Service**: Ollama (local LLM server)
3. **Tertiary Service**: Transformers (client-side processing)

For SVG generation, the system utilizes:
1. **Chat2SVG**: Three-stage AI pipeline for text-to-SVG generation
2. **Native Template System**: Fast, reliable template-based visualization rendering

When a service becomes unavailable, requests automatically route to the next available backend while maintaining different capability levels.

## Installation

```bash
# Clone the repository
git clone https://github.com/bilalobe/opossum.git
cd Opposum

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Additional libraries for background animation
pip install markovify emoji

# Set up Chat2SVG (for SVG generation)
git submodule update --init --recursive

# Set environment variables
export GEMINI_API_KEY="your_gemini_api_key"  # On Windows: set GEMINI_API_KEY=your_gemini_api_key
```

### Prerequisites

- Python 3.8+
- For Ollama backend: Ollama server running locally
- For Gemini: Valid API key
- For Chat2SVG: CairoSVG and PyYAML
- markovify (for NLP-based text generation)
- emoji (for emoji integration)

## Usage

```bash
# Start the application
python main.py
```

Visit http://localhost:5000 in your browser to access the chat interface.

## Configuration

Edit `app/config.py` to modify:

- API keys and endpoints
- Model parameters (temperature, tokens, etc.)
- Service fallback behavior
- Caching settings
- SVG generation options
- Background animation settings and refresh rate
- Text generation parameters

## Service Availability

The system continually monitors service health and adapts accordingly:

- Tracks response time and availability percentage
- Implements rate limiting for Gemini API
- Visualizes current service status
- Automatically selects the most appropriate backend based on request type and service health

## SVG Generation

Opossum Search provides two complementary approaches for SVG generation:

### Native Template System
- Fast, template-based generation for operational visualizations
- Low resource usage and high reliability
- Perfect for service status dashboards and process diagrams

### Chat2SVG Integration
- Text-to-SVG generation using a three-stage AI pipeline
- Template Generation with LLMs
- Detail Enhancement (resource-aware)
- SVG Optimization
- Streaming generation for large SVGs
- Client-side rendering options for resource-constrained environments

Example SVG generation via GraphQL:

```graphql
mutation {
  generateSVG(
    input: {
      type: TEXT_TO_SVG
      prompt: "An opossum playing with a keyboard under moonlight"
      style: "cartoon"
    }
  ) {
    svg_content
    base64_image
    metadata
  }
}
```

## GraphQL API

Opossum Search provides a GraphQL API for integration with other services:

- **Service Status**: Query the availability of AI backends
- **Chat Operations**: Send messages and receive responses
- **Image Processing**: Submit images for analysis
- **SVG Generation**: Create vector graphics from text descriptions
- **Service Control**: Force service checks and manage backend selection

API documentation is available in the MkDocs documentation under API Reference, including:
- GraphQL schema details
- Available queries and mutations
- Error handling
- Rate limits and throttling policies
- Subscription options for real-time updates

Example usage:
```bash
# Check service status
curl -X POST http://localhost:5000/graphql \
  -H "Content-Type: application/json" \
  -d '{"query": "{ serviceStatus { name, status, responseTime, availability } }"}'

# Send a chat message
curl -X POST http://localhost:5000/graphql \
  -H "Content-Type: application/json" \
  -d '{"query": "mutation { sendMessage(message: \"Tell me about opossums\") { response, service, timestamp } }"}'
```

## Visual Features

### Dynamic Background

The application features an AI-powered dynamic background that:

- Generates authentic-looking gibberish text using Markov chains
- Integrates contextually relevant emojis
- Creates a snake-like flowing text pattern
- Highlights opossum-related terms
- Animates individual words and emojis independently
- Auto-refreshes periodically to maintain visual interest

### Special Features

- **National Opossum Day** (October 18): Special visualizations and themes are automatically activated
- **Interactive SVG Visualizations**: Real-time service status, failover process diagrams, and capability visualizations
- **Text-to-SVG Generation**: Create custom SVG illustrations from text descriptions

## Documentation

Documentation is built with MkDocs:

```bash
# Install MkDocs
pip install mkdocs

# Serve documentation locally
mkdocs serve
```

Visit http://localhost:8000 to view the documentation.

## License

[MIT License](LICENSE)

## Contributing

Contributions welcome! Please feel free to submit a Pull Request.