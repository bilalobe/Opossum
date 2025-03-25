import asyncio
import logging

from flask import Flask, render_template
from flask_compress import Compress
from flask_cors import CORS

from app.api import init_graphql_routes
from app.api.middleware.apollo import ApolloMiddleware
from app.api.middleware.graphql_request_processor import GraphQLMiddleware
from app.api.schema import schema
from app.config import Config
from app.models.hybrid import HybridModelBackend
from app.routes import bp as main_bp

logger = logging.getLogger(__name__)


def create_app(config=None):
    """Create and configure the Flask application."""
    app = Flask(__name__)

    # Load default configuration
    app.config.from_object('app.config.Config')

    # Override with any provided config
    if config:
        app.config.update(config)

    # Initialize service availability monitoring
    from app.models.availability import ServiceAvailability
    availability_monitor = ServiceAvailability()

    # Setup Prometheus metrics
    availability_monitor.setup_prometheus_metrics()

    # Add Prometheus metrics endpoint
    try:
        from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
        @app.route('/metrics')
        def metrics():
            return app.response_class(
                response=generate_latest(),
                status=200,
                mimetype=CONTENT_TYPE_LATEST
            )

        logger.info("Prometheus metrics endpoint enabled at /metrics")
    except ImportError:
        logger.warning("prometheus_client not installed, metrics endpoint disabled")

    # Start background availability checks
    @app.before_first_request
    def start_background_tasks():
        asyncio.create_task(availability_monitor.start_background_checks(app))
        logger.info("Started background service availability monitoring")

    # Store availability monitor in app context for access in routes
    app.availability_monitor = availability_monitor

    # Enable CORS
    CORS(app,
         resources={
             r"/api/graphql/*": {"origins": app.config['CORS_ALLOWED_ORIGINS']},
             r"/static/*": {"origins": "*"}
         },
         supports_credentials=app.config['CORS_ALLOW_CREDENTIALS'],
         expose_headers=app.config['CORS_EXPOSE_HEADERS'])

    # Enable response compression
    Compress(app)

    # Register main blueprint for static routes
    app.register_blueprint(main_bp)

    # Initialize Apollo Studio integration
    apollo = ApolloMiddleware(app, schema)

    # Initialize GraphQL middleware with rate limiting and metrics
    graphql_middleware = GraphQLMiddleware(app, schema)
    app.wsgi_app = graphql_middleware(app.wsgi_app)

    # Initialize GraphQL API routes (/api/graphql)
    init_graphql_routes(app)

    # Add GraphQL Voyager route
    @app.route('/voyager')
    def voyager():
        return render_template('voyager.html')

    logger.info("Flask application initialized with GraphQL API, Apollo Studio, and rate limiting support")
    return app


async def prewarm_models():
    """Pre-initialize frequently used models."""
    backend = HybridModelBackend()
    await backend.__get_or_create_backend('transformers')

    if Config.PREWARM_GEMINI:
        await backend.__get_or_create_backend('gemini')
