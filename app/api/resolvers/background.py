"""Background text generation resolvers."""
import logging
from app.routes import _get_markov_models, _get_random_emojis

logger = logging.getLogger(__name__)

async def resolve_generate_gibberish(root, info, num_lines=25):
    """Generate background gibberish text with emojis."""
    try:
        opossum_model, tech_model = _get_markov_models()
        
        # Generate sentences alternating between models
        sentences = []
        for i in range(num_lines):
            model = opossum_model if i % 2 == 0 else tech_model
            sentences.append(model.make_sentence() or "Opossums are fascinating creatures!")

        text = " ".join(sentences)
        emojis = _get_random_emojis(count=5)
        
        return {
            "text": text,
            "emojis": emojis
        }
    except Exception as e:
        logger.error(f"Error generating background text: {e}")
        raise