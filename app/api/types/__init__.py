"""Common GraphQL types that can be reused across schema files."""
import json
from datetime import datetime
from typing import Dict, Any, List, Optional

import graphene


class Timestamp(graphene.ObjectType):
    """Standardized timestamp representation."""
    iso_string = graphene.String(description="ISO8601 formatted timestamp")
    unix_timestamp = graphene.Int(description="Unix timestamp (seconds since epoch)")

    @staticmethod
    def from_datetime(dt: datetime) -> Dict[str, Any]:
        """Create timestamp from datetime object."""
        return {
            "iso_string": dt.isoformat() if dt else None,
            "unix_timestamp": int(dt.timestamp()) if dt else None
        }


class PaginationInput(graphene.InputObjectType):
    """Standard pagination input for queries."""
    page = graphene.Int(default_value=1, description="Page number (starting from 1)")
    page_size = graphene.Int(default_value=25, description="Items per page")


class PageInfo(graphene.ObjectType):
    """Pagination information for collections."""
    has_next_page = graphene.Boolean(description="Whether there are more items after this page")
    has_previous_page = graphene.Boolean(description="Whether there are items before this page")
    total_count = graphene.Int(description="Total number of items across all pages")
    page_count = graphene.Int(description="Total number of pages")
    current_page = graphene.Int(description="Current page number")
    page_size = graphene.Int(description="Items per page")


class Error(graphene.ObjectType):
    """Standard error representation."""
    message = graphene.String(description="Human-readable error message")
    code = graphene.String(description="Error code for client handling")
    path = graphene.List(graphene.String, description="Path to the error in the query")

    @staticmethod
    def create(message: str, code: str = "UNKNOWN_ERROR", path: Optional[List[str]] = None) -> Dict[str, Any]:
        """Create standardized error object."""
        return {
            "message": message,
            "code": code,
            "path": path or []
        }


class JSONScalar(graphene.Scalar):
    """Custom scalar for handling arbitrary JSON data."""

    @staticmethod
    def serialize(value):
        """Convert value to JSON-compatible format."""
        if isinstance(value, (dict, list)):
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except:
                return value
        return str(value)

    @staticmethod
    def parse_literal(ast):
        """Parse GraphQL AST node to Python representation."""
        if isinstance(ast, StringValue):
            try:
                return json.loads(ast.value)
            except:
                return ast.value
        return None

    @staticmethod
    def parse_value(value):
        """Parse variable values to Python representation."""
        if isinstance(value, str):
            try:
                return json.loads(value)
            except:
                return value
        return value


class ModelInfo(graphene.ObjectType):
    """Information about an AI model."""
    name = graphene.String(description="Model identifier")
    provider = graphene.String(description="Service provider (e.g., 'gemini', 'ollama')")
    available = graphene.Boolean(description="Whether the model is currently available")
    capabilities = graphene.List(graphene.String, description="Model capabilities")
    max_tokens = graphene.Int(description="Maximum token count for responses")
    context_length = graphene.Int(description="Maximum token count for context")

    @staticmethod
    def from_config(name: str, config: Dict[str, Any], available: bool = True) -> Dict[str, Any]:
        """Create model info from configuration."""
        capabilities = []
        if "multimodal" in config.get("features", []):
            capabilities.append("IMAGE_PROCESSING")
        if "streaming" in config.get("features", []):
            capabilities.append("STREAMING")

        return {
            "name": name,
            "provider": config.get("provider", "unknown"),
            "available": available,
            "capabilities": capabilities,
            "max_tokens": config.get("max_tokens", 1024),
            "context_length": config.get("context_length", 4096)
        }


__all__ = [
    'Timestamp',
    'PaginationInput',
    'PageInfo',
    'Error',
    'JSONScalar',
    'ModelInfo'
]
