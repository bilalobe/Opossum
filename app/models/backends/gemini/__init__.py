"""Gemini API backend implementation for Opossum Search."""

from .client import GeminiClient
from .processor import GeminiResponseProcessor
from .prompt import PromptManager, PromptTemplate

# Main export for convenient imports
from .backend import GeminiBackend

__all__ = [
    'GeminiBackend',
    'GeminiClient',
    'GeminiResponseProcessor',
    'PromptManager',
    'PromptTemplate'
]