"""Utility modules for the Opossum application.

This package provides utilities for:
- Image processing and effects
- SVG generation and rendering
- Service health monitoring
- Caching infrastructure
"""

from app.utils.health import get_service_metrics
from app.utils.infrastructure.cache import get_from_cache, add_to_cache
from app.utils.infrastructure.cache_config import CacheConfig
from app.utils.processing import ImageProcessor
from app.utils.svg import (
    SVGRenderer,
    extract_svg_from_text,
    process_llm_response,
    service_status_template,
    failover_process_template,
    capability_degradation_template
)

# Version information
__version__ = '1.0.0'

__all__ = [
    # Image processing
    'ImageProcessor',

    # Caching
    'get_from_cache',
    'add_to_cache',
    'CacheConfig',

    # Health monitoring
    'get_service_metrics',

    # SVG utilities
    'SVGRenderer',
    'extract_svg_from_text',
    'process_llm_response',
    'service_status_template',
    'failover_process_template',
    'capability_degradation_template'
]
