"""Session state models."""
from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime


@dataclass
class SessionState:
    """State for a session."""

    session_id: str
    created_at: datetime
    last_updated: datetime
    conversation_history: list
    context: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None
