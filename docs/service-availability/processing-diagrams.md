
# 10. Diagrams and Visuals

## 10.1 System Architecture Diagram

```mermaid
flowchart TD
    Client["Client Application"]
    Router["Service Router"]
    GeminiAPI["Gemini API\n(External)"]
    Ollama["Ollama\n(Local API)"]
    Transformers["Transformers\n(Local Lib)"]
    Monitoring["Availability Monitoring System"]

    Client --> Router
    Router --> GeminiAPI
    Router --> Ollama
    Router --> Transformers
    GeminiAPI & Ollama & Transformers --> Monitoring
```

## 10.2 Service Monitoring Flowchart

```mermaid
flowchart TD
    Start["Start Application"] --> CheckInterval["Check Interval Reached?"]
    CheckInterval --> CheckService["Check Service Availability"]
    CheckService --> UpdateCache["Update Cache"]
    UpdateCache --> StatusChanged["Status Changed?"]
    StatusChanged -- Yes --> StatusEvent["Status Change Event"]
    StatusEvent --> UpdateLogs["Update Logs & Send Alerts"]
    StatusChanged -- No --> Wait["Wait for Next Check"]
```

## 10.3 Failover Process Diagram

```mermaid
flowchart TD
    Request["Request Received"] --> ServiceAvailable["Service Available?"]
    ServiceAvailable -- Yes --> RateLimited["Service Rate-Limited?"]
    ServiceAvailable -- No --> TryNext["Try Next Service"]
    RateLimited -- No --> ProcessPrimary["Process with Primary Service"]
    TryNext --> AnyAvailable["Any Service Available?"]
    AnyAvailable -- No --> ReturnError["Return Error\nUse Client Fallback"]
    AnyAvailable -- Yes --> ProcessAvailable["Process with\nAvailable Service"]
```

## 10.4 Rate Limit Monitoring Diagram

```mermaid
flowchart TD
    TrackAPI["Track API Request"] --> ResetPeriod["Reset Period Elapsed?"]
    ResetPeriod -- Yes --> ResetCounters["Reset Counters"]
    ResetCounters --> IncrementCounters["Increment Counters"]
    TrackAPI --> IncrementCounters
    IncrementCounters --> ApproachingLimit["Approaching Limit?"]
    ApproachingLimit -- Yes --> LogWarning["Log Warning\nPrepare Fallback"]
    ApproachingLimit -- No --> ContinueNormal["Continue Normal Operation"]
```

## 10.5 Recovery Detection Process

```mermaid
flowchart TD
    Unavailable["Service Unavailable"] --> HealthCheck["Periodic Health Check"]
    HealthCheck --> Recovered["Service Recovered?"]
    Recovered -- No --> ContinueFallback["Continue Using Fallback"]
    Recovered -- Yes --> LogRecovery["Log Recovery\nUpdate Status"]
    LogRecovery --> ResumePreferred["Resume Using Preferred Service"]
```

## 10.6 User Experience Flow

```mermaid
flowchart TD
    UserQuery["User Submits Query"] --> FrontendProcess["Frontend Processes Input"]
    FrontendProcess --> APIRequest["API Request to Server"]
    APIRequest --> ServerAvailable["Server Available?"]
    ServerAvailable -- No --> ClientFallback["Client-side Fallback Activated"]
    ClientFallback --> ShowError["Show Error Message with Limited Mode"]
    ServerAvailable -- Yes --> UsingFallback["Service Using Fallback?"]
    UsingFallback -- Yes --> NotifyUser["Notify User of Service Limitations"]
    UsingFallback -- No --> NormalResponse["Normal Response Processing"]
```

## 10.7 C4 Context Diagram

```mermaid
C4Context
    title System Context diagram for Opossum Search

    Person(user, "User", "A user of the Opossum Search system")
    
    Enterprise_Boundary(b0, "Opossum Search System") {
        System(searchSystem, "Opossum Search System", "Provides search functionality with multiple model providers")
        
        System_Ext(geminiAPI, "Gemini API", "External large language model provider")
        System_Ext(ollamaSystem, "Ollama", "Local large language model hosting")
        System_Ext(transformersLib, "Transformers", "Local machine learning library")
    }
    
    Rel(user, searchSystem, "Submits search queries to")
    Rel(searchSystem, geminiAPI, "Uses for processing when available")
    Rel(searchSystem, ollamaSystem, "Falls back to when Gemini is unavailable")
    Rel(searchSystem, transformersLib, "Uses as final fallback option")
```
