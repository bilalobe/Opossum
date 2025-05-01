"""
Centralized registry for Opossum Interceptors.

This module defines which interceptors are active and at which points
in the request lifecycle they operate.
"""

import uuid
from flask import g
import serilog

# Import Config from the main app level
from app.config import Config
from app.core.interceptor_manager import OpossumInterceptorManager
from app.core.interceptors import InterceptionPoint, InterceptorPriority, InterceptorResult

# Import specific interceptor implementations
# Assuming security interceptors are in app/interceptors/security.py
# Adjust imports based on your actual file structure
# Check if the security.py file exists before importing
try:
    from app.interceptors.security import NocturnalWatcherInterceptor, PlayDeadRateLimiterInterceptor
    security_interceptors_available = True
except ImportError:
    serilog.Log.warning("Security interceptors not found (app/interceptors/security.py). Skipping registration.")
    security_interceptors_available = False

# Example: from app.interceptors.logging import RequestResponseLoggerInterceptor
# Example: from app.interceptors.metrics import PerformanceMetricsInterceptor

def register_all_interceptors(manager: OpossumInterceptorManager):
    """
    Registers all active interceptors with the provided manager.

    Args:
        manager: The OpossumInterceptorManager instance.
    """
    serilog.Log.information("Registering application interceptors...")

    # --- PRE_ROUTE Interceptors (Run before routing) ---
    if security_interceptors_available:
        # Register security interceptors only if they were imported successfully
        manager.register(
            NocturnalWatcherInterceptor(api_key=Config.API_KEY),
            InterceptionPoint.PRE_ROUTE
        )
        manager.register(
            PlayDeadRateLimiterInterceptor(limit_per_minute=Config.get('RATE_LIMIT', 60)), # Example: Get limit from config
            InterceptionPoint.PRE_ROUTE
        )
    else:
        serilog.Log.warning("Skipping registration of NocturnalWatcher and PlayDeadRateLimiter interceptors.")


    # --- PRE_HANDLER Interceptors (Run after routing, before view function) ---

    # Example using the decorator style for a simple function-based interceptor
    @manager.create_interceptor_decorator(
        point=InterceptionPoint.PRE_HANDLER,
        priority=InterceptorPriority.HIGH # Run early in pre-handler phase
    )
    def request_id_generator(context):
        """
        Ensures a unique request ID exists for each request, either from
        an incoming header (X-Request-ID) or by generating a new UUID.
        Adds the request_id to Flask's 'g' context and the interceptor context.
        """
        # Prefer existing header, otherwise generate new
        req_id = context.get('headers', {}).get('X-Request-ID') or str(uuid.uuid4())

        # Ensure request_id is available in Flask's 'g' context for view functions
        g.request_id = req_id
        serilog.Log.debug("Using Request ID: {RequestId}", RequestId=req_id)

        # Modify the context for subsequent interceptors/handlers if needed
        # This makes 'request_id' available directly in the context dict
        return InterceptorResult(
            should_continue=True,
            modified_request={'request_id': req_id}
        )

    # Example: Register a logging interceptor (assuming it exists)
    # try:
    #     from app.interceptors.logging import RequestStartLoggerInterceptor
    #     manager.register(
    #         RequestStartLoggerInterceptor(),
    #         InterceptionPoint.PRE_HANDLER,
    #         priority=InterceptorPriority.NORMAL # Run after request_id generation
    #     )
    # except ImportError:
    #     serilog.Log.debug("RequestStartLoggerInterceptor not found, skipping registration.")


    # --- POST_HANDLER Interceptors (Run after view function, before response sent) ---

    # Example: Register a response header interceptor
    # try:
    #     from app.interceptors.headers import AddCustomHeadersInterceptor
    #     manager.register(
    #         AddCustomHeadersInterceptor({'X-Powered-By': 'Opossum Power'}),
    #         InterceptionPoint.POST_HANDLER,
    #         priority=InterceptorPriority.LOW # Run late in post-handler phase
    #     )
    # except ImportError:
    #     serilog.Log.debug("AddCustomHeadersInterceptor not found, skipping registration.")


    # --- EXCEPTION Interceptors (Run on unhandled exceptions) ---

    # Example: Register a custom exception logger
    # try:
    #     from app.interceptors.errors import DetailedExceptionLoggerInterceptor
    #     manager.register(
    #         DetailedExceptionLoggerInterceptor(),
    #         InterceptionPoint.EXCEPTION,
    #         priority=InterceptorPriority.HIGH # Handle exceptions early
    #     )
    # except ImportError:
    #     serilog.Log.debug("DetailedExceptionLoggerInterceptor not found, skipping registration.")


    serilog.Log.information(
        "Interceptor registration complete. Total registered: {Count}",
        Count=len(manager._registered_interceptors) # Access the internal list for count
    )
    # Optionally log the registered interceptors for clarity during startup
    # serilog.Log.debug("Registered Interceptors: {Interceptors}", Interceptors=manager.list_interceptors())
