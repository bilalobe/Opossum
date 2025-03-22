"""Service availability schema types and operations."""
import graphene
from app.api.resolvers.services import resolve_service_status, resolve_force_service_check, resolve_model_info
from app.api.types import Timestamp, ModelInfo

class ServiceStatus(graphene.ObjectType):
    """Status information for a backend service in the system."""
    name = graphene.String(description="The name of the service (e.g., 'gemini', 'ollama', 'transformers')")
    available = graphene.Boolean(description="Whether the service is currently available")
    status = graphene.String(description="Human-readable status: 'online', 'degraded', or 'offline'")
    response_time = graphene.Int(description="Response time in milliseconds for the last health check")
    availability = graphene.Float(description="Service availability percentage over the last 24 hours")
    last_checked = graphene.Field(Timestamp, description="When the service was last checked")

class ServiceStatusResponse(graphene.ObjectType):
    """Combined service status information with visualization."""
    service_data = graphene.JSONString(description="JSON object containing status data for all services")
    svg_content = graphene.String(description="SVG visualization of service status")
    last_updated = graphene.Field(Timestamp, description="When the status was last updated")
    error = graphene.Field(graphene.String, description="Error message if something went wrong")

# Service-related Query fields
services_query_fields = {
    'service_status': graphene.Field(
        ServiceStatusResponse,
        description="Get current status of all backend services with visualization",
        resolver=resolve_service_status
    ),
    
    'model_info': graphene.Field(
        ModelInfo,
        model_name=graphene.String(required=True),
        description="Get detailed information about a specific model",
        resolver=resolve_model_info
    )
}

# Service-related Mutation fields
services_mutation_fields = {
    'force_service_check': graphene.Field(
        graphene.Boolean,
        description="Force an immediate check of all service availability",
        resolver=resolve_force_service_check
    )
}
