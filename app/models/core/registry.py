"""Registry system for model backends."""
import logging
from typing import Dict, Type, List, Optional, Set, Callable

from .types import BackendType

logger = logging.getLogger(__name__)


class ModelRegistry:
    """Registry for model backend classes."""
    
    # Dictionary mapping backend types to their classes
    _backend_classes: Dict[BackendType, Type] = {}
    
    @classmethod
    def register(cls, backend_type: BackendType, backend_class: Type) -> None:
        """Register a model backend class.
        
        Args:
            backend_type: The type identifier for the backend
            backend_class: The backend class to register
        """
        cls._backend_classes[backend_type] = backend_class
        logger.debug(f"Registered backend: {backend_type.name} -> {backend_class.__name__}")
    
    @classmethod
    def get_backend_class(cls, backend_type: BackendType) -> Optional[Type]:
        """Get the class for a backend type.
        
        Args:
            backend_type: The type identifier to look up
            
        Returns:
            The backend class or None if not found
        """
        return cls._backend_classes.get(backend_type)
    
    @classmethod
    def get_registered_backends(cls) -> List[BackendType]:
        """Get a list of all registered backend types.
        
        Returns:
            List of registered backend types
        """
        return list(cls._backend_classes.keys())
    
    @classmethod
    def is_registered(cls, backend_type: BackendType) -> bool:
        """Check if a backend type is registered.
        
        Args:
            backend_type: The type identifier to check
            
        Returns:
            Boolean indicating registration status
        """
        return backend_type in cls._backend_classes


def register_backend(backend_type: BackendType) -> Callable:
    """Decorator for registering model backends.
    
    Args:
        backend_type: The type identifier for the backend
        
    Returns:
        Decorator function that registers the decorated class
    """
    def decorator(cls):
        ModelRegistry.register(backend_type, cls)
        return cls
    return decorator