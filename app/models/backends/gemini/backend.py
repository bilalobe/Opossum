"""Gemini backend implementation using Google's Generative AI API."""
import logging
from typing import Dict, Any, Optional, Tuple, List

from app.config import Config
from app.models.core.base import ModelBackend
from app.models.core.types import BackendCapability, ModelResponse, ErrorType
from app.utils.telemetry import record_model_usage

from .client import GeminiClient
from .processor import GeminiResponseProcessor
from .prompt import PromptManager

logger = logging.getLogger(__name__)


class GeminiBackend(ModelBackend):
    """Backend for Google's Gemini API with multimodal support."""

    def __init__(self, model_name: str = "gemini-2.0-flash-thinking-exp-01-21"):
        """Initialize the Gemini backend.
        
        Args:
            model_name: The specific Gemini model to use
        """
        super().__init__()
        self.model_name = model_name
        self.client = GeminiClient(model_name)
        self.processor = GeminiResponseProcessor()
        self.prompt_manager = PromptManager()
        
        self.model_info = {
            "name": model_name,
            "provider": "gemini",
            "version": "2.0",
            "capabilities": [
                BackendCapability.TEXT_GENERATION,
                BackendCapability.IMAGE_UNDERSTANDING,
                BackendCapability.REASONING
            ]
        }

    async def generate_response(self, prompt: str, 
                               conversation_stage: Optional[str] = None) -> ModelResponse:
        """Generate a text-only response using Gemini API.
        
        Args:
            prompt: The text prompt to send to the model
            conversation_stage: Optional conversation stage for context
            
        Returns:
            ModelResponse containing the generated text and metadata
        """
        if not self.client.is_available:
            return ModelResponse.error("Gemini API is not available", 
                                      ErrorType.SERVICE_UNAVAILABLE)
        
        # Apply prompt template if conversation stage is provided
        if conversation_stage:
            prompt = self.prompt_manager.apply_template(prompt, conversation_stage)
            
        try:
            # Generate response
            response_text, usage = await self.client.generate_text(prompt)
            
            # Record metrics and usage
            if usage:
                record_model_usage('gemini', usage)
            
            return ModelResponse(
                text=response_text,
                metadata={
                    "backend": "gemini",
                    "model": self.model_name,
                    "tokens": usage.get('total_tokens', 0) if usage else 0
                }
            )
        except Exception as e:
            logger.error(f"Gemini API error: {e}", exc_info=True)
            return ModelResponse.error(
                "I'm unable to generate a response at the moment. Please try again later.",
                ErrorType.PROCESSING_ERROR
            )
    
    async def generate_multimodal_response(self, user_message: str,
                                         conversation_stage: Optional[str] = None,
                                         image_data: Optional[str] = None) -> ModelResponse:
        """Generate a response for text + image input.
        
        Args:
            user_message: The user's text message
            conversation_stage: Optional conversation stage for context
            image_data: Base64-encoded image data
            
        Returns:
            ModelResponse containing the generated text and metadata
        """
        if not self.client.is_available:
            return ModelResponse.error("Gemini API is not available", 
                                      ErrorType.SERVICE_UNAVAILABLE)
                                      
        if not image_data:
            return await self.generate_response(user_message, conversation_stage)
            
        try:
            # Process image data
            processed_image = self.processor.process_image_data(image_data)
            
            # Generate prompt based on image and conversation context
            prompt = self.prompt_manager.create_image_prompt(
                user_message, conversation_stage or "general"
            )
            
            # Generate response with image
            response_text, usage = await self.client.generate_with_image(
                prompt, processed_image
            )
            
            # Record metrics and usage
            if usage:
                record_model_usage('gemini', {
                    **usage, 
                    'image_included': True
                })
            
            return ModelResponse(
                text=response_text,
                metadata={
                    "backend": "gemini",
                    "model": self.model_name,
                    "tokens": usage.get('total_tokens', 0) if usage else 0,
                    "multimodal": True
                }
            )
        except ValueError as e:
            logger.warning(f"Invalid image data: {e}")
            return ModelResponse.error(str(e), ErrorType.VALIDATION_ERROR)
        except Exception as e:
            logger.error(f"Gemini multimodal API error: {e}", exc_info=True)
            return ModelResponse.error(
                "I'm unable to analyze this image at the moment. Please try again later.",
                ErrorType.PROCESSING_ERROR
            )

    def get_info(self) -> Dict[str, Any]:
        """Get information about this model backend."""
        return {
            **self.model_info,
            "available": self.client.is_available,
            "max_tokens": Config.MAX_TOKENS,
            "features": [c.value for c in self.model_info["capabilities"]]
        }

    @property
    def is_available(self) -> bool:
        """Check if this backend is available."""
        return self.client.is_available

    @property
    def supports_images(self) -> bool:
        """Check if this backend supports image inputs."""
        return BackendCapability.IMAGE_UNDERSTANDING in self.model_info["capabilities"]