"""Prompt templates and management for Gemini backend."""
import re
from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass


class ConversationStage(Enum):
    """Enumeration of conversation stages."""
    GREETING = "greeting"
    QUESTION = "question"
    CLARIFICATION = "clarification"
    DEEP_DIVE = "deep_dive"
    CONCLUSION = "conclusion"


@dataclass
class PromptTemplate:
    """Template for structuring prompts."""
    name: str
    template: str
    variables: List[str]
    
    def format(self, **kwargs) -> str:
        """Format the template with provided variables."""
        result = self.template
        for var in self.variables:
            if var in kwargs:
                result = result.replace(f"{{{var}}}", str(kwargs[var]))
        return result


class PromptManager:
    """Manager for Gemini prompt templates."""
    
    def __init__(self):
        """Initialize the prompt manager with templates."""
        self.templates = {
            # Default text template
            "default": PromptTemplate(
                name="default",
                template=(
                    "You are an Opossum Information Assistant chatbot. "
                    "The user's message is: \"{message}\"\n"
                    "The current conversation stage is: {stage}\n\n"
                    "Respond in a helpful, conversational way with accurate "
                    "opossum information. Keep responses relatively brief and focused."
                ),
                variables=["message", "stage"]
            ),
            
            # Template for greeting stage
            "greeting": PromptTemplate(
                name="greeting",
                template=(
                    "You are an Opossum Information Assistant chatbot introducing "
                    "yourself to a new user. Respond warmly, briefly mention you "
                    "specialize in opossum information, and invite them to ask questions. "
                    "Keep it short and friendly.\n\nThe user said: \"{message}\""
                ),
                variables=["message"]
            ),
            
            # Template for image analysis
            "image_analysis": PromptTemplate(
                name="image_analysis",
                template=(
                    "You are an Opossum Information Assistant chatbot. "
                    "The user has provided an image related to opossums with this message: "
                    "\"{message}\"\n"
                    "The current conversation stage is: {stage}\n\n"
                    "First, describe what you see in the image related to opossums.\n"
                    "Then, respond to the user's query about the image in a helpful, "
                    "conversational way.\n"
                    "Keep responses relatively brief and focused on opossum information."
                ),
                variables=["message", "stage"]
            ),
        }
    
    def apply_template(self, message: str, stage: str) -> str:
        """Apply appropriate template based on conversation stage.
        
        Args:
            message: User message
            stage: Conversation stage
            
        Returns:
            Formatted prompt
        """
        # Select template based on stage
        template = self.templates.get(
            stage.lower() if stage.lower() in self.templates else "default"
        )
        
        # Format the template
        return template.format(message=message, stage=stage)
    
    def create_image_prompt(self, message: str, stage: str) -> str:
        """Create a prompt for image analysis.
        
        Args:
            message: User message accompanying the image
            stage: Current conversation stage
            
        Returns:
            Formatted prompt for image analysis
        """
        template = self.templates["image_analysis"]
        return template.format(message=message, stage=stage)
    
    def add_template(self, name: str, template: str, variables: List[str]):
        """Add a new template.
        
        Args:
            name: Template name
            template: The template string
            variables: List of variable names in the template
        """
        self.templates[name] = PromptTemplate(
            name=name,
            template=template,
            variables=variables
        )