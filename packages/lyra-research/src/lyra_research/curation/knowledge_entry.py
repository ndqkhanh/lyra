"""Knowledge Entry — Core data structure for curated knowledge."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class EntryStatus(Enum):
    """Status of knowledge entry in curation workflow."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    REVISED = "revised"


@dataclass
class KnowledgeEntry:
    """
    Single knowledge entry for curation.

    Represents a piece of knowledge that has been reviewed and is ready
    for curation decision (approve, reject, or request revision).
    """

    content: str
    source: str
    quality_score: float
    category: str
    tags: list[str]
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    version: int = 1
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: EntryStatus = EntryStatus.PENDING
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate entry after initialization."""
        if not self.content:
            raise ValueError("Content cannot be empty")
        if not self.source:
            raise ValueError("Source cannot be empty")
        if not 0.0 <= self.quality_score <= 1.0:
            raise ValueError("Quality score must be between 0.0 and 1.0")
        if not self.category:
            raise ValueError("Category cannot be empty")
        if not self.tags:
            raise ValueError("Tags cannot be empty")

        # Convert status to enum if string
        if isinstance(self.status, str):
            self.status = EntryStatus(self.status)

    def approve(self) -> KnowledgeEntry:
        """
        Approve this entry.

        Returns:
            New KnowledgeEntry with approved status
        """
        return KnowledgeEntry(
            id=self.id,
            content=self.content,
            source=self.source,
            quality_score=self.quality_score,
            category=self.category,
            tags=self.tags,
            version=self.version,
            created_at=self.created_at,
            updated_at=datetime.now(timezone.utc),
            status=EntryStatus.APPROVED,
            metadata=self.metadata,
        )

    def reject(self) -> KnowledgeEntry:
        """
        Reject this entry.

        Returns:
            New KnowledgeEntry with rejected status
        """
        return KnowledgeEntry(
            id=self.id,
            content=self.content,
            source=self.source,
            quality_score=self.quality_score,
            category=self.category,
            tags=self.tags,
            version=self.version,
            created_at=self.created_at,
            updated_at=datetime.now(timezone.utc),
            status=EntryStatus.REJECTED,
            metadata=self.metadata,
        )

    def revise(self, new_content: str, new_quality_score: float) -> KnowledgeEntry:
        """
        Create revised version of this entry.

        Args:
            new_content: Updated content
            new_quality_score: Updated quality score

        Returns:
            New KnowledgeEntry with revised content and incremented version
        """
        return KnowledgeEntry(
            id=self.id,
            content=new_content,
            source=self.source,
            quality_score=new_quality_score,
            category=self.category,
            tags=self.tags,
            version=self.version + 1,
            created_at=self.created_at,
            updated_at=datetime.now(timezone.utc),
            status=EntryStatus.REVISED,
            metadata=self.metadata,
        )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert entry to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "id": self.id,
            "content": self.content,
            "source": self.source,
            "quality_score": self.quality_score,
            "category": self.category,
            "tags": self.tags,
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "status": self.status.value,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> KnowledgeEntry:
        """
        Create entry from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            KnowledgeEntry instance
        """
        return cls(
            id=data["id"],
            content=data["content"],
            source=data["source"],
            quality_score=data["quality_score"],
            category=data["category"],
            tags=data["tags"],
            version=data["version"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            status=EntryStatus(data["status"]),
            metadata=data.get("metadata", {}),
        )
