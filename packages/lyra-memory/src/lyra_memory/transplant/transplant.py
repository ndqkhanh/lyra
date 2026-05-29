"""
Memory Transplant — transfers memory entries between modules
for rebalancing and reorganization without data loss.

Source: Modular Compression (ztmwHisqJ4), ICLR 2026 MemAgent Workshop.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4


@dataclass
class TransplantRecord:
    """Record of a memory transplant operation."""

    source_module: str
    target_module: str
    entry: str
    importance: float
    id: str = field(default_factory=lambda: uuid4().hex)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class MemoryTransplanter:
    """Transfers memory entries between modules.

    Used when module interference or size requires rebalancing.
    Preserves entry content and tracks full transplant history.
    """

    def __init__(self) -> None:
        self._history: list[TransplantRecord] = []

    def transplant(
        self,
        source_module: object,
        target_module: object,
        indices: list[int],
        importance: float = 0.5,
    ) -> list[TransplantRecord]:
        """Move entries from source to target module by index.

        Returns transplant records for each moved entry.
        """
        from lyra_memory.modular.memory_module import ModularMemoryModule

        src: ModularMemoryModule = source_module  # type: ignore[assignment]
        tgt: ModularMemoryModule = target_module  # type: ignore[assignment]

        records: list[TransplantRecord] = []
        entries_to_move = src.retrieve(indices)

        for _i, entry in zip(indices, entries_to_move):
            tgt.add(entry)
            record = TransplantRecord(
                source_module=src.name,
                target_module=tgt.name,
                entry=entry,
                importance=importance,
            )
            records.append(record)
            self._history.append(record)

        return records

    @property
    def history(self) -> list[TransplantRecord]:
        return list(self._history)

    @property
    def transplant_count(self) -> int:
        return len(self._history)

    def recent(self, count: int = 10) -> list[TransplantRecord]:
        """Get the most recent transplant records."""
        return self._history[-count:] if self._history else []

    def clear_history(self) -> None:
        self._history.clear()

    def filter_by_source(self, module_name: str) -> list[TransplantRecord]:
        return [r for r in self._history if r.source_module == module_name]

    def filter_by_target(self, module_name: str) -> list[TransplantRecord]:
        return [r for r in self._history if r.target_module == module_name]
