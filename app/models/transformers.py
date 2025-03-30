import asyncio
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, Optional, Union, Tuple

import torch

from app.config import Config
from app.models.base import ModelBackend

logger = logging.getLogger(__name__)


class TransformersBackend(ModelBackend):
    """Backend for HuggingFace Transformers pipeline with optimized resource usage."""

    def __init__(self):
        """Initialize the transformers backend with support for quantized models."""
        self._pipeline = None
        self._ort_session = None  # For ONNX Runtime session
        self._tokenizer = None
        self._executor = ThreadPoolExecutor(max_workers=2)
        self.model_info = {
            "name": "gemma-2b",
            "provider": "transformers",
            "version": "1.0"
        }
        self.available = False
        self.using_onnx = False
        
        # Quantization configuration
        self.use_quantized = Config.USE_QUANTIZED_MODELS if hasattr(Config, 'USE_QUANTIZED_MODELS') else True
        self.quantized_model_dir = Config.QUANTIZED_MODEL_DIR if hasattr(Config, 'QUANTIZED_MODEL_DIR') else os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
            "data", "quantized_models"
        )
        self.model_precision = Config.MODEL_PRECISION if hasattr(Config, 'MODEL_PRECISION') else "int8"
        self.validate_models = Config.VALIDATE_QUANTIZED_MODELS if hasattr(Config, 'VALIDATE_QUANTIZED_MODELS') else True
        
        # Don't load model immediately - use lazy loading

    @property
    def pipeline(self):
        """Lazy-load the pipeline or ONNX model only when first needed."""
        if self._pipeline is None and self._ort_session is None:
            try:
                # Try to load quantized ONNX model first if enabled
                if self.use_quantized and self._try_load_onnx_model():
                    self.available = True
                    self.using_onnx = True
                    logger.info("ONNX model initialized successfully")
                else:
                    # Fall back to standard Transformers pipeline
                    from transformers import pipeline
                    logger.info("Initializing standard Transformers backend with gemma-2b model")
                    self._pipeline = pipeline(
                        "text-generation",
                        model="google/gemma-2b",
                        low_cpu_mem_usage=True,
                        device_map="auto"  # Use GPU if available, otherwise CPU
                    )
                    self.available = True
                    self.using_onnx = False
                    logger.info("Standard Transformers backend initialized successfully")
                    
                if self.validate_models and self.available:
                    self._validate_model()
                    
            except ImportError as e:
                logger.warning(f"Package not available: {str(e)}")
                self.available = False
            except Exception as e:
                logger.error(f"Failed to initialize model backend: {str(e)}", exc_info=True)
                self.available = False
                
        return self._pipeline

    def _try_load_onnx_model(self) -> bool:
        """
        Try to load the optimized ONNX model.
        
        Returns:
            bool: True if ONNX model was loaded successfully, False otherwise
        """
        try:
            import onnxruntime as ort
            from transformers import AutoTokenizer
            
            # Construct path to the quantized model
            model_name = "google_gemma-2b"  # Match the sanitized name in quantize_models.py
            precision = self.model_precision
            model_dir = os.path.join(self.quantized_model_dir, model_name)
            
            # For fp16 models, the path is slightly different
            if precision == "fp16":
                onnx_dir = os.path.join(model_dir, "onnx_fp32")  # fp16 export is done during the initial export
            else:
                onnx_dir = os.path.join(model_dir, f"onnx_{precision}")
            
            # Check if model exists
            if not os.path.exists(onnx_dir):
                logger.warning(f"Quantized ONNX model not found at {onnx_dir}")
                return False
                
            # Find model.onnx file
            model_file = os.path.join(onnx_dir, "model.onnx")
            if not os.path.exists(model_file):
                logger.warning(f"model.onnx not found in {onnx_dir}")
                return False
                
            # Load tokenizer - use the original model ID for tokenizer
            self._tokenizer = AutoTokenizer.from_pretrained("google/gemma-2b")
            
            # Configure ONNX Runtime session
            sess_options = ort.SessionOptions()
            sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            
            # Create session - use CPU or CUDA provider based on availability
            providers = ['CUDAExecutionProvider', 'CPUExecutionProvider'] if torch.cuda.is_available() else ['CPUExecutionProvider']
            self._ort_session = ort.InferenceSession(model_file, sess_options, providers=providers)
            
            logger.info(f"Successfully loaded ONNX model from {onnx_dir} with precision {precision}")
            return True
            
        except ImportError as e:
            logger.warning(f"Cannot load ONNX model, missing dependency: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error loading ONNX model: {str(e)}", exc_info=True)
            return False

    def _validate_model(self):
        """Validate that the model produces reasonable outputs."""
        try:
            test_prompt = "Hello, how are you today?"
            logger.info("Validating model with test prompt")
            
            result = self._generate_text(test_prompt)
            
            # Basic validation: check if response is non-empty and reasonably long
            if result and len(result) > 10:
                logger.info("Model validation successful")
                return True
            else:
                logger.warning(f"Model validation produced a suspiciously short response: '{result}'")
                return False
                
        except Exception as e:
            logger.error(f"Model validation failed: {str(e)}")
            return False

    async def generate_response(self, prompt: str) -> str:
        """
        Generate a response using either the ONNX model or Transformers pipeline.
        
        Runs the model in a separate thread to avoid blocking the event loop.
        """
        # Ensure the model is loaded (calls pipeline property)
        _ = self.pipeline
        
        if not self.available:
            raise RuntimeError("Model backend is not available")

        try:
            # Run CPU-intensive model inference in a thread pool
            response = await asyncio.get_event_loop().run_in_executor(
                self._executor,
                self._generate_text,
                prompt
            )
            return response
        except Exception as e:
            logger.error(f"Model inference error: {e}")
            # Return fallback response instead of raising to support hybrid model
            return "I'm unable to generate a response at the moment. Please try again later."

    def _generate_text(self, prompt: str) -> str:
        """Internal method to generate text with either ONNX or pipeline."""
        generation_params = {
            "max_length": Config.MAX_TOKENS,
            "temperature": Config.TEMPERATURE,
            "top_p": Config.TOP_P,
            "top_k": Config.TOP_K,
            "do_sample": True,
            "num_return_sequences": 1,
        }

        if self.using_onnx:
            return self._generate_text_onnx(prompt, **generation_params)
        else:
            # Use standard pipeline
            result = self._pipeline(prompt, **generation_params)
            # Extract only the newly generated text (without the prompt)
            return result[0]['generated_text'][len(prompt):].strip()
            
    def _generate_text_onnx(self, prompt: str, **kwargs) -> str:
        """Generate text using the ONNX runtime model."""
        try:
            import numpy as np
            
            # Tokenize the input
            inputs = self._tokenizer(prompt, return_tensors="np")
            
            # Prepare input dictionary for ONNX
            ort_inputs = {
                "input_ids": inputs["input_ids"].astype(np.int64),
                "attention_mask": inputs["attention_mask"].astype(np.int64)
            }
            
            # Add generation parameters
            max_length = kwargs.get("max_length", 100)
            
            # Run inference with the ONNX model
            # Note: Actual implementation may vary based on the exported model's expected inputs
            outputs = self._ort_session.run(None, ort_inputs)
            
            # Process outputs
            generated_tokens = outputs[0]
            generated_text = self._tokenizer.decode(generated_tokens[0], skip_special_tokens=True)
            
            # Return only the newly generated text
            return generated_text[len(prompt):].strip()
            
        except Exception as e:
            logger.error(f"ONNX inference error: {str(e)}", exc_info=True)
            # Fall back to standard pipeline if available
            if self._pipeline is not None:
                logger.info("Falling back to standard pipeline after ONNX error")
                self.using_onnx = False
                return self._pipeline(prompt, **kwargs)[0]['generated_text'][len(prompt):].strip()
            else:
                raise e

    def get_info(self) -> Dict[str, Any]:
        """Get information about this model backend."""
        # Ensure the model is loaded for accurate info
        _ = self.pipeline
        
        return {
            **self.model_info,
            "available": self.available,
            "max_tokens": Config.MAX_TOKENS,
            "features": ["text-generation"],
            "using_quantized": self.using_onnx,
            "model_precision": self.model_precision if self.using_onnx else "fp32"
        }

    @property
    def is_available(self) -> bool:
        """Check if this backend is available."""
        # Try to initialize if not already done
        if not self.available and self._pipeline is None and self._ort_session is None:
            _ = self.pipeline
        return self.available

    def unload_model(self):
        """Explicitly unload model to free memory"""
        if self._pipeline is not None or self._ort_session is not None:
            # Clear references
            self._pipeline = None
            self._ort_session = None
            self._tokenizer = None
            
            # Force garbage collection
            import gc
            gc.collect()
            
            # Clear CUDA cache if available
            try:
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    logger.info("CUDA memory cache cleared")
            except Exception:
                pass
                
            logger.info("Model unloaded")
            self.available = False

    def __del__(self):
        """Clean up resources when object is deleted."""
        self.unload_model()
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=False)
