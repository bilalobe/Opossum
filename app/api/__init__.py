"""API package initialization and version management."""

from flask import Blueprint

# Create API v1 blueprint
api_v1 = Blueprint('api_v1', __name__, url_prefix='/api/v1')

# Import all API route modules
from app.api.v1 import conversation, images, services, background

# Register all API route modules
api_v1.register_blueprint(conversation.bp)
api_v1.register_blueprint(images.bp)
api_v1.register_blueprint(services.bp)
api_v1.register_blueprint(background.bp)