# Compliance and Usage Terms

This document outlines how Opossum Search complies with relevant service usage terms, licensing requirements, and development guidelines.

## API Usage Compliance

### Google Gemini API

Opossum Search maintains compliance with Google's AI API terms of service through:

- Rate limit adherence via the `ServiceAvailability`component
- Proper API key management through secure environment variables
- Clear attribution of Google services where appropriate
- Automated throttling to prevent quota exceedance

### Model Usage Terms

| Model Provider | Compliance Mechanism | Implementation |
|----------------|----------------------|----------------|
| Google Gemini  | Rate limiting, quota tracking | `record_gemini_usage()`
| Ollama         | Local resource management | Local service monitoring |
| Transformers   | License compliance (Apache 2.0) | Package attribution |

## Privacy and Data Handling

Opossum Search follows best practices for user data:

- No persistent storage of conversation content beyond session duration
- Clear documentation of data handling in the UI
- Session timeout with automatic cleanup after 30 minutes
- No collection of personal identifiable information

## Open Source Compliance

The project maintains license compliance:

- MIT License for the Opossum Search codebase
- All dependencies properly attributed in `requirements.txt`
- Documentation includes appropriate citations and references
- Clear contribution guidelines that preserve licensing

## Monitoring and Telemetry

Our use of OpenTelemetry and monitoring tools complies with:

- Transparent data collection limited to operational metrics
- No personally identifiable user data in telemetry
- Configurable monitoring that can be disabled if needed
- Clear logging practices with appropriate retention policies

## Third-Party Content Usage

- SVG visualizations and animations are original or properly licensed
- Emoji usage follows Unicode Consortium guidelines
- Opossum facts and scientific information are from public domain sources
- All generated content is appropriately labeled as AI-assisted

## Compliance Verification

The project includes:

- Automated rate limit checking in the code
- CI/CD pipeline validation of licenses
- Regular review of terms of service for used APIs
- Testing specifically for compliance with rate limits

## Contact for Compliance Issues

If you identify any compliance concerns, please contact the project maintainers immediately through:

1. Opening an issue in the repository
2. Emailing the project team directly
3. Using the contact form on the project website

This document was last updated on: March 23, 2025