"""Base classes and interfaces for model backends."""
import abc
import logging
from typing import Dict, Any, Optional, List, Union

from .types import ModelResponse, BackendCapability, ErrorType, ModelParameters

logger = logging.getLogger(__name__)


class ModelBackend(abc.ABC):
    """Abstract base class for all model backends."""
    
    @abc.abstractmethod
    def generate_response(self, prompt: str, 
                        conversation_stage: Optional[str] = None) -> ModelResponse:
        """Generate a response from the model.
        
        Args:
            prompt: The input prompt
            conversation_stage: Optional conversation stage for context
            
        Returns:
            ModelResponse object containing the response
        """
        pass
    
    @abc.abstractmethod
    def get_info(self) -> Dict[str, Any]:
        """Get information about this model backend.
        
        Returns:
            Dictionary with model information
        """
        pass
    
    @property
    @abc.abstractmethod
    def is_available(self) -> bool:
        """Check if this backend is available.
        
        Returns:
            Boolean indicating availability
        """
        pass
    
    @property
    def supports_images(self) -> bool:
        """Check if backend supports image inputs.
        
        Returns:
            Boolean indicating image support capability
        """
        return False


class AsyncModelBackend(ModelBackend):
    """Abstract base class for asynchronous model backends."""
    
    def generate_response(self, prompt: str,
                        conversation_stage: Optional[str] = None) -> ModelResponse:
        """Synchronous wrapper for async generate_response.
        
        This method exists for backward compatibility and will be removed in future.
        """
        import asyncio
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(
            self.generate_response_async(prompt, conversation_stage)
        )
    
    @abc.abstractmethod
    async def generate_response_async(self, prompt: str,
                                   conversation_stage: Optional[str] = None) -> ModelResponse:
        """Generate a response from the model asynchronously.
        
        Args:
            prompt: The input prompt
            conversation_stage: Optional conversation stage for context
            
        Returns:
            ModelResponse object containing the response
        """
        pass


class MultimodalBackend(AsyncModelBackend):
    """Abstract base class for multimodal model backends."""
    
    @property
    def supports_images(self) -> bool:
        """Multimodal backends support images by default."""
        return True
    
    @abc.abstractmethod
    async def generate_multimodal_response(self, user_message: str,
                                        conversation_stage: Optional[str] = None,
                                        image_data: Optional[str] = None) -> ModelResponse:
        """Generate a response from text and image inputs.
        
        Args:
            user_message: The text input from the user
            conversation_stage: Optional conversation stage for context
            image_data: Base64-encoded image data
            
        Returns:
            ModelResponse object containing the response
        """
        pass
    
    async def generate_response_async(self, prompt: str,
                                   conversation_stage: Optional[str] = None) -> ModelResponse:
        """Default implementation that calls generate_multimodal_response without image."""
        return await self.generate_multimodal_response(prompt, conversation_stage)


class ComposableBackend(AsyncModelBackend):
    """Base class for backends composed of multiple specialized models."""
    
    def __init__(self):
        """Initialize the composable backend."""
        super().__init__()
        self.backends: Dict[str, ModelBackend] = {}
        
    @abc.abstractmethod
    async def select_backend(self, prompt: str, params: ModelParameters) -> str:
        """Select the appropriate backend for the given input.
        
        Args:
            prompt: The input prompt
            params: Model parameters and request context
            
        Returns:
            Key of selected backend
        """
        pass
    
    async def generate_response_async(self, prompt: str,
                                   conversation_stage: Optional[str] = None) -> ModelResponse:
        """Route request to appropriate backend.
        
        Args:
            prompt: The input prompt
            conversation_stage: Optional conversation stage for context
            
        Returns:
            ModelResponse from selected backend
        """
        params = ModelParameters(conversation_stage=conversation_stage)
        backend_key = await self.select_backend(prompt, params)
        
        if backend_key not in self.backends:
            logger.error(f"Selected backend {backend_key} not available")
            return ModelResponse.error(
                "Selected backend is not available",
                ErrorType.CONFIGURATION_ERROR
            )
        
        backend = self.backends[backend_key]
        
        if isinstance(backend, AsyncModelBackend):
            return await backend.generate_response_async(prompt, conversation_stage)
        else:
            return backend.generate_response(prompt, conversation_stage)