# app/models/gemini.py
import base64
from venv import logger

from app.config import Config
from app.models.base import ModelBackend


class GeminiBackend(ModelBackend):
    """Backend for Google's Gemini API with multimodal support"""

    def __init__(self, model_name="gemini-2.0-flash-thinking-exp-01-21"):
        try:
            from google import generativeai as genai
            genai.configure(api_key=Config.GEMINI_API_KEY)
            self.genai = genai
            self.model = None
            self.model_name = model_name
            logger.info(f"Initialized Gemini backend with model {model_name}")
        except ImportError:
            logger.warning("Google Generative AI package not available")
            self.genai = None

    async def generate_response(self, prompt, conversation_stage):
        """Generate a text-only response using Gemini API"""
        if not self.genai:
            raise ImportError("Google Generative AI package not available")

        try:
            if not self.model:
                self.model = self.genai.GenerativeModel(self.model_name)

            generation_config = {
                "temperature": Config.TEMPERATURE,
                "top_p": Config.TOP_P,
                "top_k": Config.TOP_K,
                "max_output_tokens": Config.MAX_TOKENS,
            }

            response = self.model.generate_content(
                prompt,
                generation_config=generation_config
            )
            return response.text
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            raise

    async def generate_multimodal_response(self, user_message, conversation_stage, image_data):
        """Generate a response for text + image input"""
        if not self.genai:
            raise ImportError("Google Generative AI package not available")

        try:
            if not self.model:
                self.model = self.genai.GenerativeModel(self.model_name)

            generation_config = {
                "temperature": Config.TEMPERATURE,
                "top_p": Config.TOP_P,
                "top_k": Config.TOP_K,
                "max_output_tokens": Config.MAX_TOKENS,
            }

            # Process base64 image data
            if image_data and image_data.startswith('data:image'):
                # Extract the actual base64 data after the prefix
                image_data = image_data.split(',')[1]

            image_parts = [
                {
                    "mime_type": "image/jpeg",
                    "data": base64.b64decode(image_data)
                }
            ]

            # Create a prompt for the image analysis
            prompt = f"""
            You are an Opossum Information Assistant chatbot. 
            The user has provided an image related to opossums with this message: "{user_message}"
            The current conversation stage is: "{conversation_stage}"
            
            First, describe what you see in the image related to opossums.
            Then, respond to the user's query about the image in a helpful, conversational way.
            Keep responses relatively brief and focused on opossum information.
            """

            # Combine text and image in the request
            response = self.model.generate_content(
                [prompt, *image_parts],
                generation_config=generation_config
            )

            return response.text
        except Exception as e:
            logger.error(f"Gemini multimodal API error: {e}")
            raise
