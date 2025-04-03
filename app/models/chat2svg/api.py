"""Public API for Chat2SVG pipeline."""
import logging
from typing import Optional, Dict, Any

from app.utils.circuit_breaker import CircuitBreaker

from .pipeline import PipelineState
from .monitoring.resources import ResourceMonitor
from .monitoring.metrics import SolverMetrics
from .optimizer.hybrid import HybridOptimizer
from .optimizer.fallback import GreedyFallback
from .sensitivity.analyzer import SensitivityAnalyzer

logger = logging.getLogger(__name__)

# Initialize global components
_circuit_breaker = CircuitBreaker()
_resource_monitor = ResourceMonitor()
_metrics = SolverMetrics()
_optimizer = HybridOptimizer()
_fallback = GreedyFallback()
_analyzer = SensitivityAnalyzer()


async def generate_svg_request(prompt: str, style: Optional[str] = None,
                             priority: float = 0.5) -> Dict[str, Any]:
    """Main entry point for SVG generation requests."""
    try:
        # Initialize pipeline state
        state = PipelineState(prompt, style)
        state.priority = priority
        
        # Check circuit breaker
        if _circuit_breaker.should_use_fallback():
            logger.warning("Circuit breaker active, using fallback processing")
            state.fallback_used = True
            return await _process_with_fallback(state)
            
        # Get resource availability
        resources = await _resource_monitor.get_resources()
        
        # Process request
        try:
            result = await _process_request(state, resources)
            _circuit_breaker.record_success()
            return result
        except Exception as e:
            logger.error(f"Error processing request: {e}")
            _circuit_breaker.record_failure()
            return await _process_with_fallback(state)
            
    except Exception as e:
        logger.error(f"Fatal error in generate_svg_request: {e}")
        return {
            "error": "Internal server error",
            "detail": str(e)
        }


async def _process_request(state: PipelineState,
                          resources: Dict[str, float]) -> Dict[str, Any]:
    """Process request using main pipeline."""
    # Optimize stage selection
    solution = await _optimizer.solve([state], resources)
    if not solution:
        raise ValueError("No viable solution found")
        
    _, stages = solution[0]
    state.stages_to_run = stages
    
    # Record metrics
    _metrics.record(
        duration=sum(state.stage_durations.values()),
        success=not state.error,
        batch_size=1,
        resources=resources,
        stage_times=state.stage_durations
    )
    
    # New: Use sensitivity analyzer to gather insights
    sensitivity_data = await _analyzer.analyze_solution(solution, resources)
    # Store insights for future optimization
    
    if state.error:
        return {
            "error": state.error,
            "detail": state.error_detail
        }
        
    return {
        "svg": state.optimized_svg or state.enhanced_svg or state.template_svg,
        "stages_run": state.stages_run,
        "durations": state.stage_durations,
        "fallback_used": state.fallback_used,
        "sensitivity_insights": sensitivity_data  # Optional: return insights
    }


async def _process_with_fallback(state: PipelineState) -> Dict[str, Any]:
    """Process request using fallback strategy."""
    try:
        resources = await _resource_monitor.get_resources()
        solution = await _fallback.optimize([state], resources)
        if not solution:
            raise ValueError("Fallback processing failed")
            
        _, stages = solution[0]
        state.stages_to_run = stages
        
        return {
            "svg": state.template_svg,  # Fallback uses template only
            "stages_run": ["template"],
            "durations": state.stage_durations,
            "fallback_used": True
        }
        
    except Exception as e:
        logger.error(f"Fallback processing failed: {e}")
        return {
            "error": "Fallback processing failed",
            "detail": str(e)
        }