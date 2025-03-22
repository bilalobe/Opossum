import logging
from flask import Flask, render_template
from flask_graphql import GraphQLView
from flask_cors import CORS
from flask_compress import Compress
from app.routes import bp as main_bp
from app.api.schema import schema
from app.api.middleware.apollo import ApolloMiddleware
from app.api.middleware.middleware import GraphQLMiddleware

logger = logging.getLogger(__name__)

def create_app(config=None):
    """Create and configure the Flask application."""
    app = Flask(__name__)
    
    # Load default configuration
    app.config.from_object('app.config.Config')
    
    # Override with any provided config
    if config:
        app.config.update(config)
    
    # Enable CORS
    CORS(app, 
         resources={
             r"/graphql/*": {"origins": app.config['CORS_ALLOWED_ORIGINS']},
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
    
    # Add GraphQL endpoint with Apollo integration
    app.add_url_rule(
        app.config['GRAPHQL_ENDPOINT'],
        view_func=GraphQLView.as_view(
            'graphql',
            schema=schema,
            graphiql=app.config['GRAPHQL_GRAPHIQL'],
            batch=app.config['GRAPHQL_BATCH'],
            middleware=[],
            **apollo.get_apollo_config()
        )
    )
    
    # Add GraphQL Voyager route
    @app.route('/voyager')
    def voyager():
        return render_template('voyager.html')
    
    logger.info("Flask application initialized with GraphQL, Apollo Studio, and rate limiting support")
    return app
