# Technical Documentation Index

## Overview

The technical documentation section provides in-depth information about Opossum Search's core systems, architectures,
and implementation details. This section is intended for developers, system architects, and technical stakeholders who
need to understand how the system works under the hood.

## Core Architectures

Opossum Search is built on several key architectural components that work together to provide a resilient, performant
search experience:

- **[Redis Caching Architecture](./redis-caching-architecture.md)** - Our multi-level caching system for optimizing
  performance and reducing API costs
- **[Hybrid Model Selection](./hybrid-model-selection.md)** - How Opossum intelligently routes queries to appropriate AI
  backends
- **[Image Processing Pipeline](./image-processing-pipeline.md)** - End-to-end processing of images for multimodal
  understanding
- **[GraphQL API](./graphql-api.md)** - Our flexible, type-safe API implementation with security controls
- **[OpenTelemetry Integration](./opentelemetry-integration.md)** - Comprehensive observability implementation across
  the system
- **[SVG Markup](./svg-markup.md)** - Secure generation of vector graphics for visualizations
- **[System Architecture Overview](./system-architecture-overview.md)** - High-level view of how all components interact
- **[Deployment & Operations Guide](./devops-guide.md)** - Guide for deploying and maintaining the system
- **[Security Model](./security-model.md)** - Comprehensive security controls and practices
- **[Error Handling & Resilience](./error-handling-resilience.md)** - How the system handles failures gracefully

## Key Concepts

### Multi-Level Resilience

Opossum Search implements multiple layers of resilience, including service monitoring, circuit breakers, fallback
chains, and graceful degradation. This ensures the system remains operational even when individual components fail.

### Dynamic Model Selection

Rather than relying on a single AI model, Opossum uses a sophisticated scoring system to route queries to the most
appropriate backend based on capability, availability, and performance characteristics.

### Observability-First Design

Every component is instrumented with telemetry, providing deep visibility into system behavior, performance bottlenecks,
and error patterns through distributed tracing, metrics, and structured logging.

## When to Use This Documentation

- **Planning integrations** with Opossum's backend systems
- **Troubleshooting** complex technical issues
- **Understanding performance characteristics** of different components
- **Implementing similar architectures** in your own systems
- **Contributing** to Opossum's development

## Related Sections

- Service Availability - Higher-level documentation about system availability
- Development - Practical guides for developers working with the codebase
- Infrastructure - Details about the supporting infrastructure
