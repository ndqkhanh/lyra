"""Dual-trace encoding — fact + scene traces for +20.2pp recall.

Encodes each memory event along two parallel traces:
- Fact trace: objective data (what happened)
- Scene trace: contextual metadata (when, where, why)

This dual encoding enables higher recall by allowing retrieval
along either dimension.
"""

from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass(frozen=True)
class FactTrace:
    """Objective fact encoding of an event.

    Attributes:
        trace_id: Unique trace identifier.
        subject: The subject of the fact.
        predicate: Relationship or action.
        object: Target or result.
        confidence: Certainty 0.0–1.0.
        timestamp: Unix timestamp.
    """

    trace_id: str
    subject: str
    predicate: str
    object: str
    confidence: float
    timestamp: float


@dataclass(frozen=True)
class SceneTrace:
    """Contextual scene encoding of an event.

    Attributes:
        trace_id: Unique trace identifier (links to FactTrace).
        environment: Where the event occurred (session, tool, agent).
        context: Surrounding context description.
        emotional_valence: -1.0 (negative) to 1.0 (positive).
        importance: How critical the event was 0.0–1.0.
        timestamp: Unix timestamp.
    """

    trace_id: str
    environment: str
    context: str
    emotional_valence: float
    importance: float
    timestamp: float


class DualTraceEncoder:
    """Encodes events along fact and scene traces for dual-path retrieval.

    The fact trace captures objective subject-predicate-object triples.
    The scene trace captures contextual metadata (environment, context).
    """

    def __init__(self) -> None:
        self._fact_traces: dict[str, FactTrace] = {}
        self._scene_traces: dict[str, SceneTrace] = {}
        self._counter = 0

    async def encode(
        self,
        subject: str,
        predicate: str,
        obj: str,
        environment: str = "default",
        context: str = "",
        confidence: float = 1.0,
        importance: float = 0.5,
        emotional_valence: float = 0.0,
    ) -> str:
        """Encode an event along both traces.

        Args:
            subject: Subject of the fact.
            predicate: Relationship or action.
            obj: Target or result.
            environment: Where it happened.
            context: Surrounding context.
            confidence: Fact certainty.
            importance: Scene importance.
            emotional_valence: Scene emotional tone.

        Returns:
            The shared trace_id.
        """
        self._counter += 1
        trace_id = f"trace-{self._counter}"
        now = time.time()

        fact = FactTrace(
            trace_id=trace_id,
            subject=subject,
            predicate=predicate,
            object=obj,
            confidence=min(max(confidence, 0.0), 1.0),
            timestamp=now,
        )
        scene = SceneTrace(
            trace_id=trace_id,
            environment=environment,
            context=context,
            emotional_valence=min(max(emotional_valence, -1.0), 1.0),
            importance=min(max(importance, 0.0), 1.0),
            timestamp=now,
        )

        self._fact_traces[trace_id] = fact
        self._scene_traces[trace_id] = scene
        return trace_id

    async def search_by_fact(
        self, subject: str | None = None, predicate: str | None = None
    ) -> tuple[FactTrace, ...]:
        """Search by fact trace dimensions.

        Args:
            subject: Optional subject filter.
            predicate: Optional predicate filter.

        Returns:
            Matching FactTrace entries.
        """
        results = []
        for fact in self._fact_traces.values():
            if subject and subject.lower() not in fact.subject.lower():
                continue
            if predicate and predicate.lower() not in fact.predicate.lower():
                continue
            results.append(fact)
        results.sort(key=lambda f: f.confidence, reverse=True)
        return tuple(results)

    async def search_by_scene(
        self,
        environment: str | None = None,
        min_importance: float = 0.0,
    ) -> tuple[SceneTrace, ...]:
        """Search by scene trace dimensions.

        Args:
            environment: Optional environment filter.
            min_importance: Minimum importance threshold.

        Returns:
            Matching SceneTrace entries.
        """
        results = []
        for scene in self._scene_traces.values():
            if environment and environment.lower() not in scene.environment.lower():
                continue
            if scene.importance < min_importance:
                continue
            results.append(scene)
        results.sort(key=lambda s: s.importance, reverse=True)
        return tuple(results)

    async def get_full_trace(self, trace_id: str) -> tuple[FactTrace, SceneTrace]:
        """Get both traces for a given ID."""
        if trace_id not in self._fact_traces:
            raise KeyError(f"Trace not found: {trace_id}")
        return (self._fact_traces[trace_id], self._scene_traces[trace_id])

    @property
    def trace_count(self) -> int:
        return len(self._fact_traces)
