"""Client for interacting with Google's Gemini API."""
import logging
import base64
from typing import Dict, Any, Tuple, Optional, List, Union

from app.config import Config
from app.utils.circuit_breaker import CircuitBreaker
from app.utils.retry import retry_with_exponential_backoff

logger = logging.getLogger(__name__)

# Circuit breaker for Gemini API
gemini_breaker = CircuitBreaker(
    name="gemini",
    failure_threshold=Config.GEMINI_FAILURE_THRESHOLD,
    reset_timeout=Config.GEMINI_RESET_TIMEOUT
)


class GeminiClient:
    """Client for Google's Gemini API with error handling and resilience."""
    
    def __init__(self, model_name: str):
        """Initialize the Gemini client.
        
        Args:
            model_name: The model to use for generation
        """
        self.genai = None
        self.model = None
        self.model_name = model_name
        self._available = False
        self._initialize()
        
    def _initialize(self):
        """Initialize the API client and check availability."""
        try:
            from google import generativeai as genai
            genai.configure(api_key=Config.GEMINI_API_KEY)
            self.genai = genai
            
            if Config.GEMINI_API_KEY and Config.GEMINI_API_KEY != "your-api-key-here":
                self._available = True
                logger.info(f"Initialized Gemini client with model {self.model_name}")
            else:
                logger.warning("Gemini API key not configured properly")
                self._available = False
        except ImportError:
            logger.warning("Google Generative AI package not available")
            self._available = False
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {str(e)}")
            self._available = False
    
    def _lazy_load_model(self):
        """Lazily initialize the model when needed."""
        if self.model is None and self._available and self.genai:
            try:
                self.model = self.genai.GenerativeModel(self.model_name)
            except Exception as e:
                logger.error(f"Failed to initialize Gemini model: {str(e)}")
                self._available = False
                raise
    
    @retry_with_exponential_backoff(max_retries=Config.GEMINI_MAX_RETRIES)
    @gemini_breaker.call
    async def generate_text(self, prompt: str) -> Tuple[str, Dict[str, int]]:
        """Generate text from a text prompt.
        
        Args:
            prompt: The text prompt to use
            
        Returns:
            Tuple of (generated_text, usage_data)
            
        Raises:
            RuntimeError: If the client is not available or model fails to load
            ValueError: For invalid inputs
        """
        if not self._available or not self.genai:
            raise RuntimeError("Gemini API is not available")
        
        self._lazy_load_model()
        
        generation_config = {
            "temperature": Config.TEMPERATURE,
            "top_p": Config.TOP_P,
            "top_k": Config.TOP_K,
            "max_output_tokens": Config.MAX_TOKENS,
        }
        
        response = await self.model.generate_content_async(
            prompt,
            generation_config=generation_config
        )
        
        # Extract usage information
        usage = None
        if hasattr(response, 'usage_metadata'):
            usage = {
                'prompt_tokens': response.usage_metadata.prompt_token_count,
                'completion_tokens': response.usage_metadata.candidates_token_count,
                'total_tokens': (
                    response.usage_metadata.prompt_token_count + 
                    response.usage_metadata.candidates_token_count
                )
            }
        
        return response.text, usage
    
    @retry_with_exponential_backoff(max_retries=Config.GEMINI_MAX_RETRIES)
    @gemini_breaker.call
    async def generate_with_image(self, prompt: str, image_data: bytes) -> Tuple[str, Dict[str, int]]:
        """Generate text from a prompt and image.
        
        Args:
            prompt: The text prompt
            image_data: Raw image bytes
            
        Returns:
            Tuple of (generated_text, usage_data)
            
        Raises:
            RuntimeError: If the client is not available or model fails to load
            ValueError: For invalid inputs
        """
        if not self._available or not self.genai:
            raise RuntimeError("Gemini API is not available")
        
        self._lazy_load_model()
        
        generation_config = {
            "temperature": Config.TEMPERATURE,
            "top_p": Config.TOP_P,
            "top_k": Config.TOP_K,
            "max_output_tokens": Config.MAX_TOKENS,
        }
        
        image_part = {
            "mime_type": "image/jpeg",  # Assumed JPEG, could be detected
            "data": image_data
        }
        
        response = await self.model.generate_content_async(
            [prompt, image_part],
            generation_config=generation_config
        )
        
        # Extract usage information
        usage = None
        if hasattr(response, 'usage_metadata'):
            usage = {
                'prompt_tokens': response.usage_metadata.prompt_token_count,
                'completion_tokens': response.usage_metadata.candidates_token_count,
                'total_tokens': (
                    response.usage_metadata.prompt_token_count + 
                    response.usage_metadata.candidates_token_count
                )
            }
        
        return response.text, usage
    
    @property
    def is_available(self) -> bool:
        """Check if the Gemini client is available."""
        return self._available