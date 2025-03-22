# app/models/selector.py
import logging
from typing import Dict, List, Tuple

from app.config import Config
from app.models.availability import ServiceAvailability
from app.utils.infrastructure.cache import get_from_cache, add_to_cache

logger = logging.getLogger(__name__)


def _determine_available_backends() -> Dict[str, List[str]]:
    """Determine which backends are available in the current environment"""
    available = {}

    # Ollama availability
    if not Config.IS_WINDOWS:
        available["ollama"] = ["gemma", "miniLM"]
    else:
        available["ollama"] = []

    # Gemini availability
    if Config.GEMINI_API_KEY:
        available["gemini"] = ["gemini-thinking"]
    else:
        available["gemini"] = []

    # Transformers always available but resource intensive
    available["transformers"] = ["gemma", "miniLM"]

    return available


def _requires_complex_reasoning(user_message: str) -> bool:
    """Detect if a message requires complex reasoning capabilities"""
    complex_indicators = [
        "compare", "difference between", "explain why",
        "how would", "analyze", "interpret", "synthesize",
        "what if", "causes of", "implications"
    ]

    message_lower = user_message.lower()
    return any(indicator in message_lower for indicator in complex_indicators)


class ModelSelector:
    """Selects the most appropriate model based on query characteristics and availability"""

    def __init__(self, topic_detector, metrics=None):
        self.topic_detector = topic_detector
        self.metrics = metrics
        self.availability = ServiceAvailability()

        # Define the 3x3 capability matrix for model selection
        # Format: {provider: {model: {capability: score}}}
        self.capability_matrix = {
            "ollama": {
                "gemma": {
                    "text_processing": 0.8,
                    "reasoning": 0.6,
                    "latency": 0.9,  # Lower is better
                    "resource_usage": 0.5,  # Lower is better
                    "offline_capable": 1.0,
                    "windows_compatible": 0.0,  # Not Windows compatible
                },
                "gemini-thinking": None,  # Not available
                "miniLM": {
                    "embeddings": 0.8,
                    "topic_detection": 0.9,
                    "resource_usage": 0.3,  # Very efficient
                    "offline_capable": 1.0,
                    "windows_compatible": 1.0,
                }
            },
            "gemini": {
                "gemma": None,  # Not available
                "gemini-thinking": {
                    "text_processing": 0.9,
                    "reasoning": 0.95,
                    "multimodal": 1.0,
                    "latency": 0.6,  # Cloud latency
                    "resource_usage": 0.2,  # Cloud-based
                    "offline_capable": 0.0,
                    "windows_compatible": 1.0,
                },
                "miniLM": None  # Not available
            },
            "transformers": {
                "gemma": {
                    "text_processing": 0.7,
                    "reasoning": 0.5,
                    "latency": 0.5,  # High local latency
                    "resource_usage": 0.8,  # High resources
                    "offline_capable": 1.0,
                    "windows_compatible": 1.0,
                },
                "gemini-thinking": None,  # Not available
                "miniLM": {
                    "embeddings": 0.8,
                    "topic_detection": 0.9,
                    "resource_usage": 0.4,
                    "offline_capable": 1.0,
                    "windows_compatible": 1.0,
                }
            }
        }

        # Available backends (depends on environment)
        self.available_backends = _determine_available_backends()

    async def select_model(self, user_message: str, conversation_stage: str, has_image: bool = False) -> Tuple[
        str, float, str]:
        """
        Select the best model based on content, system capabilities, and current availability
        Returns: (model_name, confidence, provider)
        """
        # First check service availability
        await self.availability.check_all_services()

        # Only use available backends
        available_backends = {}
        for provider, status in self.availability.service_status.items():
            if status["available"]:
                available_backends[provider] = self.available_backends.get(provider, [])

        # Fast path for images - only use Gemini if it's available
        if has_image and "gemini" in available_backends and "gemini-thinking" in available_backends["gemini"]:
            return "gemini-thinking", 1.0, "gemini"
        elif has_image:
            # If image requested but Gemini not available, log warning
            logger.warning("Image processing requested but Gemini unavailable, using text-only model")

        # Determine task requirements
        task_requirements = self._analyze_task_requirements(user_message, conversation_stage)

        # Add availability as a high-priority requirement
        task_requirements["available"] = 1.0  # Maximum importance

        # Match to capabilities, but only for available services
        model, confidence, provider = self._match_to_capabilities(
            task_requirements, available_backends)

        logger.info(f"Selected {provider}/{model} with confidence {confidence:.2f} (availability-aware)")
        return model, confidence, provider

    def _match_to_capabilities(self, requirements, available_backends):
        """Match requirements to capabilities, considering only available services"""
        best_score = -1
        best_model = None
        best_provider = None

        for provider, models in available_backends.items():
            for model in models:
                capabilities = self.capability_matrix[provider][model]
                if not capabilities:
                    continue

                # Calculate score as before
                score = 0
                matches = 0

                for req, req_value in requirements.items():
                    if req in capabilities:
                        if req in ["latency", "resource_usage"]:
                            score += (1 - capabilities[req]) * req_value
                        else:
                            score += capabilities[req] * req_value
                        matches += 1

                # Add availability bonus
                score += 0.5  # Bonus for being available

                # Normalize score
                normalized_score = score / (max(1, sum(requirements.values())) + 0.5)

                if normalized_score > best_score:
                    best_score = normalized_score
                    best_model = model
                    best_provider = provider

        # Fallback if no available service found
        if not best_model or best_score < 0.4:
            logger.warning("No suitable available model found, falling back to transformers")
            if "transformers" in available_backends and "gemma" in available_backends["transformers"]:
                return "gemma", 0.4, "transformers"

            # Last resort - use ANY available model
            for provider, models in available_backends.items():
                if models:
                    return models[0], 0.3, provider

        return best_model, best_score, best_provider

    def _analyze_task_requirements(self, user_message: str) -> Dict[str, float]:
        """Analyze the task to determine requirements
        :rtype: object
        """
        requirements = {
            "text_processing": 0.5,  # Base requirement
            "reasoning": 0.3,  # Base requirement
            "multimodal": 0.0,
            "embeddings": 0.0,
            "topic_detection": 0.0,
            "latency": 0.5,
            "resource_usage": 0.5,
            "offline_capable": 0.0,
            "windows_compatible": 1.0 if Config.IS_WINDOWS else 0.0,
        }

        # Check for complex reasoning needs
        if _requires_complex_reasoning(user_message):
            requirements["reasoning"] = 0.9

        # Topic specific requirements
        similarities = self._get_topic_similarities(user_message)
        max_topic, max_score = max(similarities.items(), key=lambda x: x[1]) if similarities else (None, 0)

        if max_topic and max_score > 0.6:
            if max_topic in ["diet_query", "habitat_query", "snake_resistance"]:
                requirements["text_processing"] = 0.7
                requirements["reasoning"] = 0.4
            elif max_topic in ["behavior_query", "general_info"]:
                requirements["reasoning"] = 0.8

        return requirements

    def _get_topic_similarities(self, user_message: str) -> Dict[str, float]:
        """Calculate similarity scores between the user message and all topics"""
        cache_key = f"similarity_{user_message}"
        similarities = get_from_cache(cache_key)

        if not similarities:
            message_embedding = self.topic_detector.model.encode(user_message.lower())

            similarities = {}
            for topic, embedding in self.topic_detector.topic_embeddings.items():
                similarity = self.topic_detector.cosine_similarity([message_embedding], [embedding])[0][0]
                similarities[topic] = similarity

            add_to_cache(cache_key, similarities)

        return similarities
