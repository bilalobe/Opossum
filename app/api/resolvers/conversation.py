"""Chat and conversation management resolvers."""
import logging
import json
from app.conversation import conversation_factory
from app.models import get_model_backend
from app.utils.infrastructure.cache_factory import cache

logger = logging.getLogger(__name__)

async def resolve_chat(root, info, input):
    """Handle chat messages with caching and response generation."""
    cache_key = f"chat_{input.session_id}_{input.message}_{input.has_image}"
    cached_response = cache.get(cache_key)
    if cached_response:
        return json.loads(cached_response)

    try:
        conversation_state, sentiment_tracker = conversation_factory.create_conversation(input.session_id)
        response_generator = conversation_factory.get_response_generator()
        backend = await get_model_backend(input.message, conversation_state.current_stage, input.has_image)
        
        response_data = await response_generator.generate_response(
            user_message=input.message,
            conversation_state=conversation_state,
            sentiment_tracker=sentiment_tracker,
            model_backend=backend
        )

        cache.set(cache_key, json.dumps(response_data), expire=3600)
        return response_data
    except Exception as e:
        logger.error(f"Error generating chat response: {str(e)}")
        return {
            "response": "I apologize, but I'm having trouble processing your request right now.",
            "next_stage": conversation_state.current_stage if conversation_state else None,
            "has_svg": False,
            "error": str(e)
        }

def resolve_submit_feedback(root, info, message, rating):
    """Handle user feedback submission."""
    try:
        logger.info(f"Feedback received for message '{message}': {rating}")
        return True
    except Exception as e:
        logger.error(f"Error submitting feedback: {e}")
        return False

def resolve_end_conversation(root, info, session_id):
    """End a conversation session."""
    try:
        conversation_factory.conversation_manager.end_conversation(session_id)
        return True
    except Exception as e:
        logger.error(f"Error ending conversation: {e}")
        return False