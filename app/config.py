import os
import platform
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment configuration
class Config:
    # System settings
    IS_WINDOWS = platform.system() == "Windows"

    # API Keys
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

    # Ollama settings
    OLLAMA_URL = "http://localhost:11434/api/generate"
    OLLAMA_MODEL = "gemma:2b"

    # Model parameters
    TEMPERATURE = 0.7
    TOP_P = 0.95
    TOP_K = 64
    MAX_TOKENS = 1024

    # Cache settings
    CACHE_TTL = 600  # 10 minutes
    CACHE_MAXSIZE = 100

    # Topic detection settings
    SENTENCE_TRANSFORMER_MODEL = 'all-MiniLM-L6-v2'
    SIMILARITY_THRESHOLD = 0.35

    # Model selection config
    DEFAULT_MODEL = "gemma"  # Default fallback model

    # Model-specific configurations
    MODEL_CONFIGS = {
        "gemini-thinking": {
            "api_name": "gemini-2.0-flash-thinking-exp-01-21",
            "max_tokens": 1024,
            "temperature": 0.7
        },
        "gemma": {
            "api_name": "gemma:2b",  # For Ollama
            "transformers_name": "google/gemma-2b",  # For HuggingFace
            "max_tokens": 1024,
            "temperature": 0.6
        }
    }

    # Ollama availability settings
    OLLAMA_HEALTH_URL = "http://localhost:11434/"

    # Gemini rate limits
    GEMINI_DAILY_LIMIT = 50  # Requests per day
    GEMINI_RPM_LIMIT = 2     # Requests per minute