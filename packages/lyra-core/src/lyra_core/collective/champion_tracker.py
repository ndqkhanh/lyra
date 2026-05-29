"""Champion hypothesis tracking — tracks best current approach with verification scoring.

AutoScientists pattern: each area has a champion p* representing the best
known approach. Champions accrue verification scores from independent
confirmations and are demoted when falsified or stale.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum


class ChampionStatus(str, Enum):
    """Lifecycle of a champion hypothesis."""
    PROPOSED = "proposed"        # Newly proposed, awaiting verification
    CONFIRMING = "confirming"    # Under active verification by N agents
    CONFIRMED = "confirmed"      # Passed noise-gated confirmation
    CONTESTED = "contested"      # A competing hypothesis has emerged
    FALSIFIED = "falsified"      # Proven wrong — demoted
    STALE = "stale"              # No activity for too long
    SUPERSEDED = "superseded"    # Replaced by a better champion


@dataclass
class ChampionState:
    """Tracked state for a champion hypothesis p*.

    Each champion accumulates verification scores from independent
    confirmations. A champion is "confirmed" once it passes the
    noise-gate threshold of independent verifiers.
    """

    hypothesis_id: str
    statement: str
    proposed_by: str
    verification_score: float = 0.0       # Aggregate score [0.0, 1.0]
    confirmations: int = 0                 # Independent verifier count
    confirmer_ids: set[str] = field(default_factory=set)
    created_at: float = field(default_factory=time.time)
    last_updated: float = field(default_factory=time.time)
    last_verified_at: float = 0.0
    status: ChampionStatus = ChampionStatus.PROPOSED
    competing_ids: list[str] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)

    @property
    def staleness_s(self) -> float:
        """Seconds since last update — zero if never updated."""
        return time.time() - self.last_updated

    @property
    def is_confirmed(self) -> bool:
        return self.status == ChampionStatus.CONFIRMED

    @property
    def is_active(self) -> bool:
        return self.status in (
            ChampionStatus.PROPOSED,
            ChampionStatus.CONFIRMING,
            ChampionStatus.CONFIRMED,
            ChampionStatus.CONTESTED,
        )

    def record_verification(self, score: float, verifier_id: str) -> None:
        """Record an independent verification of this champion."""
        self.verification_score = max(0.0, min(1.0, score))
        if verifier_id not in self.confirmer_ids:
            self.confirmer_ids.add(verifier_id)
            self.confirmations += 1
        self.last_verified_at = time.time()
        self.last_updated = time.time()


@dataclass
class ChampionRecord:
    """Historical record of a champion including its fate."""

    state: ChampionState
    demoted_at: float | None = None
    demotion_reason: str = ""


class ChampionTracker:
    """Tracks and manages champion hypotheses across the collective.

    A champion p* is the best-known approach for a given problem area.
    The tracker:
      - Maintains the current champion per area
      - Tracks verification scores across independent confirmers
      - Promotes champions that pass noise-gated confirmation
      - Demotes falsified or stale champions
      - Maintains a historical record of past champions
    """

    def __init__(self, confirmation_threshold: int = 2,
                 staleness_threshold_s: float = 600.0) -> None:
        self._champions: dict[str, ChampionState] = {}  # hypothesis_id → state
        self._area_index: dict[str, str] = {}  # area → current champion hypothesis_id
        self._history: list[ChampionRecord] = []
        self.confirmation_threshold = confirmation_threshold
        self.staleness_threshold_s = staleness_threshold_s

    # ── Core API ──────────────────────────────────────────────────────────

    def propose_champion(self, hypothesis_id: str, statement: str,
                         proposed_by: str, area: str = "default",
                         metadata: dict[str, str] | None = None) -> ChampionState:
        """Propose a new champion hypothesis. Replaces current if better.

        If an existing champion exists for the area and this proposal
        has a higher initial score, the old champion is demoted as
        SUPERSEDED.
        """
        state = ChampionState(
            hypothesis_id=hypothesis_id,
            statement=statement,
            proposed_by=proposed_by,
            metadata=metadata or {},
        )

        existing_id = self._area_index.get(area)
        if existing_id and existing_id in self._champions:
            existing = self._champions[existing_id]
            if existing.is_active:
                # Mark existing as contested — competing hypotheses exist
                existing.status = ChampionStatus.CONTESTED
                existing.competing_ids.append(hypothesis_id)
                state.competing_ids.append(existing_id)

        self._champions[hypothesis_id] = state
        self._area_index[area] = hypothesis_id
        return state

    def verify_champion(self, hypothesis_id: str, score: float,
                        verifier_id: str) -> ChampionStatus:
        """Record a verification. Promotes to CONFIRMED if threshold met."""
        state = self._champions.get(hypothesis_id)
        if state is None:
            raise KeyError(f"Unknown champion: {hypothesis_id}")

        state.record_verification(score, verifier_id)

        if state.status == ChampionStatus.PROPOSED:
            state.status = ChampionStatus.CONFIRMING

        if state.confirmations >= self.confirmation_threshold and score >= 0.5:
            state.status = ChampionStatus.CONFIRMED

        return state.status

    def falsify_champion(self, hypothesis_id: str, reason: str) -> None:
        """Demote a falsified champion and archive it."""
        state = self._champions.get(hypothesis_id)
        if state is None:
            return

        state.status = ChampionStatus.FALSIFIED
        state.last_updated = time.time()

        self._history.append(ChampionRecord(
            state=state,
            demoted_at=time.time(),
            demotion_reason=reason,
        ))

        # Clear from area index
        for area, hid in list(self._area_index.items()):
            if hid == hypothesis_id:
                del self._area_index[area]

    def get_champion(self, area: str = "default") -> ChampionState | None:
        """Get the current champion for an area."""
        hid = self._area_index.get(area)
        if hid is None:
            return None
        return self._champions.get(hid)

    def get_champion_by_id(self, hypothesis_id: str) -> ChampionState | None:
        """Get champion state by hypothesis ID."""
        return self._champions.get(hypothesis_id)

    # ── Staleness ─────────────────────────────────────────────────────────

    def check_staleness(self) -> list[str]:
        """Return IDs of champions that have gone stale. Side-effect: marks them STALE."""
        stale_ids: list[str] = []
        for hid, state in self._champions.items():
            if state.is_active and state.staleness_s > self.staleness_threshold_s:
                state.status = ChampionStatus.STALE
                stale_ids.append(hid)
        return stale_ids

    def refresh_champion(self, hypothesis_id: str) -> None:
        """Reset staleness timer for an active champion."""
        state = self._champions.get(hypothesis_id)
        if state and state.status == ChampionStatus.STALE:
            state.status = ChampionStatus.CONFIRMING
            state.last_updated = time.time()

    # ── Query ─────────────────────────────────────────────────────────────

    @property
    def active_champions(self) -> list[ChampionState]:
        return [s for s in self._champions.values() if s.is_active]

    @property
    def confirmed_champions(self) -> list[ChampionState]:
        return [s for s in self._champions.values() if s.is_confirmed]

    @property
    def areas(self) -> list[str]:
        return list(self._area_index.keys())

    @property
    def history(self) -> list[ChampionRecord]:
        return list(self._history)

    def summary(self) -> dict:
        """Return a summary dict suitable for serialization/logging."""
        return {
            "areas": len(self._area_index),
            "active": len(self.active_champions),
            "confirmed": len(self.confirmed_champions),
            "total_tracked": len(self._champions),
            "history_count": len(self._history),
            "threshold": self.confirmation_threshold,
            "staleness_s": self.staleness_threshold_s,
        }
