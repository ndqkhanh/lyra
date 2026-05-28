"""Session state models."""
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class SessionState:
    """State for a session."""

    session_id: str
    created_at: datetime
    last_updated: datetime
    conversation_history: list
    context: dict[str, Any]
    metadata: dict[str, Any] | None = None
