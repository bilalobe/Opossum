"""Hybrid model backend that intelligently combines multiple model capabilities."""

import logging
from typing import Optional, Dict, Tuple

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

    async def generate_response(self, prompt: str, conversation_stage: str) -> str:
        """Generate response using the most appropriate backend for the task."""
        try:
            # Analyze requirements and select backend
            backend_name, confidence = await self.__select_backend(prompt, conversation_stage)
            backend = await self.__get_or_create_backend(backend_name)

            if backend:
                logger.info(f"Using {backend_name} backend (confidence: {confidence:.2f})")
                return await backend.generate_response(prompt, conversation_stage)
            else:
                raise RuntimeError("No suitable backend available")

        except Exception as e:
            logger.error(f"Error in hybrid generation: {str(e)}")
            # Fallback to transformers as last resort
            return await self.__fallback_generate(prompt, conversation_stage)

    async def __select_backend(self, prompt: str, conversation_stage: str) -> Tuple[str, float]:
        """Select most appropriate backend based on task requirements and availability."""
        # Check service availability
        await self.availability.check_all_services()

        # Quick check for image processing needs
        has_image = 'image' in prompt.lower() or '[IMAGE]' in prompt
        if has_image and self.availability.service_status["gemini"]["available"]:
            return 'gemini', 1.0

        # Calculate scores for each available backend
        scores: Dict[str, float] = {}

        if self.availability.service_status["gemini"]["available"]:
            scores['gemini'] = self.__calculate_backend_score({
                'text_processing': 0.9,
                'reasoning': 0.95,
                'multimodal': 1.0,
                'latency': 0.6,
                'resource_usage': 0.2
            })

        if self.availability.service_status["ollama"]["available"]:
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

        # Select highest scoring backend
        if scores:
            best_backend = max(scores.items(), key=lambda x: x[1])
            return best_backend[0], best_backend[1]

        return 'transformers', 0.5  # Fallback option

    def __calculate_backend_score(self, capabilities: Dict[str, float]) -> float:
        """Calculate weighted score for a backend based on its capabilities."""
        score = 0.0
        for capability, weight in self.__capability_weights.items():
            if capability in capabilities:
                score += capabilities[capability] * weight
        return score

    async def __get_or_create_backend(self, backend_name: str) -> Optional[ModelBackend]:
        """Get or lazily create a backend instance."""
        if not self.__backends[backend_name]:
            try:
                if backend_name == 'gemini':
                    self.__backends[backend_name] = GeminiBackend(
                        model_name=Config.MODEL_CONFIGS["gemini-thinking"]["api_name"]
                    )
                elif backend_name == 'ollama':
                    self.__backends[backend_name] = OllamaBackend(
                        model_name=Config.MODEL_CONFIGS["gemma"]["api_name"]
                    )
                elif backend_name == 'transformers':
                    self.__backends[backend_name] = TransformersBackend(
                        model_name=Config.MODEL_CONFIGS["gemma"]["transformers_name"]
                    )
            except Exception as e:
                logger.error(f"Failed to initialize {backend_name} backend: {str(e)}")
                return None

        return self.__backends[backend_name]

    async def __fallback_generate(self, prompt: str, conversation_stage: str) -> str:
        """Fallback generation using transformers backend."""
        try:
            backend = await self.__get_or_create_backend('transformers')
            if backend:
                return await backend.generate_response(prompt, conversation_stage)
        except Exception as e:
            logger.error(f"Fallback generation failed: {str(e)}")

        return "I apologize, but I'm having trouble processing your request right now."
