import logging
import os
import platform
import tempfile
from typing import List, Dict

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BaseConfig:
    """Base configuration class with common settings."""
    # System settings
    IS_WINDOWS = platform.system() == "Windows"
    ENV = os.getenv("FLASK_ENV", "development")

    # API Keys
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    APOLLO_KEY = os.getenv("APOLLO_KEY")

    # Ollama settings
    OLLAMA_HOST = os.getenv("OLLAMA_HOST", "localhost")
    OLLAMA_PORT = int(os.getenv("OLLAMA_PORT", "11434"))
    OLLAMA_BASE_URL = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}"
    OLLAMA_URL = f"{OLLAMA_BASE_URL}/api/generate"
    OLLAMA_HEALTH_URL = OLLAMA_BASE_URL
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma:1b")
    LLAVA_MODEL = os.getenv("LLAVA_MODEL", "llava")
    MINILM_MODEL = os.getenv("MINILM_MODEL", "all-minilm")

    # Model parameters
    TEMPERATURE = float(os.getenv("TEMPERATURE", "0.7"))
    TOP_P = float(os.getenv("TOP_P", "0.95"))
    TOP_K = int(os.getenv("TOP_K", "64"))
    MAX_TOKENS = int(os.getenv("MAX_TOKENS", "1024"))

    # Cache settings
    CACHE_TTL = int(os.getenv("CACHE_TTL", "600"))  # 10 minutes
    CACHE_MAXSIZE = int(os.getenv("CACHE_MAXSIZE", "100"))
    AVAILABILITY_CACHE_TTL = int(os.getenv("AVAILABILITY_CACHE_TTL", "30"))  # seconds
    AVAILABILITY_CHECK_INTERVAL = int(os.getenv("AVAILABILITY_CHECK_INTERVAL", "30"))
    MODEL_SELECTION_CACHE_TTL = int(os.getenv("MODEL_SELECTION_CACHE_TTL", "60"))
    PREWARM_GEMINI = os.getenv("PREWARM_GEMINI", "True").lower() == "true"

    # Topic detection settings
    SENTENCE_TRANSFORMER_MODEL = os.getenv("SENTENCE_TRANSFORMER_MODEL", "all-MiniLM-L6-v2")
    SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.35"))

    # Default model configuration
    DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gemma")  # Default fallback model
    MULTIMODAL_FALLBACK_ORDER = os.getenv("MULTIMODAL_FALLBACK_ORDER", "gemini,llava,text-only").split(",")

    # Model-specific configurations
    MODEL_CONFIGS = {
        "gemini-thinking": {
            "api_name": os.getenv("GEMINI_MODEL_NAME", "gemini-2.0-flash"),
            "max_tokens": int(os.getenv("GEMINI_MAX_TOKENS", "1048576")),
            "temperature": float(os.getenv("GEMINI_TEMPERATURE", "1.2"))
        },
        "gemma": {
            "api_name": os.getenv("GEMMA_OLLAMA_MODEL", "gemma:1b"),
            "transformers_name": os.getenv("GEMMA_TRANSFORMERS_MODEL", "google/gemma-2b"),
            "max_tokens": int(os.getenv("GEMMA_MAX_TOKENS", "4096")),
            "temperature": float(os.getenv("GEMMA_TEMPERATURE", "0.6"))
        }
    }

    # Service monitoring settings
    SERVICE_HISTORY_MAX_ITEMS = int(os.getenv("SERVICE_HISTORY_MAX_ITEMS", "100"))
    GEMINI_DAILY_TOKEN_LIMIT = int(os.getenv("GEMINI_DAILY_TOKEN_LIMIT", "1000000"))
    GEMINI_DAILY_LIMIT = int(os.getenv("GEMINI_DAILY_LIMIT", "50"))
    GEMINI_RPM_LIMIT = int(os.getenv("GEMINI_RPM_LIMIT", "2"))

    # Redis Configuration
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB = int(os.getenv("REDIS_DB", "0"))
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
    REDIS_TTL = int(os.getenv("REDIS_TTL", "600"))

    # OpenTelemetry Configuration
    OTEL_EXPORTER_OTLP_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318/v1/traces")
    OTEL_SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "opossum-search")
    OTEL_ENABLED = os.getenv("OTEL_ENABLED", "True").lower() == "true"

    # GraphQL Configuration
    GRAPHQL_ENDPOINT = os.getenv("GRAPHQL_ENDPOINT", "/graphql")
    GRAPHQL_GRAPHIQL = os.getenv("GRAPHQL_GRAPHIQL", "True").lower() == "true"
    GRAPHQL_BATCH = os.getenv("GRAPHQL_BATCH", "True").lower() == "true"
    GRAPHQL_PRETTY = os.getenv("GRAPHQL_PRETTY", "True").lower() == "true"
    GRAPHQL_COMPLEXITY_THRESHOLD = int(os.getenv("GRAPHQL_COMPLEXITY_THRESHOLD", "100"))
    GRAPHQL_DEPTH_LIMIT = int(os.getenv("GRAPHQL_DEPTH_LIMIT", "10"))

    # Apollo Studio Configuration
    APOLLO_STUDIO_ENABLED = os.getenv("APOLLO_STUDIO_ENABLED", "True").lower() == "true"
    APOLLO_GRAPH_REF = os.getenv("APOLLO_GRAPH_REF", "opossum-search@current")
    APOLLO_SCHEMA_REPORTING = os.getenv("APOLLO_SCHEMA_REPORTING", "True").lower() == "true"
    APOLLO_INCLUDE_TRACES = os.getenv("APOLLO_INCLUDE_TRACES", "True").lower() == "true"

    # GraphQL Voyager Configuration
    VOYAGER_ENABLED = os.getenv("VOYAGER_ENABLED", "True").lower() == "true"
    VOYAGER_ENDPOINT = os.getenv("VOYAGER_ENDPOINT", "/voyager")
    VOYAGER_PATH = os.getenv("VOYAGER_PATH", "voyager.html")

    # CORS Settings for GraphQL
    CORS_ALLOWED_ORIGINS = os.getenv("CORS_ALLOWED_ORIGINS",
                                     "http://localhost:5000,https://studio.apollographql.com").split(",")
    CORS_ALLOW_CREDENTIALS = os.getenv("CORS_ALLOW_CREDENTIALS", "True").lower() == "true"
    CORS_ALLOW_HEADERS = os.getenv("CORS_ALLOW_HEADERS", "Content-Type,Authorization,apollo-require-preflight").split(
        ",")
    CORS_EXPOSE_HEADERS = os.getenv("CORS_EXPOSE_HEADERS", "X-Rate-Limit").split(",")

    # Response Compression
    COMPRESS_ALGORITHM = os.getenv("COMPRESS_ALGORITHM", "br,gzip,deflate").split(",")
    COMPRESS_LEVEL = int(os.getenv("COMPRESS_LEVEL", "6"))
    COMPRESS_MIN_SIZE = int(os.getenv("COMPRESS_MIN_SIZE", "500"))

    # GraphQL Rate Limiting - defining as a class method to handle the complex structure
    @classmethod
    def get_rate_limits(cls) -> Dict[str, List[str]]:
        default_limits = os.getenv("RATE_LIMIT_DEFAULT", "200 per day,50 per hour").split(",")
        complex_limits = os.getenv("RATE_LIMIT_COMPLEX", "100 per day,20 per hour").split(",")
        mutation_limits = os.getenv("RATE_LIMIT_MUTATION", "50 per day,10 per hour").split(",")

        return {
            "default": default_limits,
            "complex_query": complex_limits,
            "mutation": mutation_limits
        }

    GRAPHQL_RATE_LIMIT = get_rate_limits.__func__()

    # Query cost map 
    GRAPHQL_COST_MAP = {
        "Query": {
            "service_status": int(os.getenv("COST_SERVICE_STATUS", "5")),
            "generate_gibberish": int(os.getenv("COST_GENERATE_GIBBERISH", "2"))
        },
        "Mutation": {
            "chat": int(os.getenv("COST_CHAT", "10")),
            "process_image": int(os.getenv("COST_PROCESS_IMAGE", "15")),
            "force_service_check": int(os.getenv("COST_FORCE_SERVICE_CHECK", "5"))
        }
    }

    # Security settings
    API_KEY_REQUIRED = os.getenv("API_KEY_REQUIRED", "False").lower() == "true"
    API_KEY = os.getenv("API_KEY", "")  # Should be set in production

    # Chat2SVG Integration Config
    CHAT2SVG_ENABLED = os.getenv("CHAT2SVG_ENABLED", "true").lower() == "true"
    CHAT2SVG_DETAIL_ENHANCEMENT = os.getenv("CHAT2SVG_DETAIL_ENHANCEMENT", "false").lower() == "true"
    CHAT2SVG_PATH = os.getenv(
        "CHAT2SVG_PATH", 
        os.path.join(os.path.expanduser("~"), ".local", "share", "chat2svg")
    )
    if not os.path.exists(CHAT2SVG_PATH):
        logger.warning(f"CHAT2SVG_PATH does not exist or is inaccessible: {CHAT2SVG_PATH}")
        if BaseConfig.ENV != "production":
            # Create directory structure only in non-production environments
            try:
                os.makedirs(CHAT2SVG_PATH, exist_ok=True)
                logger.info(f"Created Chat2SVG directory at: {CHAT2SVG_PATH}")
            except Exception as e:
                logger.error(f"Failed to create Chat2SVG directory: {e}")
                
    # Additional Chat2SVG Configuration
    CHAT2SVG_CACHE_TTL = int(os.getenv("CHAT2SVG_CACHE_TTL", "3600"))  # 1 hour
    CHAT2SVG_CACHE_MAXSIZE = int(os.getenv("CHAT2SVG_CACHE_MAXSIZE", "50"))
    CHAT2SVG_OUTPUT_DIR = os.getenv("CHAT2SVG_OUTPUT_DIR", os.path.join(CHAT2SVG_PATH, 'output'))
    CHAT2SVG_TEMP_DIR = os.getenv("CHAT2SVG_TEMP_DIR", tempfile.gettempdir())
    
    # SVG Generation Settings
    CHAT2SVG_DEFAULT_STYLE = os.getenv("CHAT2SVG_DEFAULT_STYLE", "modern")
    CHAT2SVG_DEFAULT_THEME = os.getenv("CHAT2SVG_DEFAULT_THEME", "light")
    CHAT2SVG_DEFAULT_COLOR_PALETTE = os.getenv("CHAT2SVG_DEFAULT_COLOR_PALETTE", "default")
    CHAT2SVG_MAX_SVG_SIZE = int(os.getenv("CHAT2SVG_MAX_SVG_SIZE", "1024"))  # Maximum dimension in pixels
    
    # Performance and Resource Settings
    CHAT2SVG_MAX_PROMPT_LENGTH = int(os.getenv("CHAT2SVG_MAX_PROMPT_LENGTH", "500"))
    CHAT2SVG_TIMEOUT = int(os.getenv("CHAT2SVG_TIMEOUT", "60"))  # Timeout in seconds
    CHAT2SVG_RESOURCE_MODE = os.getenv("CHAT2SVG_RESOURCE_MODE", "adaptive")  # "adaptive", "high", "medium", "low", "minimal"
    
    # Resource thresholds for adaptive mode
    CHAT2SVG_RESOURCE_THRESHOLDS = {
        "high": {
            "cpu_percent_available": int(os.getenv("CHAT2SVG_HIGH_CPU_THRESHOLD", "50")),  # At least 50% CPU available
            "memory_percent_available": int(os.getenv("CHAT2SVG_HIGH_MEMORY_THRESHOLD", "40")),  # At least 40% memory available
            "detail_level": "high",
        },
        "medium": {
            "cpu_percent_available": int(os.getenv("CHAT2SVG_MEDIUM_CPU_THRESHOLD", "30")),
            "memory_percent_available": int(os.getenv("CHAT2SVG_MEDIUM_MEMORY_THRESHOLD", "20")),
            "detail_level": "medium",
        },
        "low": {
            "cpu_percent_available": int(os.getenv("CHAT2SVG_LOW_CPU_THRESHOLD", "10")),
            "memory_percent_available": int(os.getenv("CHAT2SVG_LOW_MEMORY_THRESHOLD", "10")),
            "detail_level": "low",
        },
        "minimal": {
            "cpu_percent_available": int(os.getenv("CHAT2SVG_MINIMAL_CPU_THRESHOLD", "0")),
            "memory_percent_available": int(os.getenv("CHAT2SVG_MINIMAL_MEMORY_THRESHOLD", "0")),
            "detail_level": "minimal",
        }
    }
    
    # Advanced SVG Optimization Settings
    CHAT2SVG_OPTIMIZATION_LEVEL = int(os.getenv("CHAT2SVG_OPTIMIZATION_LEVEL", "2"))  # 1-3, higher is more intensive
    CHAT2SVG_PATH_SIMPLIFICATION = float(os.getenv("CHAT2SVG_PATH_SIMPLIFICATION", "0.2"))  # 0.0-1.0
    CHAT2SVG_ENABLE_ANIMATIONS = os.getenv("CHAT2SVG_ENABLE_ANIMATIONS", "false").lower() == "true"


class DevelopmentConfig(BaseConfig):
    """Development configuration."""
    DEBUG = True
    TESTING = False
    GRAPHQL_GRAPHIQL = True
    VOYAGER_ENABLED = True
    # In development, we can use a local path for easier debugging
    CHAT2SVG_PATH = os.getenv(
        "CHAT2SVG_PATH", 
        os.path.join(os.path.dirname(os.path.dirname(__file__)), 'Chat2SVG-main')
    )


class TestingConfig(BaseConfig):
    """Testing configuration."""
    DEBUG = False
    TESTING = True
    GRAPHQL_GRAPHIQL = False
    VOYAGER_ENABLED = False
    # Use lightweight model configurations for testing
    PREWARM_GEMINI = False
    # Disable Chat2SVG in testing by default unless explicitly enabled
    CHAT2SVG_ENABLED = os.getenv("CHAT2SVG_ENABLED", "false").lower() == "true"


class ProductionConfig(BaseConfig):
    """Production configuration."""
    DEBUG = False
    TESTING = False
    GRAPHQL_GRAPHIQL = False
    VOYAGER_ENABLED = False
    API_KEY_REQUIRED = True
    # Require more secure settings
    CORS_ALLOWED_ORIGINS = os.getenv("CORS_ALLOWED_ORIGINS", "").split(",")
    # In production, Chat2SVG should be installed properly in a system path
    CHAT2SVG_PATH = os.getenv(
        "CHAT2SVG_PATH", 
        "/opt/chat2svg"
    )
    # Set to false by default in production - must be explicitly enabled
    CHAT2SVG_ENABLED = os.getenv("CHAT2SVG_ENABLED", "false").lower() == "true"

    # Model Quantization Settings
    MODEL_QUANTIZATION_ENABLED = os.getenv("MODEL_QUANTIZATION_ENABLED", "true").lower() == "true"
    MODEL_QUANTIZATION_PRECISION = os.getenv("MODEL_QUANTIZATION_PRECISION", "int8")  # fp32, fp16, int8
    QUANTIZED_MODEL_DIR = os.getenv(
        "QUANTIZED_MODEL_DIR",
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "quantized_models")
    )
    
    # Transformers Quantization
    TRANSFORMERS_CACHE = os.getenv(
        "TRANSFORMERS_CACHE",
        os.path.join(os.path.expanduser("~"), ".cache", "huggingface", "hub")
    )
    TRANSFORMERS_FORCE_CPU = os.getenv("TRANSFORMERS_FORCE_CPU", "false").lower() == "true"
    
    # Chat2SVG Quantization
    CHAT2SVG_QUANTIZE_MODELS = os.getenv("CHAT2SVG_QUANTIZE_MODELS", "true").lower() == "true"
    CHAT2SVG_QUANTIZATION_PRECISION = os.getenv("CHAT2SVG_QUANTIZATION_PRECISION", "fp16")  # fp32 or fp16 only

    @classmethod
    def get_quantization_config(cls):
        """Get model quantization configuration."""
        return {
            "enabled": cls.MODEL_QUANTIZATION_ENABLED,
            "precision": cls.MODEL_QUANTIZATION_PRECISION,
            "transformers_cache": cls.TRANSFORMERS_CACHE,
            "chat2svg_path": cls.CHAT2SVG_PATH,
            "output_dir": cls.QUANTIZED_MODEL_DIR,
            "force_cpu": cls.TRANSFORMERS_FORCE_CPU,
        }
