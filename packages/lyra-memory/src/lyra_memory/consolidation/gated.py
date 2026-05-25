"""
Gated Memory Consolidation — selectively gates short-term memories
into long-term storage using salience-based thresholds and cooldown.

Source: Modular Compression (ztmwHisqJ4), ICLR 2026 MemAgent Workshop.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4


@dataclass
class GatedMemory:
    """A memory entry pending gate evaluation."""

    content: str
    importance: float
    source: str = ""
    id: str = field(default_factory=lambda: uuid4().hex)
    passed: bool = False
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class GateConfig:
    """Configuration for consolidation gate."""

    threshold: float = 0.5
    cooldown_cycles: int = 3
    max_batch: int = 100


class ConsolidationGate:
    """Gates short-term memories into long-term storage.

    Only memories above the importance threshold pass through.
    A cooldown mechanism prevents flooding by spacing consolidation cycles.
    """

    def __init__(self, config: GateConfig | None = None) -> None:
        self.config = config or GateConfig()
        self._pool: list[GatedMemory] = []
        self._consolidated: list[GatedMemory] = []
        self._cycles: int = 0
        self._last_consolidation: int = -self.config.cooldown_cycles

    def submit(self, content: str, importance: float, source: str = "") -> GatedMemory:
        """Submit a memory for gate evaluation."""
        mem = GatedMemory(content=content, importance=importance, source=source)
        self._pool.append(mem)
        return mem

    def consolidate(self) -> list[GatedMemory]:
        """Run a consolidation cycle. Returns memories that passed the gate."""
        self._cycles += 1

        if self._cycles - self._last_consolidation < self.config.cooldown_cycles:
            return []

        batch = self._pool[-self.config.max_batch:] if len(self._pool) > self.config.max_batch else self._pool
        passed: list[GatedMemory] = []

        for mem in batch:
            if mem.importance >= self.config.threshold:
                mem.passed = True
                passed.append(mem)
                self._consolidated.append(mem)

        self._last_consolidation = self._cycles
        return passed

    @property
    def pool_size(self) -> int:
        return len(self._pool)

    @property
    def consolidated_count(self) -> int:
        return len(self._consolidated)

    @property
    def cycle(self) -> int:
        return self._cycles

    @property
    def pass_rate(self) -> float:
        if not self._pool:
            return 0.0
        return sum(1 for m in self._pool if m.passed) / len(self._pool)
