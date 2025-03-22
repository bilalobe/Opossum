import logging
import os
import platform

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
    GEMINI_RPM_LIMIT = 2  # Requests per minute

    # Redis Configuration
    REDIS_HOST = "localhost"
    REDIS_PORT = 6379
    REDIS_DB = 0
    REDIS_TTL = 600  # 10 minutes cache TTL

    # GraphQL Configuration
    GRAPHQL_ENDPOINT = "/graphql"
    GRAPHQL_GRAPHIQL = True  # Enable GraphiQL interface for development
    GRAPHQL_BATCH = True  # Enable batch queries
    GRAPHQL_PRETTY = True  # Pretty print JSON responses

    # Apollo Studio Configuration
    APOLLO_STUDIO_ENABLED = True
    APOLLO_KEY = os.environ.get("APOLLO_KEY")  # Required for schema reporting
    APOLLO_GRAPH_REF = "opossum-search@current"
    APOLLO_SCHEMA_REPORTING = True
    APOLLO_INCLUDE_TRACES = True

    # GraphQL Voyager Configuration
    VOYAGER_ENABLED = True
    VOYAGER_ENDPOINT = "/voyager"
    VOYAGER_PATH = "voyager.html"

    # CORS Settings for GraphQL
    CORS_ALLOWED_ORIGINS = ["http://localhost:5000", "https://studio.apollographql.com"]
    CORS_ALLOW_CREDENTIALS = True
    CORS_ALLOW_HEADERS = ["Content-Type", "Authorization", "apollo-require-preflight"]
    CORS_EXPOSE_HEADERS = ["X-Rate-Limit"]

    # Response Compression
    COMPRESS_ALGORITHM = ["br", "gzip", "deflate"]
    COMPRESS_LEVEL = 6
    COMPRESS_MIN_SIZE = 500

    # GraphQL Rate Limiting
    GRAPHQL_RATE_LIMIT = {
        "default": ["200 per day", "50 per hour"],
        "complex_query": ["100 per day", "20 per hour"],
        "mutation": ["50 per day", "10 per hour"]
    }
    GRAPHQL_COMPLEXITY_THRESHOLD = 100
    GRAPHQL_DEPTH_LIMIT = 10
    GRAPHQL_COST_MAP = {
        "Query": {
            "service_status": 5,
            "generate_gibberish": 2
        },
        "Mutation": {
            "chat": 10,
            "process_image": 15,
            "force_service_check": 5
        }
    }
