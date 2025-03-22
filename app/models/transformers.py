import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Dict, Any, List

from app.config import Config
from app.models.base import ModelBackend

logger = logging.getLogger(__name__)


class TransformersBackend(ModelBackend):
    """Backend for HuggingFace Transformers pipeline with optimized resource usage."""

    def __init__(self):
        """Initialize the transformers pipeline with optimized memory usage."""
        self.pipeline = pipeline(
            "text-generation", 
            model="google/gemma-2b",
            low_cpu_mem_usage=True,
            device_map="auto"
        )
        self._pipeline = None
        self._executor = ThreadPoolExecutor(max_workers=2)
        self.model_info = {
            "name": "gemma-2b",
            "provider": "transformers",
            "version": "1.0"
        }
        self.available = False
        # Don't load model immediately - use lazy loading

    @property
    def pipeline(self):
        """Lazy-load the pipeline only when first needed."""
        if self._pipeline is None:
            try:
                from transformers import pipeline
                logger.info("Initializing Transformers backend with gemma-2b model")
                self._pipeline = pipeline(
                    "text-generation", 
                    model="google/gemma-2b",
                    low_cpu_mem_usage=True,
                    device_map="auto"  # Use GPU if available, otherwise CPU
                )
                self.available = True
                logger.info("Transformers backend initialized successfully")
            except ImportError:
                logger.warning("Transformers package not available")
                self.available = False
            except Exception as e:
                logger.error(f"Failed to initialize Transformers backend: {str(e)}")
                self.available = False
        return self._pipeline

    async def generate_response(self, prompt: str) -> str:
        """
        Generate a response using a Transformers pipeline.
        
        Runs the model in a separate thread to avoid blocking the event loop.
        """
        if not self.available or self.pipeline is None:
            raise RuntimeError("Transformers backend is not available")

        try:
            # Run CPU-intensive model inference in a thread pool
            response = await asyncio.get_event_loop().run_in_executor(
                self._executor,
                self._generate_text,
                prompt
            )
            return response
        except Exception as e:
            logger.error(f"Transformers pipeline error: {e}")
            # Return fallback response instead of raising to support hybrid model
            return "I'm unable to generate a response at the moment. Please try again later."
    
    def _generate_text(self, prompt: str) -> str:
        """Internal method to generate text with the pipeline."""
        generation_params = {
            "max_length": Config.MAX_TOKENS,
            "temperature": Config.TEMPERATURE,
            "top_p": Config.TOP_P,
            "top_k": Config.TOP_K,
            "do_sample": True,
            "num_return_sequences": 1,
        }
        
        result = self.pipeline(prompt, **generation_params)
        # Extract only the newly generated text (without the prompt)
        return result[0]['generated_text'][len(prompt):].strip()
            
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
        # Try to initialize if not already done
        if not self.available and self._pipeline is None:
            _ = self.pipeline
        return self.available
    
    def unload_model(self):
        """Explicitly unload model to free memory"""
        if self._pipeline is not None:
            # Clear pipeline reference
            self._pipeline = None
            # Force garbage collection
            import gc
            gc.collect()
            # Clear CUDA cache if available
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    logger.info("CUDA memory cache cleared")
            except ImportError:
                pass
            logger.info("Transformers model unloaded")
            self.available = False
            
    def __del__(self):
        """Clean up resources when object is deleted."""
        self.unload_model()
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=False)