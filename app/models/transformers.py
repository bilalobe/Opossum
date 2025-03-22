import logging
from app.models.base import ModelBackend
from app.config import Config

logger = logging.getLogger(__name__)

class TransformersBackend(ModelBackend):
    """Backend for HuggingFace Transformers pipeline"""

    def __init__(self):
        try:
            from transformers import pipeline
            self.pipeline = pipeline("text-generation", model="google/gemma-2b")
            logger.info("Initialized Transformers backend")
        except ImportError:
            logger.warning("Transformers package not available")
            self.pipeline = None

    async def generate_response(self, prompt):
        """Generate a response using a Transformers pipeline"""
        if not self.pipeline:
            raise ImportError("Transformers package not available")

        try:
            response = self.pipeline(
                prompt,
                max_length=1024,
                temperature=Config.TEMPERATURE,
                top_p=Config.TOP_P,
                top_k=Config.TOP_K,
                do_sample=True,
                num_return_sequences=1,
            )
            return response[0]['generated_text'][len(prompt):].strip()
        except Exception as e:
            logger.error(f"Transformers pipeline error: {e}")
            raise