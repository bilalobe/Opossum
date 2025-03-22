"""Local Ollama model backend integration."""
import asyncio
import logging
from typing import Dict, Any, Optional, Union, List

import httpx

from app.config import Config
from app.models.base import ModelBackend

logger = logging.getLogger(__name__)


class OllamaBackend(ModelBackend):
    """Backend for local Ollama instance"""
    
    def __init__(self, model_name: str = None):
        """Initialize the Ollama backend.
        
        Args:
            model_name: The specific Ollama model to use (defaults to config value)
        """
        self.model_name = model_name or Config.OLLAMA_MODEL
        self.available = False
        self.model_info = {
            "name": self.model_name,
            "provider": "ollama",
            "version": "1.0"
        }
        self.api_url = Config.OLLAMA_URL
        
        # Check if Ollama is available
        asyncio.create_task(self._check_availability())
    
    async def _check_availability(self) -> None:
        """Check if Ollama API is available."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_url}/api/tags",
                    timeout=5
                )
                response.raise_for_status()
                
                # Check if our model is available in the list
                models = response.json().get("models", [])
                model_names = [model.get("name") for model in models]
                
                if self.model_name in model_names:
                    self.available = True
                    logger.info(f"Ollama backend initialized with model {self.model_name}")
                else:
                    logger.warning(f"Model {self.model_name} not available in Ollama")
                    self.available = False
        except Exception as e:
            logger.error(f"Failed to connect to Ollama: {str(e)}")
            self.available = False

    # Create persistent connection pool
    http_client = httpx.AsyncClient(limits=httpx.Limits(max_connections=20))

    async def generate_response(self, prompt: str, conversation_stage: Optional[str] = None) -> str:
        """Generate a response using Ollama API.
        
        Args:
            prompt: The text prompt to send to the model
            conversation_stage: Optional conversation stage for context
            
        Returns:
            The generated text response
            
        Raises:
            RuntimeError: If the Ollama backend is not available
        """
        if not self.available:
            raise RuntimeError("Ollama API is not available")

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = await self.http_client.post(
                    f"{self.api_url}/api/generate",
                    json={
                        "model": self.model_name,
                        "prompt": prompt,
                        "temperature": Config.TEMPERATURE,
                        "top_p": Config.TOP_P,
                        "top_k": Config.TOP_K,
                        "max_tokens": Config.MAX_TOKENS,
                        "stream": False
                    },
                    timeout=30
                )
                response.raise_for_status()
                return response.json().get('response', '')
            except httpx.RequestError as e:
                logger.error(f"Ollama API error (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)  # Wait before retrying
                else:
                    # Return fallback response instead of raising to support hybrid model
                    return "I'm unable to generate a response at the moment. Please try again later."
    
    async def process_image(self, image_data: str, prompt: str) -> str:
        """Process an image using LLaVa via Ollama API."""
        logger.info("Processing image with LLaVa model")
        
        try:
            api_url = f"{Config.OLLAMA_BASE_URL}/api/chat"
            
            payload = {
                "model": Config.LLAVA_MODEL,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt,
                        "images": [image_data]  # Base64 encoded image
                    }
                ],
                "stream": False,
                "options": {
                    "temperature": Config.TEMPERATURE,
                    "top_p": Config.TOP_P
                }
            }
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(api_url, json=payload)
                response.raise_for_status()
                result = response.json()
                
            return result["message"]["content"]
        except Exception as e:
            logger.error(f"Error processing image with LLaVa: {str(e)}")
            return "I couldn't analyze this image. The image processing service is currently unavailable."

    async def get_embeddings(self, texts: Union[str, List[str]]) -> Optional[List[List[float]]]:
        """Generate embeddings using MiniLM via Ollama API."""
        logger.info("Generating embeddings with MiniLM model")
        
        try:
            input_texts = texts if isinstance(texts, list) else [texts]
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{Config.OLLAMA_BASE_URL}/api/embed",
                    json={
                        "model": Config.MINILM_MODEL,
                        "input": input_texts
                    }
                )
                response.raise_for_status()
                result = response.json()
                
            return result["embeddings"]
        except Exception as e:
            logger.error(f"Error generating embeddings with MiniLM: {str(e)}")
            return None

    def get_info(self) -> Dict[str, Any]:
        """Get information about this model backend.
        
        Returns:
            Dictionary with model information
        """
        return {
            **self.model_info,
            "available": self.available,
            "max_tokens": Config.MAX_TOKENS,
            "features": ["text-generation"]
        }
    
    @property
    def is_available(self) -> bool:
        """Check if this backend is available.
        
        Returns:
            True if the backend is available, False otherwise
        """
        return self.available
    
    @property
    def supports_images(self) -> bool:
        """Check if this backend supports image inputs.
        
        Returns:
            False as most Ollama models don't support multimodal inputs
        """
        return False
