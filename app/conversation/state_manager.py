"""Conversation state management and context tracking."""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class ConversationState:
    """Represents the current state of a conversation."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.current_stage = "greeting"
        self.last_topic = None
        self.topic_history: List[str] = []
        self.message_history: List[Dict[str, Any]] = []
        self.last_interaction = datetime.now()
        self.context: Dict[str, Any] = {}
        self.user_preferences: Dict[str, Any] = {}

    def add_message(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add a message to the conversation history."""
        self.message_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        })
        self.last_interaction = datetime.now()

    def update_stage(self, new_stage: str) -> None:
        """Update conversation stage and maintain history."""
        if new_stage != self.current_stage:
            self.topic_history.append(self.current_stage)
            self.current_stage = new_stage
            self.last_topic = new_stage

    def is_expired(self, timeout_minutes: int = 30) -> bool:
        """Check if conversation has expired due to inactivity."""
        return (datetime.now() - self.last_interaction) > timedelta(minutes=timeout_minutes)

    def get_context_window(self, window_size: int = 5) -> List[Dict[str, Any]]:
        """Get recent conversation context."""
        return self.message_history[-window_size:] if self.message_history else []

    def add_context(self, key: str, value: Any) -> None:
        """Add contextual information to the conversation."""
        self.context[key] = value

    def set_preference(self, key: str, value: Any) -> None:
        """Set a user preference."""
        self.user_preferences[key] = value


class ConversationManager:
    """Manages multiple conversation states and their lifecycles."""

    def __init__(self, timeout_minutes: int = 30):
        self.conversations: Dict[str, ConversationState] = {}
        self.timeout_minutes = timeout_minutes
        self._cleanup_interval = timedelta(minutes=5)
        self._last_cleanup = datetime.now()

    def get_conversation(self, session_id: str) -> ConversationState:
        """Get or create a conversation state for a session."""
        self._cleanup_expired()

        if session_id not in self.conversations:
            self.conversations[session_id] = ConversationState(session_id)
        return self.conversations[session_id]

    def end_conversation(self, session_id: str) -> None:
        """Explicitly end a conversation."""
        if session_id in self.conversations:
            del self.conversations[session_id]

    def _cleanup_expired(self) -> None:
        """Remove expired conversations."""
        now = datetime.now()
        if (now - self._last_cleanup) < self._cleanup_interval:
            return

        expired = [
            sid for sid, conv in self.conversations.items()
            if conv.is_expired(self.timeout_minutes)
        ]
        for session_id in expired:
            del self.conversations[session_id]

        if expired:
            logger.info(f"Cleaned up {len(expired)} expired conversations")
        self._last_cleanup = now
