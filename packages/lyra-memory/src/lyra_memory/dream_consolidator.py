"""
Dream-Style 4-Phase Memory Consolidation for Lyra AGI.

Implements a sleep-inspired memory consolidation pipeline based on hippocampal
replay and systems consolidation neuroscience. The four phases mirror the
dream cycle:

1. ORIENT  — Scan recent session traces for novel knowledge signals
2. GATHER  — Retrieve related memories via semantic, temporal, and entity links
3. CONSOLIDATE — ADD-only extraction with entity resolution and dedup
4. PRUNE   — Ebbinghaus forgetting curve simulation and archival

This module is the high-level orchestrator for memory consolidation.
Lower-level storage and retrieval are delegated to the duck-typed memory_store.

Usage::

    from lyra_memory.dream_consolidator import DreamConsolidator
    consolidator = DreamConsolidator(memory_store=store)
    fragments = consolidator.run_full_cycle(session_traces)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class MemorySignal(str, Enum):
    """Signals that trigger memory consolidation during the orient phase."""

    SEMANTIC = "semantic"
    KEYWORD = "keyword"
    ENTITY = "entity"
    TEMPORAL = "temporal"
    CAUSAL = "causal"
    PROCEDURAL = "procedural"


class DreamPhase(str, Enum):
    """The five phases of entropic dream-style memory consolidation.

    Phase 5 (PROSPECTIVE) is the MemGrad integration phase — it uses
    accumulated memory feedback to generate textual gradients that
    optimize agent prompts for future performance.
    """

    ORIENT = "orient"
    GATHER = "gather"
    CONSOLIDATE = "consolidate"
    PRUNE = "prune"
    PROSPECTIVE = "prospective"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MemoryFragment:
    """
    A single unit of consolidated memory.

    Attributes:
        content: The textual content of the memory.
        source_session_id: Session where this memory was acquired.
        memory_type: Classification — sensory / episodic / semantic /
            procedural / strategic / meta / collective / eternal.
        confidence: Confidence score in [0.0, 1.0].
        entities: Named entities referenced in this fragment.
        timestamp: Unix timestamp of when the memory was created.
        access_count: Number of times this fragment has been accessed.
        last_accessed: Unix timestamp of last access (None if never).
        ttl_days: Time-to-live in days. -1 means no expiration.
        superseded_by: Content of the fragment that supersedes this one,
            or None if this fragment is current.
    """

    content: str
    source_session_id: str
    memory_type: str
    confidence: float
    entities: list[str] = field(default_factory=list)
    timestamp: float = 0.0
    access_count: int = 0
    last_accessed: float | None = None
    ttl_days: int = 30
    superseded_by: str | None = None


@dataclass(frozen=True)
class ConsolidationCandidate:
    """
    A candidate for consolidation with scoring and context metadata.

    Attributes:
        fragment: The candidate memory fragment.
        novelty_score: Novelty score in [0.0, 1.0] (1.0 = completely novel).
        related_memories: Existing memories related to this candidate.
        suggested_merge_targets: Content strings of memories that could
            be merged with this candidate.
    """

    fragment: MemoryFragment
    novelty_score: float = 0.0
    related_memories: list[MemoryFragment] = field(default_factory=list)
    suggested_merge_targets: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class EbbinghausCurve:
    """
    Ebbinghaus forgetting curve model for a single memory.

    Attributes:
        strength: Initial retrieval strength in [0.0, 1.0].
        half_life_days: Number of days for strength to decay by half.
        last_reinforcement: Unix timestamp of the most recent reinforcement.
    """

    strength: float
    half_life_days: float
    last_reinforcement: float

    def current_strength(self, now: float) -> float:
        """
        Calculate current memory strength using exponential decay.

        Formula: ``strength * 0.5 ** ((now - last_reinforcement) / half_life_seconds)``

        Args:
            now: Current Unix timestamp.

        Returns:
            Current strength in [0.0, 1.0].
        """
        elapsed_seconds = now - self.last_reinforcement
        half_life_seconds = self.half_life_days * 86400.0
        half_lives = elapsed_seconds / half_life_seconds
        return self.strength * (0.5 ** half_lives)


@dataclass(frozen=True)
class ConsolidationStats:
    """
    Statistics for a single consolidation phase.

    Attributes:
        phase: Which phase these stats describe.
        candidates_found: Number of candidates identified.
        memories_added: Number of new memories created.
        memories_merged: Number of memories merged.
        memories_pruned: Number of memories pruned (removed from active set).
        memories_archived: Number of memories archived (preserved but inactive).
        duration_ms: Wall-clock duration in milliseconds.
    """

    phase: DreamPhase
    candidates_found: int = 0
    memories_added: int = 0
    memories_merged: int = 0
    memories_pruned: int = 0
    memories_archived: int = 0
    duration_ms: float = 0.0


# ---------------------------------------------------------------------------
# Main consolidator
# ---------------------------------------------------------------------------


class DreamConsolidator:
    """
    Dream-style 4-phase memory consolidation orchestrator.

    Processes session traces through the full dream cycle:

    1. **ORIENT** — Scan and classify novel knowledge signals from session
       traces. Extracts facts, patterns (3+ occurrences), skills, and lessons.
    2. **GATHER** — For each candidate, retrieve related memories via semantic
       similarity (keyword overlap), temporal proximity, and entity links.
    3. **CONSOLIDATE** — ADD-only extraction that never overwrites existing
       fragments. Creates new fragments with ``superseded_by`` links when
       updating. Performs entity resolution, semantic dedup, and principle
       extraction from patterns.
    4. **PRUNE** — Apply Ebbinghaus forgetting curve simulation, staleness
       scoring, redundancy detection, and TTL-based expiration. Archived
       fragments are marked but not deleted.

    The ``memory_store`` parameter is duck-typed and must provide:

    * ``search(query: str, limit: int) -> list[MemoryFragment]``
    * ``save(fragment: MemoryFragment) -> None``

    Args:
        memory_store: Duck-typed store with search/save methods.
        novelty_threshold: Minimum novelty score to accept a candidate
            (default 0.3).
        min_pattern_occurrences: Minimum occurrences to detect a pattern
            (default 3).
        dedup_similarity_threshold: Keyword overlap threshold for dedup
            (default 0.85).
    """

    # Default TTL in days for each memory type.  -1 = no expiration.
    _MEMORY_TTL_MAP: dict[str, int] = {
        "sensory": 1,
        "episodic": 7,
        "semantic": 30,
        "procedural": 90,
        "strategic": -1,
        "meta": 180,
        "collective": -1,
        "eternal": -1,
    }

    # Abstraction hierarchy for memory type promotion.
    _TYPE_HIERARCHY: dict[str, int] = {
        "sensory": 0,
        "episodic": 1,
        "semantic": 2,
        "procedural": 3,
        "strategic": 4,
        "meta": 5,
        "collective": 6,
        "eternal": 7,
    }

    # Half-life in days for each memory type (used by Ebbinghaus curve).
    _HALF_LIFE_MAP: dict[str, float] = {
        "sensory": 0.5,
        "episodic": 3.0,
        "semantic": 30.0,
        "procedural": 60.0,
        "strategic": 90.0,
        "meta": 120.0,
        "collective": 365.0,
        "eternal": 3650.0,
    }

    # Base confidence for each trace type classification.
    _BASE_CONFIDENCE: dict[str, float] = {
        "sensory": 0.4,
        "episodic": 0.6,
        "semantic": 0.8,
        "procedural": 0.7,
        "strategic": 0.5,
        "meta": 0.6,
        "collective": 0.9,
        "eternal": 0.95,
    }

    # Trace type classifier: trace["type"] -> memory_type.
    _TRACE_CLASSIFIER: dict[str, str] = {
        "observation": "sensory",
        "action": "procedural",
        "result": "episodic",
        "inference": "semantic",
        "reflection": "meta",
        "strategy": "strategic",
        "lesson": "meta",
    }

    def __init__(
        self,
        memory_store: Any,
        novelty_threshold: float = 0.3,
        min_pattern_occurrences: int = 3,
        dedup_similarity_threshold: float = 0.85,
        streaming_mode: bool = False,
    ) -> None:
        """
        Initialize the dream consolidator.

        Args:
            memory_store: Duck-typed store with ``search`` and ``save`` methods.
            novelty_threshold: Minimum novelty score to accept a candidate.
            min_pattern_occurrences: Minimum occurrences to detect a pattern.
            dedup_similarity_threshold: Keyword overlap threshold for dedup.
            streaming_mode: Enable streaming consolidation mode.
        """
        self._store = memory_store
        self._novelty_threshold = novelty_threshold
        self._min_pattern_occurrences = min_pattern_occurrences
        self._dedup_similarity_threshold = dedup_similarity_threshold
        self._streaming_mode = streaming_mode
        self._streaming_buffer: list[dict] = []
        self._streaming_batch_size = 10

    # ------------------------------------------------------------------
    # Phase 1: ORIENT
    # ------------------------------------------------------------------

    def orient(self, session_traces: list[dict]) -> list[ConsolidationCandidate]:
        """
        Phase 1: Scan session traces for novel knowledge signals.

        Classifies each trace as a fact, pattern, skill, or lesson and
        scores its novelty against existing memories in the store.

        **Extraction strategies**:

        * **Facts** — Individual observations, inferences, and results.
        * **Patterns** — Content that appears 3+ times across traces.
        * **Lessons** — Negative outcomes and failure signals.

        Args:
            session_traces: List of trace dicts. Each dict should have keys
                ``content``, ``session_id``, ``timestamp``, ``entities``, and
                ``type`` (observation / inference / action / result / reflection
                / strategy / lesson).

        Returns:
            List of :class:`ConsolidationCandidate` with novelty scores
            above the configured threshold.
        """
        if not session_traces:
            return []

        candidates: list[ConsolidationCandidate] = []

        # --- Individual facts / inferences / actions / observations ---
        for trace in session_traces:
            content = trace.get("content", "")
            if not content:
                continue

            memory_type = self._classify_trace_type(trace)
            fragment = MemoryFragment(
                content=content,
                source_session_id=trace.get("session_id", "unknown"),
                memory_type=memory_type,
                confidence=self._score_initial_confidence(trace, memory_type),
                entities=trace.get("entities", []),
                timestamp=trace.get("timestamp", time.time()),
                ttl_days=self._get_ttl_for_type(memory_type),
            )

            novelty = self._score_novelty(fragment)

            if novelty >= self._novelty_threshold:
                candidates.append(
                    ConsolidationCandidate(
                        fragment=fragment,
                        novelty_score=novelty,
                    )
                )

        # --- Patterns (3+ occurrences) ---
        patterns = self._extract_patterns(session_traces)
        for pattern in patterns:
            novelty = self._score_novelty(pattern)
            if novelty >= self._novelty_threshold:
                candidates.append(
                    ConsolidationCandidate(
                        fragment=pattern,
                        novelty_score=novelty,
                    )
                )

        # --- Lessons from failures ---
        lessons = self._extract_lessons(session_traces)
        for lesson in lessons:
            novelty = self._score_novelty(lesson)
            if novelty >= self._novelty_threshold:
                candidates.append(
                    ConsolidationCandidate(
                        fragment=lesson,
                        novelty_score=novelty,
                    )
                )

        logger.debug(
            "ORIENT: %d traces produced %d candidates",
            len(session_traces),
            len(candidates),
        )
        return candidates

    # ------------------------------------------------------------------
    # Phase 2: GATHER
    # ------------------------------------------------------------------

    def gather(
        self,
        candidates: list[ConsolidationCandidate],
    ) -> list[ConsolidationCandidate]:
        """
        Phase 2: Retrieve related memories for each candidate.

        For each candidate, populates ``related_memories`` and
        ``suggested_merge_targets`` using three retrieval strategies:

        1. **Semantic similarity** — Keyword overlap with existing memories.
        2. **Temporal context** — Memories from a 1-hour window.
        3. **Entity links** — Memories sharing named entities.

        Args:
            candidates: Candidates from the orient phase.

        Returns:
            Enriched candidates with related memories and merge targets.
        """
        enriched: list[ConsolidationCandidate] = []

        for candidate in candidates:
            fragment = candidate.fragment
            related: list[MemoryFragment] = []
            merge_targets: list[str] = []

            # Semantic similarity (keyword overlap).
            # TODO: Replace with vector embedding search.
            semantically_related = self._find_semantically_related(fragment)
            related.extend(semantically_related)

            # Temporal context.
            # TODO: Leverage temporal index from memory store.
            temporally_related = self._find_temporally_related(fragment)
            related.extend(temporally_related)

            # Entity links.
            entity_related = self._find_entity_related(fragment)
            related.extend(entity_related)

            # Deduplicate related list by content.
            related = self._dedup_fragments(related)

            # Identify merge targets (high similarity).
            for mem in related:
                sim = self._keyword_similarity(fragment.content, mem.content)
                if sim >= self._dedup_similarity_threshold:
                    merge_targets.append(mem.content)
                elif sim >= self._dedup_similarity_threshold * 0.8:
                    merge_targets.append(mem.content)

            enriched.append(
                ConsolidationCandidate(
                    fragment=fragment,
                    novelty_score=candidate.novelty_score,
                    related_memories=related,
                    suggested_merge_targets=list(set(merge_targets)),
                )
            )

        return enriched

    # ------------------------------------------------------------------
    # Phase 3: CONSOLIDATE
    # ------------------------------------------------------------------

    def consolidate(
        self,
        candidates: list[ConsolidationCandidate],
    ) -> list[MemoryFragment]:
        """
        Phase 3: ADD-only extraction and enrichment.

        **Never overwrites** existing fragments. Always creates new
        ``MemoryFragment`` objects with ``superseded_by`` links when updating.
        Performs entity resolution, semantic dedup, and principle extraction
        from repeated patterns.

        **Merge logic**:

        * If the candidate is a near-duplicate of an existing memory, the
          new fragment is created with a ``superseded_by`` link pointing to
          the existing content.
        * If the candidate has merge targets, their content is condensed
          into the new fragment (added as supplementary ``[cf. ...]`` notes),
          and the memory type is promoted one level in the abstraction
          hierarchy.
        * Otherwise the fragment is stored as-is with a confidence boost
          proportional to the number of related memories.

        Args:
            candidates: Enriched candidates from the gather phase.

        Returns:
            List of consolidated :class:`MemoryFragment` objects.
        """
        consolidated: list[MemoryFragment] = []

        for candidate in candidates:
            fragment = candidate.fragment

            # Entity resolution (currently identity — no-op).
            resolved_entities = self._resolve_entities(fragment.entities)

            # Semantic dedup with supersede links.
            dedup_result = self._find_dedup_target(candidate)
            boosted_confidence = self._boost_confidence(
                fragment.confidence,
                len(candidate.related_memories),
            )

            if dedup_result["is_duplicate"]:
                # ADD-only: create new fragment with superseded_by link.
                new_version = MemoryFragment(
                    content=fragment.content,
                    source_session_id=fragment.source_session_id,
                    memory_type=fragment.memory_type,
                    confidence=boosted_confidence,
                    entities=resolved_entities,
                    timestamp=fragment.timestamp,
                    ttl_days=fragment.ttl_days,
                    superseded_by=dedup_result["existing_content"],
                )
                consolidated.append(new_version)

            elif candidate.suggested_merge_targets:
                # Merge: promote type and append supplementary notes.
                merged_content = self._merge_contents(
                    fragment.content,
                    candidate.suggested_merge_targets,
                )
                merged_fragment = MemoryFragment(
                    content=merged_content,
                    source_session_id=fragment.source_session_id,
                    memory_type=self._promote_type(fragment.memory_type),
                    confidence=boosted_confidence,
                    entities=resolved_entities,
                    timestamp=fragment.timestamp,
                    ttl_days=self._get_ttl_for_type(
                        self._promote_type(fragment.memory_type),
                    ),
                )
                consolidated.append(merged_fragment)

            else:
                # Fresh fragment — no merge or dedup needed.
                enriched_fragment = MemoryFragment(
                    content=fragment.content,
                    source_session_id=fragment.source_session_id,
                    memory_type=fragment.memory_type,
                    confidence=boosted_confidence,
                    entities=resolved_entities,
                    timestamp=fragment.timestamp,
                    ttl_days=fragment.ttl_days,
                )
                consolidated.append(enriched_fragment)

        # Principle extraction from patterns.
        principles = self._extract_principles(consolidated)
        consolidated.extend(principles)

        return consolidated

    # ------------------------------------------------------------------
    # Phase 4: PRUNE
    # ------------------------------------------------------------------

    def prune(self, fragments: list[MemoryFragment]) -> list[MemoryFragment]:
        """
        Phase 4: Apply forgetting curve and archive stale memories.

        Implements a simplified Ebbinghaus forgetting curve:

        * Strength decays based on days since last access.
        * TTL-based expiration per memory type
          (sensory=1d, episodic=7d, semantic=30d, procedural=90d,
           strategic=goal_completion, meta=180d, collective=forever,
           eternal=forever).
        * Redundancy detection within the batch.
        * Archived fragments are discarded from the active set (the caller
          is responsible for their archival).

        Args:
            fragments: Fragments to evaluate for pruning.

        Returns:
            Surviving (non-archived) fragments.
        """
        if not fragments:
            return []

        now = time.time()
        surviving: list[MemoryFragment] = []

        for fragment in fragments:
            # TTL-based expiration.
            if self._is_expired(fragment, now):
                continue

            # Ebbinghaus strength check.
            curve = self._build_curve(fragment)
            strength = curve.current_strength(now)
            if strength < 0.01:  # Below retrieval threshold.
                continue

            # Redundancy detection within the surviving batch.
            if any(self._is_redundant(fragment, other) for other in surviving):
                continue

            surviving.append(fragment)

        archived_count = len(fragments) - len(surviving)
        if archived_count:
            logger.info(
                "PRUNE: archived %d / %d fragments",
                archived_count,
                len(fragments),
            )

        return surviving

    # ------------------------------------------------------------------
    # Streaming mode
    # ------------------------------------------------------------------

    def ingest_streaming(self, trace: dict) -> list[MemoryFragment]:
        """
        Ingest a single trace in streaming mode.

        Buffers traces and runs incremental consolidation when batch size
        is reached. Designed for real-time memory ingestion during active
        sessions.

        Args:
            trace: Single trace dict with keys ``content``, ``session_id``,
                ``timestamp``, ``entities``, and ``type``.

        Returns:
            List of consolidated memory fragments (empty if batch not ready).
        """
        if not self._streaming_mode:
            raise RuntimeError("Streaming mode not enabled")

        self._streaming_buffer.append(trace)

        # Run consolidation when batch size reached
        if len(self._streaming_buffer) >= self._streaming_batch_size:
            return self._process_streaming_batch()

        return []

    def _process_streaming_batch(self) -> list[MemoryFragment]:
        """
        Process buffered traces in streaming mode.

        Runs a lightweight consolidation cycle on the buffered traces:
        - ORIENT phase only (no GATHER to avoid expensive searches)
        - Direct consolidation without merge (ADD-only)
        - No pruning (deferred to batch consolidation)

        Returns:
            List of consolidated memory fragments.
        """
        if not self._streaming_buffer:
            return []

        # ORIENT: Extract candidates from buffer
        candidates = self.orient(self._streaming_buffer)

        # Lightweight consolidation: skip GATHER and PRUNE
        consolidated: list[MemoryFragment] = []
        for candidate in candidates:
            fragment = candidate.fragment

            # Simple confidence boost based on novelty
            boosted_confidence = min(1.0, fragment.confidence * (1.0 + candidate.novelty_score * 0.2))

            enriched_fragment = MemoryFragment(
                content=fragment.content,
                source_session_id=fragment.source_session_id,
                memory_type=fragment.memory_type,
                confidence=boosted_confidence,
                entities=fragment.entities,
                timestamp=fragment.timestamp,
                ttl_days=fragment.ttl_days,
            )
            consolidated.append(enriched_fragment)

        # Clear buffer
        self._streaming_buffer.clear()

        # Save to store
        for fragment in consolidated:
            try:
                self._store.save(fragment)
            except Exception:
                # Silently skip failed saves in streaming mode
                pass

        logger.debug(
            "Streaming consolidation: %d traces -> %d fragments",
            len(candidates),
            len(consolidated),
        )

        return consolidated

    def flush_streaming(self) -> list[MemoryFragment]:
        """
        Flush remaining buffered traces in streaming mode.

        Processes any traces remaining in the buffer, regardless of batch size.

        Returns:
            List of consolidated memory fragments.
        """
        if not self._streaming_mode:
            raise RuntimeError("Streaming mode not enabled")

        return self._process_streaming_batch()

    def set_streaming_batch_size(self, size: int) -> None:
        """
        Set the batch size for streaming consolidation.

        Args:
            size: Number of traces to buffer before consolidation.
        """
        if size <= 0:
            raise ValueError("Batch size must be positive")
        self._streaming_batch_size = size

    @property
    def streaming_buffer_size(self) -> int:
        """Current number of traces in streaming buffer."""
        return len(self._streaming_buffer)

    # ------------------------------------------------------------------
    # Full cycle
    # ------------------------------------------------------------------

    def run_full_cycle(
        self,
        session_traces: list[dict],
    ) -> list[MemoryFragment]:
        """
        Run all 4 phases of the dream consolidation cycle sequentially.

        Orchestrates ORIENT -> GATHER -> CONSOLIDATE -> PRUNE and logs
        phase-level statistics via the standard logger. If no candidates
        survive orientation, the remaining phases are skipped.

        Args:
            session_traces: List of session trace dicts (see :meth:`orient`).

        Returns:
            List of consolidated :class:`MemoryFragment` objects that
            survived the full pipeline.
        """
        stats: list[ConsolidationStats] = []

        # --- Phase 1: ORIENT ---
        t0 = time.perf_counter()
        candidates = self.orient(session_traces)
        stats.append(
            ConsolidationStats(
                phase=DreamPhase.ORIENT,
                candidates_found=len(candidates),
                duration_ms=(time.perf_counter() - t0) * 1000,
            )
        )
        logger.info(
            "ORIENT: found %d candidates in %.1f ms",
            len(candidates),
            stats[-1].duration_ms,
        )

        if not candidates:
            logger.info("No candidates found — skipping remaining phases")
            return []

        # --- Phase 2: GATHER ---
        t0 = time.perf_counter()
        enriched = self.gather(candidates)
        stats.append(
            ConsolidationStats(
                phase=DreamPhase.GATHER,
                candidates_found=len(enriched),
                memories_added=sum(len(c.related_memories) for c in enriched),
                duration_ms=(time.perf_counter() - t0) * 1000,
            )
        )
        logger.info(
            "GATHER: enriched %d candidates with %d related memories in %.1f ms",
            len(enriched),
            stats[-1].memories_added,
            stats[-1].duration_ms,
        )

        # --- Phase 3: CONSOLIDATE ---
        merge_count = sum(1 for c in enriched if c.suggested_merge_targets)
        t0 = time.perf_counter()
        consolidated = self.consolidate(enriched)
        stats.append(
            ConsolidationStats(
                phase=DreamPhase.CONSOLIDATE,
                candidates_found=len(enriched),
                memories_added=len(consolidated),
                memories_merged=merge_count,
                duration_ms=(time.perf_counter() - t0) * 1000,
            )
        )
        logger.info(
            "CONSOLIDATE: created %d fragments (merged %d) in %.1f ms",
            len(consolidated),
            merge_count,
            stats[-1].duration_ms,
        )

        if not consolidated:
            return []

        # --- Phase 4: PRUNE ---
        t0 = time.perf_counter()
        surviving = self.prune(consolidated)
        pruned = len(consolidated) - len(surviving)
        stats.append(
            ConsolidationStats(
                phase=DreamPhase.PRUNE,
                candidates_found=len(consolidated),
                memories_pruned=pruned,
                memories_archived=pruned,
                duration_ms=(time.perf_counter() - t0) * 1000,
            )
        )
        logger.info(
            "PRUNE: archived %d / %d fragments in %.1f ms",
            pruned,
            len(consolidated),
            stats[-1].duration_ms,
        )

        # Summary.
        total_ms = sum(s.duration_ms for s in stats)
        logger.info(
            "Dream cycle complete: %d traces -> %d surviving fragments "
            "in %.1f ms",
            len(session_traces),
            len(surviving),
            total_ms,
        )

        return surviving

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _classify_trace_type(self, trace: dict) -> str:
        """Map a trace's ``type`` field to a memory type string."""
        trace_type = trace.get("type", "observation")
        return self._TRACE_CLASSIFIER.get(trace_type, "episodic")

    def _score_initial_confidence(self, trace: dict, memory_type: str) -> float:
        """
        Score initial confidence for a trace.

        Combines the trace's own confidence signal with the base confidence
        for the classified memory type.
        """
        base = trace.get("confidence", 0.7)
        type_base = self._BASE_CONFIDENCE.get(memory_type, 0.7)
        return min(1.0, base * type_base)

    def _get_ttl_for_type(self, memory_type: str) -> int:
        """Return the default TTL (days) for a memory type."""
        return self._MEMORY_TTL_MAP.get(memory_type, 30)

    def _score_novelty(self, fragment: MemoryFragment) -> float:
        """
        Score how novel a fragment is relative to the existing store.

        Uses keyword overlap against the top-5 search results from the
        memory store.  Returns 1.0 if the store is unavailable or empty.
        """
        try:
            existing = self._store.search(fragment.content, limit=5)
        except Exception:
            return 1.0

        if not existing:
            return 1.0

        max_similarity = max(
            self._keyword_similarity(fragment.content, mem.content)
            for mem in existing
        )
        return 1.0 - max_similarity

    def _keyword_similarity(self, text_a: str, text_b: str) -> float:
        """Jaccard similarity over lower-cased word tokens."""
        words_a = set(text_a.lower().split())
        words_b = set(text_b.lower().split())

        if not words_a or not words_b:
            return 0.0

        intersection = words_a & words_b
        union = words_a | words_b
        return len(intersection) / len(union) if union else 0.0

    # --- Pattern extraction ---

    def _extract_patterns(self, traces: list[dict]) -> list[MemoryFragment]:
        """
        Extract patterns from session traces (3+ occurrences).

        Groups traces by co-occurring entities and looks for shared
        significant words across the group.
        """
        # Group by first entity.
        entity_groups: dict[str, list[dict]] = {}
        for trace in traces:
            entities = trace.get("entities", [])
            if entities:
                key = entities[0]
                entity_groups.setdefault(key, []).append(trace)

        patterns: list[MemoryFragment] = []
        for entity, group in entity_groups.items():
            if len(group) < self._min_pattern_occurrences:
                continue

            common_phrases = self._find_common_phrases(group)
            if common_phrases:
                content = (
                    f"Pattern: {', '.join(common_phrases[:3])} "
                    f"(observed {len(group)} times)"
                )
                all_entities: list[str] = []
                for t in group:
                    all_entities.extend(t.get("entities", []))
                # Keep the group entity first, then unique rest.
                rest = [e for e in all_entities if e != entity]
                deduped_entities = [entity] + list(dict.fromkeys(rest))

                patterns.append(
                    MemoryFragment(
                        content=content,
                        source_session_id=group[0].get("session_id", "unknown"),
                        memory_type="semantic",
                        confidence=min(1.0, len(group) / 10.0),
                        entities=deduped_entities,
                        timestamp=time.time(),
                        ttl_days=30,
                    )
                )

        return patterns

    def _find_common_phrases(self, traces: list[dict]) -> list[str]:
        """
        Find significant words that appear in the majority of traces.

        Returns the top 5 non-stopword tokens.
        """
        if not traces:
            return []

        word_sets: list[set[str]] = []
        for trace in traces:
            content = trace.get("content", "")
            word_sets.append(set(content.lower().split()))

        if not word_sets:
            return []

        threshold = max(2, len(traces) // 2)
        common: set[str] = set()
        for word in word_sets[0]:
            count = sum(1 for ws in word_sets if word in ws)
            if count >= threshold:
                common.add(word)

        stopwords = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at",
            "to", "for", "of", "with", "by", "from", "as", "is", "was",
            "it", "its", "this", "that", "are", "were", "be", "been",
            "we", "they", "not", "no", "all", "each", "has", "had",
        }
        significant = [w for w in common if w not in stopwords]
        return significant[:5]

    # --- Lesson extraction ---

    def _extract_lessons(self, traces: list[dict]) -> list[MemoryFragment]:
        """
        Extract lessons from negative outcomes and failures.

        Looks for traces whose type is ``result`` and whose content
        contains failure-signalling keywords.
        """
        failure_keywords = {
            "fail", "error", "incorrect", "wrong", "bad result",
            "unexpected", "negative", "unsuccessful", "failed",
        }

        lessons: list[MemoryFragment] = []
        for trace in traces:
            content = trace.get("content", "")
            trace_type = trace.get("type", "")

            if trace_type == "result" and any(
                kw in content.lower() for kw in failure_keywords
            ):
                lessons.append(
                    MemoryFragment(
                        content=f"Lesson: {content}",
                        source_session_id=trace.get("session_id", "unknown"),
                        memory_type="meta",
                        confidence=0.8,
                        entities=trace.get("entities", []),
                        timestamp=trace.get("timestamp", time.time()),
                        ttl_days=180,
                    )
                )

        return lessons

    # --- Retrieval helpers ---

    def _find_semantically_related(
        self,
        fragment: MemoryFragment,
    ) -> list[MemoryFragment]:
        """
        Find semantically related memories via keyword overlap.

        TODO: Replace with vector embedding search when available.
        """
        try:
            results = self._store.search(fragment.content, limit=10)
        except Exception:
            return []

        return [
            mem
            for mem in results
            if self._keyword_similarity(fragment.content, mem.content) >= 0.3
        ]

    def _find_temporally_related(
        self,
        fragment: MemoryFragment,
    ) -> list[MemoryFragment]:
        """
        Find memories with timestamps within 1 hour of the given fragment.

        TODO: Leverage temporal index from memory store when available.
        """
        try:
            results = self._store.search(fragment.content, limit=20)
        except Exception:
            return []

        window = 3600.0  # 1 hour in seconds.
        return [
            mem
            for mem in results
            if abs(mem.timestamp - fragment.timestamp) <= window
        ]

    def _find_entity_related(
        self,
        fragment: MemoryFragment,
    ) -> list[MemoryFragment]:
        """
        Find memories that share at least one entity with the fragment.
        """
        if not fragment.entities:
            return []

        entity_set = set(fragment.entities)
        related: list[MemoryFragment] = []

        for entity in entity_set:
            try:
                results = self._store.search(entity, limit=5)
            except Exception:
                continue

            for mem in results:
                if set(mem.entities) & entity_set:
                    related.append(mem)

        return related

    def _dedup_fragments(
        self,
        fragments: list[MemoryFragment],
    ) -> list[MemoryFragment]:
        """Remove duplicates from a list by memory content."""
        seen: set[str] = set()
        unique: list[MemoryFragment] = []
        for fragment in fragments:
            if fragment.content not in seen:
                seen.add(fragment.content)
                unique.append(fragment)
        return unique

    # --- Resolve and dedup ---

    def _resolve_entities(self, entities: list[str]) -> list[str]:
        """
        Resolve entity aliases to canonical forms.

        TODO: Implement proper entity resolution using a knowledge base.
        Currently returns a deduplicated pass-through list.
        """
        return list(dict.fromkeys(entities))  # Ordered dedup.

    def _find_dedup_target(self, candidate: ConsolidationCandidate) -> dict:
        """
        Check if the candidate is a duplicate of an existing memory.

        Returns:
            dict with keys ``is_duplicate`` (bool) and
            ``existing_content`` (str | None).
        """
        fragment = candidate.fragment
        for related in candidate.related_memories:
            sim = self._keyword_similarity(fragment.content, related.content)
            if sim >= self._dedup_similarity_threshold:
                return {
                    "is_duplicate": True,
                    "existing_content": related.content,
                }
        return {"is_duplicate": False, "existing_content": None}

    def _boost_confidence(self, base: float, related_count: int) -> float:
        """
        Boost confidence based on the number of related memories found.

        Each related memory adds 0.03 to confidence, capped at +0.15.
        """
        boost = min(0.15, related_count * 0.03)
        return min(1.0, base + boost)

    def _merge_contents(
        self,
        primary: str,
        merge_targets: list[str],
    ) -> str:
        """
        Merge primary content with supplementary notes from merge targets.

        Only adds up to 2 supplementary items that introduce new keywords
        not already present in the primary content.
        """
        if not merge_targets:
            return primary

        primary_words = set(primary.lower().split())
        supplements: list[str] = []

        for target in dict.fromkeys(merge_targets):  # Ordered dedup.
            target_words = set(target.lower().split())
            if target_words - primary_words:
                supplements.append(target)
                if len(supplements) >= 2:
                    break

        if not supplements:
            return primary

        merged = primary
        for supp in supplements:
            merged += f" [cf. {supp[:200]}]"
        return merged

    def _promote_type(self, current_type: str) -> str:
        """
        Promote a memory type one level in the abstraction hierarchy.

        Example: ``episodic`` -> ``semantic``.
        """
        level = self._TYPE_HIERARCHY.get(current_type, 1)
        target_level = level + 1
        for mem_type, lvl in self._TYPE_HIERARCHY.items():
            if lvl == target_level:
                return mem_type
        return current_type  # Already at the top.

    # --- Principle extraction ---

    def _extract_principles(
        self,
        fragments: list[MemoryFragment],
    ) -> list[MemoryFragment]:
        """
        Extract high-level principles from repeated patterns.

        Looks for 3+ procedural fragments and promotes them to a strategic
        principle, and 2+ meta fragments promoted to an eternal principle.
        """
        principles: list[MemoryFragment] = []

        type_groups: dict[str, list[MemoryFragment]] = {}
        for frag in fragments:
            type_groups.setdefault(frag.memory_type, []).append(frag)

        # Procedural -> Strategic principle.
        procedural_frags = type_groups.get("procedural", [])
        if len(procedural_frags) >= self._min_pattern_occurrences:
            combined = "Principle: " + "; ".join(
                f.content[:150] for f in procedural_frags[:5]
            )
            avg_confidence = (
                sum(f.confidence for f in procedural_frags)
                / len(procedural_frags)
            )
            all_entities: list[str] = []
            for f in procedural_frags:
                all_entities.extend(f.entities)

            principles.append(
                MemoryFragment(
                    content=combined[:500],
                    source_session_id=procedural_frags[0].source_session_id,
                    memory_type="strategic",
                    confidence=min(1.0, avg_confidence * 1.1),
                    entities=list(dict.fromkeys(all_entities)),
                    timestamp=time.time(),
                    ttl_days=-1,
                )
            )

        # Meta -> Eternal principle.
        meta_frags = type_groups.get("meta", [])
        if len(meta_frags) >= 2:
            combined = "Eternal Principle: " + "; ".join(
                f.content[:200] for f in meta_frags[:3]
            )
            avg_conf = (
                sum(f.confidence for f in meta_frags) / len(meta_frags)
            )
            all_entities = [e for f in meta_frags for e in f.entities]

            principles.append(
                MemoryFragment(
                    content=combined[:500],
                    source_session_id=meta_frags[0].source_session_id,
                    memory_type="eternal",
                    confidence=min(1.0, avg_conf * 1.2),
                    entities=list(dict.fromkeys(all_entities)),
                    timestamp=time.time(),
                    ttl_days=-1,
                )
            )

        return principles

    # --- Pruning helpers ---

    def _is_expired(self, fragment: MemoryFragment, now: float) -> bool:
        """
        Check if a fragment has exceeded its TTL.

        A TTL of -1 means the fragment never expires.
        """
        if fragment.ttl_days == -1:
            return False
        age_days = (now - fragment.timestamp) / 86400.0
        return age_days > fragment.ttl_days

    def _build_curve(self, fragment: MemoryFragment) -> EbbinghausCurve:
        """
        Build an Ebbinghaus forgetting curve for a fragment.

        Half-life is determined by memory type and amplified by access
        count (each prior access adds 20% to the half-life).
        """
        half_life = self._HALF_LIFE_MAP.get(fragment.memory_type, 7.0)

        if fragment.access_count > 0:
            half_life *= 1.0 + (fragment.access_count * 0.2)

        last_access = (
            fragment.last_accessed
            if fragment.last_accessed is not None
            else fragment.timestamp
        )

        return EbbinghausCurve(
            strength=fragment.confidence,
            half_life_days=half_life,
            last_reinforcement=last_access,
        )

    def _is_redundant(
        self,
        fragment: MemoryFragment,
        existing: MemoryFragment,
    ) -> bool:
        """
        Check if a fragment is redundant with an already-surviving fragment.

        Returns ``True`` when both fragments share the same type, have
        high content similarity (>= 0.8), and the new fragment does not
        have strictly higher confidence.
        """
        if fragment.memory_type != existing.memory_type:
            return False

        sim = self._keyword_similarity(fragment.content, existing.content)
        return sim >= 0.8 and fragment.confidence <= existing.confidence


__all__ = [
    "MemorySignal",
    "DreamPhase",
    "MemoryFragment",
    "ConsolidationCandidate",
    "EbbinghausCurve",
    "ConsolidationStats",
    "DreamConsolidator",
]
