"""Hybrid model backend that intelligently combines multiple model capabilities."""

import logging
from typing import Optional, Dict, Tuple, Any, cast

from app.config import Config
from app.models.availability import ServiceAvailability
from app.models.base import ModelBackend
from app.models.gemini import GeminiBackend
from app.models.ollama import OllamaBackend
from app.models.transformers import TransformersBackend

logger = logging.getLogger(__name__)


class HybridModelBackend(ModelBackend):
    """Intelligent hybrid model that combines multiple backends based on capabilities and availability."""

    def __init__(self):
        """Initialize the hybrid model backend."""
        self.availability = ServiceAvailability()
        self.__backends: Dict[str, Optional[ModelBackend]] = {
            'gemini': None,
            'ollama': None,
            'transformers': None
        }
        self.__capability_weights = {
            'text_processing': 0.3,
            'reasoning': 0.3,
            'multimodal': 0.2,
            'latency': 0.1,
            'resource_usage': 0.1
        }
        self.model_info = {
            "name": "hybrid-model",
            "provider": "opossum-search",
            "version": "1.0"
        }
        # Always available since it includes fallbacks
        self.available = True

    async def generate_response(self, prompt: str, conversation_stage: Optional[str] = None) -> str:
        """Generate response using the most appropriate backend for the task.
        
        Args:
            prompt: The text prompt to send to the model
            conversation_stage: Optional conversation stage for context
            
        Returns:
            The generated text response
        """
        cache_key = f"{prompt}:{conversation_stage}"
        cached_response = await redis_client.get(cache_key)
        if cached_response:
            return cached_response.decode('utf-8')

        try:
            # Analyze requirements and select backend
            backend_name, confidence = await self.__select_backend(prompt, conversation_stage or "general")
            backend = await self.__get_or_create_backend(backend_name)

            if backend:
                logger.info(f"Using {backend_name} backend (confidence: {confidence:.2f})")
                response = await backend.generate_response(prompt, conversation_stage)
                await redis_client.setex(cache_key, Config.CACHE_TTL, response)
                return response
            else:
                logger.warning("No suitable backend available, using fallback")
                response = await self.__fallback_generate(prompt, conversation_stage)
                await redis_client.setex(cache_key, Config.CACHE_TTL, response)
                return response

        except Exception as e:
            logger.error(f"Error in hybrid generation: {str(e)}", exc_info=True)
            # Fallback to transformers as last resort
            response = await self.__fallback_generate(prompt, conversation_stage)
            await redis_client.setex(cache_key, Config.CACHE_TTL, response)
            return response

    async def generate_multimodal_response(self,
                                           user_message: str,
                                           conversation_stage: Optional[str] = None,
                                           image_data: Optional[str] = None) -> str:
        """Generate a response for text + image input using the most appropriate backend.
        
        Args:
            user_message: The user's text message
            conversation_stage: Optional conversation stage for context
            image_data: Base64-encoded image data with or without MIME prefix
            
        Returns:
            The generated text response
        """
        if not image_data:
            # If no image is provided, fall back to text-only generation
            return await self.generate_response(user_message, conversation_stage)

        try:
            # For multimodal, we prefer Gemini if available
            if await self.__is_backend_available('gemini'):
                backend = await self.__get_or_create_backend('gemini')
                if backend and isinstance(backend, GeminiBackend):
                    logger.info("Using Gemini backend for multimodal request")
                    return await backend.generate_multimodal_response(
                        user_message, conversation_stage, image_data
                    )

            # Fallback to text-only with image description
            fallback_prompt = (
                f"[Image description: The user uploaded an image, but I'm unable to view it.]\n\n"
                f"The user said: {user_message}\n\n"
                f"I'll respond based on the text only, acknowledging I cannot see the image."
            )
            logger.warning("No multimodal backend available, using text-only fallback")
            return await self.generate_response(fallback_prompt, conversation_stage)

        except Exception as e:
            logger.error(f"Error in hybrid multimodal generation: {str(e)}", exc_info=True)
            return (
                "I apologize, but I'm having trouble processing your image right now. "
                "Could you please describe what's in the image or try again later?"
            )

    async def __select_backend(self, prompt: str, conversation_stage: str) -> Tuple[str, float]:
        """Select the most appropriate backend based on prompt and availability.
        
        Args:
            prompt: The text prompt to analyze
            conversation_stage: Current stage of conversation
            
        Returns:
            Tuple of (selected backend name, confidence score)
        """
        # Create cache key from prompt and stage
        import hashlib
        message_hash = hashlib.md5(prompt.encode()).hexdigest()[:8]
        cache_key = f"model_select:{message_hash}:{conversation_stage}"

        # Try to get cached result
        from app.utils.infrastructure.redis_config import get_from_cache
        cached = get_from_cache(cache_key, dependency_keys=["service_status"])
        if cached:
            logger.debug("Using cached model selection result")
            return cached

        # Calculate scores for each available backend
        scores = {}

        # Rest of the existing backend selection logic
        if self.availability.service_status.get("gemini", {}).get("available", False):
            scores['gemini'] = self.__calculate_backend_score({
                'text_processing': 0.9,
                'reasoning': 0.95,
                'multimodal': 1.0,
                'latency': 0.6,
                'resource_usage': 0.2
            })

        if self.availability.service_status.get("ollama", {}).get("available", False):
            scores['ollama'] = self.__calculate_backend_score({
                'text_processing': 0.8,
                'reasoning': 0.7,
                'multimodal': 0.0,
                'latency': 0.8,
                'resource_usage': 0.6
            })

        # Transformers always available as fallback
        scores['transformers'] = self.__calculate_backend_score({
            'text_processing': 0.7,
            'reasoning': 0.5,
            'multimodal': 0.0,
            'latency': 0.4,
            'resource_usage': 0.8
        })

        # Analyze prompt complexity and adjust scores
        if any(word in prompt.lower() for word in ['what', 'when', 'where']) and len(prompt.split()) < 15:
            scores['transformers'] += 0.2

        if any(word in prompt.lower() for word in ['why', 'how', 'explain', 'analyze']):
            if 'gemini' in scores:
                scores['gemini'] += 0.2

        # Select highest scoring backend
        if scores:
            best_backend = max(scores.items(), key=lambda x: x[1])
            result = (best_backend[0], best_backend[1])

            # Cache the result
            from app.utils.infrastructure.redis_config import add_to_cache
            add_to_cache(cache_key, result, ttl=Config.MODEL_SELECTION_CACHE_TTL,
                         dependency_keys=["service_status"])

            # Update Prometheus metrics if available
            if hasattr(self.availability, 'metrics'):
                self.availability._increment_model_selection(best_backend[0])

            return result

        return 'transformers', 0.5  # Fallback option

    def __calculate_backend_score(self, capabilities: Dict[str, float]) -> float:
        """Calculate weighted score for a backend based on its capabilities.
        
        Args:
            capabilities: Dictionary mapping capability names to scores (0.0-1.0)
            
        Returns:
            Weighted score for the backend
        """
        score = 0.0
        for capability, weight in self.__capability_weights.items():
            if capability in capabilities:
                score += capabilities[capability] * weight
        return score

    async def __get_or_create_backend(self, backend_name: str) -> Optional[ModelBackend]:
        """Get or lazily create a backend instance.
        
        Args:
            backend_name: Name of the backend to create
            
        Returns:
            ModelBackend instance or None if creation fails
        """
        if not self.__backends[backend_name]:
            try:
                if backend_name == 'gemini':
                    self.__backends[backend_name] = GeminiBackend(
                        model_name=Config.MODEL_CONFIGS.get("gemini-thinking", {}).get("api_name", "gemini-pro")
                    )
                elif backend_name == 'ollama':
                    self.__backends[backend_name] = OllamaBackend(
                        model_name=Config.MODEL_CONFIGS.get("gemma", {}).get("api_name", "gemma:7b")
                    )
                elif backend_name == 'transformers':
                    self.__backends[backend_name] = TransformersBackend(
                        model_name=Config.MODEL_CONFIGS.get("gemma", {}).get("transformers_name", "google/gemma-2b")
                    )
            except Exception as e:
                logger.error(f"Failed to initialize {backend_name} backend: {str(e)}", exc_info=True)
                return None

        return self.__backends[backend_name]

    async def __is_backend_available(self, backend_name: str) -> bool:
        """Check if a specific backend is available.
        
        Args:
            backend_name: Name of the backend to check
            
        Returns:
            True if the backend is available, False otherwise
        """
        if backend_name not in self.__backends:
            return False

        # If backend is already initialized, check its availability
        if self.__backends[backend_name]:
            backend = self.__backends[backend_name]
            if hasattr(backend, 'is_available'):
                return cast(bool, backend.is_available)
            return True

        # Otherwise check the service availability
        return self.availability.service_status.get(backend_name, {}).get("available", False)

    async def __fallback_generate(self, prompt: str, conversation_stage: Optional[str] = None) -> str:
        """Fallback generation using transformers backend.
        
        Args:
            prompt: The text prompt to send to the model
            conversation_stage: Optional conversation stage for context
            
        Returns:
            The generated text response
        """
        try:
            # Try transformers first
            backend = await self.__get_or_create_backend('transformers')
            if backend:
                return await backend.generate_response(prompt, conversation_stage)

            # If transformers fails, return a template response
            logger.error("All backends failed, using template response")
            return self.__template_response(prompt, conversation_stage)

        except Exception as e:
            logger.error(f"Fallback generation failed: {str(e)}", exc_info=True)
            return self.__template_response(prompt, conversation_stage)

    def __template_response(self, prompt: str, conversation_stage: Optional[str] = None) -> str:
        """Generate a template response when all backends fail.
        
        Args:
            prompt: The original prompt
            conversation_stage: The conversation stage
            
        Returns:
            A template response
        """
        # Extract a potential topic from the prompt
        words = prompt.split()
        topic = "opossums"  # Default topic

        # Look for potential topics in the prompt
        nature_keywords = ["live", "habitat", "eat", "diet", "food", "sleep", "baby", "babies", "young"]
        if any(word.lower() in nature_keywords for word in words):
            return (
                "Opossums are adaptable marsupials that live throughout North and South America. "
                "They're omnivores that eat almost anything, including insects, small animals, fruits, and even carrion. "
                "Opossums are generally docile and prefer to avoid confrontation. "
                "I apologize that I can't provide more specific information right now."
            )

        return (
            "I apologize, but I'm having trouble generating a response right now. "
            "Opossums are fascinating creatures with many interesting characteristics. "
            "They're the only marsupials native to North America and have excellent immune systems. "
            "If you have specific questions about opossums, please try again later."
        )

    def get_info(self) -> Dict[str, Any]:
        """Get information about this model backend.
        
        Returns:
            Dictionary with model information
        """
        backends_info = {}
        for name, backend in self.__backends.items():
            if backend:
                try:
                    if hasattr(backend, 'get_info'):
                        backends_info[name] = backend.get_info()
                    else:
                        backends_info[name] = {"available": True, "name": name}
                except:
                    backends_info[name] = {"available": False, "name": name}
            else:
                backends_info[name] = {"available": False, "name": name}

        return {
            **self.model_info,
            "available": True,  # Hybrid is always available due to fallbacks
            "backends": backends_info,
            "features": ["text-generation", "multimodal", "fallback-handling", "auto-selection"]
        }

    @property
    def is_available(self) -> bool:
        """Check if this backend is available.
        
        Returns:
            Always True as the hybrid backend always has fallbacks
        """
        return True

    @property
    def supports_images(self) -> bool:
        """Check if this backend supports image inputs.
        
        Returns:
            True if at least one backend supports images
        """
        # Check if Gemini is available, as it's our primary multimodal backend
        if self.__backends.get('gemini'):
            backend = self.__backends['gemini']
            if hasattr(backend, 'supports_images'):
                return cast(bool, backend.supports_images)

        # Otherwise check availability status
        return self.availability.service_status.get("gemini", {}).get("available", False)
