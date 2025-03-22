import asyncio
import logging

import httpx

from app.config import Config
from app.models.base import ModelBackend

logger = logging.getLogger(__name__)


async def generate_response(prompt):
    """Generate a response using Ollama API"""
    max_retries = 3
    async with httpx.AsyncClient() as client:
        for attempt in range(max_retries):
            try:
                response = await client.post(
                    Config.OLLAMA_URL,
                    json={
                        "model": Config.OLLAMA_MODEL,
                        "prompt": prompt,
                        "temperature": Config.TEMPERATURE,
                        "top_p": Config.TOP_P,
                        "top_k": Config.TOP_K,
                        "max_tokens": Config.MAX_TOKENS
                    },
                    timeout=30
                )
                response.raise_for_status()
                return response.json().get('response', '')
            except httpx.RequestError as e:
                logger.error(f"Ollama API error (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)  # Wait before retrying
                else:
                    raise


class OllamaBackend(ModelBackend):
    """Backend for local Ollama instance"""
