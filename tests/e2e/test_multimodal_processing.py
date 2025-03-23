"""E2E test for multimodal (image) processing capabilities."""
import pytest
import base64
import os
from unittest.mock import patch
from io import BytesIO
from PIL import Image, ImageDraw

@pytest.fixture
def sample_image():
    """Create a simple test image."""
    # Create a 200x200 white image with a black circle
    image = Image.new('RGB', (200, 200), color='white')
    draw = ImageDraw.Draw(image)
    draw.ellipse((50, 50, 150, 150), fill='black')
    
    # Convert to base64
    buffer = BytesIO()
    image.save(buffer, format='PNG')
    img_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    return img_str

@pytest.mark.e2e
def test_image_processing_flow(graphql, sample_image):
    """Test the complete image processing flow."""
    # Step 1: Check which services are available
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
    
    status_response = graphql.query(status_query)
    services = status_response["data"]["serviceStatus"]["services"]
    
    # Track if we have multimodal capabilities
    has_gemini = any(s["name"] == "gemini" and s["status"] == "online" for s in services)
    has_llava = any(s["name"] == "ollama" and s["status"] == "online" for s in services)
    
    if not (has_gemini or has_llava):
        pytest.skip("No multimodal capabilities available for testing")
    
    # Step 2: Submit an image for processing
    mutation = """
    mutation ProcessImage($input: ProcessImageInput!) {
      processImage(input: $input) {
        description
        modelUsed
        tags
        success
      }
    }
    """
    
    variables = {
        "input": {
            "image": sample_image,
            "prompt": "Describe what you see in this image in detail."
        }
    }
    
    # Execute the mutation
    response = graphql.mutation(mutation, variables)
    
    # Verify the response structure
    assert "data" in response
    assert "processImage" in response["data"]
    assert "description" in response["data"]["processImage"]
    assert "modelUsed" in response["data"]["processImage"]
    assert "success" in response["data"]["processImage"]
    
    # Response should be successful
    assert response["data"]["processImage"]["success"] == True
    
    # Description should not be empty
    assert len(response["data"]["processImage"]["description"]) > 0
    
    # Step 3: Test fallback behavior when primary service fails
    # Find which model was used
    primary_model = response["data"]["processImage"]["modelUsed"]
    
    # Mock primary service as unavailable
    with patch('app.models.availability.ServiceAvailability.check_all_services') as mock_check:
        # Mock implementation to disable the primary service
        async def side_effect():
            from flask import current_app
            monitor = current_app.availability_monitor
            
            # Make the previously used service unavailable
            if primary_model == "gemini":
                monitor.service_status["gemini"]["available"] = False
                monitor.service_status["gemini"]["status"] = "offline"
            elif primary_model == "llava":
                monitor.service_status["ollama"]["available"] = False
                monitor.service_status["ollama"]["status"] = "offline"
                
            monitor._update_availability_metrics()
        
        mock_check.side_effect = side_effect
        
        # Force service check
        force_check_mutation = """
        mutation {
          forceServiceCheck {
            successful
          }
        }
        """
        
        graphql.mutation(force_check_mutation)
        
        # Try processing an image again
        fallback_response = graphql.mutation(mutation, variables)
        
        # If both multimodal services are unavailable, we should get a fallback response
        # indicating the system cannot process the image
        if not (has_gemini and has_llava):
            assert fallback_response["data"]["processImage"]["success"] == False
            assert "cannot" in fallback_response["data"]["processImage"]["description"].lower() or \
                   "unable" in fallback_response["data"]["processImage"]["description"].lower()
        else:
            # If both services are available, we should still get a successful response
            # but from a different model
            assert fallback_response["data"]["processImage"]["success"] == True
            assert fallback_response["data"]["processImage"]["modelUsed"] != primary_model

@pytest.mark.e2e
def test_image_chat_integration(graphql, sample_image):
    """Test using images within a conversation context."""
    # Create a unique conversation ID
    conversation_id = f"image-test-{pytest.config.getoption('worker', default=0)}"
    
    # Step 1: Start with a text-only message
    text_mutation = """
    mutation StartConversation($input: ChatInput!) {
      chat(input: $input) {
        response
        conversationId
        modelUsed
      }
    }
    """
    
    text_variables = {
        "input": {
            "message": "I'm going to show you an image. Please be ready to analyze it.",
            "conversationId": conversation_id
        }
    }
    
    text_response = graphql.mutation(text_mutation, text_variables)
    assert "data" in text_response
    
    # Step 2: Send an image as part of the conversation
    image_mutation = """
    mutation SendImageMessage($input: MultimodalChatInput!) {
      multimodalChat(input: $input) {
        response
        conversationId
        modelUsed
      }
    }
    """
    
    image_variables = {
        "input": {
            "message": "What's in this image?",
            "conversationId": conversation_id,
            "imageData": sample_image
        }
    }
    
    image_response = graphql.mutation(image_mutation, image_variables)
    
    # If we have multimodal capabilities, this should work
    if image_response.get("errors"):
        status_response = graphql.query(status_query)
        services = status_response["data"]["serviceStatus"]["services"]
        has_multimodal = any(s["name"] in ["gemini", "ollama"] and s["status"] == "online" for s in services)
        
        if has_multimodal:
            assert False, f"Multimodal chat failed with errors: {image_response['errors']}"
        else:
            pytest.skip("No multimodal capabilities available")
    else:
        assert "data" in image_response
        assert "multimodalChat" in image_response["data"]
        assert "response" in image_response["data"]["multimodalChat"]
        assert "modelUsed" in image_response["data"]["multimodalChat"]
        
        # Response should refer to the image in some way
        response_text = image_response["data"]["multimodalChat"]["response"].lower()
        assert any(term in response_text for term in ["image", "picture", "circle", "shape", "black", "white"])
    
    # Step 3: Verify the conversation history includes the image
    history_query = """
    query GetConversationHistory($id: ID!) {
      conversation(id: $id) {
        id
        messages {
          role
          content
          hasImage
          timestamp
        }
      }
    }
    """
    
    history_variables = {
        "id": conversation_id
    }
    
    history_response = graphql.query(history_query, history_variables)
    
    # Verify history response
    assert "data" in history_response
    assert "conversation" in history_response["data"]
    assert "messages" in history_response["data"]["conversation"]
    
    # Should find at least one message with hasImage=true
    messages = history_response["data"]["conversation"]["messages"]
    assert any(msg.get("hasImage") for msg in messages)