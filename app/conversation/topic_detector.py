import logging
from app.config import Config

logger = logging.getLogger(__name__)

class TopicDetector:
    """NLP-based topic detection for conversation management"""

    def __init__(self):
        try:
            from sentence_transformers import SentenceTransformer
            import numpy as np
            from sklearn.metrics.pairwise import cosine_similarity

            self.model = SentenceTransformer(Config.SENTENCE_TRANSFORMER_MODEL)
            self.cosine_similarity = cosine_similarity

            # Pre-compute embeddings for topics
            self.topic_sentences = {
                "snake_resistance": "Opossums are resistant to snake venom and can eat venomous snakes",
                "florida_opossums": "Opossums in Florida and the southeastern United States",
                "diet_query": "What opossums eat and their diet habits",
                "habitat_query": "Where opossums live and their natural habitat",
                "behavior_query": "Opossum behavior, playing dead, and nocturnal activities",
                "general_info": "General information about opossums",
                "closing": "Thank you, goodbye, or ending the conversation"
            }

            # Precompute the embeddings for efficiency
            self.topic_embeddings = {topic: self.model.encode(sentence)
                                     for topic, sentence in self.topic_sentences.items()}

            logger.info("Initialized TopicDetector with sentence transformer")
        except ImportError:
            logger.error("Required NLP packages not available")
            raise

    def determine_next_stage(self, user_message, current_stage):
        """Determine the next conversation stage using NLP sentence similarity"""
        # Always progress from greeting to initial_query
        if current_stage == "greeting":
            return "initial_query"

        # Get the embedding for the user's message
        message_embedding = self.model.encode(user_message.lower())

        # Calculate similarity scores with all topics
        similarities = {}
        for topic, embedding in self.topic_embeddings.items():
            similarity = self.cosine_similarity([message_embedding], [embedding])[0][0]
            similarities[topic] = similarity

        # Find the topic with the highest similarity score
        max_topic = max(similarities, key=similarities.get)
        max_score = similarities[max_topic]

        # Only change the topic if similarity is high enough
        if max_score > Config.SIMILARITY_THRESHOLD:
            return max_topic

        # For follow-up questions, maintain context by keeping current stage
        follow_up_words = ["more", "also", "another", "explain", "elaborate", "why", "how", "what"]
        is_follow_up = any(word in user_message.lower().split() for word in follow_up_words)

        if is_follow_up and current_stage in self.topic_sentences:
            return current_stage

        # Default to general_info if no clear topic is detected
        return "general_info"