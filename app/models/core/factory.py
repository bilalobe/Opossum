"""Factory for creating model backends."""
import logging
from typing import Dict, Any, Optional, Type

from app.config import Config
from .registry import ModelRegistry
from .base import ModelBackend
from .types import BackendType, ModelConfig

logger = logging.getLogger(__name__)


class ModelFactory:
    """Factory for creating model backend instances."""
    
    @classmethod
    def create_backend(cls, backend_type: BackendType, 
                     config: Optional[ModelConfig] = None) -> Optional[ModelBackend]:
        """Create a model backend instance.
        
        Args:
            backend_type: The type of backend to create
            config: Optional configuration for the backend
            
        Returns:
            ModelBackend instance or None if creation fails
        """
        backend_class = ModelRegistry.get_backend_class(backend_type)
        
        if not backend_class:
            logger.error(f"No backend registered for type: {backend_type}")
            return None
        
        try:
            if config:
                return backend_class(**config)
            else:
                return backend_class()
        except Exception as e:
            logger.error(f"Failed to create backend {backend_type}: {e}", exc_info=True)
            return None
    
    @classmethod
    def create_all_backends(cls) -> Dict[BackendType, ModelBackend]:
        """Create all registered backend instances.
        
        Returns:
            Dictionary mapping backend types to instances
        """
        backends = {}
        for backend_type in ModelRegistry.get_registered_backends():
            # Get config if available
            config = cls._get_config_for_backend(backend_type)
            
            # Create backend
            backend = cls.create_backend(backend_type, config)
            if backend:
                backends[backend_type] = backend
                
        return backends
    
    @classmethod
    def _get_config_for_backend(cls, backend_type: BackendType) -> Optional[ModelConfig]:
        """Get configuration for a specific backend type.
        
        Args:
            backend_type: The backend type to get config for
            
        Returns:
            Configuration dictionary or None
        """
        # Convert BackendType enum to string for config lookup
        backend_name = backend_type.name.lower()
        
        # Look up config in app config
        if hasattr(Config, f"{backend_name.upper()}_CONFIG"):
            return getattr(Config, f"{backend_name.upper()}_CONFIG")
            
        # Check MODEL_CONFIGS dictionary
        if hasattr(Config, "MODEL_CONFIGS") and backend_name in Config.MODEL_CONFIGS:
            return Config.MODEL_CONFIGS[backend_name]
            
        return None