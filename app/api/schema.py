import graphene
from app.models.availability import ServiceAvailability
from app.conversation import conversation_factory
from app.models import get_model_backend
from app.utils.infrastructure.cache_factory import cache
from app.utils.svg import generate_service_status_svg
from app.utils.processing.image_processor import ImageProcessor
import json
import logging

from app.api.resolvers.background import resolve_generate_gibberish
from app.api.resolvers.conversation import resolve_chat, resolve_submit_feedback, resolve_end_conversation
from app.api.resolvers.images import resolve_process_image, resolve_image_info, resolve_upload_image
from app.api.resolvers.services import resolve_service_status, resolve_force_service_check

logger = logging.getLogger(__name__)

# Types with comprehensive descriptions
class ServiceStatus(graphene.ObjectType):
    """Status information for a backend service in the system."""
    name = graphene.String(description="The name of the service (e.g., 'gemini', 'ollama', 'transformers')")
    available = graphene.Boolean(description="Whether the service is currently available")
    status = graphene.String(description="Human-readable status: 'online', 'degraded', or 'offline'")
    response_time = graphene.Int(description="Response time in milliseconds for the last health check")
    availability = graphene.Float(description="Service availability percentage over the last 24 hours")
    last_checked = graphene.String(description="ISO timestamp of the last availability check")

class ImageInfo(graphene.ObjectType):
    """Metadata and information about an image."""
    width = graphene.Int(description="Width of the image in pixels")
    height = graphene.Int(description="Height of the image in pixels")
    format = graphene.String(description="Image format (e.g., 'JPEG', 'PNG')")
    size = graphene.Int(description="File size in bytes")
    metadata = graphene.JSONString(description="Additional image metadata in JSON format")

class ProcessedImage(graphene.ObjectType):
    """Result of image processing operations."""
    processed_image = graphene.String(description="Base64-encoded processed image data")
    thumbnail = graphene.String(description="Base64-encoded thumbnail of the processed image")
    info = graphene.Field(ImageInfo, description="Metadata about the processed image")

class ChatInput(graphene.InputObjectType):
    """Input parameters for chat interactions."""
    message = graphene.String(required=True, description="User's chat message")
    session_id = graphene.String(required=True, description="Unique identifier for the chat session")
    has_image = graphene.Boolean(default_value=False, description="Whether the message includes an image")
    image_data = graphene.String(description="Base64-encoded image data if has_image is true")

class ChatResponse(graphene.ObjectType):
    """Response from the chat system."""
    response = graphene.String(description="AI-generated text response")
    next_stage = graphene.String(description="Next conversation stage identifier")
    has_svg = graphene.Boolean(description="Whether the response includes SVG visualization")
    svg_content = graphene.String(description="SVG markup if has_svg is true")
    base64_image = graphene.String(description="Base64-encoded image if response includes an image")
    error = graphene.String(description="Error message if something went wrong")

class ImageEffects(graphene.InputObjectType):
    """Parameters for image processing effects."""
    brightness = graphene.Float(description="Brightness adjustment (-1.0 to 1.0)")
    contrast = graphene.Float(description="Contrast adjustment (-1.0 to 1.0)")
    saturation = graphene.Float(description="Saturation adjustment (-1.0 to 1.0)")
    blur = graphene.Float(description="Gaussian blur radius (0.0+)")
    sharpen = graphene.Float(description="Sharpening intensity (0.0 to 1.0)")

class ServiceStatusResponse(graphene.ObjectType):
    """Combined service status information with visualization."""
    service_data = graphene.JSONString(description="JSON object containing status data for all services")
    svg_content = graphene.String(description="SVG visualization of service status")
    last_updated = graphene.String(description="ISO timestamp of the last status update")

class GibberishResponse(graphene.ObjectType):
    """Generated background text with emojis."""
    text = graphene.String(description="Generated opossum-themed text")
    emojis = graphene.List(graphene.String, description="List of relevant emojis")

# Queries
class Query(graphene.ObjectType):
    """Root query type for the GraphQL API."""
    service_status = graphene.Field(
        ServiceStatusResponse,
        description="Get current status of all backend services with visualization",
        resolver=resolve_service_status
    )
    
    image_info = graphene.Field(
        ImageInfo,
        image_data=graphene.String(required=True),
        description="Get metadata about an image",
        resolver=resolve_image_info
    )
    
    generate_gibberish = graphene.Field(
        GibberishResponse,
        num_lines=graphene.Int(default_value=25),
        description="Generate opossum-themed background text with emojis",
        resolver=resolve_generate_gibberish
    )

# Mutations    
class Mutation(graphene.ObjectType):
    """Root mutation type for the GraphQL API."""
    chat = graphene.Field(
        ChatResponse,
        input=ChatInput(required=True),
        description="Send a message to the chat system",
        resolver=resolve_chat
    )
    
    process_image = graphene.Field(
        ProcessedImage,
        image_data=graphene.String(required=True),
        effects=ImageEffects(),
        description="Process an image with optional effects",
        resolver=resolve_process_image
    )
    
    upload_image = graphene.Field(
        ProcessedImage,
        file_data=graphene.String(required=True),
        content_type=graphene.String(required=True),
        description="Upload and process a new image",
        resolver=resolve_upload_image
    )
    
    force_service_check = graphene.Field(
        graphene.Boolean,
        description="Force an immediate check of all service availability",
        resolver=resolve_force_service_check
    )
    
    submit_feedback = graphene.Field(
        graphene.Boolean,
        message=graphene.String(required=True),
        rating=graphene.Int(required=True),
        description="Submit user feedback about a chat response",
        resolver=resolve_submit_feedback
    )
    
    end_conversation = graphene.Field(
        graphene.Boolean,
        session_id=graphene.String(required=True),
        description="End a chat session",
        resolver=resolve_end_conversation
    )

schema = graphene.Schema(
    query=Query,
    mutation=Mutation,
    description="Opossum Search GraphQL API for chat, image processing, and service monitoring"
)