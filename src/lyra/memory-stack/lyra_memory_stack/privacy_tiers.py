"""Privacy tiers — ephemeral → private → durable → shared classification.

Every memory entry is assigned a privacy tier controlling retention,
visibility, and sharing behavior.
"""

from __future__ import annotations

import enum
import time
from dataclasses import dataclass


class PrivacyTier(enum.Enum):
    """Privacy classification for memory entries.

    EPHEMERAL: Session-only, purged on session end.
    PRIVATE: Persisted but never shared with other agents/sessions.
    DURABLE: Persisted and available for self-reference across sessions.
    SHARED: Persisted and shareable with other agents/sessions.
    """

    EPHEMERAL = "ephemeral"
    PRIVATE = "private"
    DURABLE = "durable"
    SHARED = "shared"


@dataclass(frozen=True)
class PrivacyLabel:
    """Privacy metadata attached to a memory entry.

    Attributes:
        entry_ref: Reference to the memory entry.
        tier: Privacy classification.
        owner_id: The agent/session that owns this entry.
        allowed_recipients: Explicit allowlist for shared access.
        created_at: Unix timestamp.
        expires_at: Optional expiry timestamp.
    """

    entry_ref: str
    tier: PrivacyTier
    owner_id: str
    allowed_recipients: tuple[str, ...]
    created_at: float
    expires_at: float | None


class PrivacyManager:
    """Manages privacy tiers for memory entries.

    Controls retention (ephemeral vs durable) and visibility (private vs shared)
    for all memory entries in the stack.
    """

    def __init__(self) -> None:
        self._labels: dict[str, PrivacyLabel] = {}

    async def classify(
        self,
        entry_ref: str,
        tier: PrivacyTier,
        owner_id: str,
        allowed_recipients: tuple[str, ...] = (),
        ttl: float | None = None,
    ) -> PrivacyLabel:
        """Classify a memory entry with a privacy tier.

        Args:
            entry_ref: Reference to the memory entry.
            tier: Privacy classification.
            owner_id: Owning agent/session.
            allowed_recipients: Explicit sharing allowlist.
            ttl: Optional time-to-live in seconds.

        Returns:
            The created PrivacyLabel.
        """
        now = time.time()
        expires_at = now + ttl if ttl is not None else None
        label = PrivacyLabel(
            entry_ref=entry_ref,
            tier=tier,
            owner_id=owner_id,
            allowed_recipients=allowed_recipients,
            created_at=now,
            expires_at=expires_at,
        )
        self._labels[entry_ref] = label
        return label

    async def check_access(
        self, entry_ref: str, requester_id: str
    ) -> bool:
        """Check if a requester can access an entry.

        Args:
            entry_ref: The memory entry reference.
            requester_id: Who is requesting access.

        Returns:
            True if access is allowed.
        """
        if entry_ref not in self._labels:
            return True

        label = self._labels[entry_ref]

        if label.expires_at is not None and time.time() > label.expires_at:
            return False

        if label.tier == PrivacyTier.SHARED:
            return True

        if label.owner_id == requester_id:
            return True

        if requester_id in label.allowed_recipients:
            return True

        return False

    async def get_tier(self, entry_ref: str) -> PrivacyTier:
        """Get the privacy tier for an entry."""
        if entry_ref not in self._labels:
            return PrivacyTier.DURABLE
        return self._labels[entry_ref].tier

    async def purge_ephemeral(self) -> int:
        """Purge all ephemeral entries.

        Returns:
            Number of entries purged.
        """
        to_remove = [
            ref
            for ref, label in self._labels.items()
            if label.tier == PrivacyTier.EPHEMERAL
        ]
        for ref in to_remove:
            del self._labels[ref]
        return len(to_remove)

    async def purge_expired(self) -> int:
        """Purge all expired entries.

        Returns:
            Number of entries purged.
        """
        now = time.time()
        to_remove = [
            ref
            for ref, label in self._labels.items()
            if label.expires_at is not None and now > label.expires_at
        ]
        for ref in to_remove:
            del self._labels[ref]
        return len(to_remove)

    @property
    def label_count(self) -> int:
        return len(self._labels)
