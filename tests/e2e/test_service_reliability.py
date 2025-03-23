"""E2E test for service reliability and failover mechanisms."""
import pytest
import time
from unittest.mock import patch

@pytest.mark.e2e
def test_service_failover_flow(graphql):
    """Test service failover when primary service becomes unavailable."""
    # Step 1: Check current service status
    status_query = """
    query {
      serviceStatus {
        services {
          name
          status
          availability
        }
      }
    }
    """
    
    initial_status = graphql.query(status_query)
    assert "data" in initial_status
    assert "serviceStatus" in initial_status["data"]
    
    # Step 2: Make a baseline request using current service configuration
    chat_mutation = """
    mutation {
      chat(input: {
        message: "What is the capital of France?",
        conversationId: "service-test"
      }) {
        response
        conversationId
        modelUsed
      }
    }
    """
    
    baseline_response = graphql.mutation(chat_mutation)
    assert "data" in baseline_response
    assert "chat" in baseline_response["data"]
    assert "modelUsed" in baseline_response["data"]["chat"]
    
    baseline_model = baseline_response["data"]["chat"]["modelUsed"]
    
    # Step 3: Simulate primary service failure
    # We'll patch the availability check for the service that was just used
    with patch('app.models.availability.ServiceAvailability.check_all_services') as mock_check:
        # Mock implementation to make the primary service unavailable
        async def side_effect():
            # Get the app's availability monitor
            from flask import current_app
            monitor = current_app.availability_monitor
            
            # Make the previously used service unavailable
            if baseline_model == "gemini":
                monitor.service_status["gemini"]["available"] = False
                monitor.service_status["gemini"]["status"] = "offline"
            elif baseline_model == "ollama":
                monitor.service_status["ollama"]["available"] = False
                monitor.service_status["ollama"]["status"] = "offline"
                
            # Ensure transformers is always available as ultimate fallback
            monitor.service_status["transformers"]["available"] = True
            monitor.service_status["transformers"]["status"] = "online"
            
            # Update metrics
            monitor._update_availability_metrics()
        
        # Set the side effect
        mock_check.side_effect = side_effect
        
        # Force a service check
        force_check_mutation = """
        mutation {
          forceServiceCheck {
            successful
            services {
              name
              status
            }
          }
        }
        """
        
        graphql.mutation(force_check_mutation)
        
        # Step 4: Verify that new service status shows primary as unavailable
        updated_status = graphql.query(status_query)
        services = updated_status["data"]["serviceStatus"]["services"]
        
        primary_service = next((s for s in services if s["name"] == baseline_model), None)
        assert primary_service is not None
        assert primary_service["status"] == "offline"
        
        # Step 5: Make another request - should use fallback service
        failover_response = graphql.mutation(chat_mutation)
        assert "data" in failover_response
        assert "chat" in failover_response["data"]
        assert "modelUsed" in failover_response["data"]["chat"]
        
        # Should use a different model than the baseline
        assert failover_response["data"]["chat"]["modelUsed"] != baseline_model

@pytest.mark.e2e
def test_rate_limiting_behavior(graphql):
    """Test that rate limiting correctly triggers fallback mechanisms."""
    # First, get current service status to see what's available
    status_query = """
    query {
      serviceStatus {
        services {
          name
          status
          availability
        }
      }
    }
    """
    
    initial_status = graphql.query(status_query)
    services = initial_status["data"]["serviceStatus"]["services"]
    
    # If Gemini isn't available, we can't properly test rate limiting
    gemini_service = next((s for s in services if s["name"] == "gemini"), None)
    if not gemini_service or gemini_service["status"] != "online":
        pytest.skip("Gemini service not available for rate limit testing")
    
    # Prepare a simple query to execute multiple times
    chat_mutation = """
    mutation {
      chat(input: {
        message: "Give me a one-sentence fact about space.",
        conversationId: "rate-limit-test"
      }) {
        response
        modelUsed
      }
    }
    """
    
    # Step 1: Make initial request, should use Gemini
    initial_response = graphql.mutation(chat_mutation)
    assert initial_response["data"]["chat"]["modelUsed"] == "gemini"
    
    with patch('app.models.availability.ServiceAvailability.record_gemini_usage') as mock_usage:
        # Mock implementation to simulate hitting rate limits after a few calls
        call_count = 0
        
        def usage_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            
            # Get the app's availability monitor
            from flask import current_app
            monitor = current_app.availability_monitor
            
            # After 3 calls, simulate hitting rate limit
            if call_count >= 3:
                monitor.gemini_usage["minute_count"] = monitor.gemini_usage.get("minute_count", 0) + 1
                monitor.service_status["gemini"]["available"] = False
                monitor.service_status["gemini"]["status"] = "rate_limited"
        
        mock_usage.side_effect = usage_side_effect
        
        # Step 2: Make several requests to trigger rate limiting
        for _ in range(5):
            response = graphql.mutation(chat_mutation)
            
            # After rate limit kicks in, should use a different model
            if call_count >= 3:
                assert response["data"]["chat"]["modelUsed"] != "gemini"
    
    # Step 3: Verify final service status shows Gemini as rate limited
    final_status = graphql.query(status_query)
    services = final_status["data"]["serviceStatus"]["services"]
    
    gemini_service = next((s for s in services if s["name"] == "gemini"), None)
    assert gemini_service["status"] in ["rate_limited", "offline"]