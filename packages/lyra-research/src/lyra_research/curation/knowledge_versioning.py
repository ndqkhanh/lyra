"""Knowledge Versioning — Version control for knowledge entries."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from lyra_research.curation.knowledge_entry import KnowledgeEntry


@dataclass
class KnowledgeVersion:
    """
    Single version of a knowledge entry.

    Tracks changes to knowledge entries over time with metadata
    about who changed it and why.
    """

    entry_id: str
    version: int
    content: str
    changed_by: str
    change_reason: str
    timestamp: datetime
    quality_score: float
    metadata: dict[str, str] | None = None

    def __post_init__(self) -> None:
        """Validate version after initialization."""
        if not self.entry_id:
            raise ValueError("Entry ID cannot be empty")
        if self.version < 1:
            raise ValueError("Version must be >= 1")
        if not self.content:
            raise ValueError("Content cannot be empty")
        if not self.changed_by:
            raise ValueError("Changed by cannot be empty")
        if not self.change_reason:
            raise ValueError("Change reason cannot be empty")
        if not 0.0 <= self.quality_score <= 1.0:
            raise ValueError("Quality score must be between 0.0 and 1.0")


class VersionManager:
    """
    Manages versions of knowledge entries.

    Provides version control functionality including creating versions,
    retrieving version history, and rolling back to previous versions.
    """

    def __init__(self) -> None:
        """Initialize version manager."""
        # Store versions: entry_id -> list of versions
        self._versions: dict[str, list[KnowledgeVersion]] = {}

    def create_version(
        self, entry: KnowledgeEntry, changed_by: str, reason: str
    ) -> KnowledgeVersion:
        """
        Create new version of entry.

        Args:
            entry: Knowledge entry to version
            changed_by: Who made the change
            reason: Reason for the change

        Returns:
            New KnowledgeVersion
        """
        if not changed_by:
            raise ValueError("Changed by cannot be empty")
        if not reason:
            raise ValueError("Reason cannot be empty")

        version = KnowledgeVersion(
            entry_id=entry.id,
            version=entry.version,
            content=entry.content,
            changed_by=changed_by,
            change_reason=reason,
            timestamp=datetime.now(timezone.utc),
            quality_score=entry.quality_score,
            metadata={
                "category": entry.category,
                "source": entry.source,
                "status": entry.status.value,
            },
        )

        # Store version
        if entry.id not in self._versions:
            self._versions[entry.id] = []
        self._versions[entry.id].append(version)

        return version

    def get_version_history(self, entry_id: str) -> list[KnowledgeVersion]:
        """
        Get all versions of entry.

        Args:
            entry_id: Entry ID to get history for

        Returns:
            List of KnowledgeVersion sorted by version number
        """
        if entry_id not in self._versions:
            return []

        # Return sorted by version (ascending)
        return sorted(self._versions[entry_id], key=lambda v: v.version)

    def get_version(self, entry_id: str, version: int) -> KnowledgeVersion | None:
        """
        Get specific version of entry.

        Args:
            entry_id: Entry ID
            version: Version number

        Returns:
            KnowledgeVersion if found, None otherwise
        """
        if entry_id not in self._versions:
            return None

        for v in self._versions[entry_id]:
            if v.version == version:
                return v

        return None

    def get_latest_version(self, entry_id: str) -> KnowledgeVersion | None:
        """
        Get latest version of entry.

        Args:
            entry_id: Entry ID

        Returns:
            Latest KnowledgeVersion if found, None otherwise
        """
        history = self.get_version_history(entry_id)
        if not history:
            return None
        return history[-1]

    def rollback_to_version(
        self, entry: KnowledgeEntry, version: int, changed_by: str, reason: str
    ) -> KnowledgeEntry:
        """
        Rollback entry to specific version.

        Args:
            entry: Current knowledge entry
            version: Version number to rollback to
            changed_by: Who is performing the rollback
            reason: Reason for rollback

        Returns:
            New KnowledgeEntry with content from specified version
        """
        target_version = self.get_version(entry.id, version)
        if not target_version:
            raise ValueError(f"Version {version} not found for entry {entry.id}")

        # Create new entry with content from target version
        rolled_back = entry.revise(
            new_content=target_version.content,
            new_quality_score=target_version.quality_score,
        )

        # Record rollback as new version
        self.create_version(
            rolled_back,
            changed_by=changed_by,
            reason=f"Rollback to version {version}: {reason}",
        )

        return rolled_back

    def get_version_count(self, entry_id: str) -> int:
        """
        Get number of versions for entry.

        Args:
            entry_id: Entry ID

        Returns:
            Number of versions
        """
        return len(self.get_version_history(entry_id))

    def has_versions(self, entry_id: str) -> bool:
        """
        Check if entry has any versions.

        Args:
            entry_id: Entry ID

        Returns:
            True if entry has versions, False otherwise
        """
        return entry_id in self._versions and len(self._versions[entry_id]) > 0
