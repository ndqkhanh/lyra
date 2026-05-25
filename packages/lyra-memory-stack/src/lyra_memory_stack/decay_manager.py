"""Decay manager — TTL, decay curves, and contradiction detection.

Manages memory decay with configurable curves, age-based priority
reduction, and automatic contradiction scanning.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class DecayConfig:
    """Configuration for decay behavior.

    Attributes:
        half_life: Seconds until priority halves.
        min_priority: Priority floor; entries below this are evicted.
        contradiction_threshold: Cosine similarity below which entries
            are flagged as contradictory.
        scan_interval: Seconds between contradiction scans.
    """

    half_life: float = 86400.0
    min_priority: float = 0.1
    contradiction_threshold: float = -0.3
    scan_interval: float = 3600.0


@dataclass(frozen=True)
class DecayEntry:
    """An entry tracked for decay.

    Attributes:
        entry_id: Reference to the memory entry.
        initial_priority: Starting priority value.
        current_priority: Current decayed priority.
        embedding: Optional embedding for contradiction detection.
        content: Text content for contradiction scanning.
        created_at: Unix timestamp.
    """

    entry_id: str
    initial_priority: float
    current_priority: float
    embedding: np.ndarray | None
    content: str
    created_at: float


class DecayManager:
    """Manages priority decay and contradiction detection.

    Priorities decay exponentially with a configurable half-life.
    Contradiction scanning detects semantically opposed facts.
    """

    def __init__(self, config: DecayConfig | None = None) -> None:
        self._config = config or DecayConfig()
        self._entries: dict[str, DecayEntry] = {}

    @property
    def config(self) -> DecayConfig:
        return self._config

    async def register(
        self,
        entry_id: str,
        priority: float,
        content: str,
        embedding: np.ndarray | None = None,
    ) -> None:
        """Register an entry for decay tracking."""
        entry = DecayEntry(
            entry_id=entry_id,
            initial_priority=priority,
            current_priority=priority,
            embedding=embedding,
            content=content,
            created_at=time.time(),
        )
        self._entries[entry_id] = entry

    async def get_priority(self, entry_id: str) -> float:
        """Get the current decayed priority for an entry.

        Applies exponential decay based on age and half-life config.
        """
        if entry_id not in self._entries:
            raise KeyError(f"Entry not found: {entry_id}")

        entry = self._entries[entry_id]
        age = time.time() - entry.created_at
        decay_factor = np.exp(-np.log(2) * age / self._config.half_life)
        current = entry.initial_priority * decay_factor
        return current

    async def find_contradictions(
        self, query_embedding: np.ndarray, threshold: float | None = None
    ) -> tuple[DecayEntry, ...]:
        """Find entries that contradict the query embedding.

        Uses cosine similarity — negative similarity suggests contradiction.
        """
        thresh = threshold or self._config.contradiction_threshold
        query_norm = query_embedding / (np.linalg.norm(query_embedding) + 1e-10)

        contradictions = []
        for entry in self._entries.values():
            if entry.embedding is None:
                continue
            entry_norm = entry.embedding / (np.linalg.norm(entry.embedding) + 1e-10)
            similarity = float(np.dot(query_norm, entry_norm))
            if similarity < thresh:
                contradictions.append(entry)

        return tuple(contradictions)

    async def evict_decayed(self) -> tuple[str, ...]:
        """Remove entries that have decayed below the minimum priority.

        Returns:
            IDs of evicted entries.
        """
        evicted = []
        for entry_id in list(self._entries.keys()):
            priority = await self.get_priority(entry_id)
            if priority < self._config.min_priority:
                del self._entries[entry_id]
                evicted.append(entry_id)
        return tuple(evicted)

    async def boost_priority(self, entry_id: str, factor: float = 1.5) -> None:
        """Boost an entry's priority (e.g., after successful retrieval)."""
        if entry_id not in self._entries:
            raise KeyError(f"Entry not found: {entry_id}")
        entry = self._entries[entry_id]
        self._entries[entry_id] = DecayEntry(
            entry_id=entry.entry_id,
            initial_priority=entry.initial_priority * factor,
            current_priority=entry.current_priority * factor,
            embedding=entry.embedding,
            content=entry.content,
            created_at=entry.created_at,
        )

    @property
    def entry_count(self) -> int:
        return len(self._entries)
