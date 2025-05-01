import dspy
from app.prompts.loader import get_prompt_template

class OpossumDSPyManager:
    """Adapter between Opossum prompt system and DSPy"""
    
    def __init__(self, config=None):
        # Initialize with your preferred model backend
        provider = config.get("provider", "google")
        model = config.get("model", "gemini-pro")
        
        self.lm = dspy.LM(f"{provider}/{model}")
        dspy.configure(lm=self.lm)