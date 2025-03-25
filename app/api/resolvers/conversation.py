"""Conversation resolvers with enhanced functionality and error handling."""
import logging

from app.api.directives import apply_cost, rate_limit
from app.api.types import Timestamp
from app.conversation import conversation_factory

logger = logging.getLogger(__name__)


@apply_cost(value=10)
@rate_limit(limit=30, duration=60)  # 30 requests per minute
async def resolve_chat(root, info, input):
    """Handle chat conversations using the selected model."""
    try:
        # Extract input parameters
        message = input.get('message', '')
        session_id = input.get('session_id', '')
        has_image = input.get('has_image', False)
        image_data = input.get('image_data', '') if has_image else None

        # Get conversation manager for this session
        conversation = conversation_factory.get_conversation(session_id)

        # Process the message
        result = await conversation.process_message(
            message=message,
            image_data=image_data if has_image else None
        )

        # Return structured response
        return {
            "response": result.get("response", ""),
            "next_stage": result.get("next_stage", ""),
            "has_svg": "svg_content" in result and bool(result["svg_content"]),
            "svg_content": result.get("svg_content", ""),
            "base64_image": result.get("base64_image", "")
        }
    except Exception as e:
        logger.error(f"Error processing chat: {e}", exc_info=True)
        return {
            "response": "I'm sorry, I encountered an error processing your request.",
            "next_stage": "error",
            "has_svg": False,
            "error": str(e)
        }


@apply_cost(value=2)
async def resolve_submit_feedback(root, info, message, rating):
    """Record user feedback about a conversation."""
    try:
        # This would typically connect to a feedback storage system
        logger.info(f"Feedback received - Rating: {rating}, Message: {message}")

        # For now, just log the feedback
        feedback_data = {
            "message": message,
            "rating": rating,
            "timestamp": Timestamp.from_datetime.now(),
            "user_agent": getattr(info.context, 'user_agent', 'unknown'),
            "ip_address": getattr(info.context, 'ip_address', 'unknown')
        }

        # In a real implementation, store this in a database
        logger.info(f"Feedback data: {feedback_data}")

        return True
    except Exception as e:
        logger.error(f"Error submitting feedback: {e}")
        return False


@apply_cost(value=1)
async def resolve_end_conversation(root, info, session_id):
    """End a conversation session and clean up resources."""
    try:
        # Remove conversation from factory
        conversation_factory.end_conversation(session_id)
        logger.info(f"Ended conversation session: {session_id}")
        return True
    except Exception as e:
        logger.error(f"Error ending conversation: {e}")
        return False
