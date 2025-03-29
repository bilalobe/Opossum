import logging
import time
import random
from datetime import datetime
from typing import Dict, Any, Optional
from functools import lru_cache

from app.utils.infrastructure.cache import get_from_cache, add_to_cache
from app.models.chat2svg import chat2svg_generator

logger = logging.getLogger(__name__)

# Time-based activation thresholds
ACTIVATION_THRESHOLD = 0.8  # 80% chance of activation for date-based eggs
DEGRADED_ACTIVATION_THRESHOLD = 0.5  # Lower chance during degraded conditions
RESOURCE_CHECK_TTL = 60  # Check resource conditions every minute

# Service status cache
_service_status_cache = {
    "last_check": 0,
    "system_degraded": False,
    "resource_pressure": False,
    "available_services": {}
}

class EasterEggManager:
    """Manager for Easter egg features with resilience patterns."""
    
    def __init__(self):
        self.enabled = True
        self.fallback_mode = False
        self.recent_activations = {}
        self.activation_counts = {}
    
    def is_system_degraded(self) -> bool:
        """Check if the system is in a degraded state."""
        current_time = time.time()
        
        # Only check system status periodically to avoid overhead
        if current_time - _service_status_cache["last_check"] > RESOURCE_CHECK_TTL:
            try:
                # This would normally call service availability APIs
                # For now we'll simulate with a low probability of degradation
                _service_status_cache["system_degraded"] = random.random() < 0.05  # 5% chance
                _service_status_cache["resource_pressure"] = random.random() < 0.10  # 10% chance
                _service_status_cache["last_check"] = current_time
            except Exception as e:
                logger.error(f"Error checking system status: {str(e)}")
                # In case of error, assume degraded to be safe
                return True
        
        return _service_status_cache["system_degraded"] or _service_status_cache["resource_pressure"]
    
    @lru_cache(maxsize=100)
    def get_activation_threshold(self, egg_type: str) -> float:
        """Get the activation threshold for an Easter egg, with different values for different types."""
        if egg_type == "national_opossum_day":
            return ACTIVATION_THRESHOLD
        elif egg_type == "possum_party":
            return 1.0  # Always activate explicit commands 
        elif egg_type == "konami_code":
            return 1.0  # Always activate
        else:
            return 0.7  # Default threshold
    
    def should_activate(self, egg_type: str) -> bool:
        """Determine if an Easter egg should activate based on system conditions."""
        # Always check if Easter eggs are globally enabled
        if not self.enabled:
            return False
        
        # Get base activation threshold for this egg type
        threshold = self.get_activation_threshold(egg_type)
        
        # Reduce activation chance if system is degraded, except for explicit commands
        if self.is_system_degraded() and egg_type not in ["possum_party", "konami_code"]:
            threshold = min(threshold, DEGRADED_ACTIVATION_THRESHOLD)
        
        # Implement rate limiting for repeated activations
        current_time = time.time()
        last_activation = self.recent_activations.get(egg_type, 0)
        
        # If activated recently, gradually increase threshold to prevent spamming
        if current_time - last_activation < 300:  # 5 minutes
            activation_count = self.activation_counts.get(egg_type, 0)
            if activation_count > 3:  # After 3 activations in 5 minutes
                return False  # Disable temporarily
            threshold += 0.1 * activation_count  # Gradually increase threshold
        elif egg_type in self.recent_activations:
            # Reset counter after cool-down period
            self.activation_counts[egg_type] = 0
        
        # Random chance based on adjusted threshold
        should_activate = random.random() < threshold
        
        # Update activation tracking if activated
        if should_activate:
            self.recent_activations[egg_type] = current_time
            self.activation_counts[egg_type] = self.activation_counts.get(egg_type, 0) + 1
        
        return should_activate
    
    def record_activation(self, egg_type: str, success: bool):
        """Record the outcome of an activation attempt for adaptive behavior."""
        if not success and egg_type in self.recent_activations:
            # If activation failed, adjust thresholds and potentially enter fallback mode
            self.fallback_mode = True
            logger.warning(f"Easter egg {egg_type} activation failed, entering fallback mode")


# Singleton instance
easter_egg_manager = EasterEggManager()


async def check_for_easter_eggs(request_date, query):
    """Check if any Easter eggs should be activated with resilience patterns"""
    try:
        # Check for National Opossum Day (October 18)
        if request_date.month == 10 and request_date.day == 18:
            egg_type = "national_opossum_day"
            
            if easter_egg_manager.should_activate(egg_type):
                # Use cached SVG if available to reduce load
                svg_content = None
                base64_image = None
                
                if not easter_egg_manager.fallback_mode and chat2svg_generator.is_available():
                    try:
                        # Try to generate a custom SVG for National Opossum Day
                        cache_key = f"national_opossum_day_svg_{request_date.year}"
                        cached_svg = get_from_cache(cache_key)
                        
                        if cached_svg:
                            svg_content = cached_svg.get("svg_content")
                            base64_image = cached_svg.get("base64_image")
                        else:
                            # Generate new SVG
                            result = await chat2svg_generator.generate_svg_from_prompt(
                                "A celebratory opossum wearing a party hat for National Opossum Day"
                            )
                            
                            if result and "svg_content" in result:
                                svg_content = result["svg_content"]
                                base64_image = result["base64_image"]
                                # Cache the result for a day
                                add_to_cache(cache_key, result, ttl=86400)
                    except Exception as e:
                        logger.error(f"Failed to generate National Opossum Day SVG: {str(e)}")
                        # Record activation failure
                        easter_egg_manager.record_activation(egg_type, False)
                        # Continue with fallback features
                
                return {
                    "easter_egg": egg_type,
                    "activate": True,
                    "ui_theme": "party_opossum",
                    "response_modifiers": ["opossum_jokes", "purple_text"],
                    "animations": ["confetti", "scurrying_opossums"],
                    "svg_content": svg_content,
                    "base64_image": base64_image,
                    "fallback_mode": easter_egg_manager.fallback_mode
                }
            else:
                logger.info("National Opossum Day detected but activation throttled due to system conditions")
        
        # Check for "possum party" command
        if query.lower() == "possum party":
            egg_type = "possum_party"
            
            if easter_egg_manager.should_activate(egg_type):
                return {
                    "easter_egg": egg_type,
                    "activate": True,
                    "special_mode": "opossum_mode",
                    "animation": "dancing_opossums",
                    "duration": "session",
                    "fallback_mode": easter_egg_manager.fallback_mode
                }
        
        # Check for Konami code - handled separately in frontend but needs tracking
        if "konami_code_activated" in query.lower():
            easter_egg_manager.record_activation("konami_code", True)
        
        return {"activate": False}
        
    except Exception as e:
        # Emergency error handling - fail safely
        logger.error(f"Error checking Easter eggs: {str(e)}")
        return {"activate": False, "error": str(e)}


def is_national_opossum_day() -> bool:
    """Utility function to check if today is National Opossum Day."""
    today = datetime.now()
    return today.month == 10 and today.day == 18


def get_easter_egg_features(egg_type: str) -> Dict[str, Any]:
    """Get feature configuration for an Easter egg type with fallback options."""
    base_features = {
        "national_opossum_day": {
            "ui_theme": "party_opossum",
            "response_modifiers": ["opossum_jokes", "purple_text"],
            "animations": ["confetti", "scurrying_opossums"]
        },
        "possum_party": {
            "special_mode": "opossum_mode",
            "animation": "dancing_opossums",
            "duration": "session"
        },
        "konami_code": {
            "animation": "konami_dance",
            "overlay": True,
            "duration": 5  # seconds
        }
    }
    
    fallback_features = {
        "national_opossum_day": {
            "ui_theme": "party_opossum_light",  # Lighter version with fewer animations
            "response_modifiers": ["purple_text"], # Only add purple text, no jokes to generate
            "animations": []  # No animations to reduce load
        },
        "possum_party": {
            "special_mode": None,
            "animation": "simple_possum_animation",  # Simpler animation
            "duration": 3  # shorter duration
        },
        "konami_code": {
            "animation": "simple_flash",
            "overlay": False,
            "duration": 2  # seconds
        }
    }
    
    if egg_type not in base_features:
        return {}
        
    if easter_egg_manager.fallback_mode:
        return fallback_features.get(egg_type, {})
        
    return base_features.get(egg_type, {})