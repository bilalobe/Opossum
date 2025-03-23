"""Integration tests for model selection and fallback mechanisms."""
import pytest
import asyncio
from unittest.mock import patch, MagicMock
from app.models.availability import ServiceAvailability
from app.models.selector import ModelSelector
from app.models.hybrid import HybridModelBackend

@pytest.fixture
async def availability_service():
    """Fixture for service availability."""
    service = ServiceAvailability()
    # Initialize with known state for testing
    service.service_status["gemini"]["available"] = True
    service.service_status["ollama"]["available"] = True
    service.service_status["transformers"]["available"] = True
    return service

@pytest.fixture
async def model_selector(availability_service):
    """Fixture for model selector with controlled availability."""
    selector = ModelSelector(availability_service)
    return selector

@pytest.mark.asyncio
async def test_model_selection_with_all_services_available(model_selector):
    """Test model selection when all services are available."""
    # Simple query should prefer local model
    model, confidence, provider = await model_selector.select_model(
        "What are opossums?", 
        "general"
    )
    
    assert provider in ["transformers", "ollama", "gemini"]
    assert confidence > 0.5
    assert model is not None

@pytest.mark.asyncio
async def test_gemini_to_ollama_fallback(model_selector, availability_service):
    """Test fallback from Gemini to Ollama when Gemini is unavailable."""
    # Make Gemini unavailable
    availability_service.service_status["gemini"]["available"] = False
    
    # Complex reasoning query would typically select Gemini, but should fallback to Ollama
    model, confidence, provider = await model_selector.select_model(
        "Explain the theory of relativity and its implications for modern physics.",
        "reasoning"
    )
    
    assert provider == "ollama"
    assert confidence > 0.4
    assert model is not None

@pytest.mark.asyncio
async def test_image_query_fallback_chain(model_selector, availability_service):
    """Test fallback chain for image queries."""
    # Test with only transformers available (which doesn't support images)
    availability_service.service_status["gemini"]["available"] = False
    availability_service.service_status["ollama"]["available"] = False
    
    # Image query should attempt to fallback but ultimately fail
    model, confidence, provider = await model_selector.select_model(
        "What's in this image?", 
        "visual", 
        has_image=True
    )
    
    # Should select transformers as fallback even though it can't process images
    # The application layer should handle this appropriately
    assert provider == "transformers"
    assert confidence < 0.5  # Low confidence expected

@pytest.mark.asyncio
async def test_hybrid_model_delegation(availability_service):
    """Test that HybridModelBackend correctly delegates to the selected backend."""
    hybrid = HybridModelBackend()
    hybrid.availability = availability_service
    
    # Patch the backend selection to return a known value
    with patch.object(hybrid, '_HybridModelBackend__select_backend', 
                     return_value=("gemini", 0.9)):
        # Also patch the backend creation to return a mock
        mock_backend = MagicMock()
        mock_backend.generate_response.return_value = "This is a test response"
        
        with patch.object(hybrid, '_HybridModelBackend__get_or_create_backend',
                         return_value=mock_backend):
            response = await hybrid.generate_response("Test prompt", "general")
            
            # Verify the result was obtained from the mock backend
            assert response == "This is a test response"
            mock_backend.generate_response.assert_called_once_with("Test prompt", "general")