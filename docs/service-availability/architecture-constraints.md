# 3. Architecture Constraints

## 3.1 External Service Dependencies

| Service               | Dependency Type                  | Constraint                                       | Impact                                             |
|-----------------------|----------------------------------|--------------------------------------------------|----------------------------------------------------|
| Gemini API            | Hard dependency for primary path | Requires valid API key and network connectivity  | Service unavailability triggers failover to Ollama |
| Google Cloud Platform | Infrastructure for Gemini        | Subject to Google's maintenance windows and SLAs | May cause temporary Gemini unavailability          |
| OpenAI API            | Optional fallback service        | Rate-limited based on subscription tier          | Provides additional redundancy if configured       |

## 3.2 Local Service Dependencies

| Service        | Constraint                                 | Impact                                              |
|----------------|--------------------------------------------|-----------------------------------------------------|
| Ollama         | Requires local GPU for optimal performance | Performance degradation on CPU-only systems         |
| Transformers   | Requires sufficient RAM for model loading  | Lower capability models used when RAM is limited    |
| Python Runtime | Version 3.8+ required                      | Application will not start on older Python versions |

## 3.3 Infrastructure Requirements

| Component | Requirement                                    | Rationale                                                |
|-----------|------------------------------------------------|----------------------------------------------------------|
| CPU       | 4+ cores recommended                           | Needed for concurrent service checks and model inference |
| RAM       | Minimum 8GB, 16GB recommended                  | Required for local model loading and operation           |
| Storage   | 10GB minimum for application and models        | Local models require significant storage space           |
| Network   | Reliable internet connection for external APIs | Intermittent connectivity will affect Gemini service     |
| Docker    | Optional but recommended for Ollama isolation  | Simplifies deployment and management of Ollama service   |

## 3.4 Operating Environment Constraints

| Constraint             | Description                                           | Mitigation                                                |
|------------------------|-------------------------------------------------------|-----------------------------------------------------------|
| Firewall Restrictions  | Corporate firewalls may block API calls to Google     | Configure proxy settings or use local services only       |
| Rate Limits            | Gemini API has strict rate limits                     | Implement request queueing and smart routing              |
| Offline Operation      | Must function with degraded capabilities when offline | Ensure Transformers models are pre-downloaded             |
| Cross-Platform Support | Must run on Windows, macOS, and Linux                 | Abstract platform-specific code and test on all platforms |

## 3.5 Technical Debt and Limitations

| Limitation                | Description                                              | Future Improvement                                            |
|---------------------------|----------------------------------------------------------|---------------------------------------------------------------|
| Manual Failover Recovery  | System does not automatically recover preferred services | Implement automatic service recovery detection                |
| Limited API Compatibility | Different model providers have different APIs            | Create abstraction layer to normalize responses               |
| Fixed Check Interval      | Service checks occur at fixed intervals                  | Implement adaptive check intervals based on service stability |
| Missing Health Metrics    | Only binary up/down status tracked                       | Add response time and error rate tracking                     |
| Circuit Breaker Patterns  | Basic implementation of failure detection                | Implement comprehensive circuit breaker patterns              |