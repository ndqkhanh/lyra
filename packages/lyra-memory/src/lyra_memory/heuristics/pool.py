"""
Heuristic Pool — configurable memory management heuristics
for retention, eviction, and compression strategies.

Source: Modular Compression (ztmwHisqJ4), ICLR 2026 MemAgent Workshop.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable
from uuid import uuid4


@dataclass
class MemoryHeuristic:
    """A heuristic rule for memory management.

    Each heuristic has a priority, a condition predicate, and an action.
    Higher priority heuristics are applied first.
    """

    name: str
    priority: float
    condition: Callable[[object], bool]
    action: Callable[[object], int]
    id: str = field(default_factory=lambda: uuid4().hex)
    enabled: bool = True
    cooldown: int = 0
    _last_applied: int = -1

    def applies(self, module: object, cycle: int) -> bool:
        """Check if this heuristic should fire on the given module."""
        if not self.enabled:
            return False
        if self.cooldown > 0 and cycle - self._last_applied < self.cooldown:
            return False
        return self.condition(module)

    def apply(self, module: object, cycle: int) -> int:
        """Apply the heuristic action. Returns number of items affected."""
        self._last_applied = cycle
        return self.action(module)


class HeuristicPool:
    """A pool of memory management heuristics.

    Heuristics can be registered, enabled/disabled, and applied
    in priority order to optimize memory modules.
    """

    def __init__(self) -> None:
        self._heuristics: dict[str, MemoryHeuristic] = {}
        self._cycle: int = 0

    def register(self, heuristic: MemoryHeuristic) -> None:
        self._heuristics[heuristic.id] = heuristic

    def unregister(self, heuristic_id: str) -> bool:
        return self._heuristics.pop(heuristic_id, None) is not None

    def enable(self, heuristic_id: str) -> bool:
        h = self._heuristics.get(heuristic_id)
        if h:
            h.enabled = True
            return True
        return False

    def disable(self, heuristic_id: str) -> bool:
        h = self._heuristics.get(heuristic_id)
        if h:
            h.enabled = False
            return True
        return False

    def tick(self) -> int:
        """Advance the cycle counter."""
        self._cycle += 1
        return self._cycle

    def apply(self, module: object, max_heuristics: int = 3) -> int:
        """Apply heuristics to a module in priority order. Returns total affected."""
        sorted_heuristics = sorted(
            [h for h in self._heuristics.values() if h.enabled],
            key=lambda h: h.priority,
            reverse=True,
        )

        total_affected = 0
        applied = 0
        for h in sorted_heuristics:
            if applied >= max_heuristics:
                break
            if h.applies(module, self._cycle):
                total_affected += h.apply(module, self._cycle)
                applied += 1

        return total_affected

    @property
    def heuristics(self) -> list[MemoryHeuristic]:
        return list(self._heuristics.values())

    @property
    def enabled_count(self) -> int:
        return sum(1 for h in self._heuristics.values() if h.enabled)

    @property
    def cycle(self) -> int:
        return self._cycle

    def top_k(self, k: int = 3) -> list[MemoryHeuristic]:
        """Get the top-k enabled heuristics by priority."""
        enabled = sorted(
            [h for h in self._heuristics.values() if h.enabled],
            key=lambda h: h.priority,
            reverse=True,
        )
        return enabled[:k]

    def find(self, name: str) -> list[MemoryHeuristic]:
        """Find heuristics by name (case-insensitive substring match)."""
        lower = name.lower()
        return [h for h in self._heuristics.values() if lower in h.name.lower()]
