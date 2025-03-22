from abc import ABC, abstractmethod

class ModelBackend(ABC):
    """Abstract base class for all model backends"""

    @abstractmethod
    async def generate_response(self, prompt, conversation_stage):
        """Generate a response for the given prompt and conversation stage"""
        pass

    @staticmethod
    def format_prompt(user_message, conversation_stage):
        """Format the prompt for the model"""
        return f"""
        You are an Opossum Information Assistant chatbot. The user's message is: "{user_message}"
        The current conversation stage is: "{conversation_stage}"

        Respond in a helpful, conversational way about opossums. Keep responses relatively brief.
        If the user asks about opossum diet, habitat, or behavior, provide accurate information.
        If they make typos like "snak" for "snake" or "florbida" for "Florida", gently correct them.

        Do not mention that you are an AI language model. Stay in character as the Opossum Search Helper Bot.
        """