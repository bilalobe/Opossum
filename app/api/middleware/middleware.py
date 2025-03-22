"""GraphQL-focused middleware with rate limiting and performance monitoring."""
import json
import time
from functools import wraps
from typing import Dict, Optional, List

from flask import request, Response, g
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from graphql import GraphQLError, parse, get_operation_complexity

from app.config import Config

class GraphQLMiddleware:
    """GraphQL-specific middleware handling rate limits, metrics, and error handling."""
    
    def __init__(self, app, schema):
        self.app = app
        self.schema = schema
        self.setup_rate_limiting()
        self.setup_error_handlers()
        
    def setup_rate_limiting(self):
        """Configure rate limiting with complexity-based rules."""
        self.limiter = Limiter(
            app=self.app,
            key_func=get_remote_address,
            default_limits=["200 per day", "50 per hour"],
            storage_uri="memory://"
        )
        
        # Add complexity-based rate limiting
        @self.limiter.request_filter
        def complexity_check():
            if request.path == Config.GRAPHQL_ENDPOINT:
                data = request.get_json()
                if data and 'query' in data:
                    try:
                        # Parse query and check complexity
                        ast = parse(data['query'])
                        complexity = get_operation_complexity(self.schema, ast)
                        g.query_complexity = complexity
                        
                        # Adjust rate limits based on complexity
                        if complexity > 100:
                            return False  # Apply stricter limits
                    except Exception as e:
                        g.query_complexity = 0
                        return True
            return True
            
    def setup_error_handlers(self):
        """Configure error handlers for GraphQL-specific errors."""
        @self.app.errorhandler(GraphQLError)
        def handle_graphql_error(error):
            return self.format_error_response(str(error), 400)
            
        @self.app.errorhandler(429)
        def handle_rate_limit(error):
            return self.format_error_response(
                "Rate limit exceeded. Please reduce query complexity or try again later.",
                429
            )
            
    def process_request(self):
        """Process incoming GraphQL request with timing and metrics."""
        g.start_time = time.time()
        
    def process_response(self, response: Response) -> Response:
        """Add performance metrics and headers to response."""
        if hasattr(g, 'start_time'):
            processing_time = int((time.time() - g.start_time) * 1000)
            complexity = getattr(g, 'query_complexity', 0)
            
            # Add custom headers
            response.headers['X-Processing-Time'] = str(processing_time)
            response.headers['X-Query-Complexity'] = str(complexity)
            
            # Add rate limit headers
            if hasattr(g, 'rate_limit_remaining'):
                response.headers['X-Rate-Limit-Remaining'] = str(g.rate_limit_remaining)
            
        return response
        
    def format_error_response(self, message: str, status_code: int) -> Response:
        """Format error responses consistently."""
        response = Response(
            json.dumps({
                'errors': [{
                    'message': message,
                    'status': status_code
                }]
            }),
            status=status_code,
            mimetype='application/json'
        )
        return self.process_response(response)
        
    def __call__(self, environ, start_response):
        """WSGI middleware interface."""
        def _start_response(status, headers, exc_info=None):
            """Wrap the WSGI start_response to inject our headers."""
            if request.path == Config.GRAPHQL_ENDPOINT:
                self.process_request()
            return start_response(status, headers, exc_info)
            
        return self.app(environ, _start_response)