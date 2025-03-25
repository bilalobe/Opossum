"""Bot user simulation framework for testing Opossum Search.

This module provides classes for automated testing of the Opossum Search system
through simulated user interactions. It includes various specialized bot types
for different testing scenarios.
"""
import asyncio
import logging
import random
import uuid
import time
import json
import httpx
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple

logger = logging.getLogger(__name__)


class BotUser:
    """Base class for simulated bot users.
    
    Attributes:
        base_url: The API endpoint base URL
        user_id: Unique identifier for this bot
        session_id: Unique session identifier
        behavior_profile: The behavioral pattern this bot will follow
        conversation_history: List of interactions with the system
        response_times: List of response times for performance tracking
        min_delay: Minimum seconds to wait between messages
        max_delay: Maximum seconds to wait between messages
        query_pool: List of queries this bot can send
        query_sets: Predefined sets of queries for different scenarios
        session_length: Number of interactions in a typical session
    """
    
    def __init__(self, base_url: str, user_id: Optional[str] = None, 
                behavior_profile: str = "standard"):
        """Initialize a bot user.
        
        Args:
            base_url: The API endpoint base URL
            user_id: Optional unique identifier (auto-generated if not provided)
            behavior_profile: The behavioral pattern this bot will follow
        """
        self.base_url = base_url
        self.user_id = user_id or f"bot-{uuid.uuid4()}"
        self.session_id = f"session-{uuid.uuid4()}"
        self.behavior_profile = behavior_profile
        
        # Track conversation and performance
        self.conversation_history = []
        self.response_times = []
        self.errors = []
        
        # Configure behavior based on profile
        self._configure_behavior_profile(behavior_profile)
        
        # Session configuration
        self.session_length = 5  # Default session length
        
        logger.info(f"Initialized bot user {self.user_id} with {behavior_profile} profile")
    
    def _configure_behavior_profile(self, profile: str):
        """Configure bot behavior based on the selected profile.
        
        Args:
            profile: The behavior profile to use
        """
        # Set delay between messages based on profile
        if profile == "aggressive":
            self.min_delay = 0.1
            self.max_delay = 1.0
        elif profile == "careful":
            self.min_delay = 3.0
            self.max_delay = 8.0
        else:  # standard
            self.min_delay = 1.0
            self.max_delay = 3.0
        
        # Define query sets for different testing scenarios
        self.query_sets = {
            "standard": [
                "Tell me about opossums",
                "What do opossums eat?",
                "Do opossums carry diseases?",
                "How do opossums protect themselves?",
                "Where do opossums live?",
                "How long do opossums live?",
                "What are baby opossums called?",
                "Are opossums dangerous?",
                "Do opossums eat ticks?",
                "What predators do opossums have?"
            ],
            "complex_reasoning": [
                "Compare opossums to other marsupials in North America",
                "Explain the ecological benefits of having opossums in suburban environments",
                "Analyze the evolutionary advantages of the opossum's marsupial reproductive system",
                "What would happen to tick populations if opossums disappeared from an ecosystem?",
                "Synthesize what we know about opossum immunity to snake venom and the implications for medical research",
                "How would climate change likely affect opossum populations and distribution?",
                "What are the causes of negative perceptions of opossums and how might these be addressed?",
                "Compare the advantages and disadvantages of the opossum's 'playing dead' strategy versus active defense"
            ],
            "error_prone": [
                "",  # Empty query
                "SELECT * FROM users;",  # SQL injection attempt
                "<script>alert('XSS')</script>",  # XSS attempt
                "a" * 10000,  # Very long input
                "/?&$%#@!",  # Special characters
                "null undefined NaN",  # Programming terms
                "rm -rf / || del /f /s /q c:\\",  # Command injection attempt
                "{\"malformed\": json"  # Malformed JSON
            ],
            "easter_eggs": [
                "play possum",
                "possum party",
                "national opossum day",
                "konami code",
                "opossum easter egg",
                "tell me a secret about opossums",
                "happy birthday opossum",
                "developer mode"
            ]
        }
        
        # Set query pool based on profile
        if profile == "standard":
            self.query_pool = self.query_sets["standard"].copy()
        elif profile == "complex_reasoning":
            self.query_pool = self.query_sets["complex_reasoning"].copy()
        elif profile == "error_prone":
            self.query_pool = self.query_sets["error_prone"].copy()
        elif profile == "easter_egg_hunter":
            self.query_pool = self.query_sets["easter_eggs"].copy()
        else:
            # Default to standard
            self.query_pool = self.query_sets["standard"].copy()
    
    async def send_chat_message(self, message: str) -> Dict[str, Any]:
        """Send a chat message to the API.
        
        Args:
            message: The message to send
            
        Returns:
            The response from the API
        """
        # Record start time for response time tracking
        start_time = time.time()
        
        # Create a GraphQL query
        query = """
        mutation SendChatMessage($input: ChatInput!) {
            chat(input: $input) {
                response
                next_stage
                has_svg
                svg_content
                base64_image
                error
            }
        }
        """
        
        variables = {
            "input": {
                "message": message,
                "session_id": self.session_id,
                "has_image": False,
                "image_data": None
            }
        }
        
        # Prepare request data
        request_data = {
            "query": query,
            "variables": variables
        }
        
        logger.debug(f"Bot {self.user_id} sending message: {message[:50]}...")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/graphql",
                    json=request_data,
                    headers=self._get_headers()
                )
                
                # Record response time
                response_time = time.time() - start_time
                self.response_times.append(response_time)
                
                # Process response
                if response.status_code == 200:
                    response_data = response.json()
                    
                    if "errors" in response_data:
                        error = response_data["errors"][0]["message"]
                        self.errors.append({
                            "message": message,
                            "error": error,
                            "time": datetime.now().isoformat()
                        })
                        
                        logger.warning(f"Bot {self.user_id} received error: {error}")
                        
                        result = {"error": error}
                    else:
                        result = response_data["data"]["chat"]
                else:
                    error = f"HTTP Error: {response.status_code} - {response.text}"
                    self.errors.append({
                        "message": message,
                        "error": error,
                        "time": datetime.now().isoformat()
                    })
                    
                    logger.warning(f"Bot {self.user_id} received HTTP error: {response.status_code}")
                    
                    result = {"error": error}
                
                # Add to conversation history
                self.conversation_history.append({
                    "user_message": message,
                    "bot_response": result.get("response"),
                    "has_svg": result.get("has_svg", False),
                    "error": result.get("error"),
                    "response_time": response_time,
                    "timestamp": datetime.now().isoformat()
                })
                
                # Apply bot-specific response processing
                return await self.analyze_response(result)
                
        except Exception as e:
            error = f"Exception: {str(e)}"
            logger.error(f"Bot {self.user_id} exception: {error}")
            
            self.errors.append({
                "message": message,
                "error": error,
                "time": datetime.now().isoformat()
            })
            
            result = {"error": error}
            
            # Add to conversation history
            self.conversation_history.append({
                "user_message": message,
                "error": error,
                "timestamp": datetime.now().isoformat()
            })
            
            return result
    
    async def analyze_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze the response from the API.
        
        This method can be overridden by subclasses to add specialized
        response analysis. The base implementation just returns the response.
        
        Args:
            response: The response from the API
            
        Returns:
            The processed response
        """
        return response
    
    async def run_session(self, num_messages: Optional[int] = None) -> Dict[str, Any]:
        """Run a complete conversation session.
        
        Args:
            num_messages: Number of messages to send (defaults to self.session_length)
            
        Returns:
            Session statistics
        """
        if num_messages is None:
            num_messages = self.session_length
        
        start_time = time.time()
        query_pool_copy = self.query_pool.copy()
        
        logger.info(f"Bot {self.user_id} starting session with {num_messages} messages")
        
        for i in range(num_messages):
            # If we've used all queries, reset the pool
            if not query_pool_copy:
                query_pool_copy = self.query_pool.copy()
            
            # Select a random query from the pool
            query_index = random.randint(0, len(query_pool_copy) - 1)
            query = query_pool_copy.pop(query_index)
            
            # Send the message
            await self.send_chat_message(query)
            
            # Simulate user think time between messages (if not the last message)
            if i < num_messages - 1:
                delay = random.uniform(self.min_delay, self.max_delay)
                await asyncio.sleep(delay)
        
        # Calculate session statistics
        session_time = time.time() - start_time
        stats = self.get_session_stats()
        
        logger.info(f"Bot {self.user_id} completed session in {session_time:.2f}s with success rate {stats['success_rate']:.2f}")
        
        return stats
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get statistics about the current session.
        
        Returns:
            Dictionary with session statistics
        """
        if not self.conversation_history:
            return {
                "request_count": 0,
                "error_count": 0,
                "success_rate": 0,
                "avg_response_time": 0,
                "session_length": 0
            }
        
        request_count = len(self.conversation_history)
        error_count = len([c for c in self.conversation_history if "error" in c and c["error"]])
        success_count = request_count - error_count
        success_rate = success_count / request_count if request_count > 0 else 0
        
        # Calculate average response time for successful requests
        successful_times = [c.get("response_time", 0) for c in self.conversation_history 
                           if "error" not in c or not c["error"]]
        
        avg_response_time = sum(successful_times) / len(successful_times) if successful_times else 0
        
        return {
            "request_count": request_count,
            "error_count": error_count,
            "success_count": success_count,
            "success_rate": success_rate,
            "avg_response_time": avg_response_time,
            "min_response_time": min(self.response_times) if self.response_times else 0,
            "max_response_time": max(self.response_times) if self.response_times else 0,
            "session_length": len(self.conversation_history)
        }
    
    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for API requests.
        
        Returns:
            Dictionary with headers
        """
        return {
            "Content-Type": "application/json",
            "User-Agent": f"OposumBot/{self.user_id}",
            "X-Bot-ID": self.user_id,
            "X-Session-ID": self.session_id
        }


class TimeBasedBotUser(BotUser):
    """Bot user that simulates requests at a specific date/time.
    
    This is useful for testing features that are date-dependent,
    such as National Opossum Day (October 18).
    
    Attributes:
        simulated_date: The date to simulate for requests
    """
    
    def __init__(self, base_url: str, user_id: Optional[str] = None,
                behavior_profile: str = "standard", 
                simulated_date: Optional[date] = None):
        """Initialize a time-based bot user.
        
        Args:
            base_url: The API endpoint base URL
            user_id: Optional unique identifier
            behavior_profile: The behavioral pattern this bot will follow
            simulated_date: The date to simulate (defaults to today)
        """
        super().__init__(base_url, user_id, behavior_profile)
        
        self.simulated_date = simulated_date or date.today()
        
        logger.info(f"Bot {self.user_id} simulating date: {self.simulated_date}")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers including simulated date for API requests.
        
        Returns:
            Dictionary with headers
        """
        headers = super()._get_headers()
        
        # Add simulated date header
        headers["X-Simulated-Date"] = self.simulated_date.isoformat()
        
        return headers


class NationalOpossumDayTester(TimeBasedBotUser):
    """Specialized bot for testing National Opossum Day features.
    
    This bot is configured specifically to test the special features
    that activate on October 18 (National Opossum Day).
    """
    
    def __init__(self, base_url: str, user_id: Optional[str] = None):
        """Initialize a National Opossum Day tester bot.
        
        Args:
            base_url: The API endpoint base URL
            user_id: Optional unique identifier
        """
        # Set date to October 18 of current year
        today = date.today()
        opossum_day = date(today.year, 10, 18)
        
        # If October 18 already passed this year, use next year
        if opossum_day < today:
            opossum_day = date(today.year + 1, 10, 18)
        
        super().__init__(
            base_url=base_url, 
            user_id=user_id or "national-opossum-day-tester",
            behavior_profile="easter_egg_hunter",
            simulated_date=opossum_day
        )
        
        # Special flags for feature detection
        self.special_features_detected = {
            "festive_ui_elements": False,
            "special_responses": False,
            "possum_party_command": False,
            "playing_dead_command": False
        }
    
    async def analyze_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze the response for National Opossum Day features.
        
        Args:
            response: The response from the API
            
        Returns:
            The processed response
        """
        response_text = response.get("response", "").lower()
        has_svg = response.get("has_svg", False)
        
        # Check for special day references
        special_day_indicators = ["national opossum day", "october 18", "celebrate", "special day"]
        if any(indicator in response_text for indicator in special_day_indicators):
            self.special_features_detected["special_responses"] = True
            logger.info(f"Bot {self.user_id} detected special day response")
        
        # Check for festive UI elements indicator
        festive_ui_indicators = ["party hat", "animated", "confetti", "celebration", "festive"]
        if any(indicator in response_text for indicator in festive_ui_indicators):
            self.special_features_detected["festive_ui_elements"] = True
            logger.info(f"Bot {self.user_id} detected festive UI reference")
        
        # Check for SVG content which could indicate special visuals
        if has_svg:
            self.special_features_detected["festive_ui_elements"] = True
            logger.info(f"Bot {self.user_id} detected SVG content")
        
        return response
    
    async def test_national_opossum_day_features(self) -> Dict[str, Any]:
        """Run a comprehensive test of National Opossum Day features.
        
        Returns:
            Dictionary with test results
        """
        logger.info(f"Bot {self.user_id} testing National Opossum Day features")
        
        # 1. Basic query to test day activation
        await self.send_chat_message("Tell me about opossums")
        
        # 2. Test possum party command
        party_response = await self.send_chat_message("possum party")
        party_text = party_response.get("response", "").lower()
        party_indicators = ["party", "dance", "celebration", "mode activated"]
        
        if any(indicator in party_text for indicator in party_indicators) or party_response.get("has_svg", False):
            self.special_features_detected["possum_party_command"] = True
            logger.info(f"Bot {self.user_id} detected possum party command")
        
        # 3. Test playing dead command
        play_dead_response = await self.send_chat_message("play possum")
        play_dead_text = play_dead_response.get("response", "").lower()
        play_dead_indicators = ["played dead", "playing dead", "back to life", "thanatosis"]
        
        if any(indicator in play_dead_text for indicator in play_dead_indicators):
            self.special_features_detected["playing_dead_command"] = True
            logger.info(f"Bot {self.user_id} detected playing dead command")
        
        # 4. Send a few more queries to test consistent special responses
        await self.send_chat_message("What do opossums eat?")
        await self.send_chat_message("How do opossums play dead?")
        
        # Calculate results
        features_detected_count = sum(1 for feature, detected in self.special_features_detected.items() if detected)
        
        return {
            "features_detected_count": features_detected_count,
            "special_features_detected": self.special_features_detected,
            "session_stats": self.get_session_stats()
        }


class ConcurrentBotSimulation:
    """Manages multiple bot users for concurrent testing.
    
    This class creates and coordinates multiple bot users to simulate
    realistic load and concurrent usage patterns.
    
    Attributes:
        base_url: The API endpoint base URL
        bots: List of bot users in this simulation
    """
    
    def __init__(self, base_url: str, num_bots: int = 5, 
                behavior_profiles: Optional[List[str]] = None):
        """Initialize a bot simulation.
        
        Args:
            base_url: The API endpoint base URL
            num_bots: Number of bot users to create
            behavior_profiles: List of behavior profiles to use (cycled through)
        """
        self.base_url = base_url
        self.bots = []
        
        # Default behavior profiles if none provided
        if not behavior_profiles:
            behavior_profiles = ["standard", "aggressive", "standard", "careful", "error_prone"]
        
        # Create the requested number of bots
        for i in range(num_bots):
            # Cycle through behavior profiles
            profile = behavior_profiles[i % len(behavior_profiles)]
            
            bot = BotUser(
                base_url=base_url,
                user_id=f"sim-bot-{i+1}",
                behavior_profile=profile
            )
            
            self.bots.append(bot)
        
        logger.info(f"Created simulation with {num_bots} bots")
    
    async def run_simulation(self, messages_per_bot: Union[int, List[int]] = 5,
                           max_concurrency: int = 5,
                           max_duration: Optional[float] = None) -> Dict[str, Any]:
        """Run a simulation with multiple concurrent bots.
        
        Args:
            messages_per_bot: Number of messages per bot (int or list for varied lengths)
            max_concurrency: Maximum number of bots to run concurrently
            max_duration: Maximum duration in seconds (None for unlimited)
            
        Returns:
            Dictionary with simulation results
        """
        # Normalize messages_per_bot to a list
        if isinstance(messages_per_bot, int):
            messages_per_bot = [messages_per_bot] * len(self.bots)
        
        # Ensure we have the right number of message counts
        if len(messages_per_bot) < len(self.bots):
            messages_per_bot.extend([5] * (len(self.bots) - len(messages_per_bot)))
        
        # Track start time for performance metrics
        start_time = time.time()
        
        # Run bots in controlled batches to limit concurrency
        for i in range(0, len(self.bots), max_concurrency):
            # Check if we've exceeded the maximum duration
            if max_duration and time.time() - start_time > max_duration:
                logger.warning(f"Simulation exceeded maximum duration of {max_duration}s")
                break
            
            batch = self.bots[i:i+max_concurrency]
            batch_tasks = []
            
            for j, bot in enumerate(batch):
                # Get the appropriate message count for this bot
                bot_index = i + j
                msg_count = messages_per_bot[bot_index] if bot_index < len(messages_per_bot) else 5
                
                # Create task for this bot's session
                task = bot.run_session(num_messages=msg_count)
                batch_tasks.append(task)
            
            # Run this batch of bots concurrently
            logger.info(f"Running batch of {len(batch_tasks)} bots (batch {i//max_concurrency + 1})")
            await asyncio.gather(*batch_tasks)
        
        # Calculate overall simulation statistics
        total_duration = time.time() - start_time
        simulation_stats = self._calculate_simulation_stats(total_duration)
        
        logger.info(f"Simulation completed in {total_duration:.2f}s with " +
                  f"{simulation_stats['total_requests']} total requests " +
                  f"({simulation_stats['requests_per_second']:.2f} req/s)")
        
        return simulation_stats
    
    def _calculate_simulation_stats(self, duration: float) -> Dict[str, Any]:
        """Calculate statistics for the entire simulation.
        
        Args:
            duration: Total duration of the simulation in seconds
            
        Returns:
            Dictionary with simulation statistics
        """
        # Collect stats from all bots
        all_stats = [bot.get_session_stats() for bot in self.bots]
        
        # Sum up key metrics
        total_requests = sum(stats["request_count"] for stats in all_stats)
        total_errors = sum(stats["error_count"] for stats in all_stats)
        success_rate = (total_requests - total_errors) / total_requests if total_requests > 0 else 0
        
        # Collect all response times
        all_response_times = []
        for bot in self.bots:
            all_response_times.extend(bot.response_times)
        
        # Calculate request rate
        requests_per_second = total_requests / duration if duration > 0 else 0
        
        # Calculate overall average response time
        overall_avg_response_time = sum(all_response_times) / len(all_response_times) if all_response_times else 0
        
        return {
            "total_requests": total_requests,
            "total_errors": total_errors,
            "success_rate": success_rate,
            "requests_per_second": requests_per_second,
            "duration": duration,
            "overall_avg_response_time": overall_avg_response_time,
            "min_response_time": min(all_response_times) if all_response_times else 0,
            "max_response_time": max(all_response_times) if all_response_times else 0,
            "bot_count": len(self.bots),
            "individual_bot_stats": all_stats
        }