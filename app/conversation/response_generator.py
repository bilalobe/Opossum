"""Context-aware response generation with sentiment and topic awareness."""

import logging
import random
import yaml
from datetime import datetime
from typing import Dict, Any, List
import os

from app.conversation.sentiment_analyzer import SentimentTracker
from app.conversation.state_manager import ConversationState
from app.conversation.topic_detector import TopicDetector
from app.features.easter_eggs import check_for_easter_eggs

logger = logging.getLogger(__name__)


class ResponseGenerator:
    """Generates contextually appropriate responses based on conversation state."""

    def __init__(self):
        self.topic_detector = TopicDetector()
        self.prompts = self._load_prompts()
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
        
    def _load_prompts(self) -> Dict:
        """Load prompts from the YAML file."""
        try:
            prompts_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                        "prompts", "prompts.yaml")
            with open(prompts_path, 'r') as file:
                return yaml.safe_load(file)
        except Exception as e:
            logger.error(f"Failed to load prompts: {e}")
            # Return a minimal default prompt structure if loading fails
            return {
                "system": "You are the Opossum Search Helper Bot.",
                "general_query": "Provide information about {query}.",
                "error_response": "I apologize, but I'm experiencing difficulties."
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
        sentiment_analysis = sentiment_tracker.analyze(
            user_message,
            self._is_follow_up(user_message)
        )

        # Check for Easter eggs
        current_date = datetime.now()
        easter_egg = await check_for_easter_eggs(current_date, user_message)
        
        if easter_egg["activate"]:
            # Handle special Easter egg responses
            if easter_egg["easter_egg"] == "national_opossum_day":
                # Get random opossum facts for National Opossum Day
                opossum_facts = self._get_random_opossum_facts(3)
                facts_text = "\n".join([f"• {fact}" for fact in opossum_facts])
                
                # Use enhanced prompt if we have knowledge to inject
                if conversation_state.has_knowledge_context():
                    response_template = self.prompts.get("national_opossum_day_enhanced", 
                                                        self.prompts["national_opossum_day"])
                    knowledge = conversation_state.get_knowledge_context()
                    response_text = response_template.format(
                        query=user_message,
                        facts=facts_text,
                        knowledge=knowledge
                    )
                else:
                    response_text = self.prompts["national_opossum_day"].format(
                        query=user_message,
                        facts=facts_text
                    )
                
                conversation_state.add_message(
                    role="user",
                    content=user_message,
                    metadata={"sentiment": sentiment_analysis["sentiment"]}
                )
                conversation_state.add_message(
                    role="assistant",
                    content=response_text,
                    metadata={"special": "opossum_day"}
                )

                return {
                    "response": response_text,
                    "next_stage": conversation_state.current_stage,
                    "sentiment": sentiment_analysis,
                    "needs_reengagement": False,
                    "special": "opossum_day"
                }
            
            elif easter_egg["easter_egg"] == "possum_party":
                # Get random opossum facts for Possum Party
                opossum_facts = self._get_random_opossum_facts(4)
                facts_text = "\n".join([f"• {fact}" for fact in opossum_facts])
                
                # Use enhanced prompt if available
                if "possum_party_enhanced" in self.prompts:
                    response_text = self.prompts["possum_party_enhanced"].format(facts=facts_text)
                else:
                    response_text = self.prompts["possum_party_response"].format(facts=facts_text)
                
                conversation_state.add_message(
                    role="user",
                    content=user_message,
                    metadata={"sentiment": sentiment_analysis["sentiment"]}
                )
                conversation_state.add_message(
                    role="assistant",
                    content=response_text,
                    metadata={"special": "possum_party"}
                )
                
                return {
                    "response": response_text,
                    "next_stage": "special_mode",
                    "sentiment": sentiment_analysis,
                    "needs_reengagement": False,
                    "special": "possum_party",
                    "special_mode": "opossum_mode"
                }

        # Determine next conversation stage
        next_stage = self.topic_detector.determine_next_stage(
            user_message,
            conversation_state.current_stage
        )

        # Update conversation state
        conversation_state.update_stage(next_stage)

        # Select the appropriate prompt template based on topic
        prompt_template = self._select_prompt_template(next_stage, user_message, conversation_state)
        
        # Generate base response
        base_prompt = self._create_prompt(
            user_message,
            conversation_state,
            sentiment_analysis,
            prompt_template
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

    def _select_prompt_template(self, stage: str, user_message: str, conversation_state: ConversationState) -> str:
        """Select the appropriate prompt template based on conversation stage."""
        # Map the conversation stage to a specific prompt template if available
        stage_to_prompt = {
            "habitat_query": self.prompts.get("habitat_query"),
            "diet_query": self.prompts.get("diet_query"),
            "behavior_query": self.prompts.get("behavior_query"),
            "reproduction_query": self.prompts.get("reproduction_query"),
            "anatomy_query": self.prompts.get("anatomy_query"),
        }
        
        # Use knowledge-enhanced prompt if we have specific knowledge to inject
        if conversation_state.has_knowledge_context() and "knowledge_enhanced_query" in self.prompts:
            return self.prompts["knowledge_enhanced_query"]
        
        # Use topic-specific prompt if available
        if stage in stage_to_prompt and stage_to_prompt[stage]:
            return stage_to_prompt[stage]
        
        # Default to general query prompt
        return self.prompts.get("general_query", "{query}")

    def _create_prompt(
            self,
            user_message: str,
            conversation_state: ConversationState,
            sentiment_analysis: Dict[str, Any],
            prompt_template: str
    ) -> str:
        """Create a context-aware prompt for the model."""
        # Get recent conversation context
        context_window = conversation_state.get_context_window()

        # Format the selected prompt template
        formatted_prompt = prompt_template.format(
            query=user_message,
            knowledge=conversation_state.get_knowledge_context() if conversation_state.has_knowledge_context() else ""
        )
        
        # Build context-aware prompt
        prompt_parts = [
            self.prompts.get("system", "You are the Opossum Search Helper Bot."),
            f"Current topic: {conversation_state.current_stage}",
            f"User sentiment: {sentiment_analysis['sentiment']['polarity']:.2f}",
            "Recent context:",
        ]

        for msg in context_window:
            prompt_parts.append(f"{msg['role']}: {msg['content']}")

        prompt_parts.append(f"User message: {user_message}")
        prompt_parts.append(f"Response template: {formatted_prompt}")

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
        
    def inject_knowledge(self, conversation_state: ConversationState, knowledge: str, query: str = None) -> None:
        """Inject specific knowledge into the conversation state for enhanced responses."""
        if query:
            template = self.prompts.get("knowledge_injection_with_context", 
                                      self.prompts.get("knowledge_injection", "{knowledge}"))
            formatted_knowledge = template.format(knowledge=knowledge, query=query)
        else:
            template = self.prompts.get("knowledge_injection", "{knowledge}")
            formatted_knowledge = template.format(knowledge=knowledge)
            
        conversation_state.set_knowledge_context(formatted_knowledge)
