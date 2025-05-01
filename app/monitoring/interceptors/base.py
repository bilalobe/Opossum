"""Base interceptor pattern implementation for Opossum Search.

Creates a standardized approach to implementing cross-cutting concerns like monitoring,
logging, circuit breaking, and performance tracking throughout the application.
"""
import time
import functools
import inspect
from typing import Callable, TypeVar, Optional, Dict, Any, Union, Type, Set, Tuple

import asyncio
from serilog.events import LogEventLevel
import serilog
from app.config import Config

T = TypeVar('T')
F = TypeVar('F', bound=Callable[..., Any])


class Interceptor:
    """Base class for all interceptors in the system."""
    
    def __init__(self, name: Optional[str] = None, service: Optional[str] = None):
        """Initialize a new interceptor.
        
        Args:
            name: Optional name for this interceptor instance
            service: Optional service name this interceptor belongs to
        """
        self.name = name or self.__class__.__name__
        self.service = service
        self.enabled = True
        self.metrics = {
            "calls_total": 0,
            "success_total": 0, 
            "failure_total": 0,
            "bypass_total": 0,
            "execution_times": []
        }
        self.max_tracked_times = 100
        
        # Register with the registry automatically
        from app.monitoring.interceptors.registry import registry, InterceptorType
        self.registry_name = registry.register(
            name=self.name,
            interceptor_type=self._get_interceptor_type(),
            instance=self,
            service=service,
            config=self._get_config()
        )
        
        serilog.Log.debug("Initialized interceptor: {Name} (Service: {Service})", 
                          self.name, service or "global")
    
    def _get_interceptor_type(self):
        """Determine the interceptor type based on class."""
        from app.monitoring.interceptors.registry import InterceptorType
        
        # Map class names to interceptor types
        class_name = self.__class__.__name__.lower()
        if "circuit" in class_name:
            return InterceptorType.CIRCUIT_BREAKER
        elif "retry" in class_name:
            return InterceptorType.RETRY
        elif "jitter" in class_name:
            return InterceptorType.JITTER
        elif "rate" in class_name:
            return InterceptorType.RATE_LIMIT
        elif "fallback" in class_name:
            return InterceptorType.FALLBACK
        elif "cache" in class_name:
            return InterceptorType.CACHE
        elif "telemetry" in class_name:
            return InterceptorType.TELEMETRY
        elif "transform" in class_name:
            return InterceptorType.TRANSFORMATION
        elif "validate" in class_name:
            return InterceptorType.VALIDATION
        else:
            return InterceptorType.CUSTOM
    
    def _get_config(self) -> Dict[str, Any]:
        """Get the configuration info for this interceptor."""
        return {}
    
    def should_intercept(self, *args, **kwargs) -> bool:
        """Determine if the interceptor should be applied."""
        return self.enabled
    
    def execute(self, func: Callable, *args, **kwargs):
        """Execute the function with the interceptor applied."""
        if not self.should_intercept(*args, **kwargs):
            self._record_bypass()
            return func(*args, **kwargs)
            
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            self._record_success(time.time() - start_time)
            return result
        except Exception as e:
            self._record_failure(time.time() - start_time)
            raise
    
    async def execute_async(self, func: Callable, *args, **kwargs):
        """Execute an async function with the interceptor applied."""
        if not self.should_intercept(*args, **kwargs):
            self._record_bypass()
            return await func(*args, **kwargs)
            
        start_time = time.time()
        
        try:
            result = await func(*args, **kwargs)
            self._record_success(time.time() - start_time)
            return result
        except Exception as e:
            self._record_failure(time.time() - start_time)
            raise
    
    def _record_success(self, execution_time: float):
        """Record a successful execution."""
        self.metrics["calls_total"] += 1
        self.metrics["success_total"] += 1
        self._track_execution_time(execution_time)
        
        # Report to registry
        from app.monitoring.interceptors.registry import registry
        registry.record_call(
            name=self.registry_name,
            success=True,
            execution_time=execution_time
        )
    
    def _record_failure(self, execution_time: float):
        """Record a failed execution."""
        self.metrics["calls_total"] += 1
        self.metrics["failure_total"] += 1
        self._track_execution_time(execution_time)
        
        # Report to registry
        from app.monitoring.interceptors.registry import registry
        registry.record_call(
            name=self.registry_name,
            success=False,
            execution_time=execution_time
        )
    
    def _record_bypass(self):
        """Record an interceptor bypass."""
        self.metrics["calls_total"] += 1
        self.metrics["bypass_total"] += 1
        
        # Report to registry
        from app.monitoring.interceptors.registry import registry
        registry.record_call(
            name=self.registry_name,
            success=True,
            execution_time=0.0,
            bypassed=True
        )
    
    def _track_execution_time(self, execution_time: float):
        """Track execution time in metrics."""
        self.metrics["execution_times"].append(execution_time)
        
        # Keep only the most recent entries
        if len(self.metrics["execution_times"]) > self.max_tracked_times:
            self.metrics["execution_times"].pop(0)
    
    def success_rate(self) -> float:
        """Calculate the success rate."""
        total_executions = self.metrics["success_total"] + self.metrics["failure_total"]
        if total_executions == 0:
            return 1.0
        return self.metrics["success_total"] / total_executions
    
    def avg_execution_time(self) -> float:
        """Calculate average execution time."""
        if not self.metrics["execution_times"]:
            return 0.0
        return sum(self.metrics["execution_times"]) / len(self.metrics["execution_times"])

    def disable(self):
        """Disable this interceptor."""
        self.enabled = False
        serilog.Log.information("Interceptor {Name} disabled", self.registry_name)
    
    def enable(self):
        """Enable this interceptor."""
        self.enabled = True
        serilog.Log.information("Interceptor {Name} enabled", self.registry_name)

    def __call__(self, func: F) -> F:
        """Use the interceptor as a decorator."""
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await self.execute_async(func, *args, **kwargs)
            return async_wrapper
        else:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                return self.execute(func, *args, **kwargs)
            return wrapper


def intercept(
    name: Optional[str] = None,
    service: Optional[str] = None,
    interceptor_class: Optional[Type[Interceptor]] = None,
    **kwargs
) -> Callable[[F], F]:
    """Decorator to apply an interceptor to a function.
    
    Args:
        name: Optional name for this interceptor instance
        service: Optional service name this interceptor belongs to
        interceptor_class: The interceptor class to use
        **kwargs: Additional arguments to pass to the interceptor
        
    Returns:
        A decorator that applies the specified interceptor
    """
    def decorator(func: F) -> F:
        # Use default interceptor class if none specified
        interceptor_cls = interceptor_class or Interceptor
        
        # Create and configure the interceptor
        interceptor = interceptor_cls(name=name or func.__name__, service=service, **kwargs)
        
        # Apply it to the function
        return interceptor(func)
    
    return decorator