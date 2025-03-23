# Provider Integration

## Overview

Opossum Search integrates with multiple AI model providers to deliver resilient, high-quality responses. This document details the implementation specifics for each supported provider, including authentication, request/response handling, and provider-specific optimizations.

## Supported Providers

The system currently integrates with these model providers:

| Provider | Type | Primary Use Cases | Integration Type |
|----------|------|------------------|------------------|
| Gemini | Cloud API | Advanced reasoning, multimodal | REST API |
| Ollama | Local deployment | Cost-effective, private deployment | HTTP API |
| Transformers | Local library | Fallback, specialized models | Direct library |

## Gemini Integration

Gemini provides state-of-the-art AI capabilities through Google's API service.

### Authentication

```python
class GeminiBackend:
    def __init__(self, config):
        self.api_key = config.get('api_key') or os.environ.get('GEMINI_API_KEY')
        if not self.api_key:
            raise ConfigurationError("Gemini API key not provided")
        
        self.model = config.get('model', 'gemini-pro')
        self.timeout = config.get('timeout', 10)
        self.retries = config.get('max_retries', 2)
        
        # Initialize client
        self.client = genai.Client(api_key=self.api_key)
```

### Request Processing

```python
def process(self, query, context=None):
    """Process a query using Gemini API"""
    try:
        # Build generation config
        generation_config = {
            "temperature": self.temperature,
            "top_p": self.top_p,
            "top_k": self.top_k,
            "max_output_tokens": self.max_tokens
        }
        
        # Prepare context if provided
        safety_settings = [
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_ONLY_HIGH"
            },
            # Other safety settings...
        ]
        
        # Create model instance
        model = self.client.get_model(self.model)
        
        # Build prompt with context if available
        content = [query]
        if context:
            content = context + [query]
        
        # Generate response
        response = model.generate_content(
            content,
            generation_config=generation_config,
            safety_settings=safety_settings
        )
        
        return response.text
        
    except Exception as e:
        # Handle different error types
        if "rate limit" in str(e).lower():
            raise RateLimitError(f"Gemini rate limit exceeded: {str(e)}")
        elif "quota" in str(e).lower():
            raise QuotaExceededError(f"Gemini quota exceeded: {str(e)}")
        elif "unavailable" in str(e).lower() or "timeout" in str(e).lower():
            raise ServiceUnavailableError(f"Gemini service unavailable: {str(e)}")
        else:
            raise ModelProcessingError(f"Error processing with Gemini: {str(e)}")
```

### Multimodal Handling

```python
def process_multimodal(self, text, images=None):
    """Process a multimodal query with text and images"""
    try:
        # Create multimodal prompt
        parts = [text]
        
        # Add images if provided
        if images:
            for image in images:
                if isinstance(image, str):
                    # Image is a URL or file path
                    if image.startswith(('http://', 'https://')):
                        img_data = Image.from_url(image)
                    else:
                        img_data = Image.from_file(image)
                else:
                    # Image is already a binary object
                    img_data = image
                
                parts.append(img_data)
        
        # Generate response
        model = self.client.get_model("gemini-pro-vision")
        response = model.generate_content(parts)
        
        return response.text
        
    except Exception as e:
        # Handle errors
        logger.error(f"Error in multimodal processing: {str(e)}")
        raise ModelProcessingError(f"Error processing multimodal content: {str(e)}")
```

### Usage Tracking

```python
def track_usage(self, response):
    """Track token usage for monitoring and quota management"""
    if hasattr(response, 'usage_metadata'):
        usage = {
            'prompt_tokens': response.usage_metadata.prompt_token_count,
            'completion_tokens': response.usage_metadata.candidates_token_count,
            'total_tokens': (
                response.usage_metadata.prompt_token_count + 
                response.usage_metadata.candidates_token_count
            )
        }
        
        # Record usage in telemetry
        telemetry.record_model_usage('gemini', usage)
        
        return usage
    
    return None
```

## Ollama Integration

Ollama provides locally deployed open-source models with a simple API.

### Connection Setup

```python
class OllamaBackend:
    def __init__(self, config):
        self.host = config.get('host', 'localhost')
        self.port = config.get('port', 11434)
        self.timeout = config.get('timeout', 15)
        
        # Get default model
        self.models = config.get('models', [{'name': 'llama2', 'default': True}])
        self.default_model = next(
            (m['name'] for m in self.models if m.get('default')), 
            'llama2'
        )
        
        # Build base URL
        self.base_url = f"http://{self.host}:{self.port}"
        
        # Verify connection
        self._verify_connection()
    
    def _verify_connection(self):
        """Verify connection to Ollama server"""
        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=self.timeout
            )
            response.raise_for_status()
            available_models = response.json().get('models', [])
            
            # Check if our models are available
            for required_model in self.models:
                model_name = required_model['name']
                if not any(m['name'] == model_name for m in available_models):
                    logger.warning(f"Model {model_name} not found in Ollama server")
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to connect to Ollama server: {str(e)}")
            # Don't raise here - allow system to try connection when needed
```

### Request Processing

```python
def process(self, query, context=None, model=None):
    """Process a query using Ollama API"""
    try:
        model = model or self.default_model
        
        # Prepare request body
        request_body = {
            "model": model,
            "prompt": query,
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "top_p": self.top_p,
                "num_ctx": 2048  # Context window size
            }
        }
        
        # Add system context if provided
        if context:
            request_body["system"] = context
        
        # Send request to Ollama API
        response = requests.post(
            f"{self.base_url}/api/generate",
            json=request_body,
            timeout=self.timeout
        )
        response.raise_for_status()
        result = response.json()
        
        return result.get('response', '')
        
    except requests.exceptions.Timeout:
        raise ServiceUnavailableError("Ollama request timed out")
    except requests.exceptions.ConnectionError:
        raise ServiceUnavailableError("Unable to connect to Ollama server")
    except requests.exceptions.HTTPError as e:
        raise ModelProcessingError(f"Ollama HTTP error: {str(e)}")
    except Exception as e:
        raise ModelProcessingError(f"Error processing with Ollama: {str(e)}")
```

### Model Management

```python
def list_available_models(self):
    """List models available on the Ollama server"""
    try:
        response = requests.get(
            f"{self.base_url}/api/tags",
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json().get('models', [])
    except Exception as e:
        logger.error(f"Error listing Ollama models: {str(e)}")
        return []

def pull_model(self, model_name):
    """Pull a model to the Ollama server if not already available"""
    try:
        # Check if model exists
        available_models = self.list_available_models()
        if any(m['name'] == model_name for m in available_models):
            logger.info(f"Model {model_name} already available")
            return True
        
        # Pull model
        logger.info(f"Pulling model {model_name} to Ollama server...")
        response = requests.post(
            f"{self.base_url}/api/pull",
            json={"name": model_name},
            timeout=300  # Longer timeout for model pulls
        )
        response.raise_for_status()
        
        return True
    except Exception as e:
        logger.error(f"Error pulling model {model_name}: {str(e)}")
        return False
```

## Transformers Integration

Hugging Face Transformers provides a flexible library for running models locally.

### Initialization

```python
class TransformersBackend:
    def __init__(self, config):
        self.model_path = config.get('model_path', './models/local')
        self.default_model = config.get('default_model', 'microsoft/phi-2')
        self.quantization = config.get('quantization', 'int8')
        
        # Determine device (CPU/GPU)
        self.device = config.get('device', 'auto')
        if self.device == 'auto':
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        
        # Load default model
        self.models = {}
        self._load_model(self.default_model)
    
    def _load_model(self, model_name):
        """Load a model if not already loaded"""
        if model_name in self.models:
            return self.models[model_name]
        
        try:
            logger.info(f"Loading Transformers model: {model_name}")
            
            # Load model with appropriate quantization
            if self.quantization == 'int8':
                model = AutoModelForCausalLM.from_pretrained(
                    model_name,
                    device_map=self.device,
                    load_in_8bit=True
                )
            elif self.quantization == 'int4':
                model = AutoModelForCausalLM.from_pretrained(
                    model_name,
                    device_map=self.device,
                    load_in_4bit=True
                )
            else:
                model = AutoModelForCausalLM.from_pretrained(
                    model_name, 
                    device_map=self.device
                )
            
            # Load tokenizer
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            
            self.models[model_name] = {
                'model': model,
                'tokenizer': tokenizer,
                'last_used': time.time()
            }
            
            return self.models[model_name]
            
        except Exception as e:
            logger.error(f"Error loading model {model_name}: {str(e)}")
            raise ModelInitializationError(f"Failed to load {model_name}: {str(e)}")
```

### Request Processing

```python
def process(self, query, context=None, model_name=None):
    """Process a query using Transformers"""
    try:
        model_name = model_name or self.default_model
        
        # Load model if not already loaded
        if model_name not in self.models:
            self._load_model(model_name)
        
        model_data = self.models[model_name]
        model = model_data['model']
        tokenizer = model_data['tokenizer']
        
        # Update last used timestamp
        model_data['last_used'] = time.time()
        
        # Prepare input text with context if provided
        if context:
            input_text = f"{context}\n\nUser: {query}\n\nAssistant:"
        else:
            input_text = f"User: {query}\n\nAssistant:"
        
        # Tokenize input
        inputs = tokenizer(input_text, return_tensors="pt").to(self.device)
        
        # Generate response
        with torch.no_grad():
            output = model.generate(
                inputs["input_ids"],
                max_new_tokens=512,
                temperature=0.7,
                top_p=0.9,
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id
            )
        
        # Decode and clean response
        response_text = tokenizer.decode(output[0], skip_special_tokens=True)
        response_text = response_text.replace(input_text, "").strip()
        
        # Unload rarely used models to save memory
        self._manage_loaded_models()
        
        return response_text
        
    except torch.cuda.OutOfMemoryError:
        logger.error(f"CUDA out of memory while processing with {model_name}")
        raise ResourceExhaustedError("GPU memory exhausted")
    except Exception as e:
        raise ModelProcessingError(f"Error processing with Transformers: {str(e)}")
```

### Memory Management

```python
def _manage_loaded_models(self):
    """Unload models that haven't been used recently to free memory"""
    now = time.time()
    unload_threshold = 3600  # 1 hour
    
    # Don't unload if only one model is loaded
    if len(self.models) <= 1:
        return
    
    # Check each model's last used time
    for model_name, model_data in list(self.models.items()):
        # Skip default model
        if model_name == self.default_model:
            continue
            
        # Unload if unused for threshold period
        if now - model_data['last_used'] > unload_threshold:
            logger.info(f"Unloading unused model: {model_name}")
            # Remove from loaded models
            del self.models[model_name]
            
            # Force garbage collection
            if self.device == 'cuda':
                torch.cuda.empty_cache()
            gc.collect()
```

## Error Handling

Each provider has specific error types that require specialized handling:

```python
class ModelError(Exception):
    """Base class for model-related errors"""
    pass

class ModelInitializationError(ModelError):
    """Error initializing a model"""
    pass

class ModelProcessingError(ModelError):
    """Error processing a request"""
    pass

class ServiceUnavailableError(ModelError):
    """Model service is unavailable"""
    pass

class RateLimitError(ModelError):
    """Rate limit exceeded"""
    pass

class QuotaExceededError(ModelError):
    """Usage quota exceeded"""
    pass

class ResourceExhaustedError(ModelError):
    """Computational resources exhausted"""
    pass
```

## Provider-Specific Considerations

### Gemini

- **Rate Limiting**: Implements exponential backoff for rate limit errors
- **API Key Rotation**: Supports multiple API keys with automatic rotation
- **Quota Tracking**: Monitors token usage to prevent quota overruns
- **Safety Settings**: Configurable content safety parameters

### Ollama

- **Health Checks**: Periodic verification of server availability
- **Model Loading**: Dynamic loading of models as needed
- **Resource Monitoring**: Tracks resource usage to prevent overloading
- **Concurrency Control**: Limits parallel requests to prevent resource contention

### Transformers

- **GPU Management**: Dynamic allocation of GPU resources
- **Memory Optimization**: Automatic model unloading to preserve memory
- **Quantization**: Support for different quantization levels (4-bit, 8-bit)
- **Model Caching**: Efficient loading and caching of model weights

## Related Documentation

- Model Integration Architecture
- Backend Selection
- Capability Matrix
- Model Configuration