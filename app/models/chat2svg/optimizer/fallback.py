"""Fallback optimization strategy using greedy approach."""
import logging
from typing import List, Dict, Tuple, Optional
from ..pipeline import PipelineState, STAGE_SPECS

logger = logging.getLogger(__name__)


class GreedyFallback:
    """Implements greedy fallback strategy when exact solver fails."""
    
    def __init__(self, quality_threshold: float = 0.6):
        self.quality_threshold = quality_threshold
        
    async def optimize(self, requests: List[PipelineState],
                      resources: Dict[str, float]) -> List[Tuple[PipelineState, List[str]]]:
        """Optimize using greedy approach."""
        solution = []
        remaining_resources = resources.copy()
        
        # Sort by estimated value/cost ratio
        sorted_requests = sorted(
            requests,
            key=lambda r: self._calculate_value_cost_ratio(r),
            reverse=True
        )
        
        for request in sorted_requests:
            stages = self._select_minimal_stages(request, remaining_resources)
            if stages:
                solution.append((request, stages))
                # Update remaining resources
                for stage in stages:
                    for resource, amount in STAGE_SPECS[stage].items():
                        if resource in remaining_resources:
                            remaining_resources[resource] = max(
                                0.0,
                                remaining_resources[resource] - amount
                            )
                            
        return solution
        
    def _calculate_value_cost_ratio(self, request: PipelineState) -> float:
        """Calculate value/cost ratio for request prioritization."""
        # Estimate value based on waiting time and priority
        value = 1.0
        if hasattr(request, 'priority'):
            value *= (1.0 + request.priority)
            
        # Estimate cost based on prompt complexity
        cost = 1.0 + (len(request.prompt.split()) / 100.0)
        
        return value / cost
        
    def _select_minimal_stages(self, request: PipelineState,
                             resources: Dict[str, float]) -> List[str]:
        """Select minimal set of stages that meet quality threshold."""
        stages = ["template"]  # Always include template
        quality = 0.4  # Base quality from template
        
        # Try adding detail stage if resources allow
        if all(resources.get(r, 0) >= STAGE_SPECS["detail"][r] 
               for r in STAGE_SPECS["detail"]):
            stages.append("detail")
            quality += 0.4
            
            # Only try optimize if we have detail and need more quality
            if (quality < self.quality_threshold and 
                all(resources.get(r, 0) >= STAGE_SPECS["optimize"][r] 
                    for r in STAGE_SPECS["optimize"])):
                stages.append("optimize")
                quality += 0.2
                
        return stages
        
    def get_quality_estimate(self, stages: List[str]) -> float:
        """Estimate solution quality based on stages used."""
        quality_contributions = {
            "template": 0.4,
            "detail": 0.4,
            "optimize": 0.2
        }
        return sum(quality_contributions[s] for s in stages)