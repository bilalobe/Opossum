"""Context-aware response generation with sentiment and topic awareness."""

import logging
from typing import Dict, Any

from app.conversation.sentiment_analyzer import SentimentTracker
from app.conversation.state_manager import ConversationState
from app.conversation.topic_detector import TopicDetector

logger = logging.getLogger(__name__)


class ResponseGenerator:
    """Generates contextually appropriate responses based on conversation state."""

    def __init__(self):
        self.topic_detector = TopicDetector()
        self.reengagement_prompts = {
            "snake_resistance": [
                "Would you like to know more about how opossums handle encounters with snakes?",
                "Did you know opossums have fascinating adaptations for dealing with venomous snakes?"
            ],
            "florida_opossums": [
                "I could tell you more about how opossums thrive in Florida's unique environment.",
                "Would you like to learn about specific opossum behaviors in southeastern habitats?"
            ],
            "diet_query": [
                "I know some interesting facts about opossum dietary preferences.",
                "Would you like to learn about the unique things opossums eat?"
            ],
            "habitat_query": [
                "I could share more about where opossums make their homes.",
                "Did you know opossums are very adaptable to different environments?"
            ],
            "behavior_query": [
                "Would you like to hear about some fascinating opossum behaviors?",
                "I could tell you more about why opossums 'play dead'."
            ]
        }

    async def generate_response(
            self,
            user_message: str,
            conversation_state: ConversationState,
            sentiment_tracker: SentimentTracker,
            model_backend: Any
    ) -> Dict[str, Any]:
        """Generate a contextually appropriate response."""
        # Analyze message sentiment
        sentiment_analysis = sentiment_tracker.analyze_message(
            user_message,
            self._is_follow_up(user_message)
        )

        # Determine next conversation stage
        next_stage = self.topic_detector.determine_next_stage(
            user_message,
            conversation_state.current_stage
        )

        # Update conversation state
        conversation_state.update_stage(next_stage)

        # Generate base response
        base_prompt = self._create_prompt(
            user_message,
            conversation_state,
            sentiment_analysis
        )

        response_text = await model_backend.generate_response(
            base_prompt,
            next_stage
        )

        # Add engagement prompts if needed
        if sentiment_tracker.get_engagement_summary()["needs_reengagement"]:
            response_text = self._add_engagement_prompt(
                response_text,
                next_stage
            )

        # Record the interaction
        conversation_state.add_message(
            role="user",
            content=user_message,
            metadata={"sentiment": sentiment_analysis["sentiment"]}
        )
        conversation_state.add_message(
            role="assistant",
            content=response_text,
            metadata={"stage": next_stage}
        )

        return {
            "response": response_text,
            "next_stage": next_stage,
            "sentiment": sentiment_analysis,
            "needs_reengagement": sentiment_tracker.get_engagement_summary()["needs_reengagement"]
        }

    def _create_prompt(
            self,
            user_message: str,
            conversation_state: ConversationState,
            sentiment_analysis: Dict[str, Any]
    ) -> str:
        """Create a context-aware prompt for the model."""
        # Get recent conversation context
        context_window = conversation_state.get_context_window()

        # Build context-aware prompt
        prompt_parts = [
            f"Current topic: {conversation_state.current_stage}",
            f"User sentiment: {sentiment_analysis['sentiment']['polarity']:.2f}",
            "Recent context:",
        ]

        for msg in context_window:
            prompt_parts.append(f"{msg['role']}: {msg['content']}")

        prompt_parts.append(f"User message: {user_message}")

        return "\n".join(prompt_parts)

    def _is_follow_up(self, message: str) -> bool:
        """Detect if message is a follow-up question."""
        follow_up_indicators = [
            "more", "also", "another", "explain",
            "elaborate", "why", "how", "what",
            "tell me more", "what about"
        ]
        return any(indicator in message.lower() for indicator in follow_up_indicators)

    def _add_engagement_prompt(self, response: str, stage: str) -> str:
        """Add an engagement prompt to the response if appropriate."""
        if stage in self.reengagement_prompts:
            prompt = self.reengagement_prompts[stage][0]  # Use first prompt by default
            return f"{response}\n\n{prompt}"
        return response
