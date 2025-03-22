"""Conversation management components."""

from app.conversation.response_generator import ResponseGenerator
from app.conversation.sentiment_analyzer import SentimentTracker
from app.conversation.state_manager import ConversationManager, ConversationState
from app.conversation.topic_detector import TopicDetector


class ConversationFactory:
    """Factory for creating and initializing conversation components."""

    def __init__(self):
        self.conversation_manager = ConversationManager()
        self.response_generator = ResponseGenerator()

    def create_conversation(self, session_id: str) -> tuple[ConversationState, SentimentTracker]:
        """Create a new conversation with all necessary components."""
        conversation = self.conversation_manager.get_conversation(session_id)
        sentiment_tracker = SentimentTracker()
        return conversation, sentiment_tracker

    def get_response_generator(self) -> ResponseGenerator:
        """Get the response generator instance."""
        return self.response_generator


# Create singleton instances
conversation_factory = ConversationFactory()
topic_detector = TopicDetector()

__all__ = [
    'conversation_factory',
    'topic_detector',
    'ConversationState',
    'SentimentTracker',
    'ResponseGenerator'
]
