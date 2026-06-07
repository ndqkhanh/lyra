"""
Quarantine — isolation zone for rejected or low-trust artifacts.

Provides:
    - ``QuarantineItem``: an artifact placed in quarantine with a reason,
      expiry, and strike count.
    - ``QuarantinePool``: manages the lifecycle of quarantined items —
      add, review, reclaim (with reduced trust), and purge.

References
----------
    FORGE (2026). Population-Level Memory Synthesis for Multi-Agent
        Systems. arXiv:2605.16233 — low-trust memory suppression.
    Shao et al. (2025). Your Agent May Misevolve. arXiv:2509.26354v2 —
        3-strike quarantine pattern to prevent misevolution propagation.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_REVIEW_DAYS: int = 7
"""Default time before a quarantined item is eligible for review."""

QUARANTINE_STRIKE_LIMIT: int = 3
"""Number of strikes before an item is permanently quarantined."""

RECLAIM_INITIAL_TRUST: float = 0.3
"""Trust value assigned to a reclaimed item (start low)."""


# ---------------------------------------------------------------------------
# QuarantineItem
# ---------------------------------------------------------------------------


@dataclass
class QuarantineItem:
    """An artifact placed in the quarantine pool.

    Attributes:
        item_id: Unique identifier for this quarantined item.
        artifact: The artifact being quarantined (memory, gene, etc.).
        reason: Human-readable explanation of why it was quarantined.
        quarantined_at: Unix timestamp when the item was quarantined.
        review_after: Unix timestamp after which this item may be reviewed.
        strikes: Number of times this item has been re-quarantined
            (default 0). At 3 strikes the item is permanently flagged.
        metadata: Optional arbitrary context.
    """

    item_id: str
    artifact: Any
    reason: str
    quarantined_at: float = 0.0
    review_after: float = 0.0
    strikes: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        now = time.time()
        if self.quarantined_at == 0.0:
            self.quarantined_at = now
        if self.review_after == 0.0:
            self.review_after = now + DEFAULT_REVIEW_DAYS * 86400

    @property
    def is_reviewable(self) -> bool:
        """Whether this item is past its review date.

        Returns:
            ``True`` if the current time is past ``review_after``.
        """
        return time.time() >= self.review_after

    @property
    def is_permanent(self) -> bool:
        """Whether this item has reached the permanent strike limit.

        Returns:
            ``True`` if ``strikes >= QUARANTINE_STRIKE_LIMIT``.
        """
        return self.strikes >= QUARANTINE_STRIKE_LIMIT

    def with_strike(self) -> QuarantineItem:
        """Return a copy of this item with strike count incremented.

        The ``quarantined_at`` and ``review_after`` timestamps are
        reset to the current time.
        """
        now = time.time()
        return QuarantineItem(
            item_id=self.item_id,
            artifact=self.artifact,
            reason=self.reason,
            quarantined_at=now,
            review_after=now + DEFAULT_REVIEW_DAYS * 86400,
            strikes=self.strikes + 1,
            metadata=self.metadata,
        )


# ---------------------------------------------------------------------------
# QuarantinePool
# ---------------------------------------------------------------------------


@dataclass
class QuarantinePool:
    """Isolation zone for rejected or low-trust artifacts.

    Manages the full lifecycle:
        - **Add**: Place an artifact in quarantine with a reason.
        - **Review**: Check all items past their review date.
        - **Reclaim**: Restore a quarantined item with reduced trust.
        - **Purge**: Permanently delete a quarantined item.

    Attributes:
        items: Mapping of ``item_id -> QuarantineItem``.
    """

    items: dict[str, QuarantineItem] = field(default_factory=dict)

    def add(
        self,
        artifact: Any,
        reason: str,
        review_after_days: int = DEFAULT_REVIEW_DAYS,
        strikes: int = 0,
    ) -> QuarantineItem:
        """Add an artifact to the quarantine pool.

        Args:
            artifact: The artifact to quarantine.
            reason: Why the artifact was quarantined.
            review_after_days: Days after which this item may be
                reviewed. Default 7.
            strikes: Initial strike count. Default 0.

        Returns:
            The created ``QuarantineItem``.
        """
        item_id = str(uuid.uuid4())
        now = time.time()
        item = QuarantineItem(
            item_id=item_id,
            artifact=artifact,
            reason=reason,
            quarantined_at=now,
            review_after=now + review_after_days * 86400,
            strikes=strikes,
        )
        self.items[item_id] = item
        return item

    def review(self) -> list[QuarantineItem]:
        """Return all items past their review date.

        Items that have reached the strike limit are flagged as
        permanent and should be reviewed manually.

        Returns:
            List of ``QuarantineItem`` instances eligible for review.
        """
        return [item for item in self.items.values() if item.is_reviewable]

    def reclaim(self, item_id: str) -> tuple[Any, float]:
        """Remove an item from quarantine and return it with reduced trust.

        The artifact is restored with a starting trust of
        ``RECLAIM_INITIAL_TRUST`` (0.3). If the item has reached the
        strike limit, it may not be reclaimed.

        Args:
            item_id: The identifier of the item to reclaim.

        Returns:
            ``(artifact, initial_trust)`` tuple.

        Raises:
            KeyError: If the item does not exist.
            ValueError: If the item has reached the permanent strike
                limit.
        """
        item = self.items.get(item_id)
        if item is None:
            raise KeyError(f"Quarantine item '{item_id}' not found.")
        if item.is_permanent:
            raise ValueError(
                f"Item '{item_id}' has reached {QUARANTINE_STRIKE_LIMIT} "
                f"strikes and cannot be reclaimed. Use purge() instead.",
            )

        artifact = item.artifact
        del self.items[item_id]
        return artifact, RECLAIM_INITIAL_TRUST

    def purge(self, item_id: str) -> None:
        """Permanently delete a quarantined item.

        Args:
            item_id: The identifier of the item to purge.

        Raises:
            KeyError: If the item does not exist.
        """
        if item_id not in self.items:
            raise KeyError(f"Quarantine item '{item_id}' not found.")
        del self.items[item_id]

    def get_statistics(self) -> dict[str, Any]:
        """Return summary statistics for the quarantine pool.

        Returns:
            Dict with total count, reviewable count, permanent count,
            and strike distribution.
        """
        all_strikes = [item.strikes for item in self.items.values()]
        return {
            "total_items": len(self.items),
            "reviewable_items": len(self.review()),
            "permanent_items": sum(
                1 for item in self.items.values() if item.is_permanent
            ),
            "strike_counts": {
                str(k): all_strikes.count(k) for k in set(all_strikes)
            },
        }
