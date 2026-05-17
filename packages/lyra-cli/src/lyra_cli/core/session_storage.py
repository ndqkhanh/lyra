"""Session storage for persisting sessions."""
from pathlib import Path
from typing import Optional
import json
from datetime import datetime

from .session_state import SessionState


class SessionStorage:
    """Storage for session state."""

    def __init__(self, storage_dir: Path):
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def save(self, session: SessionState) -> None:
        """Save a session."""
        file_path = self.storage_dir / f"{session.session_id}.json"
        data = {
            "session_id": session.session_id,
            "created_at": session.created_at.isoformat(),
            "last_updated": session.last_updated.isoformat(),
            "conversation_history": session.conversation_history,
            "context": session.context,
            "metadata": session.metadata
        }
        file_path.write_text(json.dumps(data, indent=2))

    def load(self, session_id: str) -> Optional[SessionState]:
        """Load a session by ID."""
        file_path = self.storage_dir / f"{session_id}.json"
        if not file_path.exists():
            return None

        data = json.loads(file_path.read_text())
        return SessionState(
            session_id=data["session_id"],
            created_at=datetime.fromisoformat(data["created_at"]),
            last_updated=datetime.fromisoformat(data["last_updated"]),
            conversation_history=data["conversation_history"],
            context=data["context"],
            metadata=data.get("metadata")
        )

    def delete(self, session_id: str) -> bool:
        """Delete a session."""
        file_path = self.storage_dir / f"{session_id}.json"
        if file_path.exists():
            file_path.unlink()
            return True
        return False

    def list_all(self) -> list:
        """List all session IDs."""
        return [f.stem for f in self.storage_dir.glob("*.json")]
