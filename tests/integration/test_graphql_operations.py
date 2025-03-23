"""Integration tests for GraphQL API and resolvers."""
import pytest
import json
from unittest.mock import patch, MagicMock
from app import create_app
from app.models.availability import ServiceAvailability
from app.models.hybrid import HybridModelBackend

@pytest.fixture
def client():
    """Create a test client with a test configuration."""
    app = create_app({"TESTING": True})
    with app.test_client() as client:
        yield client

@pytest.fixture
def mock_hybrid_model():
    """Create a mock hybrid model for testing GraphQL resolvers."""
    mock_model = MagicMock(spec=HybridModelBackend)
    mock_model.generate_response.return_value = "This is a mock response"
    mock_model.is_available = True
    
    return mock_model

def test_service_status_query(client):
    """Test the GraphQL service status query."""
    # GraphQL query to fetch service status
    query = """
    query {
      serviceStatus {
        services {
          name
          status
          availability
          responseTime
        }
      }
    }
    """
    
    # Make the request
    response = client.post(
        '/api/graphql',
        json={'query': query}
    )
    
    # Check the response
    assert response.status_code == 200
    data = json.loads(response.data)
    
    # Basic validation of the response structure
    assert 'data' in data
    assert 'serviceStatus' in data['data']
    assert 'services' in data['data']['serviceStatus']
    
    # We should have data for all our services
    services = data['data']['serviceStatus']['services']
    service_names = [service['name'] for service in services]
    
    assert 'gemini' in service_names
    assert 'ollama' in service_names
    assert 'transformers' in service_names

@pytest.mark.asyncio
async def test_chat_mutation(client, mock_hybrid_model):
    """Test the GraphQL chat mutation."""
    # GraphQL mutation to send a chat message
    mutation = """
    mutation {
      chat(input: {
        message: "What is an opossum?",
        conversationId: "test-conversation"
      }) {
        response
        conversationId
        modelUsed
      }
    }
    """
    
    # Patch the model backend for testing
    with patch('app.api.resolvers.conversation.get_model_backend', 
              return_value=mock_hybrid_model):
        # Make the request
        response = client.post(
            '/api/graphql',
            json={'query': mutation}
        )
        
        # Check the response
        assert response.status_code == 200
        data = json.loads(response.data)
        
        # Validate the response structure
        assert 'data' in data
        assert 'chat' in data['data']
        assert 'response' in data['data']['chat']
        assert data['data']['chat']['response'] == "This is a mock response"
        assert data['data']['chat']['conversationId'] == "test-conversation"

@pytest.mark.asyncio
async def test_force_service_check_mutation(client):
    """Test the mutation to force a service availability check."""
    # GraphQL mutation to force a service check
    mutation = """
    mutation {
      forceServiceCheck {
        successful
        services {
          name
          status
          availability
        }
      }
    }
    """
    
    # Mock the service availability check to avoid actual network calls
    with patch.object(ServiceAvailability, 'check_all_services', return_value=None):
        # Make the request
        response = client.post(
            '/api/graphql',
            json={'query': mutation}
        )
        
        # Check the response
        assert response.status_code == 200
        data = json.loads(response.data)
        
        # Validate the response structure
        assert 'data' in data
        assert 'forceServiceCheck' in data['data']
        assert 'successful' in data['data']['forceServiceCheck']
        assert data['data']['forceServiceCheck']['successful'] == True
        assert 'services' in data['data']['forceServiceCheck']

def test_graphql_error_handling(client):
    """Test error handling in GraphQL responses."""
    # Invalid GraphQL query
    query = """
    query {
      invalidField {
        something
      }
    }
    """
    
    # Make the request
    response = client.post(
        '/api/graphql',
        json={'query': query}
    )
    
    # Check the response
    assert response.status_code == 200  # GraphQL returns 200 even for errors
    data = json.loads(response.data)
    
    # Validate error structure
    assert 'errors' in data
    assert len(data['errors']) > 0
    assert 'message' in data['errors'][0]