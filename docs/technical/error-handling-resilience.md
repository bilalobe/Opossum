# 8. Fallback Mechanisms

## 8.1 Fallback Hierarchy

| Priority      | Service      | Type          | Capabilities                               | Limitations                                    |
|---------------|--------------|---------------|--------------------------------------------|------------------------------------------------|
| 1 (Primary)   | Gemini API   | External API  | Full model capabilities, high intelligence | Rate limited, requires internet                |
| 2 (Secondary) | Ollama       | Local service | Good capabilities, custom models           | Requires GPU for performance, local deployment |
| 3 (Tertiary)  | Transformers | Local library | Basic capabilities, offline operation      | Higher latency, limited model size             |
| 4 (Emergency) | Client-side  | JavaScript    | Basic scripted responses                   | Very limited capabilities, no real AI          |

## 8.2 Hybrid Model Implementation

The system implements an intelligent hybrid model backend that dynamically selects and combines different model
capabilities based on availability and requirements:

### 8.2.1 Backend Selection Strategy

The hybrid model uses a weighted scoring system to select the most appropriate backend:

| Capability      | Weight | Description                                  |
|-----------------|--------|----------------------------------------------|
| Text Processing | 0.3    | Basic text understanding and generation      |
| Reasoning       | 0.3    | Complex reasoning and inference capabilities |
| Multimodal      | 0.2    | Ability to process images with text          |
| Latency         | 0.1    | Response time importance                     |
| Resource Usage  | 0.1    | System resource consumption consideration    |

### 8.2.2 Service Capabilities

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

### 8.2.3 Implementation Features

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

### 8.2.4 Selection Process

1. Check service availability status
2. Quick check for image processing needs
    - Route directly to Gemini if available
3. Calculate capability scores for available services
4. Select highest scoring available backend
5. Initialize backend if needed
6. Monitor response and handle failures

### 8.2.5 Recovery and Resilience

The hybrid implementation provides several layers of resilience:

- Automatic failover to next best service
- Lazy initialization to prevent cascading failures
- Clear logging for debugging and monitoring
- Graceful degradation of capabilities
- User-friendly error messages

### 8.2.6 Configuration

Service configuration is managed through:

- `Config.MODEL_CONFIGS` for model-specific settings
- Capability weights in HybridModelBackend
- ServiceAvailability check intervals
- Backend-specific timeouts and retry settings

## 8.3 Fallback Implementation

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

## 8.4 Client-Side Fallback

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

## 8.5 Capability Degradation

| Service      | Capability Level | Features Available                       | Features Limited                                 |
|--------------|------------------|------------------------------------------|--------------------------------------------------|
| Gemini API   | Full             | Complete AI capabilities, image analysis | None                                             |
| Ollama       | High             | Near-complete AI capabilities            | Some specialized models, slower image processing |
| Transformers | Medium           | Basic Q&A, text completion               | Complex reasoning, image processing              |
| Client-side  | Minimal          | Scripted responses only                  | All AI capabilities                              |

## 8.6 User Experience During Fallback

| Fallback Scenario     | User Notification                   | Experience Impact                       |
|-----------------------|-------------------------------------|-----------------------------------------|
| Gemini → Ollama       | "Using alternative AI service"      | Minimal impact, slight latency increase |
| Ollama → Transformers | "Using simplified model"            | Noticeable capability reduction         |
| Server → Client       | "Using simplified mode temporarily" | Severely limited capabilities           |
| Temporary Outage      | Loading indicator, retry message    | Brief delay before fallback activates   |

## 8.7 Recovery Mechanisms

| Recovery Type  | Detection                  | Implementation                                   | User Experience                         |
|----------------|----------------------------|--------------------------------------------------|-----------------------------------------|
| Automatic      | Periodic health checks     | Service switching when preferred service returns | Seamless transition to better service   |
| Semi-Automatic | Service status monitoring  | Manual approval of service transition            | Brief service interruption              |
| Manual         | Administrator intervention | Configuration update and service restart         | Temporary unavailability during restart |

## 8.8 Fallback Testing

| Test Type         | Frequency | Methodology                             | Success Criteria                            |
|-------------------|-----------|-----------------------------------------|---------------------------------------------|
| Controlled Outage | Weekly    | Simulate API unavailability             | Successful transition to fallback within 2s |
| Rate Limit Test   | Monthly   | Generate high request volume            | Preemptive fallback before limit reached    |
| Complete Failure  | Quarterly | Simulate all service unavailability     | Client-side fallback activated within 10s   |
| Recovery Test     | Monthly   | Restore services after simulated outage | Return to primary service within 30s        |