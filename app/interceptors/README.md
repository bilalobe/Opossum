# Opossum Interceptors

This directory contains implementations of the `OpossumInterceptor` pattern used throughout the Opossum Search application.

## Overview

The Opossum Interceptor system provides a flexible way to handle cross-cutting concerns within the Flask request/response lifecycle, inspired by Java Servlet Filters and the adaptable nature of opossums. Interceptors inject themselves into the processing flow at specific points to perform tasks like authentication, logging, rate limiting, request modification, and response enhancement.

## Key Concepts

-   **`OpossumInterceptor` (Base Class):** Found in `app.core.interceptors`. All custom interceptors must inherit from this class and implement the `intercept` method.
-   **`InterceptorPriority`:** Defines the execution order within a chain (CRITICAL, HIGH, NORMAL, LOW). Critical interceptors run first.
-   **`InterceptionPoint`:** Specifies *when* an interceptor runs (PRE_ROUTE, PRE_HANDLER, POST_HANDLER, EXCEPTION).
-   **`InterceptorResult`:** Returned by the `intercept` method, indicating whether the chain should continue (`should_continue`) and optionally providing a direct `response` to short-circuit the request or `modified_request` data to pass along.
-   **`OpossumInterceptorManager`:** Manages the registration and execution of interceptor chains. Integrated with the Flask app.

## Creating a New Interceptor

1.  Create a new Python file within the `app/interceptors/` directory (e.g., `app/interceptors/caching.py`).
2.  Define a class that inherits from `OpossumInterceptor`.
3.  Implement the `__init__` method, calling `super().__init__(name="YourInterceptorName", priority=InterceptorPriority.NORMAL)`. Choose an appropriate priority.
4.  Implement the `intercept(self, request_context: Dict[str, Any]) -> InterceptorResult:` method. This method receives a dictionary containing request/response data (depending on the `InterceptionPoint`) and must return an `InterceptorResult`.
5.  Inside `intercept`, perform your desired logic (e.g., check headers, modify data, log information).
6.  Return `InterceptorResult(should_continue=True)` to allow the request/response chain to proceed.
7.  Return `InterceptorResult(should_continue=False, response=make_response(...))` to stop processing and return a specific response immediately.
8.  Return `InterceptorResult(should_continue=True, modified_request={'new_data': value})` to add or modify data available to subsequent interceptors or the final route handler (via Flask's `g` object for PRE_HANDLER interceptors).

## Registering Interceptors

All interceptors must be registered with the `OpossumInterceptorManager`. Registration is centralized in:

`app/config/interceptors_registry.py`

Open this file and add your new interceptor using `manager.register()`:

```python
from app.interceptors.caching import CacheCheckInterceptor # Import your interceptor

def register_all_interceptors(manager: OpossumInterceptorManager):
    # ... other registrations ...

    manager.register(
        CacheCheckInterceptor(),
        InterceptionPoint.PRE_HANDLER # Choose the correct point
    )

    # ... other registrations ...