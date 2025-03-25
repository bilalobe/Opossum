"""GraphQL API initialization."""
from flask import Blueprint
from flask_graphql import GraphQLView

from app.api.middleware.apollo import ApolloMiddleware
from app.api.middleware.graphql_request_processor import GraphQLRequestProcessor
from app.api.schema import schema

# Create a blueprint for GraphQL API
api = Blueprint('api', __name__, url_prefix='/api')


# Configure GraphQL endpoints
def init_graphql_routes(app):
    """Initialize GraphQL routes."""
    # Main GraphQL endpoint
    api.add_url_rule(
        '/graphql',
        view_func=GraphQLView.as_view(
            'graphql',
            schema=schema,
            graphiql=app.config.get('GRAPHQL_GRAPHIQL', True),
            batch=app.config.get('GRAPHQL_BATCH', True)
        )
    )

    # GraphQL Explorer endpoint
    api.add_url_rule(
        '/explorer',
        view_func=lambda: app.send_static_file('graphql_explorer.html'),
        methods=['GET']
    )

    # Register the blueprint with the app
    app.register_blueprint(api)

    # Apply middleware for request processing
    graphql_middleware = GraphQLRequestProcessor(app, schema)
    app.wsgi_app = graphql_middleware(app.wsgi_app)

    # Setup Apollo Studio integration if enabled
    if app.config.get('APOLLO_STUDIO_ENABLED', False):
        apollo = ApolloMiddleware(app, schema)
        apollo.init_reporting()

    return app
