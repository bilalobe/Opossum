"""Conversation schema types and mutations."""
import graphene
from app.api.resolvers.conversation import resolve_chat, resolve_submit_feedback, resolve_end_conversation

class ChatInput(graphene.InputObjectType):
    """Input parameters for chat interactions."""
    message = graphene.String(required=True, description="User's chat message")
    session_id = graphene.String(required=True, description="Unique identifier for the chat session")
    has_image = graphene.Boolean(default_value=False, description="Whether the message includes an image")
    image_data = graphene.String(description="Base64-encoded image data if has_image is true")

class ChatResponse(graphene.ObjectType):
    """Response from the chat system."""
    response = graphene.String(description="AI-generated text response")
    next_stage = graphene.String(description="Next conversation stage identifier")
    has_svg = graphene.Boolean(description="Whether the response includes SVG visualization")
    svg_content = graphene.String(description="SVG markup if has_svg is true")
    base64_image = graphene.String(description="Base64-encoded image if response includes an image")
    error = graphene.String(description="Error message if something went wrong")

# Conversation-related Query fields
conversation_query_fields = {}

# Conversation-related Mutation fields
conversation_mutation_fields = {
    'chat': graphene.Field(
        ChatResponse,
        input=ChatInput(required=True),
        description="Send a message to the chat system",
        resolver=resolve_chat
    ),
    
    'submit_feedback': graphene.Field(
        graphene.Boolean,
        message=graphene.String(required=True),
        rating=graphene.Int(required=True),
        description="Submit user feedback about a chat response",
        resolver=resolve_submit_feedback
    ),
    
    'end_conversation': graphene.Field(
        graphene.Boolean,
        session_id=graphene.String(required=True),
        description="End a chat session",
        resolver=resolve_end_conversation
    )
}
