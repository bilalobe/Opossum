"""Resource allocation strategies for SVG pipeline."""

import asyncio
import logging
from typing import Dict, List, Tuple, Any
from app.config import Config

logger = logging.getLogger(__name__)

class ProgressiveAllocator:
    """Manages gradual resource allocation increases."""
    
    def __init__(self):
        """Initialize progressive allocator with config."""
        self.base_allocation = getattr(Config, 'CHAT2SVG_BASE_ALLOCATION', 0.3)
        self.current_allocation = self.base_allocation
        self.max_allocation = getattr(Config, 'CHAT2SVG_MAX_ALLOCATION', 0.9)
        
    async def allocate(self, available_resources: Dict[str, float]):
        """Generator that yields increasingly larger resource allocations.
        
        Args:
            available_resources: Dictionary of available resources
        
        Yields:
            Dict mapping resource names to allocated amounts
        """
        while True:
            yield {
                k: v * self.current_allocation 
                for k, v in available_resources.items()
            }
            # Gradually increase allocation
            self.current_allocation = min(
                self.current_allocation * 1.2,  # Increase by 20%
                self.max_allocation
            )
            await asyncio.sleep(5)  # Wait before next increase

class GreedyFallback:
    """Fallback scheduler using greedy allocation strategy."""
    
    def __init__(self):
        """Initialize greedy fallback scheduler."""
        self.quality_weights = {
            "template": 1.0,  # Base template required
            "detail": 0.6,    # Detail enhancement valuable but optional
            "optimize": 0.3   # Optimization lowest priority
        }
        
    async def solve(self, 
                   requests: List[Any], 
                   resources: Dict[str, float]) -> List[Tuple[Any, List[str]]]:
        """Schedule requests using greedy resource allocation.
        
        Args:
            requests: List of PipelineState objects to schedule
            resources: Available resources dict
            
        Returns:
            List of (request, stages_to_run) tuples
        """
        scheduled = []
        remaining = resources.copy()
        
        # Sort by priority and waiting time
        sorted_requests = sorted(
            requests,
            key=lambda r: (getattr(r, 'priority', 0.5), getattr(r, 'created_at', 0)),
            reverse=True
        )
        
        stage_specs = {
            "template": {"cpu": 0.1, "memory": 0.1, "gpu": 0.0},
            "detail": {"cpu": 0.4, "memory": 0.4, "gpu": 0.8},
            "optimize": {"cpu": 0.3, "memory": 0.2, "gpu": 0.3}
        }
        
        for request in sorted_requests:
            stages = []
            
            # Always try template stage first
            if self._can_allocate(remaining, stage_specs["template"]):
                stages.append("template")
                self._allocate_resources(remaining, stage_specs["template"])
                
                # Try detail if template was possible
                if self._can_allocate(remaining, stage_specs["detail"]):
                    stages.append("detail")
                    self._allocate_resources(remaining, stage_specs["detail"])
                    
                    # Try optimize if detail was possible
                    if self._can_allocate(remaining, stage_specs["optimize"]):
                        stages.append("optimize")
                        self._allocate_resources(remaining, stage_specs["optimize"])
            
            if stages:
                scheduled.append((request, stages))
            
            # Stop if we can't even run template stage
            if not self._can_allocate(remaining, stage_specs["template"]):
                break
                
        return scheduled
        
    def _can_allocate(self, remaining: Dict[str, float], 
                      requirements: Dict[str, float]) -> bool:
        """Check if required resources can be allocated."""
        return all(
            remaining.get(res, 0) >= req
            for res, req in requirements.items()
        )
        
    def _allocate_resources(self, remaining: Dict[str, float],
                          requirements: Dict[str, float]):
        """Subtract allocated resources from remaining pool."""
        for res, req in requirements.items():
            if res in remaining:
                remaining[res] = max(0.0, remaining[res] - req)