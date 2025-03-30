"""SVG generation backend using Chat2SVG.

This module provides a ModelBackend implementation for Chat2SVG,
allowing it to be used as a standard model backend in the system.
"""
import logging
from typing import Dict, Any, Optional

from app.models.base import ModelBackend
from app.models.chat2svg import chat2svg_generator

logger = logging.getLogger(__name__)

class SVGModelBackend(ModelBackend):
    """ModelBackend implementation for SVG generation using Chat2SVG."""
    
    def __init__(self):
        """Initialize the SVG model backend."""
        self.model_name = "Chat2SVG"
        self.available = chat2svg_generator.is_available()
    
    async def generate_response(self, prompt, conversation_stage):
        """Generate an SVG response for the given prompt."""
        try:
            # Generate SVG using Chat2SVG
            result = await chat2svg_generator.generate_svg_from_prompt(prompt)
            
            # Return result as structured data
            if result and "svg_content" in result:
                return {
                    "type": "svg",
                    "content": result["svg_content"],
                    "base64_image": result["base64_image"],
                    "metadata": result["metadata"]
                }
            else:
                logger.error(f"SVG generation failed for prompt: {prompt[:30]}...")
                return {
                    "type": "error",
                    "message": "SVG generation failed"
                }
                
        except Exception as e:
            logger.error(f"Error generating SVG response: {str(e)}")
            return {
                "type": "error",
                "message": f"SVG generation error: {str(e)}"
            }