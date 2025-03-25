"""Background text generation resolvers."""
import logging
import random

import markovify

from app.api.directives import apply_cost, rate_limit
from app.utils.infrastructure.cache_factory import cache

logger = logging.getLogger(__name__)

# Create a simple Markov model for opossum-themed text generation
OPOSSUM_CORPUS = """
Opossums are marsupials of the order Didelphimorphia. The largest order of marsupials in the Western Hemisphere.
Opossums are small to medium-sized marsupials with a rat-like appearance.
The Virginia opossum is the only marsupial found north of Mexico.
Opossums are scavengers and eat almost anything, including fruits, insects, small animals, and carrion.
Baby opossums are called joeys and are born tiny and undeveloped.
Opossums are known for "playing possum" which is an involuntary response to threats.
When threatened, opossums may hiss, growl, or even faint and appear dead.
Opossums have prehensile tails that they can use to grasp objects and hang from tree branches.
Opossums have 50 teeth, more than any other North American land mammal.
Opossums are resistant to many toxins and can eat venomous snakes without harm.
Opossums have excellent immune systems and rarely get sick.
Opossums are beneficial because they eat ticks and help control tick populations.
Opossums have a body temperature too low to host rabies effectively.
Opossums can live in a variety of habitats including forests, farmlands, and urban areas.
Opossums typically live for only 1-2 years in the wild.
"""

# Create Markov text model
try:
    text_model = markovify.Text(OPOSSUM_CORPUS)
except Exception as e:
    logger.error(f"Error creating Markov model: {e}")
    text_model = None

# Opossum-themed emojis
OPOSSUM_EMOJIS = ["🐭", "🐀", "🐹", "🌙", "🌳", "🍃", "🌿", "🍂", "🌲", "🐾", "💤"]

# Easter egg emojis (all bunnies for easter celebration)
EASTER_EGG_EMOJIS = ["🐰", "🐰", "🐰", "🐰", "🐰"]


@apply_cost(value=2)
@rate_limit(limit=60, duration=60)  # 60 requests per minute
async def resolve_generate_gibberish(root, info, num_lines=25):
    """Generate opossum-themed background text with emojis."""
    try:
        # Check cache first
        cache_key = f"gibberish_{num_lines}"
        cached_result = cache.get(cache_key)
        if cached_result:
            logger.debug("Using cached gibberish text")
            return cached_result

        # Generate text if no cache hit
        if not text_model:
            return {
                "text": "Unable to generate text at this time.",
                "emojis": ["❌"]
            }

        # Generate lines of text
        lines = []
        for _ in range(min(num_lines, 100)):  # Cap at 100 lines
            try:
                line = text_model.make_short_sentence(100)
                if line:
                    lines.append(line)
            except Exception:
                continue

        # If we couldn't generate enough lines, fill with fallback text
        while len(lines) < num_lines:
            lines.append("Opossums are fascinating creatures.")

        # Easter egg: rare special facts (1% chance)
        easter_egg_triggered = False
        if random.random() < 0.01:
            easter_egg_triggered = True
            secret_facts = [
                "EASTER EGG: Opossums have existed for over 70 million years, surviving the extinction that killed the dinosaurs!",
                "EASTER EGG: The word 'opossum' comes from the Algonquian language, meaning 'white dog-like animal'.",
                "EASTER EGG: An opossum's body temperature is too low to host the rabies virus effectively!",
                "EASTER EGG: Opossums can eat up to 5,000 ticks per season, helping reduce Lyme disease!",
                "EASTER EGG: You found a secret opossum fact! Baby opossums make a sneezing sound to signal their mother.",
                "EASTER EGG: Opossums have 13 nipples arranged in a circle of 12 with one in the center."
            ]
            lines.insert(random.randint(0, len(lines)), random.choice(secret_facts))

        # Select emojis based on whether easter egg was triggered
        if easter_egg_triggered:
            selected_emojis = EASTER_EGG_EMOJIS  # All bunny emojis on easter egg
        else:
            selected_emojis = random.sample(
                OPOSSUM_EMOJIS,
                min(5, len(OPOSSUM_EMOJIS))
            )

        # Build result
        result = {
            "text": "\n".join(lines),
            "emojis": selected_emojis
        }

        # Cache for 5 minutes
        cache.set(cache_key, result, expire=300)

        return result
    except Exception as e:
        logger.error(f"Error generating gibberish: {e}")
        return {
            "text": "Error generating text.",
            "emojis": ["❌"]
        }
