# Context and Scope

## Overview

This document describes the service availability monitoring system implemented for the Opossum Search application. The
system monitors the availability of multiple AI model backends, manages rate limits, and provides automatic failover to
ensure continuous operation.

## Services in Scope

The following services are monitored for availability:

| Service      | Type          | Purpose                                         | Availability Mechanism                       |
|--------------|---------------|-------------------------------------------------|----------------------------------------------|
| Gemini       | External API  | High-capability AI models with API-based access | API key validation and rate limit monitoring |
| Ollama       | Local service | Self-hosted AI models with REST API             | Connection health checking                   |
| Transformers | Local library | Fallback for offline operation                  | Always assumed available (local)             |

## Critical Paths

The application depends on at least one service being available to respond to user queries. The dependency chain is:

1. **Primary Path**: Gemini API (when available and suitable for query type)
2. **Secondary Path**: Ollama service (when available and suitable for query type)
3. **Fallback Path**: Transformers models (always available, used when other services fail)

!!! note
    The application is designed to function even when the primary service (Gemini API) is unavailable, by automatically failing over to alternative services.

## System Boundaries

The availability system:

- **Monitors**: All AI model service endpoints
- **Records**: Usage statistics for rate-limited services
- **Logs**: Service status changes and availability events
- **Does Not**: Handle network configuration or service deployment

## Stakeholders

| Stakeholder     | Interest in Service Availability                         |
|-----------------|----------------------------------------------------------|
| End Users       | Uninterrupted access to AI functionality                 |
| Operations Team | Monitoring service health and diagnostics                |
| Developers      | Understanding fallback behavior and service dependencies |

## External Interfaces

- **Gemini API**: Google Cloud API with rate limits and authentication
- **Ollama REST API**: Local service providing model inference
- **Transformers Library**: Local Python library for model inference

## Technical Context

The service availability system is implemented as a component in the model backend selection process. It:

1. Performs regular health checks (maximum once per 30 seconds per service)
2. Runs checks concurrently to minimize impact on performance
3. Influences model selection based on real-time availability
4. Provides status information for logging and diagnostics