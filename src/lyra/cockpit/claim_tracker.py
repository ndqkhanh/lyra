"""Claim tracker — tracks claims through their verification lifecycle.

Each claim progresses through stages: registered -> verifying -> verified
or disputed. The tracker maintains timelines and provides statistics.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass

from .exceptions import CockpitError


@dataclass(frozen=True)
class TrackedClaim:
    """A claim being tracked through the verification lifecycle.

    Attributes:
        claim_id: Unique identifier for this claim.
        text: The claim text.
        source: Source that produced the claim.
        status: Current status string (e.g., "registered", "verifying",
            "verified", "disputed").
        verification_rounds: Number of verification rounds completed.
        last_updated: Unix timestamp of last update.
    """

    claim_id: str
    text: str
    source: str
    status: str
    verification_rounds: int
    last_updated: float


@dataclass(frozen=True)
class ClaimTimeline:
    """Timeline of events for a tracked claim.

    Attributes:
        claim: The TrackedClaim.
        events: Ordered tuple of (timestamp, event_description) pairs.
    """

    claim: TrackedClaim
    events: tuple[tuple[float, str], ...]


class ClaimTracker:
    """Tracks claims through their verification lifecycle.

    Supports registration, status updates, timeline retrieval, pending
    claim queries, and aggregate statistics.
    """

    def __init__(self) -> None:
        self._claims: dict[str, TrackedClaim] = {}
        self._timelines: dict[str, list[tuple[float, str]]] = {}

    async def register_claim(self, text: str, source: str) -> str:
        """Register a new claim for tracking.

        Args:
            text: The claim text.
            source: Source that produced the claim.

        Returns:
            The unique claim_id for the newly registered claim.

        Raises:
            CockpitError: If text or source is empty.
        """
        if not text or not text.strip():
            raise CockpitError("Claim text cannot be empty")
        if not source or not source.strip():
            raise CockpitError("Claim source cannot be empty")

        claim_id = f"claim-{uuid.uuid4().hex[:12]}"
        now = time.time()

        claim = TrackedClaim(
            claim_id=claim_id,
            text=text,
            source=source,
            status="registered",
            verification_rounds=0,
            last_updated=now,
        )
        self._claims[claim_id] = claim
        self._timelines[claim_id] = [(now, "Claim registered")]
        return claim_id

    async def update_status(self, claim_id: str, status: str) -> None:
        """Update the status of a tracked claim.

        Args:
            claim_id: The claim to update.
            status: New status string.

        Raises:
            CockpitError: If the claim_id is unknown.
        """
        if claim_id not in self._claims:
            raise CockpitError(f"Unknown claim: {claim_id}")

        now = time.time()
        existing = self._claims[claim_id]
        updated = TrackedClaim(
            claim_id=existing.claim_id,
            text=existing.text,
            source=existing.source,
            status=status,
            verification_rounds=existing.verification_rounds
            + (1 if status in ("verified", "disputed") else 0),
            last_updated=now,
        )
        self._claims[claim_id] = updated
        self._timelines[claim_id].append((now, f"Status changed to: {status}"))

    async def get_timeline(self, claim_id: str) -> ClaimTimeline:
        """Get the full timeline for a tracked claim.

        Args:
            claim_id: The claim to query.

        Returns:
            A ClaimTimeline with the claim and its event history.

        Raises:
            CockpitError: If the claim_id is unknown.
        """
        if claim_id not in self._claims:
            raise CockpitError(f"Unknown claim: {claim_id}")

        return ClaimTimeline(
            claim=self._claims[claim_id],
            events=tuple(self._timelines[claim_id]),
        )

    async def get_pending(self) -> tuple[TrackedClaim, ...]:
        """Get all claims with pending verification status.

        Returns:
            A tuple of TrackedClaim instances whose status is "registered"
            or "verifying".
        """
        pending_statuses = {"registered", "verifying"}
        return tuple(
            c for c in self._claims.values() if c.status in pending_statuses
        )

    async def get_statistics(self) -> dict:
        """Get aggregate statistics for all tracked claims.

        Returns:
            A dict with keys: total, registered, verifying, verified,
            disputed, avg_verification_rounds.
        """
        total = len(self._claims)
        counts: dict[str, int] = {"registered": 0, "verifying": 0, "verified": 0, "disputed": 0}
        total_rounds = 0

        for claim in self._claims.values():
            if claim.status in counts:
                counts[claim.status] += 1
            total_rounds += claim.verification_rounds

        return {
            "total": total,
            **counts,
            "avg_verification_rounds": total_rounds / total if total > 0 else 0.0,
        }
