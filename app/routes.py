# app/routes.py
import logging
import random

import emoji
import markovify
from flask import Blueprint, render_template

logger = logging.getLogger(__name__)
bp = Blueprint('routes', __name__)

# Sample opossum texts for Markov chain model training
OPOSSUM_TEXTS = [
    """The Virginia opossum is the only marsupial found north of Mexico. Opossums are opportunistic omnivores with a reputation for eating almost anything. Their diet consists of carrion, rodents, insects, frogs, plants, fruits and garbage. Opossums play dead when threatened, an involuntary response triggered by fear. This is called thanatosis. Opossums have prehensile tails they use for grasping branches and carrying nesting materials.""",

    """Opossums have 50 teeth, more than any other North American land mammal. They are highly resistant to rabies and are immune to most snake venoms. Opossums eat thousands of ticks per season which helps control tick populations and Lyme disease. Baby opossums are called joeys and are born tiny, about the size of a honeybee. They immediately crawl into their mother's pouch after birth.""",

    """Didelphis virginiana has a remarkable immune system and can neutralize various venoms and toxins. Their low body temperature makes them resistant to many diseases. They have opposable thumbs on their hind feet for climbing. Opossums are excellent groomers and clean themselves meticulously, which helps control parasites. They have a relatively short lifespan of 1-2 years in the wild.""",

    """The marsupial reproductive system involves a very short gestation period of just 12-13 days. The joeys develop primarily in the mother's pouch. Opossums have 13 nipples arranged in a circle in the pouch. They perform a behavior called 'playing possum' which involves feigning death when threatened. They will lie motionless with eyes closed, tongue hanging out, and emit a foul-smelling substance.""",

    """Opossums are excellent tree climbers and use their prehensile tails for balance. They are mostly nocturnal, being active primarily at night. While they prefer woodland areas, they adapt well to urban environments. Opossums are generally solitary creatures except during mating season. They are known to eat venomous snakes without suffering harm due to their immunity to snake venom."""
]

# Technical texts for mixed gibberish generation
TECH_TEXTS = [
    """Natural Language Processing (NLP) is a branch of artificial intelligence that helps computers understand, interpret, and manipulate human language. NLP combines computational linguistics, machine learning, and deep learning models.""",

    """API endpoints provide a structured way to interact with a service. REST APIs use HTTP methods like GET, POST, PUT, and DELETE. GraphQL provides a more flexible approach with a single endpoint that can handle complex queries.""",

    """Service availability monitoring tracks the health and performance of system components. Metrics like response time, error rates, and uptime help maintain system reliability. Failover mechanisms ensure continuous service.""",

    """Machine learning models process input data through layers of mathematical computations. Neural networks can identify patterns and make predictions based on training data. Model performance depends on data quality and architecture."""
]

# Emoji categories to include
EMOJI_CATEGORIES = [
    'animal',
    'nature',
    'science',
    'computer',
    'office',
    'technical_symbol'
]

# Markov models cache
_opossum_model = None
_tech_model = None
_combined_model = None


def _get_markov_models():
    """Initialize and cache Markov models."""
    global _opossum_model, _tech_model, _combined_model

    if _combined_model is None:
        # Preprocess texts to ensure good sentence structure
        def preprocess_texts(texts):
            return [text.strip().replace('\n', ' ') for text in texts]

        processed_opossum = preprocess_texts(OPOSSUM_TEXTS)
        processed_tech = preprocess_texts(TECH_TEXTS)

        # Initialize models with processed texts
        _opossum_model = markovify.Text("\n".join(processed_opossum))
        _tech_model = markovify.Text("\n".join(processed_tech))
        # Combine models with more weight on opossum content
        _combined_model = markovify.combine([_opossum_model, _tech_model], [1.5, 1])

    return _combined_model


def _get_random_emojis(count=1):
    """Get random emojis from the specified categories."""
    # Get all emojis in the specified categories
    category_emojis = []
    for emoji_data in emoji.EMOJI_DATA.values():
        if any(cat in EMOJI_CATEGORIES for cat in emoji_data.get('category', '').lower().split()):
            category_emojis.append(emoji_data['emoji'])

    # Return random selection
    return random.sample(category_emojis, min(count, len(category_emojis)))


def _generate_nlp_gibberish(num_lines=25):
    """Generate random opossum-themed text with actual NLP."""
    model = _get_markov_models()
    lines = []

    for _ in range(num_lines):
        try:
            line = model.make_sentence(tries=100)
            if line:
                lines.append(line)
        except Exception as e:
            logger.error(f"Error generating line: {e}")
            continue

    return "\n".join(lines)


@bp.route('/')
def index():
    """Serve the main application page."""
    return render_template('index.html')
