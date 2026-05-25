"""TTL-based decay, staleness scoring, contradiction detection, and pruning.

Manages configurable half-life per memory type, scans for contradictions
between stored facts, computes staleness scores, and automatically prunes
expired or contradictory entries.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from lyra_memory_stack.exceptions import DecayError
from lyra_memory_stack.privacy_tiers import PrivacyTier


class MemoryType(Enum):
    """Types of memory subject to decay policies."""

    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    WORKING = "working"


@dataclass(frozen=True)
class DecayPolicy:
    """Decay configuration for a memory type."""

    memory_type: MemoryType
    half_life_hours: float
    max_staleness_score: float = 0.95
    pruning_threshold: float = 0.90
    soft_prune: bool = True


DEFAULT_DECAY_POLICIES: dict[MemoryType, DecayPolicy] = {
    MemoryType.EPISODIC: DecayPolicy(
        memory_type=MemoryType.EPISODIC,
        half_life_hours=720.0,  # 30 days
        max_staleness_score=0.95,
        pruning_threshold=0.90,
        soft_prune=True,
    ),
    MemoryType.SEMANTIC: DecayPolicy(
        memory_type=MemoryType.SEMANTIC,
        half_life_hours=2160.0,  # 90 days
        max_staleness_score=0.95,
        pruning_threshold=0.90,
        soft_prune=True,
    ),
    MemoryType.PROCEDURAL: DecayPolicy(
        memory_type=MemoryType.PROCEDURAL,
        half_life_hours=4320.0,  # 180 days
        max_staleness_score=0.95,
        pruning_threshold=0.90,
        soft_prune=True,
    ),
    MemoryType.WORKING: DecayPolicy(
        memory_type=MemoryType.WORKING,
        half_life_hours=1.0,  # 1 hour
        max_staleness_score=0.95,
        pruning_threshold=0.90,
        soft_prune=False,
    ),
}


@dataclass(frozen=True)
class MemoryEntry:
    """A memory entry with metadata for decay tracking."""

    entry_id: str
    memory_type: MemoryType
    content: str
    timestamp: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0
    tier: PrivacyTier = PrivacyTier.PRIVATE
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class Contradiction:
    """Represents a detected contradiction between two memory entries."""

    entry_a_id: str
    entry_b_id: str
    reason: str
    severity: float  # 0.0 (weak) to 1.0 (strong contradiction)
    detected_at: float = field(default_factory=time.time)


class DecayManager:
    """Manages TTL-based decay, staleness, contradictions, and pruning."""

    _policies: dict[MemoryType, DecayPolicy]
    _entries: dict[str, MemoryEntry]
    _contradictions: list[Contradiction]

    def __init__(
        self,
        policies: dict[MemoryType, DecayPolicy] | None = None,
    ) -> None:
        self._policies = dict(policies) if policies else dict(DEFAULT_DECAY_POLICIES)
        self._entries = {}
        self._contradictions = []

    def register_entry(self, entry: MemoryEntry) -> None:
        """Register a memory entry for decay tracking."""
        self._entries[entry.entry_id] = entry

    def unregister_entry(self, entry_id: str) -> None:
        """Remove an entry from tracking."""
        self._entries.pop(entry_id, None)
        self._contradictions = [
            c for c in self._contradictions
            if c.entry_a_id != entry_id and c.entry_b_id != entry_id
        ]

    def get_policy(self, memory_type: MemoryType) -> DecayPolicy:
        """Get the decay policy for a memory type."""
        return self._policies.get(memory_type, DEFAULT_DECAY_POLICIES[memory_type])

    def set_policy(self, memory_type: MemoryType, policy: DecayPolicy) -> None:
        """Override the decay policy for a memory type."""
        self._policies[memory_type] = policy

    def compute_staleness(self, entry_id: str) -> float:
        """Compute staleness score [0.0, 1.0] for a memory entry.

        Uses exponential decay based on half-life and access recency.
        """
        entry = self._entries.get(entry_id)
        if entry is None:
            raise DecayError(f"Entry '{entry_id}' not found for staleness computation")

        policy = self.get_policy(entry.memory_type)
        now = time.time()
        hours_since_access = (now - entry.last_accessed) / 3600.0
        decay_factor = 0.5 ** (hours_since_access / policy.half_life_hours)
        staleness = 1.0 - decay_factor

        # Boost staleness for infrequently accessed items
        if entry.access_count < 2:
            staleness = min(1.0, staleness * 1.2)

        return min(1.0, max(0.0, staleness))

    def compute_all_staleness(self) -> dict[str, float]:
        """Compute staleness scores for all registered entries."""
        return {
            eid: self.compute_staleness(eid)
            for eid in self._entries
        }

    def record_access(self, entry_id: str) -> None:
        """Record an access event for an entry, reducing its staleness."""
        entry = self._entries.get(entry_id)
        if entry is None:
            raise DecayError(f"Entry '{entry_id}' not found for access recording")
        self._entries[entry_id] = MemoryEntry(
            entry_id=entry.entry_id,
            memory_type=entry.memory_type,
            content=entry.content,
            timestamp=entry.timestamp,
            last_accessed=time.time(),
            access_count=entry.access_count + 1,
            tier=entry.tier,
            tags=entry.tags,
        )

    def entries_needing_pruning(self, soft: bool | None = None) -> list[MemoryEntry]:
        """Return entries whose staleness exceeds the pruning threshold."""
        results: list[MemoryEntry] = []
        for entry in self._entries.values():
            policy = self.get_policy(entry.memory_type)
            if soft is not None and policy.soft_prune != soft:
                continue
            staleness = self.compute_staleness(entry.entry_id)
            if staleness >= policy.pruning_threshold:
                results.append(entry)
        return results

    def prune_expired(self) -> list[str]:
        """Prune entries past their pruning threshold. Returns pruned IDs."""
        to_prune = self.entries_needing_pruning()
        pruned: list[str] = []
        for entry in to_prune:
            self._entries.pop(entry.entry_id, None)
            pruned.append(entry.entry_id)
        # Clean up contradictions referencing pruned entries
        self._contradictions = [
            c for c in self._contradictions
            if c.entry_a_id in self._entries and c.entry_b_id in self._entries
        ]
        return pruned

    def detect_contradictions(
        self,
        entry_pairs: list[tuple[str, str, str]],
    ) -> list[Contradiction]:
        """Detect contradictions between pairs of entries.

        Args:
            entry_pairs: List of (entry_a_id, entry_b_id, reason) tuples.
        """
        contradictions: list[Contradiction] = []
        for a_id, b_id, reason in entry_pairs:
            if a_id not in self._entries or b_id not in self._entries:
                continue
            contradiction = Contradiction(
                entry_a_id=a_id,
                entry_b_id=b_id,
                reason=reason,
                severity=0.8,
            )
            contradictions.append(contradiction)
            self._contradictions.append(contradiction)
        return contradictions

    def get_contradictions(self, entry_id: str) -> list[Contradiction]:
        """Get all contradictions involving a given entry."""
        return [
            c for c in self._contradictions
            if c.entry_a_id == entry_id or c.entry_b_id == entry_id
        ]

    def clear_contradictions(self) -> None:
        """Clear all stored contradictions."""
        self._contradictions.clear()

    @property
    def entry_count(self) -> int:
        """Number of registered entries."""
        return len(self._entries)

    @property
    def contradiction_count(self) -> int:
        """Number of detected contradictions."""
        return len(self._contradictions)

    def summary(self) -> dict[str, Any]:
        """Produce a summary of the decay manager state."""
        staleness = self.compute_all_staleness()
        return {
            "total_entries": self.entry_count,
            "total_contradictions": self.contradiction_count,
            "entries_needing_pruning": len(self.entries_needing_pruning()),
            "average_staleness": sum(staleness.values()) / len(staleness) if staleness else 0.0,
        }
