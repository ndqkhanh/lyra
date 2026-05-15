"""harness_core.memory_consolidation — bounded memory over multi-day sessions.

Long-running agents accumulate EPISODIC + WORKING memory faster than they
prune. Without consolidation, retrieval recall degrades (more haystack)
and stores grow unboundedly. Consolidation is the *compaction* step:
group similar old items, summarize each group, write the summary as one
SEMANTIC item, delete the originals.

The package wires four pieces:

    - :class:`ConsolidationPolicy` — eligibility (age, access count,
      importance, kind).
    - :class:`GroupingStrategy` — :class:`TagGrouping`,
      :class:`TokenJaccardGrouping`.
    - :class:`Summarizer` — :class:`ExtractiveSummarizer` (deterministic
      stdlib fallback; production wires LLM-backed summarizers).
    - :class:`MemoryConsolidator` — orchestrator that applies the above
      to a :class:`harness_core.memory_store.MemoryStore`, optionally
      witnessing each summary on a :class:`WitnessLattice`.

Used by Mentat-Learn (per-channel rolling memory), Lyra (long-running
architecture-doc memory), Polaris (research-session compaction), Helix-Bio
(multi-week experiment journals), Aegis-Ops (incident memory rollups).
"""
from __future__ import annotations

from .consolidator import MemoryConsolidator
from .grouping import TagGrouping, TokenJaccardGrouping
from .summarizer import ExtractiveSummarizer
from .types import (
    ConsolidationPolicy,
    ConsolidationReport,
    GroupingStrategy,
    Summarizer,
)

__all__ = [
    "ConsolidationPolicy",
    "ConsolidationReport",
    "ExtractiveSummarizer",
    "GroupingStrategy",
    "MemoryConsolidator",
    "Summarizer",
    "TagGrouping",
    "TokenJaccardGrouping",
]
