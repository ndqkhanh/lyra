"""
Session Management - Session sharing, replay, and analytics.

Features:
- Export/import sessions
- Session replay
- Session annotations
- Session search and filtering
- Session analytics
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class SessionEventType(Enum):
    """Session event type."""

    MESSAGE = "message"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    ERROR = "error"
    ANNOTATION = "annotation"


@dataclass
class SessionEvent:
    """Session event."""

    id: str
    type: SessionEventType
    timestamp: datetime
    data: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionAnnotation:
    """Session annotation."""

    id: str
    event_id: str
    author: str
    text: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class SessionMetadata:
    """Session metadata."""

    session_id: str
    created_at: datetime
    updated_at: datetime
    author: str
    title: str
    description: str
    tags: List[str] = field(default_factory=list)
    total_events: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0


class SessionManager:
    """
    Session manager.

    Features:
    - Export/import sessions
    - Session replay
    - Session annotations
    - Session analytics
    """

    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize session manager.

        Args:
            storage_path: Path to session storage directory
        """
        self.storage_path = storage_path or Path.home() / ".lyra" / "sessions"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.current_session: Optional[SessionMetadata] = None
        self.events: List[SessionEvent] = []
        self.annotations: List[SessionAnnotation] = []

    def create_session(
        self,
        session_id: str,
        author: str,
        title: str,
        description: str = "",
        tags: Optional[List[str]] = None,
    ) -> SessionMetadata:
        """
        Create new session.

        Args:
            session_id: Session ID
            author: Session author
            title: Session title
            description: Session description
            tags: Session tags

        Returns:
            Session metadata
        """
        metadata = SessionMetadata(
            session_id=session_id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            author=author,
            title=title,
            description=description,
            tags=tags or [],
        )
        self.current_session = metadata
        self.events = []
        self.annotations = []
        return metadata

    def add_event(
        self,
        event_id: str,
        event_type: SessionEventType,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SessionEvent:
        """
        Add event to session.

        Args:
            event_id: Event ID
            event_type: Event type
            data: Event data
            metadata: Event metadata

        Returns:
            Session event
        """
        event = SessionEvent(
            id=event_id,
            type=event_type,
            timestamp=datetime.now(),
            data=data,
            metadata=metadata or {},
        )
        self.events.append(event)

        if self.current_session:
            self.current_session.total_events += 1
            self.current_session.updated_at = datetime.now()

        return event

    def add_annotation(
        self,
        annotation_id: str,
        event_id: str,
        author: str,
        text: str,
    ) -> SessionAnnotation:
        """
        Add annotation to event.

        Args:
            annotation_id: Annotation ID
            event_id: Event ID
            author: Annotation author
            text: Annotation text

        Returns:
            Session annotation
        """
        annotation = SessionAnnotation(
            id=annotation_id,
            event_id=event_id,
            author=author,
            text=text,
        )
        self.annotations.append(annotation)
        return annotation

    def export_session(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Export session to dictionary.

        Args:
            session_id: Session ID (uses current if None)

        Returns:
            Session dictionary
        """
        if session_id:
            # Load session from storage
            session_data = self._load_session(session_id)
            return session_data

        # Export current session
        if not self.current_session:
            raise ValueError("No active session")

        return {
            "metadata": {
                "session_id": self.current_session.session_id,
                "created_at": self.current_session.created_at.isoformat(),
                "updated_at": self.current_session.updated_at.isoformat(),
                "author": self.current_session.author,
                "title": self.current_session.title,
                "description": self.current_session.description,
                "tags": self.current_session.tags,
                "total_events": self.current_session.total_events,
                "total_tokens": self.current_session.total_tokens,
                "total_cost": self.current_session.total_cost,
            },
            "events": [
                {
                    "id": event.id,
                    "type": event.type.value,
                    "timestamp": event.timestamp.isoformat(),
                    "data": event.data,
                    "metadata": event.metadata,
                }
                for event in self.events
            ],
            "annotations": [
                {
                    "id": ann.id,
                    "event_id": ann.event_id,
                    "author": ann.author,
                    "text": ann.text,
                    "timestamp": ann.timestamp.isoformat(),
                }
                for ann in self.annotations
            ],
        }

    def import_session(self, session_data: Dict[str, Any]):
        """
        Import session from dictionary.

        Args:
            session_data: Session dictionary
        """
        metadata = session_data["metadata"]
        self.current_session = SessionMetadata(
            session_id=metadata["session_id"],
            created_at=datetime.fromisoformat(metadata["created_at"]),
            updated_at=datetime.fromisoformat(metadata["updated_at"]),
            author=metadata["author"],
            title=metadata["title"],
            description=metadata["description"],
            tags=metadata["tags"],
            total_events=metadata["total_events"],
            total_tokens=metadata["total_tokens"],
            total_cost=metadata["total_cost"],
        )

        self.events = [
            SessionEvent(
                id=event["id"],
                type=SessionEventType(event["type"]),
                timestamp=datetime.fromisoformat(event["timestamp"]),
                data=event["data"],
                metadata=event["metadata"],
            )
            for event in session_data["events"]
        ]

        self.annotations = [
            SessionAnnotation(
                id=ann["id"],
                event_id=ann["event_id"],
                author=ann["author"],
                text=ann["text"],
                timestamp=datetime.fromisoformat(ann["timestamp"]),
            )
            for ann in session_data["annotations"]
        ]

    def save_session(self, session_id: Optional[str] = None):
        """
        Save session to storage.

        Args:
            session_id: Session ID (uses current if None)
        """
        if not self.current_session and not session_id:
            raise ValueError("No active session")

        sid = session_id if session_id else (self.current_session.session_id if self.current_session else "")
        if not sid:
            raise ValueError("No session ID available")

        session_data = self.export_session()

        session_file = self.storage_path / f"{sid}.json"
        with open(session_file, "w") as f:
            json.dump(session_data, f, indent=2)

    def load_session(self, session_id: str):
        """
        Load session from storage.

        Args:
            session_id: Session ID
        """
        session_data = self._load_session(session_id)
        self.import_session(session_data)

    def _load_session(self, session_id: str) -> Dict[str, Any]:
        """Load session data from file."""
        session_file = self.storage_path / f"{session_id}.json"
        if not session_file.exists():
            raise FileNotFoundError(f"Session not found: {session_id}")

        with open(session_file, "r") as f:
            return json.load(f)

    def list_sessions(self) -> List[SessionMetadata]:
        """
        List all sessions.

        Returns:
            List of session metadata
        """
        sessions = []
        for session_file in self.storage_path.glob("*.json"):
            try:
                session_data = self._load_session(session_file.stem)
                metadata = session_data["metadata"]
                sessions.append(
                    SessionMetadata(
                        session_id=metadata["session_id"],
                        created_at=datetime.fromisoformat(metadata["created_at"]),
                        updated_at=datetime.fromisoformat(metadata["updated_at"]),
                        author=metadata["author"],
                        title=metadata["title"],
                        description=metadata["description"],
                        tags=metadata["tags"],
                        total_events=metadata["total_events"],
                        total_tokens=metadata["total_tokens"],
                        total_cost=metadata["total_cost"],
                    )
                )
            except Exception:
                continue
        return sessions

    def search_sessions(
        self,
        query: Optional[str] = None,
        author: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> List[SessionMetadata]:
        """
        Search sessions.

        Args:
            query: Search query (title/description)
            author: Filter by author
            tags: Filter by tags

        Returns:
            List of matching sessions
        """
        sessions = self.list_sessions()

        if query:
            query_lower = query.lower()
            sessions = [
                s
                for s in sessions
                if query_lower in s.title.lower()
                or query_lower in s.description.lower()
            ]

        if author:
            sessions = [s for s in sessions if s.author == author]

        if tags:
            sessions = [s for s in sessions if any(tag in s.tags for tag in tags)]

        return sessions

    def get_analytics(self) -> Dict[str, Any]:
        """
        Get session analytics.

        Returns:
            Analytics dictionary
        """
        if not self.current_session:
            return {}

        event_types = {}
        for event in self.events:
            event_types[event.type.value] = event_types.get(event.type.value, 0) + 1

        return {
            "session_id": self.current_session.session_id,
            "total_events": len(self.events),
            "total_annotations": len(self.annotations),
            "event_types": event_types,
            "total_tokens": self.current_session.total_tokens,
            "total_cost": self.current_session.total_cost,
            "duration": (
                self.current_session.updated_at - self.current_session.created_at
            ).total_seconds(),
        }


class SessionReplay:
    """
    Session replay.

    Features:
    - Step-by-step replay
    - Playback controls
    - Speed control
    """

    def __init__(self, session_manager: SessionManager):
        """
        Initialize session replay.

        Args:
            session_manager: Session manager
        """
        self.session_manager = session_manager
        self.current_index = 0

    def start(self):
        """Start replay from beginning."""
        self.current_index = 0

    def next_event(self) -> Optional[SessionEvent]:
        """
        Get next event.

        Returns:
            Next event or None
        """
        if self.current_index >= len(self.session_manager.events):
            return None

        event = self.session_manager.events[self.current_index]
        self.current_index += 1
        return event

    def previous_event(self) -> Optional[SessionEvent]:
        """
        Get previous event.

        Returns:
            Previous event or None
        """
        if self.current_index <= 0:
            return None

        self.current_index -= 1
        return self.session_manager.events[self.current_index]

    def goto_event(self, index: int) -> Optional[SessionEvent]:
        """
        Go to specific event.

        Args:
            index: Event index

        Returns:
            Event at index or None
        """
        if index < 0 or index >= len(self.session_manager.events):
            return None

        self.current_index = index
        return self.session_manager.events[index]

    def get_progress(self) -> float:
        """
        Get replay progress.

        Returns:
            Progress percentage (0-100)
        """
        if not self.session_manager.events:
            return 0.0

        return (self.current_index / len(self.session_manager.events)) * 100
