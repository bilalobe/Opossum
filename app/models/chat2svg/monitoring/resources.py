"""Resource monitoring and tracking for Chat2SVG pipeline."""
import logging
import time
from collections import deque
from typing import Dict, Optional

try:
    import psutil
except ImportError:
    psutil = None
    logging.warning("psutil not installed. Resource detection will be limited.")

try:
    import torch
except ImportError:
    torch = None
    logging.debug("torch not installed. GPU detection will be skipped.")

logger = logging.getLogger(__name__)


class ResourceMonitor:
    """Enhanced resource monitoring with sliding window averages."""
    
    def __init__(self, window_size: int = 10):
        self.window_size = window_size
        self.measurements = {
            'cpu': deque(maxlen=window_size),
            'memory': deque(maxlen=window_size),
            'swap': deque(maxlen=window_size),
            'gpu': deque(maxlen=window_size),
            'vram': deque(maxlen=window_size)
        }
        self.last_update = 0
        self.update_interval = 0.1  # 100ms minimum between updates
        
    async def initialize(self) -> None:
        """Initialize with first measurement."""
        await self.get_resources()
        
    async def get_resources(self) -> Dict[str, float]:
        """Get current resources with sliding window averaging."""
        now = time.time()
        if now - self.last_update < self.update_interval:
            return self._get_averages()
            
        self.last_update = now
        current = await self._detect_resources()
        
        # Update measurements
        for key, value in current.items():
            if key in self.measurements:
                self.measurements[key].append(value)
                
        return self._get_averages()
        
    def _get_averages(self) -> Dict[str, float]:
        """Calculate sliding window averages."""
        return {
            key: sum(values) / len(values) if values else 0.0
            for key, values in self.measurements.items()
        }
        
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
        
    async def _detect_resources(self) -> Dict[str, float]:
        """Detect available system resources."""
        resources = {"cpu": 10.0, "memory": 10.0, "swap": 0.0}
        
        if psutil is None:
            return resources

        try:
            # CPU usage
            cpu_usage = psutil.cpu_percent(interval=0.1)
            resources["cpu"] = 100.0 - cpu_usage
            
            # Memory usage
            memory = psutil.virtual_memory()
            resources["memory"] = memory.available / memory.total * 100.0
            
            # Swap usage
            swap = psutil.swap_memory()
            resources["swap"] = 100.0 - swap.percent
            
            # GPU resources if available
            if torch is not None and torch.cuda.is_available():
                try:
                    with torch.cuda.device(0):
                        total = torch.cuda.get_device_properties(0).total_memory / (1024**3)
                        used = torch.cuda.memory_allocated() / (1024**3)
                        resources["gpu"] = 100.0
                        resources["vram"] = ((total - used) / total) * 100.0
                except Exception as e:
                    logger.debug(f"GPU detection error: {e}")

            logger.debug(
                f"Resources: CPU={resources['cpu']:.1f}%, "
                f"Mem={resources['memory']:.1f}%, "
                f"Swap={resources['swap']:.1f}%, "
                f"GPU={'Yes' if 'gpu' in resources else 'No'}"
            )
            
        except Exception as e:
            logger.error(f"Error detecting resources: {e}")
            
        return resources