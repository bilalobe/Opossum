# Resilience Patterns in Opossum Search

This document outlines the resilience patterns implemented throughout Opossum Search to ensure system stability,
graceful degradation, and optimal user experience under varying conditions.

## Core Principles

Our resilience strategy is built on several fundamental principles:

1. **Fail Gracefully** - When failures occur, degrade functionality rather than completely failing
2. **Defense in Depth** - Multiple layers of fallback mechanisms
3. **Resource Protection** - Prevent cascading failures through circuit breakers and rate limiting
4. **Adaptive Selection** - Intelligently choose services based on availability and capabilities
5. **Experience Preservation** - Maintain core user experience even during degraded conditions

## Circuit Breaker Pattern

We implement the Circuit Breaker pattern to prevent repeated calls to failing services:

```python
class CircuitBreaker:
    def __init__(self, name, failure_threshold=3, reset_timeout=60):
        self.name = name
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def record_success(self):
        self.failure_count = 0
        if self.state != "CLOSED":
            logger.info(f"Circuit breaker {self.name} closing after successful operation")
            self.state = "CLOSED"
    
    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == "CLOSED" and self.failure_count >= self.failure_threshold:
            logger.warning(f"Circuit breaker {self.name} opening after {self.failure_count} failures")
            self.state = "OPEN"
        elif self.state == "HALF_OPEN":
            logger.warning(f"Circuit breaker {self.name} reopening after test failure")
            self.state = "OPEN"
    
    def allow_request(self) -> bool:
        current_time = time.time()
        
        # If circuit is open but enough time has passed, allow a test request
        if self.state == "OPEN" and current_time - self.last_failure_time > self.reset_timeout:
            logger.info(f"Circuit breaker {self.name} switching to half-open state for testing")
            self.state = "HALF_OPEN"
            return True
            
        # Allow requests when closed or half-open (for testing)
        return self.state != "OPEN"
```

Circuit breakers prevent the system from making repeated calls to failing services, which:

- Reduces latency for end users
- Prevents resource exhaustion
- Allows services to recover
- Provides early failure detection

## Multi-Level Fallback

Our fallback mechanisms operate at multiple levels:

1. **Primary Service Fallback**
    - Default model selection with capability matching
    - Automatic fallback to alternative providers

2. **Emergency Fallback**
    - Predefined fallback paths when normal selection fails
    - Transformers (local) as ultimate fallback

3. **Graceful Degradation**
    - Feature downgrading during system stress
    - Simplified user interface elements

### Example: Model Selection Fallbacks

```python
def _emergency_fallback(self) -> Tuple[str, float, str]:
    """Emergency fallback when selection process itself fails"""
    logger.critical("Using EMERGENCY FALLBACK for model selection due to critical failure")
    
    # Try each emergency fallback path
    for fallback in self._emergency_fallbacks:
        provider = fallback["provider"]
        model = fallback["model"]
        
        # Skip if circuit breaker is fully open
        if provider in self.circuit_breakers and self.circuit_breakers[provider].state == "OPEN":
            continue
            
        if (provider in self.available_backends and 
            model in self.available_backends[provider]):
            logger.info(f"Emergency fallback selected: {provider}/{model}")
            return model, 0.2, provider
    
    # Ultimate emergency fallback - just try transformers/gemma
    logger.critical("ALL FALLBACKS EXHAUSTED! Using transformers/gemma as final resort")
    return "gemma", 0.1, "transformers"
```

## Adaptive Load Management

We implement several techniques to manage system load:

### 1. Request Jittering

During periods of system degradation, we intentionally introduce randomness in our service selection to prevent
thundering herd problems:

```python
if self._is_system_degraded() and random.random() < 0.2:  # 20% chance
    backup_model = self._get_fallback_model(model_selection[0], model_selection[2], available_backends)
    if backup_model:
        logger.info(f"System degraded, applying jitter to model selection")
        model_selection = backup_model
```

### 2. Tiered Caching

- Short-lived cache (10 seconds) for model selection results
- Medium-lived cache (5 minutes) for topic similarities
- Long-lived cache (1 hour) for SVG generations
- Emergency cache for critical responses

### 3. Feature Throttling

Non-critical features like Easter eggs automatically throttle their activation during system degradation:

```python
def should_activate(self, egg_type: str) -> bool:
    # ...existing code...
    
    # Reduce activation chance if system is degraded
    if self.is_system_degraded() and egg_type not in ["possum_party", "konami_code"]:
        threshold = min(threshold, DEGRADED_ACTIVATION_THRESHOLD)
```

## Experience Preservation

Even during degraded operation, we ensure the core user experience remains functional:

### Feature Downgrading

Features are downgraded rather than disabled completely:

```python
fallback_features = {
    "national_opossum_day": {
        "ui_theme": "party_opossum_light",  # Lighter version with fewer animations
        "response_modifiers": ["purple_text"], # Only add purple text, no jokes
        "animations": []  # No animations to reduce load
    },
    # ...other fallbacks...
}
```

### SVG Generation Resilience

The SVG generation system combines two approaches for maximum resilience:

1. **Template-Based Generation**
    - Fast, reliable predefined templates
    - Low resource requirements
    - Consistent output quality

2. **AI-Powered Generation via Chat2SVG**
    - Feature-rich custom SVG generation
    - Falls back to templates when unavailable

This hybrid approach ensures users always receive visualizations, even when advanced generation is unavailable.

## Health Monitoring

Our resilience systems rely on comprehensive health monitoring:

1. **Service Availability Checks**
    - Periodic health checks of all backend services
    - Cached results to prevent excessive checking

2. **Circuit State Tracking**
    - Circuit breaker states tracked and logged
    - Automatic recovery attempts after timeout periods

3. **Degradation Detection**
    - Consecutive failures tracked to identify degradation patterns
    - System-wide degradation state determined by multiple provider failures

## Implementation Areas

| Component      | Resilience Patterns                                             |
|----------------|-----------------------------------------------------------------|
| Model Selector | Circuit breakers, adaptive selection, fallback paths, jittering |
| SVG Generation | Dual implementation (templates + Chat2SVG), tiered fallbacks    |
| Easter Eggs    | Activation throttling, feature downgrading, degraded modes      |
| API Endpoints  | Timeouts, rate limiting, caching strategies                     |
| Frontend       | Progressive enhancement, graceful UI degradation                |

## Testing Resilience

We test our resilience patterns through:

1. **Chaos Engineering**
    - Simulated service outages
    - Random latency injection
    - Resource exhaustion tests

2. **Load Testing**
    - Traffic spike simulations
    - Concurrent request handling
    - Long-tail latency analysis

3. **Degraded Operation Tests**
    - Functionality verification during partial outages
    - Recovery time measurements
    - User experience evaluation during degradation

## Dashboard Integration

Our resilience patterns are visibly represented in the service status dashboard, which shows:

- Current availability of each service
- Circuit breaker states
- Fallback selection statistics
- Degradation indicators
- Recovery predictions

## Future Improvements

Planned enhancements to our resilience patterns:

1. **Predictive Circuit Breaking**
    - Use machine learning to predict failures before they occur
    - Preemptively route around problematic services

2. **Adaptive Resource Allocation**
    - Dynamically adjust resource allocation based on system load
    - Prioritize critical services during degradation

3. **User-Aware Degradation**
    - Personalized degradation strategies based on user priorities
    - Transparent communication about system status

4. **Multi-Region Resilience**
    - Geographic distribution of services
    - Regional circuit breakers and fallbacks