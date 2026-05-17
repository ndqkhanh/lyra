"""Session manager for managing sessions."""
from typing import Optional, Dict, Any
from datetime import datetime
import uuid

from .session_storage import SessionStorage
from .session_state import SessionState


class SessionManager:
    """Manager for session state."""

    def __init__(self, storage: SessionStorage):
        self.storage = storage

    def create(self) -> SessionState:
        """Create a new session."""
        session = SessionState(
            session_id=str(uuid.uuid4()),
            created_at=datetime.now(),
            last_updated=datetime.now(),
            conversation_history=[],
            context={}
        )
        self.storage.save(session)
        return session

    def save(self, session: SessionState) -> None:
        """Save a session."""
        session.last_updated = datetime.now()
        self.storage.save(session)

    def load(self, session_id: str) -> Optional[SessionState]:
        """Load a session by ID."""
        return self.storage.load(session_id)

    def delete(self, session_id: str) -> bool:
        """Delete a session."""
        return self.storage.delete(session_id)

    def list_all(self) -> list:
        """List all session IDs."""
        return self.storage.list_all()
