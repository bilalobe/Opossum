"""Custom GraphQL directives for schema extensions."""
import logging
from functools import wraps
from typing import Callable, Optional

from graphql import (
    GraphQLArgument,
    GraphQLDirective,
    DirectiveLocation,
    GraphQLString,
    GraphQLInt
)

logger = logging.getLogger(__name__)

# Custom directive implementations
deprecated_directive = GraphQLDirective(
    name='deprecated',
    description='Marks an element of a GraphQL schema as no longer supported',
    locations=[
        DirectiveLocation.FIELD_DEFINITION,
        DirectiveLocation.ENUM_VALUE,
        DirectiveLocation.ARGUMENT_DEFINITION,
        DirectiveLocation.INPUT_FIELD_DEFINITION
    ],
    args={
        'reason': GraphQLArgument(
            type=GraphQLString,
            description='Explains why this element was deprecated'
        )
    }
)

cost_directive = GraphQLDirective(
    name='cost',
    description='Indicates the computational cost of a field or operation',
    locations=[
        DirectiveLocation.FIELD_DEFINITION,
        DirectiveLocation.OBJECT
    ],
    args={
        'value': GraphQLArgument(
            type=GraphQLInt,
            description='The relative cost value (1-100)'
        ),
        'multipliers': GraphQLArgument(
            type=GraphQLString,
            description='List of arguments that multiply cost'
        )
    }
)

rate_limit_directive = GraphQLDirective(
    name='rateLimit',
    description='Enforces rate limiting on specific fields',
    locations=[DirectiveLocation.FIELD_DEFINITION],
    args={
        'limit': GraphQLArgument(
            type=GraphQLInt,
            description='Maximum number of requests'
        ),
        'duration': GraphQLArgument(
            type=GraphQLInt,
            description='Time window in seconds'
        )
    }
)

caching_directive = GraphQLDirective(
    name='caching',
    description='Controls caching behavior for a field',
    locations=[DirectiveLocation.FIELD_DEFINITION],
    args={
        'maxAge': GraphQLArgument(
            type=GraphQLInt,
            description='Maximum age in seconds'
        ),
        'scope': GraphQLArgument(
            type=GraphQLString,
            description='Caching scope (e.g., PUBLIC, PRIVATE)'
        )
    }
)

auth_directive = GraphQLDirective(
    name='auth',
    description='Requires authentication to access a field',
    locations=[DirectiveLocation.FIELD_DEFINITION],
    args={
        'requires': GraphQLArgument(
            type=GraphQLString,
            description='Required permission role(s)'
        )
    }
)

# Combine all directives
all_directives = [
    deprecated_directive,
    cost_directive,
    rate_limit_directive,
    caching_directive,
    auth_directive
]


# Directive decorator implementations
def rate_limit(limit: int, duration: int) -> Callable:
    """Decorator for rate limiting a resolver."""

    def decorator(resolver_func: Callable) -> Callable:
        @wraps(resolver_func)
        def wrapper(*args, **kwargs):
            # Rate limiting logic would go here
            logger.debug(f"Rate limit applied: {limit}/{duration}s")
            return resolver_func(*args, **kwargs)

        return wrapper

    return decorator


def auth_required(requires: Optional[str] = None) -> Callable:
    """Decorator for requiring authentication on a resolver."""

    def decorator(resolver_func: Callable) -> Callable:
        @wraps(resolver_func)
        def wrapper(root, info, *args, **kwargs):
            # In a real implementation, check auth from info.context
            # For now, just log the requirement
            logger.debug(f"Auth required: {requires}")
            return resolver_func(root, info, *args, **kwargs)

        return wrapper

    return decorator


def apply_cost(value: int, multipliers: Optional[str] = None) -> Callable:
    """Decorator for adding cost tracking to a resolver."""

    def decorator(resolver_func: Callable) -> Callable:
        @wraps(resolver_func)
        def wrapper(root, info, *args, **kwargs):
            # Calculate cost and store in info.context
            effective_cost = value
            if multipliers:
                for arg_name in multipliers.split(','):
                    if arg_name in kwargs:
                        # Multiply cost by argument value if it's numeric
                        arg_val = kwargs.get(arg_name)
                        if isinstance(arg_val, (int, float)):
                            effective_cost *= arg_val

            # Store in context for tracking
            if not hasattr(info.context, 'query_cost'):
                info.context.query_cost = 0
            info.context.query_cost += effective_cost

            return resolver_func(root, info, *args, **kwargs)

        return wrapper

    return decorator


__all__ = [
    'all_directives',
    'rate_limit',
    'auth_required',
    'apply_cost'
]
