"""
Modular Memory Module — independent memory partition with formal
interference tracking and stability bounds.

Interference Bound: Δ_t(Q) ≤ ρ_t ε_t
  where ρ_t = retrieval-update overlap
        ε_t = update magnitude

Source: Modular Compression (ztmwHisqJ4), ICLR 2026 MemAgent Workshop.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4


@dataclass
class InterferenceTracker:
    """Tracks interference between memory updates and retrievals.

    Implements the formal bound Δ_t(Q) ≤ ρ_t ε_t where:
    - ρ_t (overlap_ratio): fraction of retrievals that overlap with updates
    - ε_t (update_magnitude): average magnitude of updates
    - Δ_t: estimated interference (ρ_t × ε_t)
    """

    overlap_ratio: float = 0.0
    update_magnitude: float = 0.0
    total_retrievals: int = 0
    total_updates: int = 0
    overlapping_retrievals: int = 0
    _stability_threshold: float = 0.3

    @property
    def interference_bound(self) -> float:
        """Current estimated interference Δ_t = ρ_t × ε_t."""
        return round(self.overlap_ratio * self.update_magnitude, 6)

    @property
    def is_stable(self) -> bool:
        """Module is stable when interference is below threshold."""
        return self.interference_bound <= self._stability_threshold

    def record_update(self, magnitude: float) -> None:
        self.total_updates += 1
        alpha = 1.0 / self.total_updates if self.total_updates > 0 else 1.0
        self.update_magnitude = (1 - alpha) * self.update_magnitude + alpha * magnitude

    def record_retrieval(self, overlaps_update: bool) -> None:
        self.total_retrievals += 1
        if overlaps_update:
            self.overlapping_retrievals += 1
        self.overlap_ratio = (
            self.overlapping_retrievals / self.total_retrievals
            if self.total_retrievals > 0
            else 0.0
        )

    def set_threshold(self, value: float) -> None:
        self._stability_threshold = max(0.01, min(1.0, value))


@dataclass
class ModularMemoryModule:
    """An independent memory module with interference isolation.

    Each module has its own memory entries, update history, and
    interference tracker. Updates to one module do not affect others
    unless explicitly composed.
    """

    name: str
    entries: list[str] = field(default_factory=list)
    interference: InterferenceTracker = field(default_factory=InterferenceTracker)
    id: str = field(default_factory=lambda: uuid4().hex)
    _version: int = 0

    def add(self, content: str) -> str:
        """Add content to this module, tracking update magnitude."""
        entry_id = uuid4().hex
        self.entries.append(content)
        magnitude = len(content) / 1000.0
        self.interference.record_update(magnitude)
        self._version += 1
        return entry_id

    def retrieve(self, indices: list[int]) -> list[str]:
        """Retrieve entries by index, recording overlap with updates."""
        results = []
        for idx in indices:
            if 0 <= idx < len(self.entries):
                results.append(self.entries[idx])
                if idx >= len(self.entries) - self._version:
                    self.interference.record_retrieval(overlaps_update=True)
                else:
                    self.interference.record_retrieval(overlaps_update=False)
        return results

    def compress(self, keep_fraction: float = 0.7) -> int:
        """Compress by keeping top entries, tracking update magnitude."""
        if not self.entries:
            return 0
        keep_count = max(1, int(len(self.entries) * keep_fraction))
        removed = len(self.entries) - keep_count
        self.entries = self.entries[:keep_count]
        self.interference.record_update(0.1)
        self._version += 1
        return removed

    @property
    def size(self) -> int:
        return len(self.entries)

    @property
    def version(self) -> int:
        return self._version
