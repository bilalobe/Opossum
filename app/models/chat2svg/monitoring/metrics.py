"""Performance metrics collection and monitoring."""

import logging
from typing import Dict, Any
from prometheus_client import Gauge, Counter

logger = logging.getLogger(__name__)


class SolverMetrics:
    """Enhanced metrics with Prometheus integration."""
    
    def __init__(self):
        """Initialize solver metrics gauges."""
        self.solution_times = Gauge(
            'chat2svg_solver_duration_seconds',
            'Solver execution time'
        )
        self.success_rate = Gauge(
            'chat2svg_solver_success_rate',
            'Solver success percentage'
        )
        self.batch_size = Gauge(
            'chat2svg_batch_size_current',
            'Current optimization batch size'
        )
        
        # Resource metrics
        self.resource_usage = {
            resource: Gauge(
                f'chat2svg_resource_{resource}_usage',
                f'Current {resource} resource usage'
            )
            for resource in ['cpu', 'memory', 'gpu', 'vram']
        }
        
        # Stage metrics
        self.stage_durations = {
            stage: Gauge(
                f'chat2svg_stage_{stage}_duration_seconds',
                f'Duration of {stage} stage'
            )
            for stage in ['template', 'detail', 'optimize']
        }
        
        # Error tracking
        self.errors_total = Counter(
            'chat2svg_errors_total',
            'Total number of pipeline errors',
            ['stage', 'type']
        )
        
    def record(self, duration: float, success: bool, batch_size: int, 
               resources: Dict[str, float], stage_times: Dict[str, float]) -> None:
        """Record metrics from a solver run."""
        self.solution_times.set(duration)
        
        # Update success rate with exponential moving average
        current_rate = self.success_rate._value.get() or 0.0
        new_rate = (current_rate * 0.9) + (0.1 if success else 0.0)
        self.success_rate.set(new_rate)
        
        self.batch_size.set(batch_size)
        
        # Update resource usage metrics
        for resource, value in resources.items():
            if resource in self.resource_usage:
                self.resource_usage[resource].set(value)
                
        # Update stage duration metrics
        for stage, time in stage_times.items():
            if stage in self.stage_durations:
                self.stage_durations[stage].set(time)
                
    def record_error(self, stage: str, error_type: str) -> None:
        """Record a pipeline error."""
        self.errors_total.labels(stage=stage, type=error_type).inc()
        
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics snapshot."""
        return {
            "solver": {
                "duration": self.solution_times._value.get(),
                "success_rate": self.success_rate._value.get(),
                "batch_size": self.batch_size._value.get()
            },
            "resources": {
                resource: gauge._value.get()
                for resource, gauge in self.resource_usage.items()
            },
            "stages": {
                stage: gauge._value.get()
                for stage, gauge in self.stage_durations.items()
            }
        }