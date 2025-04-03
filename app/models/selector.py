"""Model selection and management logic."""

import logging
from typing import Dict, Optional
from prometheus_client import Counter, Gauge
from app.utils.circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)

# Model selection metrics
MODEL_SELECTIONS = Counter(
    "model_selections_total",
    "Total number of model selections by model type",
    ["model"]
)

MODEL_AVAILABILITY = Gauge(
    "model_availability",
    "Current availability status of models",
    ["model"]
)

class ModelSelector:
    """Handles model selection and availability management."""
    
        # Refactor selector.py to use centralized breakers
    def __init__(self, app=None):
        self.app = app
        # Use centralized circuit breakers instead
        # Access via: current_app.error_handler.circuit_breakers['gemini']

    def select_model(self, query_type: str, has_image: bool = False) -> str:
        """Select appropriate model based on query type and availability."""
        try:
            # Check Gemini availability for image queries
            if has_image and self.gemini_breaker.allow_request():
                MODEL_SELECTIONS.labels(model="gemini").inc()
                return "gemini-vision"

            # Try Ollama for text queries
            if self.ollama_breaker.allow_request():
                MODEL_SELECTIONS.labels(model="ollama").inc()
                return "ollama"

            # Fallback to Transformers
            if self.transformers_breaker.allow_request():
                MODEL_SELECTIONS.labels(model="transformers").inc()
                return "transformers"

            # If all circuits are open, use minimal fallback
            logger.error("All model circuits open, using minimal fallback")
            MODEL_SELECTIONS.labels(model="fallback").inc()
            return "fallback"

        except Exception as e:
            logger.error(f"Error in model selection: {e}")
            return "fallback"

    def record_success(self, model_name: str):
        """Record successful model invocation."""
        if model_name == "gemini-vision":
            self.gemini_breaker.record_success()
        elif model_name == "ollama":
            self.ollama_breaker.record_success()
        elif model_name == "transformers":
            self.transformers_breaker.record_success()

    def record_failure(self, model_name: str):
        """Record failed model invocation."""
        if model_name == "gemini-vision":
            self.gemini_breaker.record_failure()
        elif model_name == "ollama":
            self.ollama_breaker.record_failure()
        elif model_name == "transformers":
            self.transformers_breaker.record_failure()
