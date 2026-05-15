"""Types for memory_consolidation — policy + grouping + summarizer protocols."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from ..memory_store import MemoryItem, MemoryKind


@dataclass(frozen=True)
class ConsolidationPolicy:
    """Eligibility rules for consolidating MemoryItems.

    An item is *eligible* for consolidation when ALL of:

        - Its ``accessed_at`` is older than ``min_age_seconds`` from now.
        - Its ``access_count`` is at most ``max_access_count`` (hot items
          are too useful to compress).
        - Its ``importance`` is below ``preserve_min_importance`` (pinned
          items must survive verbatim).
        - Its ``kind`` is in ``target_kinds`` (e.g., default targets only
          EPISODIC + WORKING — semantic facts and procedural skills are
          assumed already-distilled).

    Then a *group* is consolidated only when its size is at least
    ``min_group_size``. Groups smaller than that are left alone.

    Defaults bias toward conservatism: long memories (1 day+), small groups
    (3+), and protected importance (>= 0.9 stays verbatim).
    """

    min_age_seconds: float = 86400.0  # 1 day
    min_group_size: int = 3
    max_access_count: int = 5
    target_kinds: tuple[MemoryKind, ...] = (
        MemoryKind.EPISODIC,
        MemoryKind.WORKING,
    )
    preserve_min_importance: float = 0.9

    def __post_init__(self) -> None:
        if self.min_age_seconds < 0:
            raise ValueError(
                f"min_age_seconds must be >= 0, got {self.min_age_seconds}"
            )
        if self.min_group_size < 2:
            raise ValueError(
                f"min_group_size must be >= 2, got {self.min_group_size}"
            )
        if self.max_access_count < 0:
            raise ValueError(
                f"max_access_count must be >= 0, got {self.max_access_count}"
            )
        if not 0.0 <= self.preserve_min_importance <= 1.0:
            raise ValueError(
                f"preserve_min_importance must be in [0, 1], got "
                f"{self.preserve_min_importance}"
            )
        if not self.target_kinds:
            raise ValueError("target_kinds must be non-empty")


@dataclass(frozen=True)
class ConsolidationReport:
    """Outcome of one consolidation pass."""

    n_eligible: int
    n_consolidated: int  # items absorbed into summaries
    n_summaries_created: int
    n_skipped_groups: int  # groups smaller than min_group_size
    summary_item_ids: tuple[str, ...] = field(default_factory=tuple)
    summary_witness_ids: tuple[str, ...] = field(default_factory=tuple)


class GroupingStrategy(Protocol):
    """Cluster eligible MemoryItems for joint summarization.

    Implementations must NOT mix items across namespaces — caller groups by
    namespace before invoking, but a defensive impl can assert it.
    """

    def group(self, items: list[MemoryItem]) -> list[list[MemoryItem]]: ...


class Summarizer(Protocol):
    """Render a group of MemoryItems into a single summary string.

    Production wires an LLM-backed summarizer; the built-in extractive
    summarizer is a deterministic stdlib-only fallback.
    """

    def summarize(self, items: list[MemoryItem]) -> str: ...


__all__ = [
    "ConsolidationPolicy",
    "ConsolidationReport",
    "GroupingStrategy",
    "Summarizer",
]
