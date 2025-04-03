"""Type definitions for model backends."""
import enum
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Union, TypedDict


class BackendType(enum.Enum):
    """Enum for backend types."""
    GEMINI = "gemini"
    OLLAMA = "ollama"
    TRANSFORMERS = "transformers"
    CHAT2SVG = "chat2svg"
    HYBRID = "hybrid"
    FALLBACK = "fallback"


class BackendCapability(enum.Enum):
    """Enum for model backend capabilities."""
    TEXT_GENERATION = "text_generation"
    IMAGE_UNDERSTANDING = "image_understanding"
    REASONING = "reasoning"
    SVG_GENERATION = "svg_generation"
    CODE_GENERATION = "code_generation"
    TOOL_USE = "tool_use"


class ErrorType(enum.Enum):
    """Enum for error types in model responses."""
    API_CONNECTION = "api_connection"
    RATE_LIMIT = "rate_limit"
    VALIDATION = "validation"
    PROCESSING_ERROR = "processing_error"
    TIMEOUT = "timeout"
    CONFIGURATION_ERROR = "configuration_error"
    SERVICE_UNAVAILABLE = "service_unavailable"
    UNKNOWN = "unknown"


@dataclass
class ModelParameters:
    """Parameters for model generation."""
    temperature: float = 0.7
    max_tokens: int = 1024
    top_p: float = 0.9
    top_k: int = 40
    conversation_stage: Optional[str] = None
    

@dataclass
class ModelResponse:
    """Model response container with metadata."""
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    error_type: Optional[ErrorType] = None
    
    @property
    def is_error(self) -> bool:
        """Check if this response represents an error."""
        return self.error is not None
    
    @classmethod
    def error(cls, error_message: str, error_type: ErrorType = ErrorType.UNKNOWN) -> 'ModelResponse':
        """Create an error response.
        
        Args:
            error_message: The error message
            error_type: The type of error
            
        Returns:
            ModelResponse instance representing an error
        """
        return cls(
            text="",
            error=error_message,
            error_type=error_type,
            metadata={"error": True, "error_type": error_type.value}
        )


# Type alias for model configuration
ModelConfig = Dict[str, Any]


class BackendUsageStats(TypedDict, total=False):
    """Usage statistics for a model backend."""
    total_tokens: int
    prompt_tokens: int
    completion_tokens: int
    processing_time: float
    request_timestamp: float
    success: bool