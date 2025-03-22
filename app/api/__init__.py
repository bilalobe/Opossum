"""GraphQL API initialization replacing the previous REST structure."""
from flask import Blueprint
from flask_graphql import GraphQLView
from app.api.schema import schema
from app.api.middleware.apollo import ApolloMiddleware
from app.api.middleware.graphql_request_processor import GraphQLRequestProcessor

# Create a versioned blueprint for GraphQL API
# This maintains the same versioning approach as the previous REST API
api_v1 = Blueprint('api_v1', __name__, url_prefix='/api/v1')

# Configure GraphQL endpoints with versioning
def init_graphql_routes(app):
    """Initialize GraphQL routes with proper versioning."""
    # Main GraphQL endpoint
    api_v1.add_url_rule(
        '/graphql',
        view_func=GraphQLView.as_view(
            'graphql',
            schema=schema,
            graphiql=app.config.get('GRAPHQL_GRAPHIQL', True),
            batch=app.config.get('GRAPHQL_BATCH', True)
        )
    )
    
    # GraphQL Explorer endpoint
    api_v1.add_url_rule(
        '/explorer',
        view_func=lambda: app.send_static_file('graphql_explorer.html'),
        methods=['GET']
    )
    
    # Register the versioned blueprint with the app
    app.register_blueprint(api_v1)
    
    # Apply middleware for request processing
    graphql_middleware = GraphQLRequestProcessor(app, schema)
    app.wsgi_app = graphql_middleware(app.wsgi_app)
    
    # Setup Apollo Studio integration if enabled
    if app.config.get('APOLLO_STUDIO_ENABLED', False):
        apollo = ApolloMiddleware(app, schema)
        apollo.init_reporting()
        
    return app