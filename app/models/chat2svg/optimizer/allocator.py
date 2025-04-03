"""Resource allocation management for Chat2SVG pipeline."""
import asyncio
import logging
from typing import Dict, AsyncGenerator

logger = logging.getLogger(__name__)


class ProgressiveAllocator:
    """Manages gradual resource allocation increases."""
    
    def __init__(self, base_allocation: float = 0.3, 
                 max_allocation: float = 0.9,
                 increase_factor: float = 1.2,
                 update_interval: float = 5.0):
        self.base_allocation = base_allocation
        self.current_allocation = base_allocation
        self.max_allocation = max_allocation
        self.increase_factor = increase_factor
        self.update_interval = update_interval
        
    async def allocate(self, available_resources: Dict[str, float]) -> AsyncGenerator[Dict[str, float], None]:
        """Generate progressively increasing resource allocations."""
        while True:
            # Calculate current allocation
            allocation = {
                k: v * self.current_allocation 
                for k, v in available_resources.items()
            }
            
            yield allocation
            
            # Gradually increase allocation
            self.current_allocation = min(
                self.current_allocation * self.increase_factor,
                self.max_allocation
            )
            
            # Wait before next update
            await asyncio.sleep(self.update_interval)
            
    def reset(self) -> None:
        """Reset allocation to base level."""
        self.current_allocation = self.base_allocation
        
    def get_current_allocation(self) -> float:
        """Get current allocation percentage."""
        return self.current_allocation
        
    def set_max_allocation(self, value: float) -> None:
        """Update maximum allocation limit."""
        if 0.0 < value <= 1.0:
            self.max_allocation = value
            # Ensure current allocation doesn't exceed new max
            self.current_allocation = min(self.current_allocation, value)
        else:
            logger.warning(f"Invalid max allocation value: {value}, must be between 0 and 1")