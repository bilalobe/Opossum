"""Sentiment analysis for conversation responses."""

import logging
from collections import deque
from typing import Dict, Any, Tuple

import numpy as np
from textblob import TextBlob

logger = logging.getLogger(__name__)


class SentimentTracker:
    """Tracks conversation sentiment and engagement metrics."""

    def __init__(self, window_size: int = 5):
        self.window_size = window_size
        self.sentiment_history = deque(maxlen=window_size)
        self.engagement_metrics = {
            "avg_response_length": 0,
            "topic_changes": 0,
            "follow_up_questions": 0,
            "sentiment_trend": 0.0
        }

    def analyze_message(self, message: str, is_follow_up: bool = False) -> Dict[str, Any]:
        """Analyze message sentiment and update metrics."""
        blob = TextBlob(message)
        sentiment_scores = {
            "polarity": blob.sentiment.polarity,
            "subjectivity": blob.sentiment.subjectivity
        }

        # Update sentiment history
        self.sentiment_history.append(sentiment_scores["polarity"])

        # Calculate sentiment trend
        if len(self.sentiment_history) >= 2:
            trend = np.polyfit(
                range(len(self.sentiment_history)),
                list(self.sentiment_history),
                1
            )[0]
            self.engagement_metrics["sentiment_trend"] = float(trend)

        # Update engagement metrics
        self.engagement_metrics["avg_response_length"] = (
                (self.engagement_metrics["avg_response_length"] *
                 (len(self.sentiment_history) - 1) + len(message)) /
                len(self.sentiment_history)
        )

        if is_follow_up:
            self.engagement_metrics["follow_up_questions"] += 1

        return {
            "sentiment": sentiment_scores,
            "engagement": self.engagement_metrics
        }

    def get_conversation_mood(self) -> Tuple[str, float]:
        """Get overall conversation mood based on recent sentiment."""
        if not self.sentiment_history:
            return "neutral", 0.0

        avg_sentiment = sum(self.sentiment_history) / len(self.sentiment_history)

        if avg_sentiment > 0.3:
            mood = "positive"
        elif avg_sentiment < -0.3:
            mood = "negative"
        else:
            mood = "neutral"

        return mood, avg_sentiment

    def detect_sentiment_shift(self, threshold: float = 0.5) -> bool:
        """Detect significant shifts in conversation sentiment."""
        if len(self.sentiment_history) < 2:
            return False

        recent = self.sentiment_history[-1]
        previous_avg = sum(list(self.sentiment_history)[:-1]) / (len(self.sentiment_history) - 1)

        return abs(recent - previous_avg) > threshold

    def get_engagement_summary(self) -> Dict[str, Any]:
        """Get summary of conversation engagement metrics."""
        mood, avg_sentiment = self.get_conversation_mood()

        return {
            "mood": mood,
            "avg_sentiment": avg_sentiment,
            "metrics": self.engagement_metrics,
            "needs_reengagement": self._needs_reengagement()
        }

    def _needs_reengagement(self) -> bool:
        """Determine if conversation needs reengagement strategies."""
        if not self.sentiment_history:
            return False

        conditions = [
            self.engagement_metrics["sentiment_trend"] < -0.2,
            self.engagement_metrics["avg_response_length"] < 10,
            len(self.sentiment_history) >= 3 and
            all(s < 0 for s in list(self.sentiment_history)[-3:])
        ]

        return any(conditions)
