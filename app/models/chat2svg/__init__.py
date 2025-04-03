"""SVG generation pipeline with hybrid optimization."""
from .api import generate_svg_request
from .pipeline import PipelineState, PipelineError
from .monitoring.circuit_breaker import CircuitBreaker
from .monitoring.metrics import SolverMetrics
from .monitoring.resources import ResourceMonitor
from .optimizer.hybrid import HybridOptimizer
from .optimizer.fallback import GreedyFallback
from .sensitivity.analyzer import SensitivityAnalyzer

__all__ = [
    'generate_svg_request',
    'PipelineState',
    'PipelineError',
    'CircuitBreaker',
    'SolverMetrics',
    'ResourceMonitor',
    'HybridOptimizer',
    'GreedyFallback',
    'SensitivityAnalyzer'
]

__version__ = '1.0.0'
