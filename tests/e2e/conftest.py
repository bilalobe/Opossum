"""End-to-End test fixtures and utilities for Opossum Search."""
import pytest
import asyncio
import json
from typing import Dict, Any
from app import create_app

@pytest.fixture(scope="session")
def app():
    """Create a test application for E2E testing."""
    app = create_app({
        "TESTING": True,
        "AVAILABILITY_CHECK_INTERVAL": 5,  # Faster checks for E2E tests
        "GEMINI_RPM_LIMIT": 10,  # Higher limit for testing
        "GEMINI_DAILY_LIMIT": 100
    })
    return app

@pytest.fixture(scope="session")
def client(app):
    """Create a test client for E2E testing."""
    with app.test_client() as client:
        yield client

class GraphQLClient:
    """Helper class for making GraphQL requests in tests."""
    
    def __init__(self, client, endpoint="/api/graphql"):
        self.client = client
        self.endpoint = endpoint
        
    def query(self, query_string: str, variables: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a GraphQL query."""
        payload = {"query": query_string}
        if variables:
            payload["variables"] = variables
            
        response = self.client.post(
            self.endpoint,
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        return json.loads(response.data.decode('utf-8'))
        
    def mutation(self, mutation_string: str, variables: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a GraphQL mutation."""
        # Uses the same mechanism as query
        return self.query(mutation_string, variables)

@pytest.fixture
def graphql(client):
    """Create a GraphQL client for E2E testing."""
    return GraphQLClient(client)