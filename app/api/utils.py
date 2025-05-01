"""API utilities for request validation and response formatting."""

from functools import wraps
from typing import Any, Dict, Optional

from flask import jsonify, request
from pydantic import BaseModel, ValidationError


def api_response(
        data: Optional[Any] = None,
        error: Optional[str] = None,
        meta: Optional[Dict] = None,
        status_code: int = 200
) -> tuple:
    """
    Create a standardized API response.
    
    Args:
        data: Response data
        error: Error message if any
        meta: Additional metadata
        status_code: HTTP status code
    
    Returns:
        JSON response with consistent format
    """
    response = {
        "success": error is None,
        "data": data if data is not None else {},
        "error": error,
        "meta": meta if meta is not None else {}
    }
    return jsonify(response), status_code


def validate_request(model: type[BaseModel]):
    """
    Decorator to validate request data against a Pydantic model.
    
    Args:
        model: Pydantic model class to validate against
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check content type for POST/PUT requests
            if request.method in ['POST', 'PUT'] and not request.is_json:
                return api_response(
                    error="Content-Type must be application/json",
                    status_code=400
                )

            try:
                # Get request data based on method
                if request.method in ['GET', 'DELETE']:
                    data = request.args.to_dict()
                else:
                    data = request.get_json(silent=True) or {}

                # Validate request data against model
                validated_data = model(**data)

                # Pass validated data to route handler
                return f(validated_data, *args, **kwargs)
            except ValidationError as e:
                # Format validation errors
                errors = []
                for error in e.errors():
                    field_path = " -> ".join(str(x) for x in error["loc"])
                    errors.append(f"{field_path}: {error['msg']}")

                return api_response(
                    error="Validation error",
                    meta={"validation_errors": errors},
                    status_code=400
                )
            except Exception as e:
                import logging
                logging.error("An unexpected error occurred", exc_info=True)
                return api_response(
                    error="An internal server error occurred.",
                    status_code=500
                )

        return decorated_function

    return decorator


def rate_limit_exceeded_response():
    """Generate response for rate limit exceeded."""
    return api_response(
        error="Rate limit exceeded",
        meta={
            "retry_after": request.headers.get("Retry-After", "60"),
            "limit": request.headers.get("X-RateLimit-Limit"),
            "remaining": request.headers.get("X-RateLimit-Remaining"),
            "reset": request.headers.get("X-RateLimit-Reset")
        },
        status_code=429
    )


def validate_content_type(*allowed_types: str):
    """
    Decorator to validate request content type.
    
    Args:
        allowed_types: List of allowed content types (e.g., 'application/json', 'image/*')
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            content_type = request.headers.get('Content-Type', '')

            # Check if content type matches any allowed types
            if not any(
                    allowed.endswith('*') and content_type.startswith(allowed[:-1]) or
                    content_type == allowed
                    for allowed in allowed_types
            ):
                return api_response(
                    error=f"Unsupported Content-Type. Allowed: {', '.join(allowed_types)}",
                    status_code=415
                )

            return f(*args, **kwargs)

        return decorated_function

    return decorator
