"""
Memory schema definitions for Lyra memory system.

Defines the core MemoryRecord dataclass and related enums.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4


class MemoryScope(str, Enum):
    """Scope of memory - determines visibility and lifecycle."""
    USER = "user"  # User-specific, persists across all projects
    SESSION = "session"  # Current session only
    PROJECT = "project"  # Project-specific, persists across sessions
    GLOBAL = "global"  # Global facts, shared across all contexts


class MemoryType(str, Enum):
    """Type of memory - determines storage and retrieval strategy."""
    EPISODIC = "episodic"  # Concrete events with timestamps
    SEMANTIC = "semantic"  # Stable facts and knowledge
    PROCEDURAL = "procedural"  # Reusable workflows and skills
    PREFERENCE = "preference"  # User preferences and settings
    FAILURE = "failure"  # Lessons from mistakes


class VerifierStatus(str, Enum):
    """Verification status of memory."""
    UNVERIFIED = "unverified"  # Not yet verified
    VERIFIED = "verified"  # Passed verification
    REJECTED = "rejected"  # Failed verification
    QUARANTINED = "quarantined"  # Suspicious, needs review


@dataclass
class MemoryRecord:
    """
    A single memory record with temporal validity and provenance.

    Attributes:
        id: Unique identifier (UUID)
        scope: Visibility scope (user/session/project/global)
        type: Memory type (episodic/semantic/procedural/preference/failure)
        content: The actual memory content (text)
        source_span: Optional reference to source (e.g., "turn 42", "file.py:123")
        created_at: When this memory was created
        valid_from: When this fact became true (None = always)
        valid_until: When this fact stopped being true (None = still true)
        confidence: Confidence score 0.0-1.0
        links: Related memory IDs
        verifier_status: Verification status
        metadata: Additional structured data
        superseded_by: ID of memory that supersedes this one
        embedding: Vector embedding for semantic search (not stored in DB)
    """

    id: str = field(default_factory=lambda: str(uuid4()))
    scope: MemoryScope = MemoryScope.SESSION
    type: MemoryType = MemoryType.EPISODIC
    content: str = ""
    source_span: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    confidence: float = 1.0
    links: List[str] = field(default_factory=list)
    verifier_status: VerifierStatus = VerifierStatus.UNVERIFIED
    metadata: Dict[str, Any] = field(default_factory=dict)
    superseded_by: Optional[str] = None
    embedding: Optional[List[float]] = None

    def __post_init__(self):
        """Validate fields after initialization."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be 0.0-1.0, got {self.confidence}")

        if self.valid_from and self.valid_until:
            if self.valid_from > self.valid_until:
                raise ValueError("valid_from must be <= valid_until")

    def is_valid_at(self, timestamp: datetime) -> bool:
        """Check if this memory is valid at the given timestamp."""
        if self.valid_from and timestamp < self.valid_from:
            return False
        if self.valid_until and timestamp > self.valid_until:
            return False
        return True

    def is_superseded(self) -> bool:
        """Check if this memory has been superseded."""
        return self.superseded_by is not None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "scope": self.scope.value,
            "type": self.type.value,
            "content": self.content,
            "source_span": self.source_span,
            "created_at": self.created_at.isoformat(),
            "valid_from": self.valid_from.isoformat() if self.valid_from else None,
            "valid_until": self.valid_until.isoformat() if self.valid_until else None,
            "confidence": self.confidence,
            "links": self.links,
            "verifier_status": self.verifier_status.value,
            "metadata": self.metadata,
            "superseded_by": self.superseded_by,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryRecord":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            scope=MemoryScope(data["scope"]),
            type=MemoryType(data["type"]),
            content=data["content"],
            source_span=data.get("source_span"),
            created_at=datetime.fromisoformat(data["created_at"]),
            valid_from=datetime.fromisoformat(data["valid_from"]) if data.get("valid_from") else None,
            valid_until=datetime.fromisoformat(data["valid_until"]) if data.get("valid_until") else None,
            confidence=data["confidence"],
            links=data.get("links", []),
            verifier_status=VerifierStatus(data["verifier_status"]),
            metadata=data.get("metadata", {}),
            superseded_by=data.get("superseded_by"),
        )
