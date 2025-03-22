"""Service health metrics collection and reporting."""

import logging
from datetime import datetime
from typing import Dict, Any

from app.models import availability_monitor

logger = logging.getLogger(__name__)


def get_service_metrics() -> Dict[str, Any]:
    """Get consolidated service health metrics.
    
    Returns:
        Dictionary containing service metrics including:
        - Availability percentages
        - Response times
        - Request counts
        - Rate limit status
    """
    metrics = {
        "timestamp": datetime.now().isoformat(),
        "services": {},
        "rate_limits": {
            "gemini": {
                "minute": {
                    "current": availability_monitor.gemini_usage["minute_count"],
                    "limit": availability_monitor.gemini_usage.get("minute_limit", 60),
                    "reset_at": availability_monitor.gemini_usage["minute_reset"].isoformat()
                },
                "daily": {
                    "current": availability_monitor.gemini_usage["daily_count"],
                    "limit": availability_monitor.gemini_usage.get("daily_limit", 60000),
                    "reset_at": availability_monitor.gemini_usage["day_reset"].isoformat()
                }
            }
        }
    }

    # Get service status data
    for service_name, service_data in availability_monitor.service_status.items():
        metrics["services"][service_name] = {
            "status": service_data["status"],
            "available": service_data["available"],
            "response_time": service_data["response_time"],
            "availability": service_data["availability"],
            "last_checked": service_data["last_checked"].isoformat()
            if service_data["last_checked"] else None
        }

        # Add service-specific metrics
        if service_name == "gemini":
            metrics["services"][service_name].update({
                "rate_limited": not service_data["available"] and any([
                    availability_monitor.gemini_usage["minute_count"] >= availability_monitor.gemini_usage.get(
                        "minute_limit", 60),
                    availability_monitor.gemini_usage["daily_count"] >= availability_monitor.gemini_usage.get(
                        "daily_limit", 60000)
                ])
            })

        elif service_name == "ollama":
            # Add Ollama-specific metrics like GPU utilization if available
            pass

        elif service_name == "transformers":
            # Add Transformers-specific metrics like memory usage if available
            pass

    return metrics
