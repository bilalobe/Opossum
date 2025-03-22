# app/routes.py
from flask import Blueprint, render_template, request, jsonify
import logging
from app.models import get_model_backend
from app.conversation import topic_detector
from app.utils.cache import get_from_cache, add_to_cache
from app.models.base import ModelBackend

logger = logging.getLogger(__name__)
bp = Blueprint('routes', __name__)

@bp.route('/')
def index():
    return render_template('index.html')

# app/routes.py
@bp.route('/chat', methods=['POST'])
async def chat():
    user_message = request.json.get('message', '')
    conversation_stage = request.json.get('stage', 'greeting')
    has_image = request.json.get('has_image', False)  # Image flag from frontend
    image_data = request.json.get('image_data', None)  # Base64 encoded image if present

    cache_key = (user_message, conversation_stage, has_image)
    response_text = get_from_cache(cache_key)

    if not response_text:
        # Get the appropriate backend based on message content and presence of image
        backend = await get_model_backend(user_message, conversation_stage, has_image)

        try:
            # Format prompt differently based on whether there's an image
            if has_image and isinstance(backend, GeminiBackend):
                response_text = await backend.generate_multimodal_response(
                    user_message, conversation_stage, image_data
                )
            else:
                prompt = ModelBackend.format_prompt(user_message, conversation_stage)
                response_text = await backend.generate_response(prompt, conversation_stage)

            add_to_cache(cache_key, response_text)
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            response_text = "Sorry, I'm having trouble processing your request right now."

    next_stage = topic_detector.determine_next_stage(user_message, conversation_stage)

    return jsonify({
        'response': response_text,
        'next_stage': next_stage
    })

@bp.route('/feedback', methods=['POST'])
def feedback():
    user_message = request.json.get('message', '')
    rating = request.json.get('rating', 0)
    # Store feedback in a database or log for analysis
    logger.info(f"Feedback received for message '{user_message}': {rating}")
    return jsonify({"status": "success"})