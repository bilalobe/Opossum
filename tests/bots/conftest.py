"""Test fixtures for bot user simulations."""
import asyncio
import logging
import pytest
from typing import Callable, Dict, Any

logger = logging.getLogger(__name__)


@pytest.fixture
def base_url():
    """Provide the base URL for the Opossum Search API."""
    # In a real test, this might come from environment variables or test config
    return "http://localhost:5000"


@pytest.fixture
async def force_service_unavailability():
    """Create a fixture to temporarily force a service to be unavailable.
    
    This fixture returns a function that can be used to force a service
    to report as unavailable for testing fallback mechanisms.
    
    Returns:
        A function to make a service unavailable or restore it
    """
    original_statuses = {}
    
    async def _force_unavailability(service_name: str, make_unavailable: bool = True):
        """Force a service to be unavailable or restore it.
        
        Args:
            service_name: The name of the service to modify (e.g., "gemini", "ollama")
            make_unavailable: Whether to make the service unavailable (True) or restore it (False)
        """
        from app.models.availability import availability_monitor
        
        if make_unavailable:
            # Save original status before modifying
            if service_name not in original_statuses:
                original_statuses[service_name] = dict(availability_monitor.service_status[service_name])
                
            # Force service to be unavailable
            availability_monitor.service_status[service_name]["available"] = False
            availability_monitor.service_status[service_name]["status"] = "offline"
            logger.info(f"Forced service {service_name} to be unavailable for testing")
            
        else:
            # Restore original status if we have it
            if service_name in original_statuses:
                availability_monitor.service_status[service_name] = original_statuses[service_name]
                logger.info(f"Restored service {service_name} to original status")
    
    # Clean up at the end of the test
    yield _force_unavailability
    
    # Restore all services that were modified
    from app.models.availability import availability_monitor
    for service_name, status in original_statuses.items():
        availability_monitor.service_status[service_name] = status
        logger.info(f"Restored service {service_name} to original status during cleanup")


@pytest.fixture
async def capture_model_selections():
    """Create a fixture to capture and analyze model selections.
    
    This fixture temporarily patches the model selector to record which
    model was selected for each query, allowing detailed analysis of 
    model selection patterns.
    
    Returns:
        A function to get recorded model selections
    """
    selections = []
    original_select_model = None
    
    # Patch the model selector to record selections
    from app.models.selector import ModelSelector
    
    original_select_model = ModelSelector.select_model
    
    async def _patched_select_model(self, user_message, conversation_stage, has_image=False):
        result = await original_select_model(self, user_message, conversation_stage, has_image)
        
        # Record the selection
        selections.append({
            "message": user_message,
            "conversation_stage": conversation_stage,
            "has_image": has_image,
            "selected_model": result[0],
            "confidence": result[1],
            "provider": result[2]
        })
        
        return result
    
    # Apply the patch
    ModelSelector.select_model = _patched_select_model
    
    def get_selections():
        """Get the recorded model selections."""
        return selections
    
    yield get_selections
    
    # Restore the original method
    ModelSelector.select_model = original_select_model


@pytest.fixture
async def run_concurrent_bots(base_url, request):
    """Fixture to run multiple bot users concurrently.
    
    Returns:
        A function to run concurrent bot users with specified configurations
    """
    async def _run_concurrent_bots(bot_configs, duration=30):
        """Run multiple bot users concurrently to test system behavior.
        
        Args:
            bot_configs: List of bot configuration dictionaries
            duration: Maximum duration in seconds to run the simulation
            
        Returns:
            Dictionary with simulation results
        """
        from tests.bots.bot_user import BotUser, ConcurrentBotSimulation
        
        # Create a simulation with the specified configurations
        bot_profiles = [config.get("behavior_profile", "standard") for config in bot_configs]
        
        simulation = ConcurrentBotSimulation(
            base_url=base_url,
            num_bots=len(bot_configs),
            behavior_profiles=bot_profiles
        )
        
        # Configure bot-specific parameters
        for i, config in enumerate(bot_configs):
            if i < len(simulation.bots):
                # Apply custom query sets if specified
                if "query_set" in config:
                    query_set = config["query_set"]
                    if query_set in simulation.bots[i].query_sets:
                        simulation.bots[i].query_pool = simulation.bots[i].query_sets[query_set]
                
                # Apply custom delay settings
                if "delay_range" in config:
                    simulation.bots[i].min_delay = config["delay_range"][0]
                    simulation.bots[i].max_delay = config["delay_range"][1]
                
                # Set session length
                if "session_length" in config:
                    simulation.bots[i].session_length = config["session_length"]
        
        # Run simulation with limits on messages per bot and concurrency
        results = await simulation.run_simulation(
            messages_per_bot=[config.get("session_length", 5) for config in bot_configs],
            max_concurrency=min(5, len(bot_configs))
        )
        
        return results
    
    return _run_concurrent_bots