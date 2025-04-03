"""
Core model abstractions, factories, and type definitions.

This package provides the foundation for Opossum's model backend system,
including abstract interfaces, factory patterns, and dynamic registration.
"""

from .base import ModelBackend, AsyncModelBackend
from .factory import ModelFactory
from .registry import ModelRegistry
from .types import (
    BackendCapability, 
    ModelResponse, 
    ModelRequest,
    ErrorType,
    ModelParameters
)

__all__ = [
    'ModelBackend',
    'AsyncModelBackend',
    'ModelFactory',
    'ModelRegistry',
    'BackendCapability',
    'ModelResponse',
    'ModelRequest',
    'ErrorType',
    'ModelParameters'
]