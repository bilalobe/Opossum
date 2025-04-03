"""Resource monitoring system for SVG pipeline optimization."""

import logging
from collections import deque
from typing import Dict, Any, Optional
import asyncio
import psutil

try:
    import torch
except ImportError:
    torch = None

logger = logging.getLogger(__name__)

class ResourceMonitor:
    """Enhanced resource monitoring with sliding window averages."""
    
    def __init__(self, window_size: int = 10):
        """Initialize resource monitor.
        
        Args:
            window_size: Number of measurements to keep in sliding window
        """
        self.window_size = window_size
        self.measurements = {
            'cpu': deque(maxlen=window_size),
            'memory': deque(maxlen=window_size),
            'gpu': deque(maxlen=window_size),
            'vram': deque(maxlen=window_size)
        }
        
    async def get_resources(self) -> Dict[str, float]:
        """Get current resource availability."""
        resources = {}
        
        try:
            # CPU and Memory
            cpu_usage = await asyncio.to_thread(psutil.cpu_percent, interval=0.1)
            memory = await asyncio.to_thread(psutil.virtual_memory)
            
            resources["cpu"] = 100.0 - cpu_usage
            resources["memory"] = memory.available / memory.total * 100.0
            
            # GPU if available
            if torch is not None and torch.cuda.is_available():
                try:
                    with torch.cuda.device(0):
                        # Get total and allocated memory
                        total_vram = torch.cuda.get_device_properties(0).total_memory / (1024**3)
                        used_vram = torch.cuda.memory_allocated() / (1024**3)
                        
                        resources["gpu"] = 100.0  # GPU compute available
                        resources["vram"] = ((total_vram - used_vram) / total_vram) * 100.0
                except RuntimeError as e:
                    logger.warning(f"Runtime error during GPU detection: {e}")
                except Exception as e:
                    logger.debug(f"Unexpected GPU detection error: {e}")
            
            # Update measurements
            for key, value in resources.items():
                self.measurements[key].append(value)
                
            logger.debug(
                f"Available resources: CPU={resources.get('cpu', 0):.1f}%, "
                f"Mem={resources.get('memory', 0):.1f}%, "
                f"GPU={'Yes' if 'gpu' in resources else 'No'}"
            )
            
        except Exception as e:
            logger.error(f"Error detecting resources: {e}")
            
        return resources
        
    async def get_trend_adjusted(self) -> Dict[str, float]:
        """Get trend-adjusted resource availability."""
        resources = await self.get_resources()
        
        # Apply trend adjustment
        for key in resources:
            trend = self.get_trend(key)
            resources[key] = max(0.0, resources[key] * (1.0 - trend))
            
        return resources
        
    def get_trend(self, resource: str) -> float:
        """Calculate resource usage trend (-1 to 1, negative means decreasing)."""
        if resource not in self.measurements or len(self.measurements[resource]) < 2:
            return 0.0
            
        values = list(self.measurements[resource])
        if len(values) < 2:
            return 0.0
            
        # Simple linear trend
        delta = values[-1] - values[0]
        max_delta = max(values) - min(values)
        if max_delta == 0:
            return 0.0
            
        return delta / max_delta  # Normalized to [-1, 1]
        
    @property
    def averages(self) -> Dict[str, float]:
        """Get average resource availability over the window."""
        return {
            key: sum(values) / len(values) if values else 0.0
            for key, values in self.measurements.items()
        }