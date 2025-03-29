"""Google Gemini model backend with multimodal capabilities."""
import base64
import logging
from typing import Dict, Any, Optional

from app.config import Config
from app.models.base import ModelBackend

logger = logging.getLogger(__name__)


class GeminiBackend(ModelBackend):
    """Backend for Google's Gemini API with multimodal support"""

    def __init__(self, model_name: str = "gemini-2.0-flash-thinking-exp-01-21"):
        """Initialize the Gemini backend.
        
        Args:
            model_name: The specific Gemini model to use
        """
        self.genai = None
        self.model = None
        self.model_name = model_name
        self.available = False
        self.model_info = {
            "name": model_name,
            "provider": "gemini",
            "version": "2.0"
        }

        try:
            from google import generativeai as genai
            genai.configure(api_key=Config.GEMINI_API_KEY)
            self.genai = genai
            # Test connection but don't initialize model yet (lazy loading)
            if Config.GEMINI_API_KEY and Config.GEMINI_API_KEY != "your-api-key-here":
                self.available = True
                logger.info(f"Initialized Gemini backend with model {model_name}")
            else:
                logger.warning("Gemini API key not configured properly")
                self.available = False
        except ImportError:
            logger.warning("Google Generative AI package not available")
            self.available = False
        except Exception as e:
            logger.error(f"Failed to initialize Gemini backend: {str(e)}")
            self.available = False
            
    def __repr__(self):
        """Return a string representation of the Gemini backend."""
        model_status = 'initialized' if self.model else 'not initialized'
        return f"GeminiBackend(model='{self.model_name}', available={self.available}, status={model_status})"

    async def generate_response(self, prompt: str, conversation_stage: Optional[str] = None) -> str:
        """Generate a text-only response using Gemini API.
        
        Args:
            prompt: The text prompt to send to the model
            conversation_stage: Optional conversation stage for context
            
        Returns:
            The generated text response
            
        Raises:
            RuntimeError: If the Gemini backend is not available
        """
        if not self.available or not self.genai:
            raise RuntimeError("Gemini API is not available")

        try:
            # Lazy initialization of the model
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
            logger.error(f"Gemini API error: {e}", exc_info=True)
            # Return fallback response instead of raising to support hybrid model
            return "I'm unable to generate a response at the moment. Please try again later."

    async def generate_multimodal_response(self,
                                           user_message: str,
                                           conversation_stage: Optional[str] = None,
                                           image_data: Optional[str] = None) -> str:
        """Generate a response for text + image input.
        
        Args:
            user_message: The user's text message
            conversation_stage: Optional conversation stage for context
            image_data: Base64-encoded image data with or without MIME prefix
            
        Returns:
            The generated text response
            
        Raises:
            RuntimeError: If the Gemini backend is not available
            ValueError: If the image data is invalid
        """
        if not self.available or not self.genai:
            raise RuntimeError("Gemini API is not available")

        if not image_data:
            # If no image is provided, fall back to text-only generation
            return await self.generate_response(user_message, conversation_stage)

        try:
            # Lazy initialization of the model
            if not self.model:
                self.model = self.genai.GenerativeModel(self.model_name)

            generation_config = {
                "temperature": Config.TEMPERATURE,
                "top_p": Config.TOP_P,
                "top_k": Config.TOP_K,
                "max_output_tokens": Config.MAX_TOKENS,
            }

            # Process base64 image data
            if image_data.startswith('data:image'):
                # Extract the actual base64 data after the prefix
                try:
                    image_data = image_data.split(',')[1]
                except IndexError:
                    raise ValueError("Invalid image data format")

            try:
                decoded_image = base64.b64decode(image_data)
            except Exception as e:
                logger.error(f"Failed to decode base64 image: {e}")
                raise ValueError("Invalid base64 image data")

            image_parts = [
                {
                    "mime_type": "image/jpeg",  # Assuming JPEG, might need detection
                    "data": decoded_image
                }
            ]

            # Create a prompt for the image analysis
            prompt = f"""
            You are an Opossum Information Assistant chatbot. 
            The user has provided an image related to opossums with this message: "{user_message}"
            The current conversation stage is: "{conversation_stage or 'general'}"
            
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
        except ValueError as ve:
            # Re-raise specific value errors for invalid inputs
            raise ve
        except Exception as e:
            logger.error(f"Gemini multimodal API error: {e}", exc_info=True)
            # Return fallback response instead of raising to support hybrid model
            return "I'm unable to analyze this image at the moment. Please try again later or try with a different image."

    def get_info(self) -> Dict[str, Any]:
        """Get information about this model backend.
        
        Returns:
            Dictionary with model information
        """
        return {
            **self.model_info,
            "available": self.available,
            "max_tokens": Config.MAX_TOKENS,
            "features": ["text-generation", "multimodal", "image-understanding"]
        }

    @property
    def is_available(self) -> bool:
        """Check if this backend is available.
        
        Returns:
            True if the backend is available, False otherwise
        """
        return self.available

    @property
    def supports_images(self) -> bool:
        """Check if this backend supports image inputs.
        
        Returns:
            True as Gemini supports multimodal inputs
        """
        return True
