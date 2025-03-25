"""Test suite for resilience features of Opossum Search using bot users.

This module tests how the system handles various failure scenarios and service degradation
using automated bot users that simulate real user behavior.
"""
import asyncio
import logging
import pytest
from datetime import datetime, timedelta

from tests.bots.bot_user import BotUser, ConcurrentBotSimulation

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_basic_bot_interaction(base_url):
    """Test that a single bot can successfully interact with the API."""
    bot = BotUser(base_url=base_url, user_id="test-basic-bot")
    
    # Send a simple message
    response = await bot.send_chat_message("Tell me about opossums")
    
    # Validate response
    assert "response" in response
    assert response.get("error") is None
    assert len(response.get("response", "")) > 0
    
    logger.info(f"Bot received response: {response.get('response', '')[:50]}...")
    
    # Check stats
    stats = bot.get_session_stats()
    assert stats["request_count"] == 1
    assert stats["error_count"] == 0
    assert stats["success_rate"] == 1.0


@pytest.mark.asyncio
async def test_service_resilience_under_load(base_url):
    """Test system resilience under concurrent bot load."""
    # Create a mix of bot profiles to test different query patterns
    behavior_profiles = ["standard", "aggressive", "complex_reasoning", "error_prone"]
    
    # Create concurrent simulation with 10 bots
    simulation = ConcurrentBotSimulation(
        base_url=base_url,
        num_bots=10,
        behavior_profiles=behavior_profiles
    )
    
    # Run simulation with 5 messages per bot and max 5 concurrent bots
    results = await simulation.run_simulation(messages_per_bot=5, max_concurrency=5)
    
    # Check overall success rate
    assert results["success_rate"] >= 0.9, "Success rate below 90% under load"
    
    # Check response times
    assert results["overall_avg_response_time"] < 5.0, "Average response time too high"
    
    # Log detailed results
    logger.info(f"Load test complete. Success rate: {results['success_rate']:.2f}")
    logger.info(f"Average response time: {results['overall_avg_response_time']:.2f}s")
    logger.info(f"Requests per second: {results['requests_per_second']:.2f}")


@pytest.mark.asyncio
async def test_model_fallback_behavior(base_url, force_service_unavailability):
    """Test that the system correctly falls back to alternative models when primary is unavailable."""
    # Temporarily make Gemini unavailable to test fallback
    force_service_unavailability("gemini")
    
    # Create a bot to test fallback behavior
    bot = BotUser(base_url=base_url, user_id="fallback-test-bot")
    
    try:
        # Run a short session with complex reasoning queries that would normally go to Gemini
        bot.query_pool = [
            "Compare opossums to raccoons",
            "Explain why opossums are beneficial to have around",
            "What are the implications of opossums' immunity to snake venom?"
        ]
        
        stats = await bot.run_session(num_messages=3)
        
        # Validate that requests succeeded despite Gemini being unavailable
        assert stats["success_rate"] >= 0.9, "Fallback mechanism failed to handle requests"
        
        # We can't directly test which model was used without additional instrumentation,
        # but we can check that responses were received
        for entry in bot.conversation_history:
            assert "bot_response" in entry
            assert len(entry["bot_response"]) > 0
            
    finally:
        # Restore service availability
        force_service_unavailability("gemini", make_unavailable=False)


@pytest.mark.asyncio
async def test_caching_effectiveness(base_url):
    """Test that the system effectively caches responses for identical queries."""
    bot = BotUser(base_url=base_url, user_id="cache-test-bot")
    
    # Send the same query multiple times to test caching
    query = "What do opossums eat?"
    
    # First query (cold cache)
    first_response = await bot.send_chat_message(query)
    first_response_time = bot.response_times[-1]
    
    # Wait briefly to ensure metrics are recorded
    await asyncio.sleep(1)
    
    # Second query (should hit cache)
    second_response = await bot.send_chat_message(query)
    second_response_time = bot.response_times[-1]
    
    # Third query (definitely should hit cache)
    third_response = await bot.send_chat_message(query)
    third_response_time = bot.response_times[-1]
    
    # Check response consistency (cached responses should match)
    assert first_response.get("response") == second_response.get("response")
    assert second_response.get("response") == third_response.get("response")
    
    # Check if caching improved response time (should be faster, but be lenient about threshold)
    # Use average of second and third to account for any variance
    avg_cached_time = (second_response_time + third_response_time) / 2
    
    logger.info(f"Cold cache response time: {first_response_time:.4f}s")
    logger.info(f"Average cached response time: {avg_cached_time:.4f}s")
    
    # Check for cache effectiveness (cached response should be at least 20% faster)
    assert avg_cached_time < first_response_time * 0.8, "Caching doesn't appear to be effective"


@pytest.mark.asyncio
async def test_error_handling_with_malicious_inputs(base_url):
    """Test that the system handles potentially malicious inputs gracefully."""
    bot = BotUser(base_url=base_url, user_id="error-handling-bot", behavior_profile="error_prone")
    
    # Run a session with error-prone queries
    stats = await bot.run_session(num_messages=8)  # Use all error_prone queries
    
    # We expect some errors with malicious inputs, but the system should handle them gracefully
    assert stats["error_count"] <= 4, "Too many errors triggered by malicious inputs"
    
    # For successful requests, check that responses don't contain error messages
    successful_conversations = [c for c in bot.conversation_history if "error" not in c or not c["error"]]
    
    for conv in successful_conversations:
        # Check for common error strings that shouldn't be exposed to users
        response = conv.get("bot_response", "").lower()
        
        error_indicators = ["exception", "error:", "traceback", "sql syntax", "undefined variable"]
        for indicator in error_indicators:
            assert indicator not in response, f"Error exposed to user: {indicator}"