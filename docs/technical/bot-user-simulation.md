# Bot User Simulation Framework

## Overview

The Bot User Simulation Framework provides automated testing capabilities for Opossum Search by simulating realistic
user behavior. This framework is particularly useful for testing:

1. **Resilience** - How the system handles high load, service failures, and error cases
2. **Special Features** - Testing date-specific Easter eggs and hidden commands
3. **Model Selection** - Verifying that the hybrid model selection system routes queries correctly

## Bot Types

The framework includes several types of bot users:

| Bot Type                   | Description                           | Main Use Cases                                        |
|----------------------------|---------------------------------------|-------------------------------------------------------|
| `BotUser`                  | Standard bot that sends chat messages | General testing, resilience testing                   |
| `TimeBasedBotUser`         | Bot that simulates specific dates     | Testing date-based features like National Opossum Day |
| `NationalOpossumDayTester` | Specialized bot for Oct 18 features   | Comprehensive testing of National Opossum Day         |
| `ModelSelectionBot`        | Analyzes model selection patterns     | Testing the hybrid model routing system               |

## Behavior Profiles

Bots can be configured with different behavior profiles to simulate various user patterns:

- **standard** - Normal user behavior with standard queries
- **aggressive** - Rapid-fire requests with minimal delays
- **error_prone** - Sends malformed or potentially malicious queries
- **easter_egg_hunter** - Specifically tests Easter egg commands and special features

## Query Sets

Each bot is pre-configured with different sets of queries:

- **standard** - Common opossum-related questions
- **complex_reasoning** - Questions requiring deeper analysis
- **error_prone** - Malformed or potentially harmful inputs
- **easter_eggs** - Known Easter egg commands and triggers

## Usage Examples

### Basic Bot Testing

```python
import asyncio
from tests.bots.bot_user import BotUser

async def test_basic_interaction():
    bot = BotUser(base_url="http://localhost:5000")
    response = await bot.send_chat_message("Tell me about opossums")
    print(f"Response: {response.get('response')}")
    
    # Run a complete session with 5 messages
    stats = await bot.run_session(num_messages=5)
    print(f"Session stats: {stats}")
```

### Testing National Opossum Day

```python
import asyncio
from datetime import date
from tests.bots.bot_user import NationalOpossumDayTester

async def test_national_opossum_day():
    # Tests with simulated date of October 18
    bot = NationalOpossumDayTester(base_url="http://localhost:5000")
    results = await bot.test_national_opossum_day_features()
    
    # Check which features were detected
    print(f"Features detected: {results['features_detected_count']}/4")
    print(f"Features: {results['special_features_detected']}")
```

### Simulating Multiple Users

```python
import asyncio
from tests.bots.bot_user import ConcurrentBotSimulation

async def run_load_test():
    # Create a simulation with 10 bots using different profiles
    simulation = ConcurrentBotSimulation(
        base_url="http://localhost:5000",
        num_bots=10,
        behavior_profiles=["standard", "aggressive", "error_prone"]
    )
    
    # Run with 5 messages per bot, 5 bots at a time
    results = await simulation.run_simulation(messages_per_bot=5, max_concurrency=5)
    
    print(f"Success rate: {results['success_rate']}")
    print(f"Avg response time: {results['overall_avg_response_time']}s")
```

## Testing Model Selection

The framework includes specialized tools for testing that queries are routed to the appropriate models:

```python
import asyncio
from tests.bots.test_model_selection import ModelSelectionBot

async def test_query_routing():
    bot = ModelSelectionBot(base_url="http://localhost:5000")
    
    # Test complex reasoning queries
    reasoning_queries = [
        "Compare opossums to raccoons",
        "Explain why opossums are beneficial to have around"
    ]
    
    results = await bot.test_query_routing("reasoning", reasoning_queries)
    print(f"Model selection: {results['counts']}")
```

## Fixture Integration

The bot framework integrates with pytest fixtures for easier test creation:

- **base_url** - Provides the API URL for testing
- **force_service_unavailability** - Temporarily makes services unavailable for testing fallback
- **capture_model_selections** - Records model selection patterns
- **run_concurrent_bots** - Runs multiple bots with configurable parameters

Example usage with fixtures:

```python
import pytest

@pytest.mark.asyncio
async def test_model_fallback(base_url, force_service_unavailability):
    # Temporarily make Gemini unavailable
    force_service_unavailability("gemini")
    
    # Bot should now use fallback models
    bot = BotUser(base_url=base_url)
    response = await bot.send_chat_message("Analyze the benefits of opossums")
    
    # Then restore service
    force_service_unavailability("gemini", make_unavailable=False)
```

## Running the Test Suite

To run the full bot user test suite:

```bash
pytest tests/bots/ -v
```

To run specific test types:

```bash
# Test resilience
pytest tests/bots/test_resilience.py -v

# Test Easter eggs
pytest tests/bots/test_easter_eggs.py -v

# Test model selection
pytest tests/bots/test_model_selection.py -v
```

## Extending the Framework

The bot simulation framework is designed to be extensible. To create a new specialized bot:

1. Subclass one of the existing bot classes
2. Override methods as needed for specialized behavior
3. Add new query types or behavior patterns

Example:

```python
class CustomBot(BotUser):
    def __init__(self, base_url, **kwargs):
        super().__init__(base_url, **kwargs)
        self.custom_feature_detected = False
        
    async def analyze_response(self, response):
        # Custom analysis logic
        if "specific pattern" in response.get("response", ""):
            self.custom_feature_detected = True
        return response
```

## Performance Considerations

- Bot users create real load on the system
- Consider running resource-intensive tests in isolation
- For load testing, start with small numbers of bots and increase gradually
- Set reasonable message delays for realistic traffic patterns