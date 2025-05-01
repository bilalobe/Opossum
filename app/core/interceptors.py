"""
Opossum Interceptor - A flexible request/response processing chain

Just as opossums are opportunistic and adaptable creatures that insert themselves
into various environments, these interceptors inject themselves into the request/response
flow to adapt, enhance, or protect the application.
"""
from typing import Callable, List, Dict, Any, Optional, Union, Type
from functools import wraps
from abc import ABC, abstractmethod
import time
from enum import Enum

from flask import request, g, Response, current_app
import serilog

# Import ErrorHandler for potential type hinting or context, but avoid circular dependency
# from app.utils.error_handler import ErrorHandler

class InterceptorPriority(Enum):
    """
    Priority levels for interceptors, like an opossum's hierarchy of survival needs.
    Lower numerical values run first.
    """
    CRITICAL = 100  # Essential protection (security, auth) - like avoiding predators
    HIGH = 200      # Important concerns (logging, metrics) - like finding food
    NORMAL = 300    # Standard processing - like routine foraging
    LOW = 400       # Optional enhancements - like exploring new territory

class InterceptionPoint(Enum):
    """
    Points where interception can occur in the request/response lifecycle.
    """
    PRE_ROUTE = "pre_route"    # Before route matching (like an opossum scouting ahead)
    PRE_HANDLER = "pre_handler" # After route matching, before handler (investigating)
    POST_HANDLER = "post_handler" # After handler, before response sent (collecting findings)
    EXCEPTION = "exception"    # When exception occurs (defensive posture)

class InterceptorResult:
    """
    Result of an interceptor's processing, determining whether to continue the chain.
    """
    def __init__(self,
                 should_continue: bool = True,
                 response: Optional[Response] = None,
                 modified_request: Optional[Dict[str, Any]] = None):
        self.should_continue = should_continue
        self.response = response
        # Data added here will be merged into the context for subsequent interceptors
        # and potentially added to flask.g by the manager
        self.modified_request = modified_request or {}

class OpossumInterceptor(ABC):
    """
    Base interceptor class - adaptable and clever like an opossum.
    """
    def __init__(self, name: str, priority: InterceptorPriority = InterceptorPriority.NORMAL):
        if not name:
            raise ValueError("Interceptor name cannot be empty")
        self.name = name
        self.priority = priority

    @abstractmethod
    def intercept(self, context: Dict[str, Any]) -> InterceptorResult:
        """
        Process the request/response, returning whether to continue and optional modified data.
        Like an opossum examining its surroundings and deciding how to proceed.

        Args:
            context: A dictionary containing request/response information relevant
                     to the current InterceptionPoint. May include keys like:
                     'request', 'response', 'error', 'path', 'method', 'headers',
                     'args', 'form', 'remote_addr', 'request_id', 'g', etc.
                     Also includes data from `modified_request` of previous interceptors.

        Returns:
            An InterceptorResult object.
        """
        pass

    def __repr__(self):
        return f"<{self.__class__.__name__} '{self.name}' priority={self.priority.name}>"

class InterceptorChain:
    """
    Manages a chain of interceptors, like a family of opossums moving through territory.
    """
    def __init__(self):
        self._interceptors: Dict[InterceptionPoint, List[OpossumInterceptor]] = {
            point: [] for point in InterceptionPoint
        }

    def add(self, interceptor: OpossumInterceptor, point: InterceptionPoint):
        """Add an interceptor to the specified interception point."""
        if not isinstance(interceptor, OpossumInterceptor):
            raise TypeError("Provided object is not an instance of OpossumInterceptor")
        if point not in self._interceptors:
            raise ValueError(f"Invalid interception point: {point}")

        self._interceptors[point].append(interceptor)
        # Sort by priority after adding (lower value = higher priority = runs first)
        self._interceptors[point].sort(key=lambda x: x.priority.value)
        serilog.Log.debug(
            "Added {InterceptorName} to {InterceptionPoint} chain (priority: {Priority})",
            interceptor.name, point.value, interceptor.priority.name
        )

    def execute_chain(self, point: InterceptionPoint, context: Dict[str, Any]) -> InterceptorResult:
        """
        Execute all interceptors in the chain for a specific interception point.
        Like opossums moving through a sequence of areas, checking each carefully.

        Args:
            point: The InterceptionPoint being executed.
            context: The initial context for this interception point.

        Returns:
            The final InterceptorResult after executing the chain. If an interceptor
            halts the chain or returns a response, subsequent interceptors are skipped.
        """
        chain = self._interceptors.get(point)
        final_result = InterceptorResult() # Start with default result (continue, no response)

        if not chain:
            return final_result # No interceptors for this point

        # Ensure request_id is in the context for logging if available
        request_id = context.get('request_id', g.get('request_id', 'N/A'))
        log = serilog.Log.for_context("request_id", request_id) \
                         .for_context("interception_point", point.value)

        log.debug("Executing {Count} interceptors at {Point}", Count=len(chain), Point=point.value)
        chain_start_time = time.time()

        # Use a copy of the context to avoid modifying the original dict directly
        # within the loop, merge modifications explicitly via InterceptorResult
        current_context = context.copy()

        # Apply each interceptor in order
        for interceptor in chain:
            interceptor_log = log.for_context("interceptor_name", interceptor.name) \
                                 .for_context("interceptor_priority", interceptor.priority.name)
            interceptor_start = time.time()

            try:
                # Update context with modifications from the *previous* interceptor's result
                if final_result.modified_request:
                    current_context.update(final_result.modified_request)
                    # Clear modified_request from final_result as it's now in current_context
                    final_result.modified_request = {}

                # Execute the current interceptor
                interceptor_log.debug("Executing interceptor...")
                current_interceptor_result = interceptor.intercept(current_context)

                if not isinstance(current_interceptor_result, InterceptorResult):
                     interceptor_log.warning("Interceptor did not return an InterceptorResult object, returning default.")
                     current_interceptor_result = InterceptorResult() # Default to continue

                # --- Process the result of the current interceptor ---

                # 1. Merge any modifications into the final result's modified_request
                #    These will be applied to the context for the *next* interceptor
                if current_interceptor_result.modified_request:
                    final_result.modified_request.update(current_interceptor_result.modified_request)

                # 2. Check if the interceptor returned a direct response
                if current_interceptor_result.response is not None:
                    final_result.response = current_interceptor_result.response
                    final_result.should_continue = False # Stop processing
                    interceptor_log.information("Interceptor returned response, halting chain.")
                    break # Exit the loop, don't run subsequent interceptors

                # 3. Check if the interceptor explicitly halted continuation
                if not current_interceptor_result.should_continue:
                    final_result.should_continue = False # Stop processing
                    interceptor_log.information("Interceptor halted chain progression.")
                    break # Exit the loop

                # If we reach here, the interceptor allowed continuation

            except Exception as e:
                # Log the error using Serilog, including exception info
                interceptor_log.error(e, "Error executing interceptor")

                # Decide whether to halt the chain based on priority or configuration
                # For now, let's halt on critical errors, otherwise log and continue chain execution
                # (but not necessarily the request itself - that depends on should_continue)
                if interceptor.priority == InterceptorPriority.CRITICAL:
                    final_result.should_continue = False
                    # Optionally create a generic error response
                    # final_result.response = Response("Internal Server Error", status=500)
                    interceptor_log.critical("Halting chain due to error in CRITICAL interceptor.")
                    break
                else:
                    # Logged the error, but allow subsequent interceptors to run
                    # The overall request might still fail later depending on the error
                    interceptor_log.warning("Continuing chain execution despite non-critical interceptor error.")
                    # Ensure we don't accidentally carry over a response from the failed interceptor
                    final_result.response = None

            finally:
                interceptor_time = time.time() - interceptor_start
                interceptor_log.debug(
                    "Interceptor completed in {Duration:.3f}ms. Continue: {Continue}",
                    Duration=interceptor_time * 1000,
                    Continue=final_result.should_continue and final_result.response is None
                )

        total_time = time.time() - chain_start_time
        log.debug(
            "Completed interception chain in {Duration:.3f}ms. Final Continue: {Continue}, Has Response: {HasResponse}",
            Duration=total_time * 1000,
            Continue=final_result.should_continue,
            HasResponse=final_result.response is not None
        )
        return final_result

    def get_interceptors(self, point: InterceptionPoint) -> List[OpossumInterceptor]:
        """Get a list of interceptors for a specific point, ordered by priority."""
        return list(self._interceptors.get(point, [])) # Return a copy