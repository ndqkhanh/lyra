"""CraniMem Bio-Gating — P2-B4 (HIGH, MED).

Bio-inspired memory gating with three mechanisms:
1. Synaptic consolidation — tag importance, consolidate important memories
2. Hippocampal replay — replay memories to strengthen retention
3. Prefrontal gating — decide what to retain vs discard

See: plan-phase2-memory.md §4.4, CraniMem paper (OpenReview: iGRGjdhl9r)
"""
from __future__ import annotations

import enum
import math
import time
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Memory Signal
# ---------------------------------------------------------------------------


class SignalStrength(str, enum.Enum):
    """Strength of a memory consolidation signal."""

    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    CRITICAL = "critical"


class GateDecision(str, enum.Enum):
    """Decision from the prefrontal gate."""

    RETAIN = "retain"       # Keep in active memory
    CONSOLIDATE = "consolidate"  # Move to long-term storage
    DISCARD = "discard"     # Remove from memory
    REPLAY = "replay"       # Schedule for hippocampal replay


# ---------------------------------------------------------------------------
# Memory Trace
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MemoryTrace:
    """A single memory trace with bio-inspired metadata."""

    trace_id: str
    content_hash: str  # hash of the memory content
    created_at: float
    last_accessed: float
    access_count: int = 0
    importance_score: float = 0.0  # 0.0–1.0 synaptic importance
    consolidation_count: int = 0   # times consolidated
    replay_count: int = 0          # times replayed
    surprise_score: float = 0.0    # novelty/surprise (0.0–1.0)
    emotional_salience: float = 0.0  # emotional weight (0.0–1.0)
    tags: frozenset[str] = frozenset()
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Synaptic Consolidation
# ---------------------------------------------------------------------------


@dataclass
class SynapticConsolidator:
    """Tags memory importance using Hebbian-like strengthening.

    Importance increases with:
    - Access frequency (use-dependent strengthening)
    - Recency (recent memories are more important, tempered by decay)
    - Surprise/novelty (prediction error drives learning)
    - Emotional salience (emotionally tagged memories are prioritized)

    Configurable weights for each factor.
    """

    access_weight: float = 0.35
    recency_weight: float = 0.25
    surprise_weight: float = 0.25
    emotion_weight: float = 0.15

    # Decay half-life in seconds (default: 1 hour)
    decay_half_life: float = 3600.0

    # Consolidation threshold
    consolidation_threshold: float = 0.6
    discard_threshold: float = 0.2

    def compute_importance(self, trace: MemoryTrace) -> float:
        """Compute synaptic importance score (0.0–1.0)."""
        now = time.time()

        # Access frequency (normalized by age)
        age = max(now - trace.created_at, 1.0)
        freq = min(trace.access_count / max(age / 60.0, 1.0), 1.0)  # per minute

        # Recency (exponential decay)
        time_since_access = max(now - trace.last_accessed, 0.0)
        recency = math.exp(-math.log(2) * time_since_access / self.decay_half_life)

        # Surprise
        surprise = trace.surprise_score

        # Emotional salience
        emotion = trace.emotional_salience

        score = (
            self.access_weight * freq
            + self.recency_weight * recency
            + self.surprise_weight * surprise
            + self.emotion_weight * emotion
        )
        return min(max(score, 0.0), 1.0)

    def classify(self, trace: MemoryTrace) -> SignalStrength:
        """Classify a memory trace by its importance signal."""
        score = self.compute_importance(trace)
        if score >= 0.8:
            return SignalStrength.CRITICAL
        if score >= self.consolidation_threshold:
            return SignalStrength.STRONG
        if score >= 0.4:
            return SignalStrength.MODERATE
        return SignalStrength.WEAK

    def should_consolidate(self, trace: MemoryTrace) -> bool:
        """Check if a trace should be consolidated to long-term memory."""
        return self.compute_importance(trace) >= self.consolidation_threshold

    def should_discard(self, trace: MemoryTrace) -> bool:
        """Check if a trace should be discarded."""
        return self.compute_importance(trace) <= self.discard_threshold

    def strengthen(self, trace: MemoryTrace, boost: float = 0.1) -> float:
        """Simulate synaptic strengthening after replay/access.

        Returns the new importance score.
        """
        current = self.compute_importance(trace)
        # Bounded increase with diminishing returns
        strengthened = current + boost * (1.0 - current)
        return min(strengthened, 1.0)


# ---------------------------------------------------------------------------
# Hippocampal Replay
# ---------------------------------------------------------------------------


@dataclass
class HippocampalReplay:
    """Simulates hippocampal replay for memory strengthening.

    Replay is triggered periodically or on-demand. During replay,
    high-importance memories are "replayed" to strengthen their
    synaptic weights. This prevents forgetting of important traces.
    """

    replay_interval_seconds: float = 300.0  # 5 min between replays
    max_replays_per_cycle: int = 10
    replay_strengthening_boost: float = 0.05

    _last_replay_time: float = field(default=0.0, init=False)
    _total_replays: int = field(default=0, init=False)

    def time_for_replay(self) -> bool:
        """Check if enough time has passed for another replay cycle."""
        return (time.time() - self._last_replay_time) >= self.replay_interval_seconds

    def select_for_replay(
        self,
        traces: list[MemoryTrace],
        consolidator: SynapticConsolidator,
    ) -> list[MemoryTrace]:
        """Select memories for hippocampal replay.

        Prioritizes:
        1. Critical/strong memories not yet replayed
        2. Recently accessed memories
        3. High-surprise memories
        """
        candidates = [
            t for t in traces
            if consolidator.classify(t) in (SignalStrength.CRITICAL, SignalStrength.STRONG)
        ]

        # Sort by importance (descending), then by time since last replay (descending)
        candidates.sort(
            key=lambda t: (
                -consolidator.compute_importance(t),
                -(time.time() - t.last_accessed),
            )
        )

        return candidates[:self.max_replays_per_cycle]

    def replay(
        self,
        traces: list[MemoryTrace],
        consolidator: SynapticConsolidator,
    ) -> dict[str, float]:
        """Run a hippocampal replay cycle.

        Returns {trace_id: new_importance_score} for replayed traces.
        """
        self._last_replay_time = time.time()
        self._total_replays += 1

        selected = self.select_for_replay(traces, consolidator)
        results: dict[str, float] = {}

        for trace in selected:
            new_score = consolidator.strengthen(trace, self.replay_strengthening_boost)
            results[trace.trace_id] = new_score

        return results

    @property
    def total_replays(self) -> int:
        return self._total_replays


# ---------------------------------------------------------------------------
# Prefrontal Gate
# ---------------------------------------------------------------------------


@dataclass
class PrefrontalGate:
    """Executive-function gate: decides retain / consolidate / discard / replay.

    Simulates the prefrontal cortex's role in memory management:
    - Working memory capacity limit (default: 7±2 items)
    - Task relevance scoring
    - Interference detection (similar memories compete)
    - Forgetting curve integration
    """

    working_memory_capacity: int = 7
    interference_threshold: float = 0.7  # cosine similarity threshold for interference

    def decide(
        self,
        trace: MemoryTrace,
        consolidator: SynapticConsolidator,
        *,
        working_memory_count: int = 0,
        task_tags: frozenset[str] | None = None,
    ) -> GateDecision:
        """Make a retention decision for a memory trace.

        Decision logic:
        1. CRITICAL importance → RETAIN
        2. STRONG importance + task-relevant → RETAIN
        3. STRONG importance + not task-relevant → CONSOLIDATE
        4. MODERATE + task-relevant → REPLAY (strengthen before deciding)
        5. MODERATE + not task-relevant → CONSOLIDATE (archive)
        6. WEAK → DISCARD
        """
        strength = consolidator.classify(trace)
        task_relevant = self._is_task_relevant(trace, task_tags)

        if strength == SignalStrength.CRITICAL:
            return GateDecision.RETAIN

        if strength == SignalStrength.STRONG:
            if task_relevant and working_memory_count < self.working_memory_capacity:
                return GateDecision.RETAIN
            return GateDecision.CONSOLIDATE

        if strength == SignalStrength.MODERATE:
            if task_relevant:
                return GateDecision.REPLAY
            return GateDecision.CONSOLIDATE

        return GateDecision.DISCARD

    def filter_working_memory(
        self,
        traces: list[MemoryTrace],
        consolidator: SynapticConsolidator,
        *,
        task_tags: frozenset[str] | None = None,
    ) -> tuple[list[MemoryTrace], list[MemoryTrace]]:
        """Partition traces into keep (working memory) and evict.

        Returns (keep_list, evict_list).
        """
        # Classify and sort by importance
        scored = [(t, consolidator.compute_importance(t)) for t in traces]
        scored.sort(key=lambda x: -x[1])

        keep: list[MemoryTrace] = []
        evict: list[MemoryTrace] = []

        for trace, score in scored:
            decision = self.decide(
                trace,
                consolidator,
                working_memory_count=len(keep),
                task_tags=task_tags,
            )
            if decision == GateDecision.RETAIN and len(keep) < self.working_memory_capacity:
                keep.append(trace)
            elif decision == GateDecision.DISCARD:
                evict.append(trace)
            else:
                # CONSOLIDATE/REPLAY — keep for now if space allows
                if len(keep) < self.working_memory_capacity:
                    keep.append(trace)
                else:
                    evict.append(trace)

        return keep, evict

    def detect_interference(
        self,
        trace: MemoryTrace,
        existing: list[MemoryTrace],
    ) -> list[MemoryTrace]:
        """Detect memories that interfere with the given trace.

        Two traces interfere if they share significant tag overlap and
        have similar content (approximated by tag Jaccard similarity).
        """
        interfering: list[MemoryTrace] = []
        trace_tags = set(trace.tags)
        if not trace_tags:
            return interfering

        for existing_trace in existing:
            if existing_trace.trace_id == trace.trace_id:
                continue
            existing_tags = set(existing_trace.tags)
            if not existing_tags:
                continue

            intersection = trace_tags & existing_tags
            union = trace_tags | existing_tags
            similarity = len(intersection) / len(union) if union else 0.0

            if similarity >= self.interference_threshold:
                interfering.append(existing_trace)

        return interfering

    @staticmethod
    def _is_task_relevant(trace: MemoryTrace, task_tags: frozenset[str] | None) -> bool:
        """Check if a trace is relevant to the current task."""
        if task_tags is None:
            return True
        if not task_tags:
            return False
        return bool(set(trace.tags) & task_tags)


# ---------------------------------------------------------------------------
# CraniMem Bio-Gating Pipeline
# ---------------------------------------------------------------------------


@dataclass
class CraniMemGate:
    """Complete bio-gating pipeline combining all three mechanisms.

    Usage::

        gate = CraniMemGate()
        gate.ingest(trace)
        gate.consolidate()    # synaptic strengthening
        gate.replay()         # hippocampal replay cycle
        keep, evict = gate.filter_working_memory()
    """

    consolidator: SynapticConsolidator = field(default_factory=SynapticConsolidator)
    replay_system: HippocampalReplay = field(default_factory=HippocampalReplay)
    prefrontal: PrefrontalGate = field(default_factory=PrefrontalGate)

    _traces: dict[str, MemoryTrace] = field(default_factory=dict)
    _consolidated: dict[str, MemoryTrace] = field(default_factory=dict)
    _discarded: list[str] = field(default_factory=list)
    _task_tags: frozenset[str] = frozenset()

    def ingest(self, trace: MemoryTrace) -> None:
        """Accept a new memory trace into the system."""
        self._traces[trace.trace_id] = trace

    def access(self, trace_id: str) -> MemoryTrace | None:
        """Record an access to a memory trace."""
        trace = self._traces.get(trace_id)
        if trace is None:
            return None
        # Update access metadata (trace is frozen, so we create a new one)
        updated = MemoryTrace(
            trace_id=trace.trace_id,
            content_hash=trace.content_hash,
            created_at=trace.created_at,
            last_accessed=time.time(),
            access_count=trace.access_count + 1,
            importance_score=trace.importance_score,
            consolidation_count=trace.consolidation_count,
            replay_count=trace.replay_count,
            surprise_score=trace.surprise_score,
            emotional_salience=trace.emotional_salience,
            tags=trace.tags,
            metadata=trace.metadata,
        )
        self._traces[trace_id] = updated
        return updated

    def consolidate(self) -> int:
        """Run synaptic consolidation: classify and move strong traces to long-term.

        Returns the number of traces consolidated.
        """
        count = 0
        to_move: list[str] = []

        for tid, trace in self._traces.items():
            strength = self.consolidator.classify(trace)
            if strength in (SignalStrength.CRITICAL, SignalStrength.STRONG):
                # Consolidate: create with incremented count
                consolidated = MemoryTrace(
                    trace_id=trace.trace_id,
                    content_hash=trace.content_hash,
                    created_at=trace.created_at,
                    last_accessed=trace.last_accessed,
                    access_count=trace.access_count,
                    importance_score=self.consolidator.compute_importance(trace),
                    consolidation_count=trace.consolidation_count + 1,
                    replay_count=trace.replay_count,
                    surprise_score=trace.surprise_score,
                    emotional_salience=trace.emotional_salience,
                    tags=trace.tags,
                    metadata=trace.metadata,
                )
                self._consolidated[tid] = consolidated
                to_move.append(tid)
                count += 1

        # Remove consolidated from active traces
        for tid in to_move:
            del self._traces[tid]

        return count

    def replay(self) -> dict[str, float]:
        """Run hippocampal replay on active traces."""
        if not self.replay_system.time_for_replay():
            return {}

        traces = list(self._traces.values())
        return self.replay_system.replay(traces, self.consolidator)

    def filter_working_memory(
        self,
        task_tags: frozenset[str] | None = None,
    ) -> tuple[list[MemoryTrace], list[MemoryTrace]]:
        """Filter active traces through the prefrontal gate.

        Returns (keep_list, evict_list).
        """
        traces = list(self._traces.values())
        tags = task_tags if task_tags is not None else self._task_tags
        keep, evict = self.prefrontal.filter_working_memory(
            traces, self.consolidator, task_tags=tags,
        )

        # Record discarded
        for t in evict:
            self._discarded.append(t.trace_id)

        return keep, evict

    def set_task_tags(self, tags: set[str]) -> None:
        """Set the current task tags for relevance filtering."""
        self._task_tags = frozenset(tags)

    def get_trace(self, trace_id: str) -> MemoryTrace | None:
        """Get a trace from active or consolidated storage."""
        return self._traces.get(trace_id) or self._consolidated.get(trace_id)

    @property
    def active_count(self) -> int:
        return len(self._traces)

    @property
    def consolidated_count(self) -> int:
        return len(self._consolidated)

    @property
    def discarded_count(self) -> int:
        return len(self._discarded)

    def stats(self) -> dict[str, Any]:
        all_traces = {**self._consolidated, **self._traces}
        strengths = [self.consolidator.classify(t) for t in all_traces.values()]
        return {
            "active_count": self.active_count,
            "consolidated_count": self.consolidated_count,
            "discarded_count": self.discarded_count,
            "total_traces": self.active_count + self.consolidated_count,
            "critical_count": strengths.count(SignalStrength.CRITICAL),
            "strong_count": strengths.count(SignalStrength.STRONG),
            "moderate_count": strengths.count(SignalStrength.MODERATE),
            "weak_count": strengths.count(SignalStrength.WEAK),
            "total_replays": self.replay_system.total_replays,
            "working_memory_capacity": self.prefrontal.working_memory_capacity,
        }

    def clear(self) -> None:
        """Reset all state."""
        self._traces.clear()
        self._consolidated.clear()
        self._discarded.clear()
        self._task_tags = frozenset()


__all__ = [
    "CraniMemGate",
    "GateDecision",
    "HippocampalReplay",
    "MemoryTrace",
    "PrefrontalGate",
    "SignalStrength",
    "SynapticConsolidator",
]
