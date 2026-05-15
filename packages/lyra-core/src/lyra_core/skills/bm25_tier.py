"""L38-1 — Tier-1 BM25 scorer for the Argus skill cascade.

Argus's tier cascade (see `LYRA_V3_8_ARGUS_INTEGRATION_PLAN.md` §1)
inserts a lexical retrieval stage between the existing description-
overlap matcher (Tier 0, ``HybridSkillRouter._trigger_overlap``) and
the embedding / cross-encoder / KG stages (Tier 2-4, deferred to
later phases).

This module ships the Tier-1 wrapper. It reuses ProceduralMemory's
existing FTS5 store rather than building a parallel index, so:

* the same SQLite file holds the registry and the BM25 substrate,
* skill descriptions automatically participate in BM25 the moment
  they're written via ``ProceduralMemory.put``,
* the router can degrade gracefully — if no ProceduralMemory is
  attached, ``BM25Tier.score()`` returns an empty list and the
  cascade falls through to Tier 0 alone.

Scoring contract: ``BM25Tier.score(query)`` returns a list of
``BM25Hit(skill_id, score)`` sorted high → low, with scores in
``(0, 1]`` (normalised from FTS5 BM25 raw via ``1 / (1 + raw)``).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from ..memory.procedural import ProceduralMemory, SkillRecord


__all__ = ["BM25Hit", "BM25Tier"]


@dataclass(frozen=True)
class BM25Hit:
    """One BM25-scored skill hit.

    ``skill_id`` matches the id used in ``Skill`` (registry) and
    ``SkillRecord`` (procedural memory) so the caller can join
    against either side without translation.
    """

    skill_id: str
    score: float
    record: SkillRecord


@dataclass
class BM25Tier:
    """Tier-1 BM25 retrieval over a ``ProceduralMemory`` substrate.

    Construct with the procedural memory whose FTS5 index will serve
    as the lexical substrate. The tier is read-only — it never
    writes to the substrate; ``ProceduralMemory.put`` is still the
    only ingestion path.
    """

    memory: ProceduralMemory
    top_k: int = 20
    min_score: float = 0.0

    def score(self, query: str) -> list[BM25Hit]:
        """Run BM25 over the substrate. Empty query → empty result."""
        q = (query or "").strip()
        if not q:
            return []
        scored = self.memory.search_with_scores(q)
        hits: list[BM25Hit] = []
        for record, raw in scored:
            if raw < self.min_score:
                continue
            hits.append(BM25Hit(skill_id=record.id, score=raw, record=record))
        hits.sort(key=lambda h: h.score, reverse=True)
        if self.top_k > 0:
            hits = hits[: self.top_k]
        return hits

    def score_map(self, query: str) -> dict[str, float]:
        """Convenience: return ``{skill_id: score}`` for fast joins."""
        return {h.skill_id: h.score for h in self.score(query)}

    def known_ids(self) -> set[str]:
        """Every skill_id present in the BM25 substrate.

        Useful for the cascade router to detect skills that exist in
        the in-memory ``SkillRegistry`` but haven't been ingested into
        ProceduralMemory yet — those should still be scored via Tier 0
        rather than silently dropped.
        """
        return {r.id for r in self.memory.all()}

    @staticmethod
    def normalise(raw_bm25: float) -> float:
        """Public form of the FTS5 raw → ``(0, 1]`` confidence map."""
        return 1.0 / (1.0 + max(0.0, raw_bm25))
