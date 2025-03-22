import logging
from typing import Optional, Dict, Any

from app.config import Config
from app.models.base import ModelBackend

logger = logging.getLogger(__name__)


class TransformersBackend(ModelBackend):
    """Backend for HuggingFace Transformers pipeline"""

    def __init__(self):
        self.pipeline = None
        self.model_info = {
            "name": "gemma-2b",
            "provider": "transformers",
            "version": "1.0"
        }
        try:
            from transformers import pipeline
            self.pipeline = pipeline("text-generation", model="google/gemma-2b")
            logger.info("Initialized Transformers backend with gemma-2b model")
            self.available = True
        except ImportError:
            logger.warning("Transformers package not available")
            self.available = False
        except Exception as e:
            logger.error(f"Failed to initialize Transformers backend: {str(e)}")
            self.available = False

    async def generate_response(self, prompt: str) -> str:
        """Generate a response using a Transformers pipeline"""
        if not self.available or not self.pipeline:
            raise RuntimeError("Transformers backend is not available")

        try:
            response = self.pipeline(
                prompt,
                max_length=Config.MAX_TOKENS,
                temperature=Config.TEMPERATURE,
                top_p=Config.TOP_P,
                top_k=Config.TOP_K,
                do_sample=True,
                num_return_sequences=1,
            )
            return response[0]['generated_text'][len(prompt):].strip()
        except Exception as e:
            logger.error(f"Transformers pipeline error: {e}")
            # Return fallback response instead of raising to support hybrid model
            return "I'm unable to generate a response at the moment. Please try again later."
            
    def get_info(self) -> Dict[str, Any]:
        """Get information about this model backend."""
        return {
            **self.model_info,
            "available": self.available,
            "max_tokens": Config.MAX_TOKENS,
            "features": ["text-generation"]
        }
    
    @property
    def is_available(self) -> bool:
        """Check if this backend is available."""
        return self.available
