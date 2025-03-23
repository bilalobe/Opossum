# Model Configuration

## Overview

The Opossum Search model integration system provides a flexible configuration framework that allows fine-grained control over model behavior, performance characteristics, and fallback mechanisms. This document details the configuration options available for each model provider and explains how to optimize settings for different deployment scenarios.

## Configuration Structure

Model configuration follows a hierarchical structure:

```yaml
model_integration:
  # Global settings
  default_backend: "gemini"
  enable_fallbacks: true
  request_timeout: 15
  
  # Backend-specific configurations
  backends:
    gemini:
      # Gemini-specific settings
    
    ollama:
      # Ollama-specific settings
    
    transformers:
      # Transformers-specific settings
  
  # Feature flags and behavior settings
  features:
    # Feature-specific settings
```

## Global Configuration Options

These settings apply to the entire model integration system:

| Option | Description | Default | Valid Values |
|--------|-------------|---------|-------------|
| `default_backend` | Primary backend to use when no specific selection is made | `"gemini"` | `"gemini"`, `"ollama"`, `"transformers"` |
| `enable_fallbacks` | Whether to use fallback backends when primary fails | `true` | `true`, `false` |
| `request_timeout` | Global request timeout in seconds | `15` | Positive integer |
| `max_retries` | Maximum number of retries for transient errors | `2` | Non-negative integer |
| `telemetry_enabled` | Whether to collect usage telemetry | `true` | `true`, `false` |
| `cache_responses` | Whether to cache responses | `true` | `true`, `false` |
| `cache_ttl` | Time-to-live for cached responses in seconds | `3600` | Positive integer |

## Provider-Specific Configuration

### Gemini Configuration

```yaml
gemini:
  api_key: "${GEMINI_API_KEY}"  # Environment variable reference
  model: "gemini-pro"
  temperature: 0.7
  top_p: 0.95
  top_k: 40
  max_tokens: 800
  timeout: 10
  max_retries: 2
  safety_settings:
    harassment: "block_only_high"
    hate_speech: "block_medium_and_above"
    sexually_explicit: "block_high"
    dangerous_content: "block_medium_and_above"
  quota_management:
    max_daily_requests: 5000
    max_tokens_per_minute: 100000
    alert_at_percentage: 80
```

#### Gemini Configuration Options

| Option | Description | Default | Valid Values |
|--------|-------------|---------|-------------|
| `api_key` | Gemini API key | Required | Valid API key string |
| `model` | Gemini model to use | `"gemini-pro"` | `"gemini-pro"`, `"gemini-pro-vision"` |
| `temperature` | Randomness in generation | `0.7` | `0.0` to `1.0` |
| `top_p` | Nucleus sampling parameter | `0.95` | `0.0` to `1.0` |
| `top_k` | Number of top tokens to consider | `40` | Positive integer |
| `max_tokens` | Maximum tokens to generate | `800` | Positive integer |
| `timeout` | Request timeout in seconds | `10` | Positive integer |
| `safety_settings` | Content filtering settings | (default values) | See safety levels |
| `quota_management` | Settings to manage API quota | (default values) | See quota options |

### Ollama Configuration

```yaml
ollama:
  host: "localhost"
  port: 11434
  timeout: 15
  models:
    - name: "llama2"
      default: true
      temperature: 0.7
      context_window: 4096
    - name: "codellama"
      temperature: 0.6
      context_window: 8192
    - name: "mistral"
      temperature: 0.8
      context_window: 8192
  concurrency: 2
  startup_timeout: 60
  health_check_interval: 300
```

#### Ollama Configuration Options

| Option | Description | Default | Valid Values |
|--------|-------------|---------|-------------|
| `host` | Ollama server hostname | `"localhost"` | Valid hostname or IP |
| `port` | Ollama server port | `11434` | Valid port number |
| `timeout` | Request timeout in seconds | `15` | Positive integer |
| `models` | List of models to use | `[{"name": "llama2", "default": true}]` | Array of model configs |
| `concurrency` | Maximum concurrent requests | `2` | Positive integer |
| `startup_timeout` | Time to wait for server startup | `60` | Positive integer |
| `health_check_interval` | Time between health checks in seconds | `300` | Positive integer |

For each model in the `models` array:

| Option | Description | Default | Valid Values |
|--------|-------------|---------|-------------|
| `name` | Model name | Required | Valid Ollama model name |
| `default` | Whether this is the default model | `false` | `true`, `false` |
| `temperature` | Generation temperature | `0.7` | `0.0` to `1.0` |
| `context_window` | Context window size | Model-dependent | Positive integer |
| `repeat_penalty` | Penalty for repeated tokens | `1.1` | Positive float |
| `top_p` | Nucleus sampling parameter | `0.9` | `0.0` to `1.0` |

### Transformers Configuration

```yaml
transformers:
  model_path: "./models/local"
  default_model: "microsoft/phi-2"
  device: "auto"  # "auto", "cpu", "cuda", "mps"
  quantization: "int8"  # "none", "int8", "int4"
  models:
    - name: "microsoft/phi-2"
      default: true
    - name: "TheBloke/Llama-2-7B-GGUF"
      file: "llama-2-7b.Q4_K_M.gguf"
      quantization: "int4"
    - name: "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
  max_memory: "4GB"
  low_memory_mode: false
  cpu_threads: 4
  generate_params:
    max_new_tokens: 512
    temperature: 0.7
    top_p: 0.9
    top_k: 50
    repetition_penalty: 1.1
```

#### Transformers Configuration Options

| Option | Description | Default | Valid Values |
|--------|-------------|---------|-------------|
| `model_path` | Path to store model files | `"./models/local"` | Valid directory path |
| `default_model` | Default model identifier | `"microsoft/phi-2"` | Valid model ID or name |
| `device` | Compute device to use | `"auto"` | `"auto"`, `"cpu"`, `"cuda"`, `"mps"` |
| `quantization` | Quantization level | `"int8"` | `"none"`, `"int8"`, `"int4"` |
| `models` | List of models to use | (default values) | Array of model configs |
| `max_memory` | Maximum memory allocation | `"4GB"` | Memory size string |
| `low_memory_mode` | Optimize for low memory | `false` | `true`, `false` |
| `cpu_threads` | CPU threads for computation | `4` | Positive integer |
| `generate_params` | Generation parameters | (default values) | See generation options |

For each model in the `models` array:

| Option | Description | Default | Valid Values |
|--------|-------------|---------|-------------|
| `name` | Model identifier or HF repo | Required | Valid model ID or name |
| `default` | Whether this is the default model | `false` | `true`, `false` |
| `file` | Specific model file for GGUF models | Model-dependent | Valid filename |
| `quantization` | Model-specific quantization | Global setting | `"none"`, `"int8"`, `"int4"` |

## Feature Configuration

```yaml
features:
  dynamic_model_selection:
    enabled: true
    capability_weight: 0.6
    performance_weight: 0.3
    cost_weight: 0.1
  
  multimodal:
    enabled: true
    preferred_backend: "gemini"
    fallback_backend: "transformers"
    
  context_management:
    max_history_items: 10
    include_system_messages: true
    
  telemetry:
    enabled: true
    sampling_rate: 0.1
    detailed_metrics: false
```

## Environment Variables Integration

The configuration system supports environment variable substitution:

```yaml
gemini:
  api_key: "${GEMINI_API_KEY}"
  
ollama:
  host: "${OLLAMA_HOST:-localhost}"
  port: "${OLLAMA_PORT:-11434}"
```

Environment variables can have default values using the `:-` syntax.

## Configuration Validation

The system validates configuration at startup:

```python
def validate_config(config):
    """Validate model integration configuration"""
    
    errors = []
    warnings = []
    
    # Check for required settings
    if 'backends' not in config:
        errors.append("Missing 'backends' section in configuration")
    
    # Validate default_backend
    default_backend = config.get('default_backend')
    if default_backend and default_backend not in config.get('backends', {}):
        errors.append(f"Default backend '{default_backend}' not defined in backends section")
    
    # Validate Gemini settings if present
    if 'gemini' in config.get('backends', {}):
        gemini_config = config['backends']['gemini']
        if not gemini_config.get('api_key'):
            errors.append("Missing Gemini API key")
    
    # Report validation results
    if errors:
        raise ConfigurationError(f"Configuration validation failed: {', '.join(errors)}")
    
    if warnings:
        for warning in warnings:
            logger.warning(f"Configuration warning: {warning}")
    
    return True
```

## Dynamic Configuration

The system supports runtime configuration updates:

```python
def update_model_config(config_updates):
    """Update model configuration at runtime"""
    
    # Get current configuration
    current_config = get_model_config()
    
    # Apply updates (deep merge)
    updated_config = deep_merge(current_config, config_updates)
    
    # Validate updated configuration
    validate_config(updated_config)
    
    # Apply new configuration
    set_model_config(updated_config)
    
    # Notify components of configuration change
    event_bus.publish("config.updated", {
        "component": "model_integration",
        "old_config": current_config,
        "new_config": updated_config
    })
    
    return updated_config
```

## Configuration Loading

The system loads configuration from multiple sources:

```python
def load_model_config():
    """Load model configuration from multiple sources"""
    
    # Start with default configuration
    config = default_model_config()
    
    # Load from configuration file
    file_config = load_config_file("config/model_integration.yaml")
    config = deep_merge(config, file_config)
    
    # Load from environment variables
    env_config = load_from_environment("MODEL_")
    config = deep_merge(config, env_config)
    
    # Process environment variable references
    config = process_env_vars(config)
    
    # Validate configuration
    validate_config(config)
    
    return config
```

## Complete Configuration Example

```yaml
model_integration:
  default_backend: "gemini"
  enable_fallbacks: true
  request_timeout: 15
  max_retries: 2
  telemetry_enabled: true
  cache_responses: true
  cache_ttl: 3600
  
  backends:
    gemini:
      api_key: "${GEMINI_API_KEY}"
      model: "gemini-pro"
      temperature: 0.7
      top_p: 0.95
      top_k: 40
      max_tokens: 800
      timeout: 10
      safety_settings:
        harassment: "block_only_high"
        hate_speech: "block_medium_and_above"
        sexually_explicit: "block_high"
        dangerous_content: "block_medium_and_above"
      quota_management:
        max_daily_requests: 5000
        max_tokens_per_minute: 100000
        alert_at_percentage: 80
    
    ollama:
      host: "${OLLAMA_HOST:-localhost}"
      port: "${OLLAMA_PORT:-11434}"
      timeout: 15
      models:
        - name: "llama2"
          default: true
          temperature: 0.7
          context_window: 4096
        - name: "codellama"
          temperature: 0.6
          context_window: 8192
        - name: "mistral"
          temperature: 0.8
          context_window: 8192
      concurrency: 2
      startup_timeout: 60
      health_check_interval: 300
    
    transformers:
      model_path: "./models/local"
      default_model: "microsoft/phi-2"
      device: "auto"
      quantization: "int8"
      models:
        - name: "microsoft/phi-2"
          default: true
        - name: "TheBloke/Llama-2-7B-GGUF"
          file: "llama-2-7b.Q4_K_M.gguf"
          quantization: "int4"
        - name: "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
      max_memory: "4GB"
      low_memory_mode: false
      cpu_threads: 4
      generate_params:
        max_new_tokens: 512
        temperature: 0.7
        top_p: 0.9
        top_k: 50
        repetition_penalty: 1.1
  
  features:
    dynamic_model_selection:
      enabled: true
      capability_weight: 0.6
      performance_weight: 0.3
      cost_weight: 0.1
    
    multimodal:
      enabled: true
      preferred_backend: "gemini"
      fallback_backend: "transformers"
      
    context_management:
      max_history_items: 10
      include_system_messages: true
      
    telemetry:
      enabled: true
      sampling_rate: 0.1
      detailed_metrics: false
```

## Configuration Best Practices

### General Guidelines

1. **Use Environment Variables for Secrets**
   - Always use environment variables for API keys and sensitive information
   - Provide clear documentation on required environment variables

2. **Provide Sensible Defaults**
   - Configure default values that work in most scenarios
   - Document the reasoning behind default values

3. **Layer Configuration**
   - Use a layered approach to configuration (defaults → files → environment)
   - Allow selective overrides without replacing entire configuration

4. **Validate Configuration**
   - Perform thorough validation at startup
   - Provide clear error messages for configuration issues

### Model-Specific Recommendations

#### Gemini

- Configure appropriate `safety_settings` based on your application's use case
- Set up `quota_management` to prevent unexpected billing
- Use a lower `temperature` (0.3-0.5) for factual responses, higher (0.7-0.9) for creative content

#### Ollama

- Configure `concurrency` based on your hardware capabilities
- Use specialized models for specific tasks (CodeLlama for code, Mistral for general text)
- Configure `health_check_interval` based on your stability requirements

#### Transformers

- Use appropriate `quantization` based on available memory
- Configure `device` correctly for your hardware
- Use the smallest model that meets your quality requirements

## Deployment Scenarios

### Low-Resource Environment

```yaml
model_integration:
  default_backend: "transformers"
  enable_fallbacks: true
  
  backends:
    transformers:
      device: "cpu"
      quantization: "int4"
      default_model: "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
      low_memory_mode: true
      generate_params:
        max_new_tokens: 256
    
    ollama:
      models:
        - name: "tinyllama"
          default: true
      concurrency: 1
    
    # No Gemini configuration in low-resource scenario
  
  features:
    dynamic_model_selection:
      enabled: false  # Simplify for performance
```

### High-Performance Environment

```yaml
model_integration:
  default_backend: "gemini"
  
  backends:
    gemini:
      max_tokens: 1500
    
    ollama:
      host: "ollama-server"  # Dedicated server
      concurrency: 4
      models:
        - name: "llama2:70b"
          default: true
    
    transformers:
      device: "cuda"
      quantization: "none"  # Full precision for quality
      default_model: "meta-llama/Llama-2-13b-chat-hf"
      models:
        - name: "meta-llama/Llama-2-13b-chat-hf"
          default: true
```

### High-Availability Environment

```yaml
model_integration:
  default_backend: "gemini"
  enable_fallbacks: true
  request_timeout: 8  # Lower timeout for faster fallback
  max_retries: 1  # Fewer retries, faster fallback
  
  backends:
    gemini:
      api_key: "${GEMINI_API_KEY}"
      timeout: 5
      
    ollama:
      host: "${OLLAMA_HOST}"
      models:
        - name: "llama2"
          default: true
      startup_timeout: 30
      health_check_interval: 60  # More frequent health checks
      
    transformers:
      default_model: "microsoft/phi-2"
      device: "cuda"
  
  features:
    dynamic_model_selection:
      enabled: true
      # Weight availability higher
      capability_weight: 0.4
      performance_weight: 0.5
      cost_weight: 0.1
```

## Related Documentation

- Model Integration Architecture
- Backend Selection
- Capability Matrix
- Provider Integration
- Infrastructure Configuration Management