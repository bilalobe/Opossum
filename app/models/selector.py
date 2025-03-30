import logging
import time
import random
from typing import Dict, List, Tuple, Optional
import os
from datetime import datetime

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

    # Chat2SVG availability
    if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'Chat2SVG-main')):
        available["chat2svg"] = ["svg_generation"]

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


class CircuitBreaker:
    """Circuit breaker pattern implementation to prevent repeated calls to failing services."""
    
    def __init__(self, name: str, failure_threshold: int = 3, reset_timeout: int = 60):
        self.name = name
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def record_success(self):
        """Record a successful operation, resetting the circuit breaker."""
        self.failure_count = 0
        if self.state != "CLOSED":
            logger.info(f"Circuit breaker {self.name} closing after successful operation")
            self.state = "CLOSED"
    
    def record_failure(self):
        """Record a failed operation, potentially opening the circuit breaker."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == "CLOSED" and self.failure_count >= self.failure_threshold:
            logger.warning(f"Circuit breaker {self.name} opening after {self.failure_count} failures")
            self.state = "OPEN"
        elif self.state == "HALF_OPEN":
            logger.warning(f"Circuit breaker {self.name} reopening after test failure")
            self.state = "OPEN"
    
    def allow_request(self) -> bool:
        """Determine if a request should be allowed based on the circuit state."""
        current_time = time.time()
        
        # If the circuit is open but enough time has passed, allow a test request
        if self.state == "OPEN" and current_time - self.last_failure_time > self.reset_timeout:
            logger.info(f"Circuit breaker {self.name} switching to half-open state for testing")
            self.state = "HALF_OPEN"
            return True
            
        # Allow requests when closed or half-open (for testing)
        return self.state != "OPEN"


class ModelSelector:
    """Selects the most appropriate model based on query characteristics and availability"""

    def __init__(self, topic_detector, metrics=None):
        self.topic_detector = topic_detector
        self.metrics = metrics
        self.availability = ServiceAvailability()
        self._last_availability_check = 0
        
        # Circuit breakers for each provider
        self.circuit_breakers = {
            "gemini": CircuitBreaker("gemini", failure_threshold=3, reset_timeout=60),
            "ollama": CircuitBreaker("ollama", failure_threshold=3, reset_timeout=120),
            "transformers": CircuitBreaker("transformers", failure_threshold=5, reset_timeout=300),
            "chat2svg": CircuitBreaker("chat2svg", failure_threshold=3, reset_timeout=90)
        }
        
        # Failure statistics for adaptive resilience
        self._failure_stats = {
            "gemini": {"count": 0, "last_time": 0, "consecutive": 0},
            "ollama": {"count": 0, "last_time": 0, "consecutive": 0},
            "transformers": {"count": 0, "last_time": 0, "consecutive": 0},
            "chat2svg": {"count": 0, "last_time": 0, "consecutive": 0}
        }
        
        # Service degradation markers
        self._service_degraded = {
            "gemini": False,
            "ollama": False,
            "transformers": False,
            "chat2svg": False
        }
        
        # Emergency fallback paths (order of preference when everything else fails)
        self._emergency_fallbacks = [
            {"provider": "transformers", "model": "gemma"},
            {"provider": "ollama", "model": "gemma"},
            {"provider": "transformers", "model": "miniLM"}
        ]

        # Define the 3x3 capability matrix for model selection
        # Format: {provider: {model: {capability: score}}}
        self.capability_matrix = {
            "ollama": {
                "llava": {
                    "text_processing": 0.7,
                    "multimodal": 0.9,
                    "image_understanding": 0.85,
                    "offline_capable": 1.0,
                    "windows_compatible": 1.0 if Config.IS_WINDOWS else 0.0,
                },
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
                    "embeddings": 0.9,
                    "topic_detection": 0.95,
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
            },
            "chat2svg": {
                "svg_generation": {
                    "text_to_svg": 0.95,
                    "style_control": 0.9,
                    "path_optimization": 0.9,
                    "resource_usage": 0.7,  # Higher resource usage
                    "offline_capable": 1.0 if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'Chat2SVG-main')) else 0.0,
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
        # Add tracing
        start_time = time.time()
        trace_id = f"select_{int(start_time * 1000)}"
        
        try:
            # Check if we have a cached selection for this input
            cache_key = f"model_selection_{user_message}_{conversation_stage}_{has_image}"
            cached_selection = get_from_cache(cache_key)
            if cached_selection:
                logger.debug(f"[TRACE:{trace_id}] Returning cached model selection")
                return cached_selection

            # Check service availability (with caching to avoid frequent checks)
            await self._check_availability()

            # Filter out providers with open circuit breakers
            available_backends = {}
            for provider, status in self.availability.service_status.items():
                # Skip if circuit breaker is open
                if not self.circuit_breakers[provider].allow_request():
                    logger.info(f"[TRACE:{trace_id}] Skipping {provider} due to open circuit breaker")
                    continue
                    
                # Add if service is available
                if status["available"]:
                    available_backends[provider] = self.available_backends.get(provider, [])
            
            # Log available backends for tracing
            logger.debug(f"[TRACE:{trace_id}] Available backends: {available_backends}")

            # Fast path for images - only use Gemini if it's available
            if has_image and "gemini" in available_backends and "gemini-thinking" in available_backends["gemini"]:
                model_selection = ("gemini-thinking", 1.0, "gemini")
                add_to_cache(cache_key, model_selection, ttl=10)  # Cache for 10 seconds
                logger.debug(f"[TRACE:{trace_id}] Fast path selection for image: {model_selection}")
                return model_selection
            elif has_image:
                # If image requested but Gemini not available, log warning
                logger.warning(f"[TRACE:{trace_id}] Image processing requested but Gemini unavailable, using text-only model")

            # Determine task requirements
            task_requirements = self._analyze_task_requirements(user_message, conversation_stage, has_image)
            logger.debug(f"[TRACE:{trace_id}] Task requirements: {task_requirements}")

            # Add availability as a high-priority requirement
            task_requirements["available"] = 1.0  # Maximum importance

            # Match to capabilities, but only for available services
            model_selection = self._match_to_capabilities(task_requirements, available_backends)
            
            # Apply jitter to model selection in degraded conditions to prevent thundering herd
            if self._is_system_degraded() and random.random() < 0.2:  # 20% chance
                backup_model = self._get_fallback_model(model_selection[0], model_selection[2], available_backends)
                if backup_model:
                    logger.info(f"[TRACE:{trace_id}] System degraded, applying jitter to model selection. "
                               f"Original: {model_selection}, New: {backup_model}")
                    model_selection = backup_model
            
            # Record elapsed time for performance metrics
            elapsed = time.time() - start_time
            logger.debug(f"[TRACE:{trace_id}] Model selection took {elapsed:.3f}s")
            
            # Cache the result
            add_to_cache(cache_key, model_selection, ttl=10)  # Cache for 10 seconds

            logger.info(f"[TRACE:{trace_id}] Selected {model_selection[2]}/{model_selection[0]} with confidence {model_selection[1]:.2f}")
            return model_selection
            
        except Exception as e:
            # Handle unexpected errors with emergency fallback
            logger.error(f"[TRACE:{trace_id}] Error in model selection: {str(e)}")
            return self._emergency_fallback()

    async def _check_availability(self):
        """Check service availability with caching to reduce API calls"""
        current_time = time.time()

        # Only check availability if the last check was more than Config.AVAILABILITY_CACHE_TTL seconds ago
        if current_time - self._last_availability_check > Config.AVAILABILITY_CACHE_TTL:
            try:
                await self.availability.check_all_services()
                self._last_availability_check = current_time
                
                # Update circuit breaker statuses based on availability
                for provider, status in self.availability.service_status.items():
                    if provider in self.circuit_breakers:
                        if status["available"]:
                            self.circuit_breakers[provider].record_success()
                        else:
                            self.circuit_breakers[provider].record_failure()
                            
            except Exception as e:
                logger.error(f"Error checking service availability: {str(e)}")
                # Don't update last check time so we'll try again soon

    def _match_to_capabilities(self, requirements, available_backends) -> Tuple[str, float, str]:
        """Match requirements to capabilities, considering only available services"""
        best_score = -1
        best_model = None
        best_provider = None
        candidates = []

        for provider, models in available_backends.items():
            for model in models:
                if model not in self.capability_matrix.get(provider, {}):
                    continue
                    
                capabilities = self.capability_matrix[provider][model]
                if not capabilities:
                    continue

                # Calculate score based on matching capabilities to requirements
                score = 0
                matches = 0

                for req, req_value in requirements.items():
                    if req in capabilities:
                        if req in ["latency", "resource_usage"]:
                            # For these metrics, lower is better
                            score += (1 - capabilities[req]) * req_value
                        else:
                            score += capabilities[req] * req_value
                        matches += 1

                # Add availability bonus
                score += 0.5  # Bonus for being available
                
                # Apply degradation penalty if service has shown signs of degradation
                if self._service_degraded.get(provider, False):
                    score *= 0.8  # 20% penalty to encourage diversity in selection
                
                # Store all candidates for potential fallback
                normalized_score = score / (max(1, sum(requirements.values())) + 0.5)
                candidates.append((model, normalized_score, provider))

                if normalized_score > best_score:
                    best_score = normalized_score
                    best_model = model
                    best_provider = provider
        
        # Sort candidates by score for potential fallbacks
        candidates.sort(key=lambda x: x[1], reverse=True)

        # Fallback if no suitable available model found
        if not best_model or best_score < 0.4:
            logger.warning("No suitable available model found, trying fallbacks")
            return self._select_fallback(candidates, available_backends)

        return best_model, best_score, best_provider
    
    def _select_fallback(self, candidates, available_backends):
        """Select a fallback model when no good match is found"""
        # Try candidates with lower scores first
        if candidates:
            # Take the second best if available (to avoid the one we already determined wasn't good enough)
            if len(candidates) > 1:
                return candidates[1]
            return candidates[0]
            
        # If no candidates at all, go to fixed fallback logic
        logger.warning("No candidates available, using emergency fallback strategy")
        
        # Try transformers/gemma first
        if "transformers" in available_backends and "gemma" in available_backends["transformers"]:
            return "gemma", 0.4, "transformers"
            
        # Try any available model as last resort
        for provider, models in available_backends.items():
            if models:
                return models[0], 0.3, provider
        
        # Ultimate fallback - use transformers even if it's not in "available" list
        # This typically means we've detected it's down, but we'll try anyway as a last resort
        return "gemma", 0.2, "transformers"

    def _analyze_task_requirements(self, user_message: str, conversation_stage: str, has_image: bool) -> Dict[
        str, float]:
        """Analyze the task to determine requirements based on message content, conversation stage, and image presence"""
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

        # Adjust based on conversation stage
        if conversation_stage == "greeting":
            # Simple responses need less reasoning
            requirements["reasoning"] = 0.2
            requirements["latency"] = 0.7  # Prioritize fast response for greeting
        elif conversation_stage == "follow_up":
            # Follow-up questions often need more context and reasoning
            requirements["reasoning"] = 0.6

        # Check for complex reasoning needs
        if _requires_complex_reasoning(user_message):
            requirements["reasoning"] = 0.9

        # Topic specific requirements
        if self.topic_detector:
            similarities = self._get_topic_similarities(user_message)
            if similarities:
                max_topic, max_score = max(similarities.items(), key=lambda x: x[1])

                if max_score > 0.6:
                    if max_topic in ["diet_query", "habitat_query", "snake_resistance"]:
                        requirements["text_processing"] = 0.7
                        requirements["reasoning"] = 0.4
                    elif max_topic in ["behavior_query", "general_info"]:
                        requirements["reasoning"] = 0.8

        if has_image:
            requirements["multimodal"] = 1.0
            requirements["image_understanding"] = 0.9

        return requirements

    def _get_topic_similarities(self, user_message: str) -> Optional[Dict[str, float]]:
        """Calculate similarity scores between the user message and all topics"""
        if not self.topic_detector:
            return None

        cache_key = f"similarity_{user_message}"
        similarities = get_from_cache(cache_key)

        if not similarities:
            try:
                message_embedding = self.topic_detector.model.encode(user_message.lower())

                similarities = {}
                for topic, embedding in self.topic_detector.topic_embeddings.items():
                    similarity = self.topic_detector.cosine_similarity([message_embedding], [embedding])[0][0]
                    similarities[topic] = similarity

                add_to_cache(cache_key, similarities, ttl=300)  # Cache for 5 minutes
            except Exception as e:
                logger.error(f"Error calculating topic similarities: {e}")
                return None

        return similarities
        
    def report_success(self, provider: str, model: str):
        """Report successful model usage to update resilience statistics"""
        if provider in self._failure_stats:
            # Reset consecutive failures
            self._failure_stats[provider]["consecutive"] = 0
            
            # Update circuit breaker
            self.circuit_breakers[provider].record_success()
            
            # Clear degradation flag if it was set
            if self._service_degraded[provider]:
                logger.info(f"Provider {provider} no longer appears degraded")
                self._service_degraded[provider] = False
    
    def report_failure(self, provider: str, model: str, error_type: str = "generic"):
        """Report model failure to update resilience statistics"""
        if provider in self._failure_stats:
            stats = self._failure_stats[provider]
            current_time = time.time()
            
            # Update failure stats
            stats["count"] += 1
            stats["last_time"] = current_time
            stats["consecutive"] += 1
            
            # Update circuit breaker
            self.circuit_breakers[provider].record_failure()
            
            # Check for service degradation (3+ consecutive failures)
            if stats["consecutive"] >= 3 and not self._service_degraded[provider]:
                logger.warning(f"Provider {provider} appears degraded after {stats['consecutive']} consecutive failures")
                self._service_degraded[provider] = True
            
            # Log failure for monitoring
            logger.error(f"Model failure: {provider}/{model} - {error_type} - consecutive: {stats['consecutive']}")
    
    def _is_system_degraded(self) -> bool:
        """Check if the overall system appears degraded based on failure patterns"""
        degraded_providers = sum(1 for degraded in self._service_degraded.values() if degraded)
        return degraded_providers >= 2  # System is degraded if 2+ providers are having issues
    
    def _emergency_fallback(self) -> Tuple[str, float, str]:
        """Emergency fallback when selection process itself fails"""
        logger.critical("Using EMERGENCY FALLBACK for model selection due to critical failure")
        
        # Try each emergency fallback path
        for fallback in self._emergency_fallbacks:
            provider = fallback["provider"]
            model = fallback["model"]
            
            # Skip if circuit breaker is fully open
            if provider in self.circuit_breakers and self.circuit_breakers[provider].state == "OPEN":
                continue
                
            if (provider in self.available_backends and 
                model in self.available_backends[provider]):
                logger.info(f"Emergency fallback selected: {provider}/{model}")
                return model, 0.2, provider
        
        # Ultimate emergency fallback - just try transformers/gemma
        logger.critical("ALL FALLBACKS EXHAUSTED! Using transformers/gemma as final resort")
        return "gemma", 0.1, "transformers"
    
    def _get_fallback_model(self, current_model: str, current_provider: str, 
                           available_backends: Dict[str, List[str]]) -> Optional[Tuple[str, float, str]]:
        """
        Get an alternative model for jittering selections during degraded conditions.

        This method attempts to find a fallback model from a different provider while maintaining 
        the same model capabilities. It avoids switching away from 'transformers' as it is typically 
        the most reliable option in degraded conditions. If no suitable alternative provider is found, 
        it returns None.

        Args:
            current_model (str): The currently selected model.
            current_provider (str): The provider of the currently selected model.
            available_backends (Dict[str, List[str]]): A dictionary of available providers and their models.

        Returns:
            Optional[Tuple[str, float, str]]: A tuple containing the fallback model name, confidence score, 
            and provider, or None if no fallback is available.
        """
        """Get an alternative model for jittering selections during degraded conditions"""
        # Don't switch away from transformers - it's usually our most reliable option
        if current_provider == "transformers":
            return None
            
        # Find an alternative provider with the same model capabilities
        alternative_providers = []
        for provider, models in available_backends.items():
            if provider != current_provider and current_model in models:
                alternative_providers.append(provider)
                
        if alternative_providers:
            chosen_provider = random.choice(alternative_providers)
            return current_model, 0.5, chosen_provider  # Confidence is lower for jittered selection
            
        return None
