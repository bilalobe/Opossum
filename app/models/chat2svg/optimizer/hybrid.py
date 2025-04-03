"""Hybrid optimization combining exact and heuristic approaches with circuit breaker pattern."""

import logging
from typing import Dict, List, Tuple
from ortools.linear_solver import pywraplp
from prometheus_client import Histogram, Counter, Gauge
from app.utils.circuit_breaker import CircuitBreaker

# Define metrics
OPTIMIZATION_TIME = Histogram(
    "svg_pipeline_optimization_seconds",
    "Time taken to solve the optimization problem",
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0]
)

OPTIMIZATION_REQUESTS = Counter(
    "svg_pipeline_optimization_requests_total", 
    "Total number of optimization requests",
    ["result"]  # success or failure
)

RESOURCE_UTILIZATION = Gauge(
    "svg_pipeline_resource_utilization",
    "Resource utilization percentage per type",
    ["resource_type"]  # cpu, memory, gpu
)

class SVGPipelineOptimizer:
    """Optimization engine using Google OR-Tools with circuit breaker."""
    
    def __init__(self):
        # Quality contribution matrices for stages
        self.quality_matrix = {
            "template": 0.6,  # 60% quality contribution
            "detail": 0.3,    # 30% quality contribution  
            "optimize": 0.1   # 10% quality contribution
        }
        
        # Resource requirement matrices with quality levels
        self.resource_requirements = {
            "high": {
                "template": {"cpu": 0.3, "memory": 0.3, "gpu": 0.0},
                "detail": {"cpu": 0.8, "memory": 0.9, "gpu": 0.95},
                "optimize": {"cpu": 0.5, "memory": 0.4, "gpu": 0.3}
            },
            "medium": {
                "template": {"cpu": 0.2, "memory": 0.2, "gpu": 0.0},
                "detail": {"cpu": 0.6, "memory": 0.8, "gpu": 0.9},
                "optimize": {"cpu": 0.4, "memory": 0.3, "gpu": 0.2}
            },
            "low": {
                "template": {"cpu": 0.15, "memory": 0.15, "gpu": 0.0},
                "detail": {"cpu": 0.4, "memory": 0.6, "gpu": 0.8},
                "optimize": {"cpu": 0.3, "memory": 0.2, "gpu": 0.15}
            }
        }
        
        self.circuit_breaker = CircuitBreaker("svg_pipeline_optimizer")
        self.current_quality_level = "medium"

    def _determine_quality_level(self, available_resources: Dict[str, float]) -> str:
        """Determine appropriate quality level based on available resources."""
        if all(v >= 50.0 for v in available_resources.values()):
            return "high"
        elif all(v >= 20.0 for v in available_resources.values()):
            return "medium"
        return "low"

    def optimize_pipeline(self, pending_requests: List[Dict], available_resources: Dict[str, float]) -> List[Tuple]:
        """Optimize pipeline scheduling using OR-Tools with circuit breaker and quality adaptation."""
        try:
            # Check circuit breaker
            if not self.circuit_breaker.allow_request():
                logging.warning("Circuit breaker is open, using fallback configuration")
                OPTIMIZATION_REQUESTS.labels(result="circuit_breaker").inc()
                return self._generate_fallback_schedule(pending_requests)

            # Update resource utilization metrics
            for resource, value in available_resources.items():
                RESOURCE_UTILIZATION.labels(resource_type=resource).set(100.0 - value)

            # Determine quality level based on resources
            self.current_quality_level = self._determine_quality_level(available_resources)
            current_requirements = self.resource_requirements[self.current_quality_level]

            with OPTIMIZATION_TIME.time():
                # Create the solver
                solver = pywraplp.Solver.CreateSolver('SCIP')
                if not solver:
                    logging.error("Could not create solver")
                    OPTIMIZATION_REQUESTS.labels(result="failure").inc()
                    self.circuit_breaker.record_failure()
                    return []

                # Create variables
                x_vars = {}
                for i, _ in enumerate(pending_requests):
                    for j in ["template", "detail", "optimize"]:
                        x_vars[(i, j)] = solver.BoolVar(f'x_{i}_{j}')

                # Objective: maximize quality across all requests
                objective = solver.Objective()
                for i, _ in enumerate(pending_requests):
                    for j in ["template", "detail", "optimize"]:
                        objective.SetCoefficient(x_vars[(i, j)], self.quality_matrix[j])
                objective.SetMaximization()

                # Resource constraints using current quality level requirements
                for resource in ["cpu", "memory", "gpu"]:
                    constraint = solver.Constraint(0, available_resources[resource])
                    for i, _ in enumerate(pending_requests):
                        for j in ["template", "detail", "optimize"]:
                            constraint.SetCoefficient(
                                x_vars[(i, j)], 
                                current_requirements[j][resource]
                            )

                # Dependency constraints
                for i, _ in enumerate(pending_requests):
                    # Detail requires template
                    detail_constraint = solver.Constraint(0, 0)
                    detail_constraint.SetCoefficient(x_vars[(i, "detail")], 1)
                    detail_constraint.SetCoefficient(x_vars[(i, "template")], -1)

                    # Optimize requires detail
                    optimize_constraint = solver.Constraint(0, 0)
                    optimize_constraint.SetCoefficient(x_vars[(i, "optimize")], 1)
                    optimize_constraint.SetCoefficient(x_vars[(i, "detail")], -1)

                # Solve
                status = solver.Solve()
                
                if status == pywraplp.Solver.OPTIMAL:
                    # Extract solution
                    scheduled_requests = []
                    for i, req in enumerate(pending_requests):
                        stages = [
                            j for j in ["template", "detail", "optimize"]
                            if x_vars[(i, j)].solution_value() > 0.5
                        ]
                        if stages:
                            scheduled_requests.append((req, stages))
                    OPTIMIZATION_REQUESTS.labels(result="success").inc()
                    self.circuit_breaker.record_success()
                    return scheduled_requests
                else:
                    logging.warning(f"Solver status: {status}")
                    OPTIMIZATION_REQUESTS.labels(result="failure").inc()
                    self.circuit_breaker.record_failure()
                    return self._generate_fallback_schedule(pending_requests)

        except Exception as e:
            logging.error(f"Optimization error: {e}")
            OPTIMIZATION_REQUESTS.labels(result="failure").inc()
            self.circuit_breaker.record_failure()
            return self._generate_fallback_schedule(pending_requests)

    def _generate_fallback_schedule(self, pending_requests: List[Dict]) -> List[Tuple]:
        """Generate a conservative fallback schedule when optimization fails."""
        fallback_schedule = []
        for req in pending_requests[:2]:  # Limit to 2 requests in fallback mode
            fallback_schedule.append((req, ["template"]))  # Only run template stage
        return fallback_schedule