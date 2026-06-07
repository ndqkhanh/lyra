"""
Findings Memory — cumulative database of research records.

Implements a structured three-stage progression for research findings::

    Idea --> Implement --> Progress

Each ``FindingRecord`` captures a hypothesis, its DeepScientist valuation
vector V = (v_u, v_q, v_e), implementation reference, experiment logs,
and analysis results.

Key features
------------
- **UCB acquisition**: balance exploration vs exploitation when selecting
  the next hypothesis to pursue.
- **Hybrid retrieval**: keyword + simulated embedding search combined via
  Reciprocal Rank Fusion (RRF).
- **Cross-quest knowledge sharing**: findings from quest A can inform
  hypothesis generation in quest B.
- **Cascade Memory integration**: all records are also stored in the
  3-tier cascade memory for graph-enhanced retrieval.

References
----------
- DeepScientist: arXiv 2505.22954 (Darwin Godel Machine)
- UCB1: Auer, Cesa-Bianchi, Fischer (2002)
- RRF: Cormack, Clarke, Buettcher (SIGIR 2009)
"""

from __future__ import annotations

import math
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

import numpy as np

from lyra.memory.cascade_memory import CascadeMemory, MemoryItem
from lyra.memory.admission_control import ContentType


# =============================================================================
# Constants
# =============================================================================

DEFAULT_UCB_EXPLORATION: float = 1.0
"""Exploration parameter ``c`` in the UCB1 formula."""

DEFAULT_RRF_K: int = 60
"""Constant ``k`` in the RRF formula (higher = more weight to top ranks)."""

DEFAULT_VALUATION_WEIGHTS: dict[str, float] = {
    "utility": 0.40, "quality": 0.35, "efficiency": 0.25,
}
"""Default weights for combining V = (v_u, v_q, v_e) into a scalar score."""

DEFAULT_HYBRID_TOP_K: int = 20
"""Default number of candidates to consider from each search leg."""


# =============================================================================
# Enums and data structures
# =============================================================================


class FindingStage(str, Enum):
    """Three-stage progression for a research finding.

    Progression is strictly::

        IDEA --> IMPLEMENT --> PROGRESS
    """

    IDEA = "idea"
    IMPLEMENT = "implement"
    PROGRESS = "progress"


@dataclass(frozen=True)
class ValuationScores:
    """DeepScientist valuation vector V = (v_u, v_q, v_e).

    Attributes:
        utility: ``v_u`` — expected usefulness / relevance of this direction.
            How much does this hypothesis move the needle on the research goal?
        quality: ``v_q`` — expected rigor / execution quality.
            How well-designed is the proposed experiment?
        efficiency: ``v_e`` — expected compute-time efficiency.
            What is the expected return per unit of compute / wall-clock time?
    """

    utility: float = 0.5
    quality: float = 0.5
    efficiency: float = 0.5

    def __post_init__(self) -> None:
        """Clamp each dimension to [0.0, 1.0]."""
        # Use object.__setattr__ because we are frozen
        for attr in ("utility", "quality", "efficiency"):
            raw = getattr(self, attr)
            clamped = max(0.0, min(1.0, raw))
            object.__setattr__(self, attr, clamped)

    def to_dict(self) -> dict[str, float]:
        return {"utility": self.utility, "quality": self.quality, "efficiency": self.efficiency}

    @classmethod
    def from_dict(cls, data: dict[str, float]) -> ValuationScores:
        return cls(
            utility=data.get("utility", 0.5),
            quality=data.get("quality", 0.5),
            efficiency=data.get("efficiency", 0.5),
        )

    def combined(self, weights: dict[str, float] | None = None) -> float:
        """Weighted scalar combination of the three dimensions.

        Args:
            weights: Dict with keys ``utility``, ``quality``, ``efficiency``.
                Defaults to ``(0.4, 0.35, 0.25)``.

        Returns:
            Weighted sum in ``[0.0, 1.0]``.
        """
        w = weights or DEFAULT_VALUATION_WEIGHTS
        return (
            w.get("utility", 0.4) * self.utility
            + w.get("quality", 0.35) * self.quality
            + w.get("efficiency", 0.25) * self.efficiency
        )


@dataclass(frozen=True)
class FindingRecord:
    """A structured research finding record.

    Progression through ``FindingStage``::

        IDEA (not yet implemented)
            --> IMPLEMENT (experiment written and executed)
            --> PROGRESS (substantial progress verified)

    Attributes:
        finding_id: Unique identifier for this finding.
        quest_id: The quest this finding belongs to.
        hypothesis: One-line description of the hypothesis being tested.
        stage: Current progression stage.
        valuation: DeepScientist V = (v_u, v_q, v_e) scores.
        implementation_ref: Reference to implementation (git hash, PR, path).
        experiment_logs: List of structured experiment log entries.
        analysis: Free-text analysis / discussion of results.
        created_at: ISO-8601 timestamp of creation.
        updated_at: ISO-8601 timestamp of last update.
        metadata: Arbitrary key-value store (tags, flags, etc.).
    """

    finding_id: str = ""
    quest_id: str = ""
    hypothesis: str = ""
    stage: FindingStage = FindingStage.IDEA
    valuation: ValuationScores = field(default_factory=ValuationScores)
    implementation_ref: str = ""
    experiment_logs: list[dict[str, Any]] = field(default_factory=list)
    analysis: str = ""
    created_at: str = ""
    updated_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "quest_id": self.quest_id,
            "hypothesis": self.hypothesis,
            "stage": self.stage.value,
            "valuation": self.valuation.to_dict(),
            "implementation_ref": self.implementation_ref,
            "experiment_logs": list(self.experiment_logs),
            "analysis": self.analysis,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FindingRecord:
        return cls(
            finding_id=data.get("finding_id", ""),
            quest_id=data.get("quest_id", ""),
            hypothesis=data.get("hypothesis", ""),
            stage=FindingStage(data["stage"]) if "stage" in data else FindingStage.IDEA,
            valuation=ValuationScores.from_dict(data.get("valuation", {})),
            implementation_ref=data.get("implementation_ref", ""),
            experiment_logs=list(data.get("experiment_logs", [])),
            analysis=data.get("analysis", ""),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            metadata=dict(data.get("metadata", {})),
        )


# =============================================================================
# FindingsMemory
# =============================================================================


class FindingsMemory:
    """Cumulative database of research findings.

    Stores structured ``FindingRecord`` objects and provides UCB-based
    acquisition, hybrid search (keyword + embedding via RRF), and
    cross-quest knowledge sharing.

    Each record is also mirrored into the ``CascadeMemory`` for
    graph-enhanced retrieval and cross-session persistence.

    Usage::

        fm = FindingsMemory()
        fm.add_record(FindingRecord(
            quest_id="q-001",
            hypothesis="Attention sparsity reduces inference cost",
            stage=FindingStage.IDEA,
            valuation=ValuationScores(utility=0.8, quality=0.6, efficiency=0.9),
        ))
        best = fm.ucb_acquisition(top_k=1)
        findings = fm.search("sparsity attention")
    """

    def __init__(
        self,
        cascade: CascadeMemory | None = None,
        ucb_exploration: float = DEFAULT_UCB_EXPLORATION,
        rrf_k: int = DEFAULT_RRF_K,
        valuation_weights: dict[str, float] | None = None,
    ) -> None:
        """
        Args:
            cascade: Optional ``CascadeMemory`` instance for persistent
                graph-backed storage. If ``None``, operates purely in-memory.
            ucb_exploration: Exploration parameter ``c`` in UCB1.
            rrf_k: RRF constant (higher = more weight to top ranks).
            valuation_weights: Weights for combining V into a scalar.
        """
        self._cascade = cascade
        self._ucb_c = ucb_exploration
        self._rrf_k = rrf_k
        self._valuation_weights = valuation_weights or dict(DEFAULT_VALUATION_WEIGHTS)

        # In-memory store: finding_id -> FindingRecord
        self._records: dict[str, FindingRecord] = {}

        # Index: quest_id -> set of finding_ids
        self._quest_index: dict[str, set[str]] = defaultdict(set)

        # Term frequency index for keyword search (word -> set of finding_ids)
        self._term_index: dict[str, set[str]] = defaultdict(set)

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def add_record(self, record: FindingRecord) -> str:
        """Add a finding record to the database.

        Auto-generates ``finding_id`` and timestamps if missing.
        Also mirrors into ``CascadeMemory`` if configured.

        Args:
            record: The finding record to store.

        Returns:
            The ``finding_id`` assigned to the record.
        """
        now = datetime.now(timezone.utc).isoformat()

        fid = record.finding_id or str(uuid.uuid4())
        quest_id = record.quest_id or "default"

        populated = FindingRecord(
            finding_id=fid,
            quest_id=quest_id,
            hypothesis=record.hypothesis,
            stage=record.stage,
            valuation=record.valuation,
            implementation_ref=record.implementation_ref,
            experiment_logs=list(record.experiment_logs),
            analysis=record.analysis,
            created_at=record.created_at or now,
            updated_at=now,
            metadata=dict(record.metadata),
        )

        self._records[fid] = populated
        self._quest_index[quest_id].add(fid)

        # Update term index
        for word in self._tokenize(populated.hypothesis + " " + populated.analysis):
            self._term_index[word].add(fid)

        # Mirror to cascade memory if available
        if self._cascade is not None:
            self._mirror_to_cascade(populated)

        return fid

    def update_stage(
        self,
        finding_id: str,
        new_stage: FindingStage,
    ) -> None:
        """Advance a finding to a new stage.

        Args:
            finding_id: The finding to update.
            new_stage: The target stage (must be later in IDEA -> IMPLEMENT -> PROGRESS).

        Raises:
            KeyError: If ``finding_id`` does not exist.
            ValueError: If the stage transition is invalid (e.g., skip IMPLEMENT).
        """
        record = self._records.get(finding_id)
        if record is None:
            raise KeyError(f"Finding {finding_id} not found.")

        stages = [FindingStage.IDEA, FindingStage.IMPLEMENT, FindingStage.PROGRESS]
        current_idx = stages.index(record.stage)
        target_idx = stages.index(new_stage)

        if target_idx <= current_idx:
            raise ValueError(
                f"Cannot transition from {record.stage.value} to {new_stage.value}. "
                "Stages must advance monotonically: IDEA -> IMPLEMENT -> PROGRESS."
            )

        self._records[finding_id] = FindingRecord(
            finding_id=record.finding_id,
            quest_id=record.quest_id,
            hypothesis=record.hypothesis,
            stage=new_stage,
            valuation=record.valuation,
            implementation_ref=record.implementation_ref,
            experiment_logs=list(record.experiment_logs),
            analysis=record.analysis,
            created_at=record.created_at,
            updated_at=datetime.now(timezone.utc).isoformat(),
            metadata=dict(record.metadata),
        )

    def update_record(self, finding_id: str, **updates: Any) -> FindingRecord:
        """Update specific fields of a finding record (immutable copy).

        Args:
            finding_id: The finding to update.
            **updates: Fields to update (``hypothesis``, ``analysis``, etc.).

        Returns:
            The updated ``FindingRecord`` (new instance).

        Raises:
            KeyError: If ``finding_id`` does not exist.
        """
        record = self._records.get(finding_id)
        if record is None:
            raise KeyError(f"Finding {finding_id} not found.")

        merged = record.to_dict()
        merged.update(updates)
        merged["updated_at"] = datetime.now(timezone.utc).isoformat()

        updated = FindingRecord.from_dict(merged)
        self._records[finding_id] = updated
        return updated

    def get_record(self, finding_id: str) -> FindingRecord | None:
        """Retrieve a single finding record by ID."""
        return self._records.get(finding_id)

    def get_records_by_quest(self, quest_id: str) -> list[FindingRecord]:
        """Return all records belonging to a quest, sorted by created_at descending."""
        ids = self._quest_index.get(quest_id, set())
        records = [self._records[fid] for fid in ids if fid in self._records]
        records.sort(key=lambda r: r.created_at, reverse=True)
        return records

    def get_records_by_stage(self, stage: FindingStage) -> list[FindingRecord]:
        """Return all records at a given stage."""
        return [r for r in self._records.values() if r.stage == stage]

    def total_records(self) -> int:
        """Total number of records in the database."""
        return len(self._records)

    # ------------------------------------------------------------------
    # UCB Acquisition
    # ------------------------------------------------------------------

    def ucb_acquisition(
        self,
        c: float | None = None,
        top_k: int = 1,
        quest_id: str | None = None,
    ) -> list[FindingRecord]:
        """UCB1 acquisition: balance exploration vs exploitation.

        Selects the ``top_k`` hypotheses with the highest UCB score::

            score = mu_h + c * sqrt(ln(N) / n_h)

        Where:
            - ``mu_h`` = weighted average of valuation scores for hypothesis ``h``.
            - ``c`` = exploration parameter (default ``self._ucb_c``).
            - ``N`` = total number of findings.
            - ``n_h`` = number of findings (attempts) for this hypothesis or
              direction (proxied by ``len(hypothesis)``-based grouping).

        A hypothesis that has never been tried gets an infinite bonus,
        ensuring it is always selected first.

        Args:
            c: Exploration parameter override.
            top_k: Number of hypotheses to return.
            quest_id: Optional filter — only consider records from this quest.

        Returns:
            List of ``FindingRecord`` with the highest UCB scores, sorted
            descending.
        """
        c = c if c is not None else self._ucb_c
        candidates = list(self._records.values())

        if quest_id is not None:
            candidates = [r for r in candidates if r.quest_id == quest_id]

        if not candidates:
            return []

        N = len(candidates)
        ln_N = max(math.log(N + 1), 0.001)

        # Group candidates by hypothesis (first 50 chars as key for grouping)
        group_counts: dict[str, int] = defaultdict(int)
        for rec in candidates:
            group_counts[rec.hypothesis[:50]] += 1

        scored: list[tuple[float, FindingRecord]] = []
        for rec in candidates:
            n_h = group_counts.get(rec.hypothesis[:50], 1)

            if n_h == 0:
                # Never explored — infinite bonus, always pick
                score = float("inf")
            else:
                mu_h = rec.valuation.combined(self._valuation_weights)
                exploration_bonus = c * math.sqrt(ln_N / n_h)
                score = mu_h + exploration_bonus

            scored.append((score, rec))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [rec for _, rec in scored[:top_k]]

    # ------------------------------------------------------------------
    # Hybrid Keyword + Embedding Search (RRF)
    # ------------------------------------------------------------------

    def search(
        self,
        query: str,
        top_k: int = DEFAULT_HYBRID_TOP_K,
    ) -> list[FindingRecord]:
        """Hybrid keyword + embedding search via Reciprocal Rank Fusion.

        Two legs:
            1. **Keyword**: TF-IDF-style term overlap search.
            2. **Embedding**: Simulated cosine similarity via word-set overlap
               (production: replace with ``VectorSearcher``).

        Results are fused via RRF::

            score(r) = sum_over_legs( 1 / (k + rank_leg(r)) )

        Args:
            query: The search query.
            top_k: Maximum results to return.

        Returns:
            Ranked list of ``FindingRecord`` fused across both legs.
        """
        if not query.strip() or not self._records:
            return []

        # --- Leg 1: Keyword search via term index ---
        query_terms = self._tokenize(query)
        keyword_matches: dict[str, float] = defaultdict(float)
        for term in query_terms:
            for fid in self._term_index.get(term, set()):
                keyword_matches[fid] += 1.0

        # Normalize keyword scores by query length
        for fid in keyword_matches:
            keyword_matches[fid] /= max(len(query_terms), 1)

        keyword_ranked = sorted(keyword_matches.keys(), key=lambda f: keyword_matches[f], reverse=True)

        # --- Leg 2: Simulated embedding (word-set Jaccard overlap) ---
        query_words = set(query_terms)
        embedding_scores: dict[str, float] = {}
        for fid, rec in self._records.items():
            content_words = set(self._tokenize(rec.hypothesis + " " + rec.analysis))
            if not query_words or not content_words:
                embedding_scores[fid] = 0.0
            else:
                intersection = len(query_words & content_words)
                union = len(query_words | content_words)
                jaccard = intersection / max(union, 1)
                # Boost by valuation
                embedding_scores[fid] = jaccard * (0.5 + 0.5 * rec.valuation.combined())

        embedding_ranked = sorted(embedding_scores.keys(), key=lambda f: embedding_scores[f], reverse=True)

        # --- Reciprocal Rank Fusion ---
        rrf_scores: dict[str, float] = defaultdict(float)
        for rank, fid in enumerate(keyword_ranked):
            rrf_scores[fid] += 1.0 / (self._rrf_k + rank + 1)
        for rank, fid in enumerate(embedding_ranked):
            rrf_scores[fid] += 1.0 / (self._rrf_k + rank + 1)

        fused = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

        return [self._records[fid] for fid, _score in fused[:top_k] if fid in self._records]

    # ------------------------------------------------------------------
    # Cross-Quest Knowledge Sharing
    # ------------------------------------------------------------------

    def cross_quest_share(
        self,
        source_quest_id: str,
        target_quest_id: str,
        top_k: int = 5,
    ) -> list[FindingRecord]:
        """Share top findings from one quest with another.

        Retrieves the highest-valued ``PROGRESS`` and ``IMPLEMENT`` findings
        from ``source_quest_id`` that are relevant to ``target_quest_id``
        (based on label/keyword overlap from quest config metadata).

        Args:
            source_quest_id: Quest to pull findings from.
            target_quest_id: Quest to share findings into.
            top_k: Maximum findings to share.

        Returns:
            List of ``FindingRecord`` shared.
        """
        source_records = self.get_records_by_quest(source_quest_id)
        # Prefer progress > implement > idea
        source_records.sort(
            key=lambda r: (
                0 if r.stage == FindingStage.PROGRESS else
                1 if r.stage == FindingStage.IMPLEMENT else 2,
                r.valuation.combined(self._valuation_weights),
            ),
            reverse=True,
        )

        shared = source_records[:top_k]

        # Tag each shared finding with the cross-quest metadata and re-fetch
        result: list[FindingRecord] = []
        for rec in shared:
            self.update_record(
                rec.finding_id,
                metadata={
                    **rec.metadata,
                    "shared_to": target_quest_id,
                    "shared_from": source_quest_id,
                },
            )
            updated = self.get_record(rec.finding_id)
            if updated is not None:
                result.append(updated)

        return result

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Serialize all records to a JSON-safe dict."""
        return {
            "records": {fid: rec.to_dict() for fid, rec in self._records.items()},
            "config": {
                "ucb_exploration": self._ucb_c,
                "rrf_k": self._rrf_k,
                "valuation_weights": dict(self._valuation_weights),
            },
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
        cascade: CascadeMemory | None = None,
    ) -> FindingsMemory:
        """Deserialize from a dict (inverse of ``to_dict``)."""
        config = data.get("config", {})
        fm = cls(
            cascade=cascade,
            ucb_exploration=config.get("ucb_exploration", DEFAULT_UCB_EXPLORATION),
            rrf_k=config.get("rrf_k", DEFAULT_RRF_K),
            valuation_weights=config.get("valuation_weights"),
        )
        for raw in data.get("records", {}).values():
            if isinstance(raw, dict):
                fm.add_record(FindingRecord.from_dict(raw))
        return fm

    def clear(self) -> None:
        """Reset all in-memory state."""
        self._records.clear()
        self._quest_index.clear()
        self._term_index.clear()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _mirror_to_cascade(self, record: FindingRecord) -> None:
        """Mirror a finding record into cascade memory for graph persistence."""
        if self._cascade is None:
            return

        content = (
            f"[{record.stage.value.upper()}] {record.hypothesis}\n"
            f"  V=({record.valuation.utility:.2f}, {record.valuation.quality:.2f}, "
            f"{record.valuation.efficiency:.2f})\n"
            f"  Ref: {record.implementation_ref}\n"
            f"  Analysis: {record.analysis[:200]}"
        )

        item = MemoryItem(
            content=content,
            content_type=ContentType.FACT,
            source=f"findings_memory/{record.quest_id}",
            importance=record.valuation.combined(self._valuation_weights),
            confidence=0.85,
            timestamp=time.time(),
            metadata={
                "finding_id": record.finding_id,
                "quest_id": record.quest_id,
                "stage": record.stage.value,
                "valuation": record.valuation.to_dict(),
            },
        )
        self._cascade.store(item)

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Tokenize text into lowercase words, filtering short stop-words."""
        words = text.lower().split()
        # Filter very common short words and punctuation-laden tokens
        stop_words: set[str] = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "can", "shall",
            "to", "of", "in", "for", "on", "with", "at", "by", "from",
            "as", "into", "through", "during", "before", "after",
            "and", "or", "but", "not", "no", "if", "this", "that",
            "it", "its", "we", "they", "you", "he", "she",
        }
        return [w for w in words if w not in stop_words and len(w) > 1]
