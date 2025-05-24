# Error Handling & Resilience

The Opossum Search system employs a centralized error handling mechanism and resilience patterns to ensure graceful degradation and robust operation even when external services or internal components fail.

## Centralized Error Handler (`app.utils.error_handler.ErrorHandler`)

The `ErrorHandler` class provides a single point for capturing, classifying, logging, and responding to exceptions throughout the application.

### Key Features:

1.  **Global Exception Capture**: Integrates with Flask to handle uncaught exceptions.
2.  **Error Classification**: Categorizes errors (e.g., `API_CONNECTION`, `RATE_LIMIT`, `VALIDATION`, `SYSTEM`) using the `ErrorCategory` enum for consistent handling.
3.  **Standardized JSON Responses**: Formats errors into a consistent JSON structure using the `ErrorResponse` Pydantic model, including an error code, message, details, request ID, and timestamp.
4.  **Contextual Logging**: Logs errors using the globally configured structured logger, including relevant context provided during the error handling call.
5.  **Circuit Breaker Integration**: Interacts with `CircuitBreaker` instances for external services (`gemini`, `ollama`, `transformers`). Failures are recorded via `record_failure`, and successes via `record_success`. Circuit breakers can be configured per service, including enabling/disabling them.
6.  **Retry Policy Integration**: Reads retry policies (max retries, base delay) configured per service (`gemini`, `ollama`, `transformers`). *Note: The actual retry logic is typically applied via decorators (like `retry_with_exponential_backoff`) before the error handler is invoked.*
7.  **Fallback Mechanism**: Supports registering and invoking fallback functions for specific services if the primary operation fails.
8.  **Prometheus Metrics**: Tracks error occurrences (`opossum_errors_total` counter) and handling duration (`opossum_error_duration_seconds` gauge) categorized by error type.

### Workflow:

1.  An exception occurs and is caught or bubbles up to the Flask app.
2.  The `ErrorHandler.handle_error(error, context)` method is invoked.
3.  The error is classified (`_classify_error`).
4.  Error metrics are updated.
5.  If the error context includes a service name, the corresponding circuit breaker's `record_failure` method is called.
6.  The handler checks if a fallback function is registered for the service and attempts to execute it (`_get_fallback_response`).
7.  If no fallback succeeds, a standardized JSON error response is formatted (`_format_error_response`) based on the error type and details.
8.  The error is logged with appropriate severity and context (`_log_error`).
9.  The formatted JSON response with the correct HTTP status code is returned.

### Configuration:

Error handling behavior, circuit breakers, and retry policies are configured via the Flask application config (see [Deployment & Operations Guide](./devops-guide.md#4-configuration-management)).

## Circuit Breaker Pattern (`app.monitoring.circuit_breaker.CircuitBreaker`)

Used to prevent repeated calls to failing external services.

- **States**: CLOSED (normal), OPEN (failing, calls blocked), HALF_OPEN (testing recovery).
- **Configuration**: Failure threshold, reset timeout (configurable per service).
- **Integration**: The `ErrorHandler` records failures. Decorators or direct checks use the breaker's state (`is_open`, `should_use_fallback`) to decide whether to call the service. `record_success` resets the failure count or closes the breaker.

## Retry Mechanism (`app.utils.retry.retry_with_exponential_backoff`)

A decorator used to automatically retry failing operations (typically API calls) with increasing delays.

- **Features**: Exponential backoff, jitter, configurable max retries, specific exception handling.
- **Configuration**: Max retries, base delay (configurable per service).
- **Integration**: Applied directly to functions making potentially failing calls. Retries happen *before* the error handler is invoked for a final failure.

## Fallback Strategies

When a primary service fails (and retries are exhausted, or the circuit breaker is open), the system attempts to use fallback mechanisms:

1.  **Registered Fallbacks**: The `ErrorHandler` can invoke specific Python functions registered per service.
2.  **Model Selection Router**: The `ServiceRouter` inherently handles fallbacks by selecting the next best available model based on scores and availability if the primary choice fails during the routing process.
3.  **Default Local Model**: The `transformers` backend often serves as the ultimate fallback if all external services are unavailable.

## Chat2SVG Pipeline Resilience

The Chat2SVG pipeline implements dedicated resilience patterns to ensure reliable SVG generation even under suboptimal conditions.

### Circuit Breaker Pattern

The pipeline uses a circuit breaker pattern to prevent cascading failures:

```python
# Initialize global components
_circuit_breaker = CircuitBreaker()

async def generate_svg_request(prompt: str, style: Optional[str] = None,
                             priority: float = 0.5) -> Dict[str, Any]:
    # Check circuit breaker
    if _circuit_breaker.should_use_fallback():
        logger.warning("Circuit breaker active, using fallback processing")
        state.fallback_used = True
        return await _process_with_fallback(state)
        
    # Normal processing...
```

### SVG Generation Fallback Strategy

When the main pipeline encounters errors or when the circuit breaker is open:

1. **Template-Only Mode**: Fallback uses simplified template generation only
2. **Resource Monitoring**: Continues to monitor available resources
3. **Degraded Output**: Returns a basic SVG with essential elements
4. **Circuit Recovery**: Success/failure tracking to automatically reset the circuit

### Integration with Global Error Handling

The Chat2SVG module integrates with the application's centralized error handling system while maintaining domain-specific fallback mechanisms:

- Re-exports the central `CircuitBreaker` component
- Records success/failure metrics to the central monitoring system
- Provides detailed error context for centralized logging

# Fallback Mechanisms

## Fallback Hierarchy

| Priority      | Service      | Type          | Capabilities                               | Limitations                                    |
|---------------|--------------|---------------|--------------------------------------------|------------------------------------------------|
| 1 (Primary)   | Gemini API   | External API  | Full model capabilities, high intelligence | Rate limited, requires internet                |
| 2 (Secondary) | Ollama       | Local service | Good capabilities, custom models           | Requires GPU for performance, local deployment |
| 3 (Tertiary)  | Transformers | Local library | Basic capabilities, offline operation      | Higher latency, limited model size             |
| 4 (SVG)       | Chat2SVG     | Pipeline      | SVG generation with optimization           | Resource-intensive for enhanced details        |
| 5 (Emergency) | Client-side  | JavaScript    | Basic scripted responses                   | Very limited capabilities, no real AI          |

## Hybrid Model Implementation

The system implements an intelligent hybrid model backend that dynamically selects and combines different model capabilities based on availability and requirements:

### Backend Selection Strategy

The hybrid model uses a weighted scoring system to select the most appropriate backend:

| Capability      | Weight | Description                                  |
|-----------------|--------|----------------------------------------------|
| Text Processing | 0.3    | Basic text understanding and generation      |
| Reasoning       | 0.3    | Complex reasoning and inference capabilities |
| Multimodal      | 0.2    | Ability to process images with text          |
| Latency         | 0.1    | Response time importance                     |
| Resource Usage  | 0.1    | System resource consumption consideration    |

### Service Capabilities

Each service is scored based on its capabilities:

#### Gemini API

- Text Processing: 0.9
- Reasoning: 0.95
- Multimodal: 1.0
- Latency: 0.6
- Resource Usage: 0.2

#### Ollama

- Text Processing: 0.8
- Reasoning: 0.7
- Multimodal: 0.0
- Latency: 0.8
- Resource Usage: 0.6

#### Transformers

- Text Processing: 0.7
- Reasoning: 0.5
- Multimodal: 0.0
- Latency: 0.4
- Resource Usage: 0.8

### Implementation Features

The hybrid model implementation includes:

1. **Lazy Backend Initialization**
    - Backends are created only when needed
    - Reduces resource usage and startup time

2. **Real-time Availability Checks**
    - Integrates with ServiceAvailability monitoring
    - Considers service health in selection decisions

3. **Intelligent Routing**
    - Fast path for image-related queries to Gemini
    - Weighted capability scoring for text queries
    - Automatic fallback to next best available service

4. **Error Handling**
    - Graceful degradation when services fail
    - Automatic fallback to Transformers as last resort
    - Clear error logging and user communication

### Selection Process

1. Check service availability status
2. Quick check for image processing needs
    - Route directly to Gemini if available
3. Calculate capability scores for available services
4. Select highest scoring available backend
5. Initialize backend if needed
6. Monitor response and handle failures

### Recovery and Resilience

The hybrid implementation provides several layers of resilience:

- Automatic failover to next best service
- Lazy initialization to prevent cascading failures
- Clear logging for debugging and monitoring
- Graceful degradation of capabilities
- User-friendly error messages

### Configuration

Service configuration is managed through:

- `Config.MODEL_CONFIGS` for model-specific settings
- Capability weights in HybridModelBackend
- ServiceAvailability check intervals
- Backend-specific timeouts and retry settings

## Fallback Implementation

```python
class ServiceRouter:
    def __init__(self, availability_manager):
        self.availability_manager = availability_manager
        
    async def route_request(self, user_request):
        """Route request to best available service"""
        services = await self.availability_manager.get_available_services()
        
        if "gemini" in services and not self.will_exceed_rate_limit(user_request):
            return await self.process_with_gemini(user_request)
        elif "ollama" in services:
            return await self.process_with_ollama(user_request)
        elif "transformers" in services:
            return await self.process_with_transformers(user_request)
        else:
            return {
                "response": "Sorry, no AI services are currently available.",
                "fallback_used": "none",
                "service_status": "unavailable"
            }
```

## Client-Side Fallback

The frontend implements a JavaScript-based fallback that simulates basic responses when server services are unavailable:

```javascript
// Excerpt from client-side fallback
function getBotResponse(userMessage) { // Fallback simulation function
    userMessage = userMessage.toLowerCase().trim();
    let botMessage = "";

    switch (conversationStage) {
        case "greeting":
            if (userMessage.includes("hi") || userMessage.includes("hello")) {
                botMessage = "Greetings! I am your Opossum Information Assistant. How can I help you?";
                conversationStage = "initial_query";
            } else {
                botMessage = "Sorry, I didn't catch that. Perhaps start with a friendly 'Hello'?";
            }
            break;
            
        // Additional conversation stages and responses...
        
        default:
            botMessage = "I'm in simulation mode. Please ask something about opossums.";
    }
    return botMessage;
}
```

## Capability Degradation

| Service      | Capability Level | Features Available                       | Features Limited                                 |
|--------------|------------------|------------------------------------------|--------------------------------------------------|
| Gemini API   | Full             | Complete AI capabilities, image analysis | None                                             |
| Ollama       | High             | Near-complete AI capabilities            | Some specialized models, slower image processing |
| Transformers | Medium           | Basic Q&A, text completion               | Complex reasoning, image processing              |
| Client-side  | Minimal          | Scripted responses only                  | All AI capabilities                              |

## User Experience During Fallback

| Fallback Scenario     | User Notification                   | Experience Impact                       |
|-----------------------|-------------------------------------|-----------------------------------------|
| Gemini → Ollama       | "Using alternative AI service"      | Minimal impact, slight latency increase |
| Ollama → Transformers | "Using simplified model"            | Noticeable capability reduction         |
| Server → Client       | "Using simplified mode temporarily" | Severely limited capabilities           |
| Temporary Outage      | Loading indicator, retry message    | Brief delay before fallback activates   |

## Recovery Mechanisms

| Recovery Type  | Detection                  | Implementation                                   | User Experience                         |
|----------------|----------------------------|--------------------------------------------------|-----------------------------------------|
| Automatic      | Periodic health checks     | Service switching when preferred service returns | Seamless transition to better service   |
| Semi-Automatic | Service status monitoring  | Manual approval of service transition            | Brief service interruption              |
| Adaptive       | Sensitivity analysis       | Dynamic resource allocation and pipeline tuning  | Quality adjustment based on resources   |
| Manual         | Administrator intervention | Configuration update and service restart         | Temporary unavailability during restart |

## Resource Sensitivity Analysis

The Chat2SVG pipeline uses a `SensitivityAnalyzer` component to enhance system resilience through resource optimization:

### Analyzer Capabilities

- **Resource Bottleneck Detection**: Identifies which resources (CPU, GPU, memory) are limiting factors
- **Parameter Impact Analysis**: Quantifies how configuration changes affect output quality
- **Solution Space Exploration**: Evaluates alternative execution paths for optimal resource usage
- **Recommendation Generation**: Produces actionable suggestions for pipeline optimization

### Integration with Error Recovery

The sensitivity analyzer's insights are used to recover from resource-related failures:

```python
# When processing a request
sensitivity_data = await _analyzer.analyze_solution(solution, resources)

# Data can inform future pipeline configurations to avoid similar failures
```

### Adaptive Resource Management

Based on sensitivity analysis:

1. **Dynamic Resource Allocation**: Shifts resources to bottlenecked components
2. **Quality-Performance Tradeoffs**: Adjusts detail levels based on available resources
3. **Predictive Failure Avoidance**: Detects potential issues before they cause failures