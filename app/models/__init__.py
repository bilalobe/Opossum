# app/models/__init__.py
import logging
import asyncio
from app.models.gemini import GeminiBackend
from app.models.ollama import OllamaBackend
from app.models.transformers import TransformersBackend
from app.models.selector import ModelSelector
from app.models.availability import ServiceAvailability
from app.config import Config
from app.conversation import topic_detector

logger = logging.getLogger(__name__)

# Create selector with availability monitoring
availability_monitor = ServiceAvailability()
model_selector = ModelSelector(topic_detector)
model_selector.availability = availability_monitor  # Attach availability monitor

async def get_model_backend(user_message=None, conversation_stage=None, has_image=False):
    """Return the appropriate model backend based on message content and availability"""

    # Default model as fallback
    selected_model = Config.DEFAULT_MODEL
    selected_provider = "transformers"  # Default provider

    if user_message and conversation_stage:
        # Check service availability first
        await availability_monitor.check_all_services()

        # Get model, confidence and provider with availability awareness
        selected_model, confidence, selected_provider = await model_selector.select_model_with_availability(
            user_message, conversation_stage, has_image
        )

        logger.info(f"Selected {selected_provider}/{selected_model} with confidence {confidence:.2f}")

    # Initialize the appropriate backend with proper error handling
    try:
        if selected_provider == "gemini" and availability_monitor.service_status["gemini"]["available"]:
            backend = GeminiBackend(model_name=Config.MODEL_CONFIGS[selected_model]["api_name"])
            # Record Gemini usage for rate limiting
            availability_monitor.record_gemini_usage()
            return backend

        elif selected_provider == "ollama" and availability_monitor.service_status["ollama"]["available"]:
            return OllamaBackend(model_name=Config.MODEL_CONFIGS[selected_model]["api_name"])

        elif selected_provider == "transformers":
            return TransformersBackend(model_name=Config.MODEL_CONFIGS[selected_model]["transformers_name"])

    except Exception as e:
        logger.error(f"Failed to initialize {selected_provider} backend with {selected_model}: {e}")
        logger.warning("Falling back to transformers backend")

    # Ultimate fallback - always use transformers if everything else fails
    return TransformersBackend(model_name=Config.MODEL_CONFIGS["gemma"]["transformers_name"])