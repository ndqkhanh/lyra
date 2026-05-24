"""MemoryConsolidator — apply policy + grouping + summarizer to a MemoryStore.

The consolidator is the entry point. One call to :meth:`consolidate` runs
one pass:

    1. Filter to eligible items per :class:`ConsolidationPolicy`.
    2. Bucket eligible items by namespace (consolidation never crosses
       namespaces — that would leak data between users / projects).
    3. Group within each namespace via the provided :class:`GroupingStrategy`.
    4. For each group whose size meets ``min_group_size``: call the
       :class:`Summarizer`, write a new SEMANTIC item carrying the merged
       tags + max parent importance + parent IDs in metadata, and delete
       the originals.
    5. Optionally emit a witness on the lattice for each summary so the
       consolidation is auditable.

Returns a :class:`ConsolidationReport` describing what changed.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

from ..memory_store import MemoryItem, MemoryKind, MemoryStore
from ..provenance import WitnessLattice
from .grouping import TagGrouping
from .summarizer import ExtractiveSummarizer
from .types import (
    ConsolidationPolicy,
    ConsolidationReport,
    GroupingStrategy,
    Summarizer,
)


@dataclass
class MemoryConsolidator:
    """Apply consolidation policy to a :class:`MemoryStore`.

    >>> from harness_core.memory_store import MemoryStore, MemoryKind
    >>> store = MemoryStore()
    >>> # ... write a bunch of EPISODIC items with shared tags ...
    >>> consolidator = MemoryConsolidator(
    ...     store=store,
    ...     policy=ConsolidationPolicy(min_age_seconds=0.0, min_group_size=2),
    ... )
    >>> report = consolidator.consolidate()
    >>> report.n_summaries_created >= 0
    True
    """

    store: MemoryStore
    policy: ConsolidationPolicy = field(default_factory=ConsolidationPolicy)
    grouping: GroupingStrategy = field(default_factory=TagGrouping)
    summarizer: Summarizer = field(default_factory=ExtractiveSummarizer)
    lattice: Optional[WitnessLattice] = None
    agent_id: str = "consolidator"
    _clock_fn: object = field(default_factory=lambda: time.time)

    def consolidate(
        self,
        *,
        namespace: Optional[str] = None,
    ) -> ConsolidationReport:
        """Run one consolidation pass over the store.

        ``namespace=None`` consolidates every namespace independently.
        """
        now = self._now()
        eligible = [
            item
            for item in self.store._items.values()  # noqa: SLF001 - intentional internal access
            if self._is_eligible(item, now=now, namespace=namespace)
        ]
        if not eligible:
            return ConsolidationReport(
                n_eligible=0,
                n_consolidated=0,
                n_summaries_created=0,
                n_skipped_groups=0,
            )

        # Bucket by namespace; never group across namespace boundaries.
        by_ns: dict[str, list[MemoryItem]] = {}
        for it in eligible:
            by_ns.setdefault(it.namespace, []).append(it)

        n_consolidated = 0
        n_summaries = 0
        n_skipped = 0
        summary_ids: list[str] = []
        witness_ids: list[str] = []

        for ns, ns_items in by_ns.items():
            groups = self.grouping.group(ns_items)
            for group in groups:
                if len(group) < self.policy.min_group_size:
                    n_skipped += 1
                    continue
                summary_id, witness_id = self._consolidate_group(
                    group=group,
                    namespace=ns,
                )
                summary_ids.append(summary_id)
                if witness_id:
                    witness_ids.append(witness_id)
                n_summaries += 1
                n_consolidated += len(group)

        return ConsolidationReport(
            n_eligible=len(eligible),
            n_consolidated=n_consolidated,
            n_summaries_created=n_summaries,
            n_skipped_groups=n_skipped,
            summary_item_ids=tuple(summary_ids),
            summary_witness_ids=tuple(witness_ids),
        )

    # --- Internals -------------------------------------------------------

    def _is_eligible(
        self,
        item: MemoryItem,
        *,
        now: float,
        namespace: Optional[str],
    ) -> bool:
        if namespace is not None and item.namespace != namespace:
            return False
        if item.kind not in self.policy.target_kinds:
            return False
        if item.access_count > self.policy.max_access_count:
            return False
        if item.importance >= self.policy.preserve_min_importance:
            return False
        if (now - item.accessed_at) < self.policy.min_age_seconds:
            return False
        return True

    def _consolidate_group(
        self,
        *,
        group: list[MemoryItem],
        namespace: str,
    ) -> tuple[str, str]:
        summary_text = self.summarizer.summarize(group)
        merged_tags = tuple(sorted({t for it in group for t in it.tags} | {"consolidated"}))
        max_importance = max(it.importance for it in group)
        parent_ids = tuple(it.item_id for it in group)

        summary_item = self.store.write(
            kind=MemoryKind.SEMANTIC,
            content=summary_text,
            namespace=namespace,
            importance=max_importance,
            tags=merged_tags,
            metadata={
                "consolidated_from": list(parent_ids),
                "n_parents": len(group),
            },
        )

        for it in group:
            self.store.delete(it.item_id)

        witness_id = ""
        if self.lattice is not None:
            w = self.lattice.record_decision(
                agent_id=self.agent_id,
                action="consolidate_memory",
                fingerprint=summary_item.item_id,
                parent_witnesses=(),
            )
            witness_id = w.witness_id

        return summary_item.item_id, witness_id

    def _now(self) -> float:
        clock = self._clock_fn
        # Allow callers to inject a fixed clock for deterministic tests.
        if callable(clock):
            return clock()
        return time.time()


__all__ = ["MemoryConsolidator"]
