from flask import Flask
import logging

logger = logging.getLogger(__name__)

def create_app():
    """Application factory pattern"""
    app = Flask(__name__, template_folder='../templates')

    # Register routes
    from app.routes import bp
    app.register_blueprint(bp)

    logger.info("Flask application initialized")
    return app