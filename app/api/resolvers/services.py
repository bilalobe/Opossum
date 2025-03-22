"""Service availability monitoring resolvers."""
import logging
import json
from datetime import datetime
from app.models.availability import ServiceAvailability
from app.utils.svg import generate_service_status_svg
from app.api.dataloaders.service_loader import service_loader
from app.api.directives import apply_cost, rate_limit
from app.api.types import Timestamp, ModelInfo, Error

logger = logging.getLogger(__name__)

@apply_cost(value=5)
@rate_limit(limit=60, duration=60)  # Once per minute
async def resolve_service_status(root, info):
    """Get current status of all services with visualization."""
    try:
        # Use dataloader for efficient fetching
        service_names = ["gemini", "ollama", "transformers", "redis"]
        service_statuses = await service_loader.load_many(service_names)
        
        # Format the service data
        service_data = {}
        for name, status in zip(service_names, service_statuses):
            service_data[name] = {
                "status": status.get("status", "unknown"),
                "response_time": status.get("response_time", 0),
                "availability": status.get("availability", 0)
            }
        
        # Generate visualization
        svg_content = generate_service_status_svg(service_data)
        last_checked = status.get("last_checked")
        
        return {
            "service_data": json.dumps(service_data),
            "svg_content": svg_content,
            "last_updated": Timestamp.from_datetime(last_checked) if last_checked else None
        }
    except Exception as e:
        logger.error(f"Error getting service status: {e}")
        return {
            "service_data": "{}",
            "svg_content": "",
            "error": Error.create(
                message=f"Failed to fetch service status: {str(e)}",
                code="SERVICE_STATUS_ERROR"
            )
        }

@rate_limit(limit=10, duration=60)  # 10 per minute max
async def resolve_force_service_check(root, info):
    """Force an immediate check of all services."""
    try:
        # Clear cache first to ensure fresh data
        service_loader.clear()
        
        service_availability = ServiceAvailability()
        await service_availability.check_all_services()
        
        # Log the forced check
        logger.info(f"Forced service check completed at {datetime.now().isoformat()}")
        return True
    except Exception as e:
        logger.error(f"Error during forced service check: {e}")
        return False

async def resolve_model_info(root, info, model_name):
    """Get detailed information about a specific model."""
    try:
        from app.config import Config
        from app.models import get_model_backend
        
        # Get model configuration
        model_config = Config.MODEL_CONFIGS.get(model_name, {})
        if not model_config:
            return Error.create(
                message=f"Unknown model: {model_name}",
                code="UNKNOWN_MODEL"
            )
            
        # Check service availability for this provider
        provider = model_config.get("provider", "transformers")
        service_availability = ServiceAvailability()
        await service_availability.check_all_services()
        available = service_availability.service_status.get(provider, {}).get("available", False)
        
        return ModelInfo.from_config(model_name, model_config, available)
    except Exception as e:
        logger.error(f"Error getting model info: {e}")
        return Error.create(
            message=f"Failed to get model info: {str(e)}",
            code="MODEL_INFO_ERROR"
        )