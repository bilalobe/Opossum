"""E2E test for conversation flow in Opossum Search."""
import pytest
import uuid
from unittest.mock import patch

@pytest.mark.e2e
def test_complete_conversation_flow(graphql):
    """Test a complete conversation flow from start to finish."""
    # Generate a unique conversation ID for this test
    conversation_id = f"test-{uuid.uuid4()}"
    
    # Step 1: Start a new conversation with a simple query
    mutation = """
    mutation StartConversation($input: ChatInput!) {
      chat(input: $input) {
        response
        conversationId
        modelUsed
      }
    }
    """
    
    variables = {
        "input": {
            "message": "Hello, what can you tell me about opossums?",
            "conversationId": conversation_id
        }
    }
    
    # Execute the mutation
    response = graphql.mutation(mutation, variables)
    
    # Verify the response structure
    assert "data" in response
    assert "chat" in response["data"]
    assert "response" in response["data"]["chat"]
    assert "conversationId" in response["data"]["chat"]
    assert "modelUsed" in response["data"]["chat"]
    
    # Verify the conversation ID matches what we sent
    assert response["data"]["chat"]["conversationId"] == conversation_id
    
    # Store the initial response text
    initial_response = response["data"]["chat"]["response"]
    
    # Step 2: Continue the conversation with a follow-up question
    follow_up_mutation = """
    mutation ContinueConversation($input: ChatInput!) {
      chat(input: $input) {
        response
        conversationId
        modelUsed
      }
    }
    """
    
    follow_up_variables = {
        "input": {
            "message": "What do they eat?",
            "conversationId": conversation_id
        }
    }
    
    # Execute the follow-up mutation
    follow_up_response = graphql.mutation(follow_up_mutation, follow_up_variables)
    
    # Verify the response structure again
    assert "data" in follow_up_response
    assert "chat" in follow_up_response["data"]
    assert "response" in follow_up_response["data"]["chat"]
    
    # Step 3: Fetch conversation history
    history_query = """
    query GetConversationHistory($id: ID!) {
      conversation(id: $id) {
        id
        messages {
          role
          content
          timestamp
        }
        topics
      }
    }
    """
    
    history_variables = {
        "id": conversation_id
    }
    
    # Execute the history query
    history_response = graphql.query(history_query, history_variables)
    
    # Verify the history response
    assert "data" in history_response
    assert "conversation" in history_response["data"]
    assert "messages" in history_response["data"]["conversation"]
    
    # Should have at least 4 messages (2 user messages, 2 assistant responses)
    messages = history_response["data"]["conversation"]["messages"]
    assert len(messages) >= 4
    
    # Verify correct message ordering (alternating roles)
    for i in range(0, len(messages), 2):
        assert messages[i]["role"] == "user"
        if i+1 < len(messages):
            assert messages[i+1]["role"] == "assistant"