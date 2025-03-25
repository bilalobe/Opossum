"""Test suite for Easter egg features of Opossum Search using bot users.

This module tests the special Easter egg features, including National Opossum Day
and other hidden features using automated bot users with time manipulation.
"""
import asyncio
import logging
import pytest
from datetime import datetime, date, timedelta

from tests.bots.bot_user import BotUser, TimeBasedBotUser, NationalOpossumDayTester

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_national_opossum_day_activation(base_url):
    """Test that National Opossum Day features activate on October 18."""
    # Create a bot that thinks it's October 18 (National Opossum Day)
    bot = TimeBasedBotUser(
        base_url=base_url,
        user_id="national-day-bot",
        simulated_date=date(2025, 10, 18)
    )
    
    # Send a standard message that should trigger the special day features
    response = await bot.send_chat_message("Tell me about opossums")
    
    # Check response for National Opossum Day references
    assert "response" in response
    assert response.get("error") is None
    
    # National Opossum Day should be mentioned in the response
    # (This assumes the system identifies the date from the X-Simulated-Date header)
    response_text = response.get("response", "").lower()
    
    # Look for indicators of National Opossum Day activation
    day_indicators = ["national opossum day", "october 18", "celebrate", "special day"]
    
    found_indicators = [indicator for indicator in day_indicators if indicator in response_text]
    
    assert len(found_indicators) > 0, f"National Opossum Day not detected in response: {response_text[:100]}..."
    
    logger.info(f"National Opossum Day references found: {found_indicators}")


@pytest.mark.asyncio
async def test_national_opossum_day_nonactivation(base_url):
    """Test that National Opossum Day features do NOT activate on other dates."""
    # Create a bot that thinks it's October 17 (day before National Opossum Day)
    bot = TimeBasedBotUser(
        base_url=base_url,
        user_id="not-national-day-bot",
        simulated_date=date(2025, 10, 17)
    )
    
    # Send the same message as the previous test
    response = await bot.send_chat_message("Tell me about opossums")
    
    # Check that the response doesn't contain special day references
    assert "response" in response
    
    response_text = response.get("response", "").lower()
    
    # The response should not specifically mention National Opossum Day
    day_indicators = ["national opossum day", "october 18", "today is special"]
    
    found_indicators = [indicator for indicator in day_indicators if indicator in response_text]
    
    assert len(found_indicators) == 0, f"National Opossum Day incorrectly activated: {found_indicators}"


@pytest.mark.asyncio
async def test_possum_party_command(base_url):
    """Test that the 'possum party' command triggers special features."""
    # This should work on any date
    bot = BotUser(base_url=base_url, user_id="possum-party-bot")
    
    # Send the special command
    response = await bot.send_chat_message("possum party")
    
    # Check for party command acknowledgment
    assert "response" in response
    assert response.get("error") is None
    
    response_text = response.get("response", "").lower()
    
    # Look for party mode indicators
    party_indicators = ["party", "dance", "celebration", "mode activated", "special mode"]
    
    found_indicators = [indicator for indicator in party_indicators if indicator in response_text]
    
    assert len(found_indicators) > 0, f"Possum party command not recognized: {response_text[:100]}..."
    
    # Also check if svg content is returned (dancing opossums animation)
    assert response.get("has_svg", False) or "animation" in response_text, "No visual elements returned for possum party"


@pytest.mark.asyncio
async def test_play_possum_command(base_url):
    """Test that the 'play possum' command triggers the playing dead animation."""
    bot = BotUser(base_url=base_url, user_id="play-possum-bot")
    
    # Send the special command
    response = await bot.send_chat_message("play possum")
    
    # Check for play dead acknowledgment
    assert "response" in response
    assert response.get("error") is None
    
    response_text = response.get("response", "").lower()
    
    # Look for play dead indicators
    play_dead_indicators = ["played dead", "playing dead", "back to life", "thanatosis"]
    
    found_indicators = [indicator for indicator in play_dead_indicators if indicator in response_text]
    
    assert len(found_indicators) > 0, f"Play possum command not recognized: {response_text[:100]}..."


@pytest.mark.asyncio
async def test_comprehensive_national_opossum_day(base_url):
    """Run a comprehensive test of all National Opossum Day features."""
    # Use the specialized National Opossum Day tester
    bot = NationalOpossumDayTester(base_url=base_url, user_id="full-national-day-test")
    
    # Run the specialized test
    results = await bot.test_national_opossum_day_features()
    
    # Log the results
    logger.info(f"National Opossum Day feature testing complete")
    logger.info(f"Features detected: {results['features_detected_count']}/4")
    logger.info(f"Features: {results['special_features_detected']}")
    
    # Check that at least 3 out of 4 special features were detected
    # This allows for some flexibility in implementation
    assert results["features_detected_count"] >= 3, "Not enough National Opossum Day features detected"
    
    # Specifically check for possum party command recognition
    assert results["special_features_detected"]["possum_party_command"], "Possum party command not recognized"
    
    # Check that the session was successful overall
    assert results["session_stats"]["success_rate"] >= 0.9, "National Opossum Day session had too many errors"