"""Integration tests for service availability monitoring."""
import pytest
import asyncio
from unittest.mock import patch, MagicMock
import time
from datetime import datetime, timedelta
import requests
from app.models.availability import ServiceAvailability
from app.config import Config

@pytest.fixture
def availability_service():
    """Create a fresh availability service for testing."""
    return ServiceAvailability()

@pytest.mark.asyncio
async def test_availability_metrics_calculation(availability_service):
    """Test that availability metrics are calculated correctly based on history."""
    service = availability_service
    
    # Create a mock history spanning 24 hours
    now = datetime.now()
    one_day_ago = now - timedelta(hours=24)
    
    # Simulate 80% availability over the last 24 hours (80 out of 100 expected checks)
    # Set expected checks to a known value for testing
    expected_checks = 100
    successful_checks = 80
    
    # Calculate check interval for this test based on expected checks
    check_interval_seconds = int(timedelta(hours=24).total_seconds() / expected_checks)
    service.check_interval = timedelta(seconds=check_interval_seconds)
    
    # Generate timestamps for the successful checks
    # Distribute them evenly across the 24-hour period
    history = []
    for i in range(successful_checks):
        check_time = one_day_ago + timedelta(seconds=i * check_interval_seconds)
        history.append(check_time.timestamp())
    
    # Set mock history for a service
    service.service_status["gemini"]["check_history"] = history
    
    # Trigger metrics calculation
    service._update_availability_metrics()
    
    # Check that availability is calculated correctly (around 80%)
    assert 79 <= service.service_status["gemini"]["availability"] <= 81, \
        f"Expected ~80% availability, got {service.service_status['gemini']['availability']}%"
    
    # Status should be "degraded" since availability is below 99%
    assert service.service_status["gemini"]["status"] == "degraded"

@pytest.mark.asyncio
async def test_gemini_rate_limiting(availability_service):
    """Test that Gemini rate limiting works correctly."""
    service = availability_service
    
    # Reset counters to a known state
    service.gemini_usage = {
        "daily_count": 0,
        "minute_count": 0,
        "tokens_used": 0,
        "day_reset": datetime.now(),
        "minute_reset": datetime.now()
    }
    
    # Verify initial state
    assert service.service_status["gemini"]["available"] == False
    
    # Simulate API key being available
    with patch.object(Config, 'GEMINI_API_KEY', 'fake-api-key'):
        # Set Gemini as initially available
        service.service_status["gemini"]["available"] = True
        
        # Record usage up to the limit
        for _ in range(Config.GEMINI_RPM_LIMIT):
            service.record_gemini_usage(tokens_used=100)
            
        # Gemini should still be available
        assert service.service_status["gemini"]["available"] == True
        
        # One more request should trigger rate limiting
        service.record_gemini_usage(tokens_used=100)
        
        # Gemini should now be unavailable due to rate limiting
        assert service.service_status["gemini"]["available"] == False
        assert service.service_status["gemini"]["status"] == "rate_limited"
        
        # Simulate time passing for a minute
        service.gemini_usage["minute_reset"] = datetime.now() - timedelta(seconds=61)
        
        # Reset counters and check availability
        service._reset_gemini_usage_counters()
        
        # Make Gemini available again since rate limits should have reset
        service.service_status["gemini"]["available"] = True
        
        # Minute count should be reset
        assert service.gemini_usage["minute_count"] == 0
        
        # Daily count should still be tracked
        assert service.gemini_usage["daily_count"] > 0

@pytest.mark.asyncio
async def test_ollama_availability_check(availability_service):
    """Test Ollama availability check with mocked responses."""
    service = availability_service
    
    # Mock successful response
    mock_response = MagicMock()
    mock_response.status_code = 200
    
    # Test successful check
    with patch('requests.get', return_value=mock_response):
        await service.check_ollama_availability()
        assert service.service_status["ollama"]["available"] == True
        
    # Mock failed response
    mock_response.status_code = 503
    
    # Test failed check
    with patch('requests.get', return_value=mock_response):
        await service.check_ollama_availability()
        assert service.service_status["ollama"]["available"] == False
        
    # Test exception handling
    with patch('requests.get', side_effect=requests.RequestException("Connection refused")):
        await service.check_ollama_availability()
        assert service.service_status["ollama"]["available"] == False