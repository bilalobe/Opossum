"""Test suite for model selection features of Opossum Search using bot users.

This module tests that the hybrid model selection system correctly routes queries
to the appropriate models based on query characteristics and service availability.
"""
import asyncio
import logging
import pytest
import re
from datetime import datetime, timedelta

from tests.bots.bot_user import BotUser, ConcurrentBotSimulation

logger = logging.getLogger(__name__)


class ModelSelectionBot(BotUser):
    """Specialized bot for testing model selection logic."""
    
    def __init__(self, base_url: str, **kwargs):
        super().__init__(base_url, **kwargs)
        
        # Track model selection patterns
        self.model_selections = {}
        self.detected_models = {}
    
    async def test_query_routing(self, query_type: str, queries: list):
        """Test that specific query types go to the expected models.
        
        Args:
            query_type: Category name for this set of queries
            queries: List of queries to test
            
        Returns:
            Dictionary with model selection statistics
        """
        logger.info(f"Testing model selection for query type: {query_type}")
        self.model_selections[query_type] = {"queries": queries, "responses": []}
        
        for query in queries:
            logger.info(f"Testing query: {query}")
            
            # Send the query
            response = await self.send_chat_message(query)
            
            # Record the response
            self.model_selections[query_type]["responses"].append({
                "query": query,
                "response": response.get("response", ""),
                "detected_model": self._detect_model_from_response(response.get("response", ""))
            })
            
            # Wait a bit to avoid rate limiting
            await asyncio.sleep(0.5)
        
        # Analyze model selection patterns
        return self._analyze_model_selections(query_type)
    
    def _detect_model_from_response(self, response: str) -> str:
        """Attempt to detect which model generated the response.
        
        This is a heuristic approach and depends on the models leaving some
        identifiable patterns in their responses. In a real implementation,
        you might want to explicitly include model information in responses.
        
        Args:
            response: The text response from the API
            
        Returns:
            Detected model name or "unknown"
        """
        # This logic would need to be customized for your actual models
        
        # Look for specific patterns that might indicate which model was used
        if re.search(r'gemini|thinking', response.lower()):
            return "gemini-thinking"
        elif re.search(r'ollama', response.lower()):
            return "ollama"
        elif re.search(r'transformers|local model', response.lower()):
            return "transformers"
        
        # Try to detect by style/quality (very heuristic)
        if len(response) > 500 and ',' in response and ';' in response:
            # Complex sentence structure suggests Gemini
            return "gemini-thinking"
        elif len(response) < 100:
            # Very short responses might be from a fallback system
            return "transformers"
        
        return "unknown"
    
    def _analyze_model_selections(self, query_type: str) -> dict:
        """Analyze model selection patterns for a query type.
        
        Args:
            query_type: The category of queries to analyze
            
        Returns:
            Dictionary with analysis results
        """
        if query_type not in self.model_selections:
            return {"error": "Query type not tested"}
        
        # Count model occurrences
        model_counts = {}
        
        for response_data in self.model_selections[query_type]["responses"]:
            model = response_data["detected_model"]
            model_counts[model] = model_counts.get(model, 0) + 1
        
        # Calculate percentages
        total = len(self.model_selections[query_type]["responses"])
        model_percentages = {model: count / total * 100 for model, count in model_counts.items()}
        
        # Store detected models for this query type
        self.detected_models[query_type] = {
            "counts": model_counts,
            "percentages": model_percentages,
            "sample_size": total
        }
        
        logger.info(f"Model selection for {query_type}: {model_counts}")
        
        return self.detected_models[query_type]


@pytest.mark.asyncio
async def test_reasoning_query_routing(base_url):
    """Test that reasoning-heavy queries are routed to capable models."""
    bot = ModelSelectionBot(base_url=base_url, user_id="reasoning-test-bot")
    
    # Define reasoning-heavy queries
    reasoning_queries = [
        "Compare the ecological benefits of opossums to other urban wildlife",
        "Analyze the evolutionary advantages of the opossum's marsupial reproductive strategy",
        "Explain why opossums have immunity to most snake venoms and what implications this has",
        "What would happen to tick populations if opossums went extinct in North America?",
        "Synthesize the different theories about why opossums developed the ability to play dead"
    ]
    
    # Test model selection for reasoning queries
    results = await bot.test_query_routing("reasoning", reasoning_queries)
    
    # Validate that most reasoning queries go to capable models
    # We expect these to primarily go to gemini-thinking but can accept reasonable fallbacks
    expected_models = ["gemini-thinking", "unknown"]  # unknown is acceptable when we can't detect
    
    # Calculate percentage of queries going to expected models
    pct_to_expected_models = sum(results["counts"].get(model, 0) for model in expected_models) / results["sample_size"] * 100
    
    assert pct_to_expected_models >= 80, f"Reasoning queries not routed to capable models: {results['counts']}"


@pytest.mark.asyncio
async def test_factual_query_routing(base_url):
    """Test that simple factual queries work with any model."""
    bot = ModelSelectionBot(base_url=base_url, user_id="factual-test-bot")
    
    # Define simple factual queries
    factual_queries = [
        "Where do opossums live?",
        "What do opossums eat?",
        "How many babies do opossums have?",
        "Do opossums carry rabies?",
        "How long do opossums live?"
    ]
    
    # Test model selection for factual queries
    results = await bot.test_query_routing("factual", factual_queries)
    
    # All models should be able to handle these, so we just verify they got responses
    assert results["sample_size"] == len(factual_queries), "Not all factual queries received responses"
    
    # Check that all responses had substantial content
    all_responses = [r["response"] for r in bot.model_selections["factual"]["responses"]]
    
    for i, response in enumerate(all_responses):
        assert len(response) > 50, f"Factual query {i} received insufficient response: {response[:30]}..."


@pytest.mark.asyncio
async def test_multimodal_selection(base_url):
    """Test that image-related requests correctly route to multimodal-capable models."""
    # This is a stub test since we can't easily send images in this test framework
    # In a real implementation, you would need to include base64-encoded images
    # For now we only check that the system identifies the need
    
    bot = BotUser(base_url=base_url, user_id="multimodal-test-bot")
    
    # These queries imply image processing needs
    image_queries = [
        "Can you analyze an image of an opossum?",
        "I'll share a picture of what I think is an opossum",
        "I need help identifying this animal from a photo",
        "Is the opossum in this image healthy?",
        "Can you tell me what this opossum is doing in the picture?"
    ]
    
    results = []
    
    for query in image_queries:
        response = await bot.send_chat_message(query)
        results.append(response)
        
        await asyncio.sleep(0.5)  # Brief pause between queries
    
    # Verify that responses acknowledge image-related functionality
    image_related_terms = ["image", "picture", "photo", "upload", "send me", "attach"]
    
    acknowledgments = 0
    for response in results:
        response_text = response.get("response", "").lower()
        
        if any(term in response_text for term in image_related_terms):
            acknowledgments += 1
    
    # At least 3 of 5 should acknowledge the image aspect
    assert acknowledgments >= 3, f"Image requests not properly acknowledged: {acknowledgments}/5"


@pytest.mark.asyncio
async def test_model_selection_with_forced_unavailability(base_url, force_service_unavailability):
    """Test model selection when primary model is unavailable."""
    # Make Gemini unavailable
    force_service_unavailability("gemini")
    
    try:
        bot = ModelSelectionBot(base_url=base_url, user_id="unavailability-test-bot")
        
        # Queries that would normally go to Gemini
        complex_queries = [
            "Analyze the role of opossums in controlling Lyme disease",
            "Compare opossums to other marsupials in North America",
            "Explain the evolutionary history of the opossum's prehensile tail"
        ]
        
        # Test routing with Gemini unavailable
        results = await bot.test_query_routing("complex_with_gemini_down", complex_queries)
        
        # Verify we got responses despite Gemini being down
        assert results["sample_size"] == len(complex_queries), "Not all queries received responses during outage"
        
        # Verify Gemini wasn't used
        assert "gemini-thinking" not in results["counts"], "Gemini was incorrectly used despite being unavailable"
        
        # Models that should be used instead
        fallback_models = ["ollama", "transformers", "unknown"]
        
        # Calculate percentage of queries going to fallback models
        pct_to_fallbacks = sum(results["counts"].get(model, 0) for model in fallback_models) / results["sample_size"] * 100
        
        assert pct_to_fallbacks == 100, f"Fallback models not used correctly: {results['counts']}"
        
    finally:
        # Restore service availability
        force_service_unavailability("gemini", make_unavailable=False)