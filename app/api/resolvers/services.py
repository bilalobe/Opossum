"""Service availability monitoring resolvers."""
import logging
from datetime import datetime
import json
from app.models.availability import ServiceAvailability
from app.utils.svg import generate_service_status_svg

logger = logging.getLogger(__name__)

async def resolve_service_status(root, info):
    """Get current status of all services with visualization."""
    try:
        service_availability = ServiceAvailability()
        await service_availability.check_all_services()
        
        service_data = service_availability.get_services_for_visualization()
        svg_content = generate_service_status_svg(service_data)
        last_updated = service_availability.service_status["gemini"]["last_checked"].isoformat() if \
            service_availability.service_status["gemini"]["last_checked"] else None
        
        return {
            "service_data": json.dumps(service_data),
            "svg_content": svg_content,
            "last_updated": last_updated
        }
    except Exception as e:
        logger.error(f"Error getting service status: {e}")
        raise

async def resolve_force_service_check(root, info):
    """Force an immediate check of all services."""
    try:
        service_availability = ServiceAvailability()
        await service_availability.check_all_services()
        return True
    except Exception as e:
        logger.error(f"Error during forced service check: {e}")
        return False