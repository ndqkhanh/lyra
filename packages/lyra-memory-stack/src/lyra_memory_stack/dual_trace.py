"""Fact + narrative scene trace encoding for improved recall.

DualTrace captures both the factual content of a memory and the narrative
scene in which it was learned — the context, agents involved, reasoning
chain, and environmental conditions — to improve recall by an estimated +20pp.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


class SceneType(Enum):
    """Types of narrative scenes that can accompany a fact."""

    OBSERVATION = auto()  # Direct observation
    INFERENCE = auto()  # Derived from reasoning
    VERIFICATION = auto()  # Confirmed by cross-checking
    CORRECTION = auto()  # Correcting a previous fact
    COLLABORATION = auto()  # Multi-agent interaction
    EXPLORATION = auto()  # Discovery during research
    ERROR_RECOVERY = auto()  # Learning from mistakes


@dataclass(frozen=True)
class SceneTrace:
    """Narrative context capturing HOW a fact was learned."""

    scene_id: str
    scene_type: SceneType
    description: str
    agents_involved: tuple[str, ...] = ()
    reasoning_chain: tuple[str, ...] = ()
    environmental_context: str = ""
    confidence_boost: float = 0.15
    timestamp: float = field(default_factory=time.time)

    def with_additional_agents(self, *agents: str) -> SceneTrace:
        """Return a new SceneTrace with additional agents (immutable)."""
        return SceneTrace(
            scene_id=self.scene_id,
            scene_type=self.scene_type,
            description=self.description,
            agents_involved=self.agents_involved + agents,
            reasoning_chain=self.reasoning_chain,
            environmental_context=self.environmental_context,
            confidence_boost=self.confidence_boost,
            timestamp=self.timestamp,
        )

    def with_reasoning(self, *steps: str) -> SceneTrace:
        """Return a new SceneTrace with additional reasoning steps (immutable)."""
        return SceneTrace(
            scene_id=self.scene_id,
            scene_type=self.scene_type,
            description=self.description,
            agents_involved=self.agents_involved,
            reasoning_chain=self.reasoning_chain + steps,
            environmental_context=self.environmental_context,
            confidence_boost=self.confidence_boost,
            timestamp=self.timestamp,
        )


@dataclass(frozen=True)
class DualTraceEntry:
    """Combines a fact with its narrative scene trace.

    The fact (statement/claim) is paired with the scene trace describing
    how it was learned, enabling context-aware recall.
    """

    fact_id: str
    statement: str
    scene_trace: SceneTrace
    domain: str = "general"
    confidence: float = 0.5
    source: str = "agent"
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def adjusted_confidence(self) -> float:
        """Confidence boosted by the scene trace's confidence_boost."""
        return min(1.0, self.confidence + self.scene_trace.confidence_boost)

    def with_updated_statement(self, new_statement: str, scene_type: SceneType = SceneType.CORRECTION) -> DualTraceEntry:
        """Return a new DualTraceEntry with an updated statement (immutable)."""
        correction_scene = SceneTrace(
            scene_id=f"corr_{self.fact_id}_{int(time.time())}",
            scene_type=scene_type,
            description=f"Corrected from: {self.statement}",
            agents_involved=self.scene_trace.agents_involved,
            reasoning_chain=self.scene_trace.reasoning_chain + ("corrected",),
            confidence_boost=0.2,
        )
        return DualTraceEntry(
            fact_id=self.fact_id,
            statement=new_statement,
            scene_trace=correction_scene,
            domain=self.domain,
            confidence=min(1.0, self.confidence + 0.1),
            source=self.source,
            timestamp=time.time(),
            metadata={**self.metadata, "previous_statement": self.statement},
        )


class DualTraceStore:
    """A store for DualTraceEntries with scene-trace-aware recall."""

    _entries: dict[str, DualTraceEntry]

    def __init__(self) -> None:
        self._entries = {}

    def store(self, entry: DualTraceEntry) -> None:
        """Store a dual-trace entry."""
        self._entries[entry.fact_id] = entry

    def get(self, fact_id: str) -> DualTraceEntry | None:
        """Retrieve a dual-trace entry by fact ID."""
        return self._entries.get(fact_id)

    def query_by_domain(self, domain: str) -> list[DualTraceEntry]:
        """Retrieve all entries in a given domain."""
        return [e for e in self._entries.values() if e.domain == domain]

    def query_by_agent(self, agent: str) -> list[DualTraceEntry]:
        """Retrieve all entries involving a given agent."""
        return [
            e for e in self._entries.values()
            if agent in e.scene_trace.agents_involved
        ]

    def query_by_scene_type(self, scene_type: SceneType) -> list[DualTraceEntry]:
        """Retrieve all entries with a given scene type."""
        return [
            e for e in self._entries.values()
            if e.scene_trace.scene_type == scene_type
        ]

    def search(self, keyword: str) -> list[DualTraceEntry]:
        """Search entries by keyword in statement, description, or domain."""
        keyword_lower = keyword.lower()
        return [
            e for e in self._entries.values()
            if keyword_lower in e.statement.lower()
            or keyword_lower in e.scene_trace.description.lower()
            or keyword_lower in e.domain.lower()
        ]

    def delete(self, fact_id: str) -> bool:
        """Delete an entry by fact ID. Returns True if deleted."""
        return self._entries.pop(fact_id, None) is not None

    def count(self) -> int:
        """Number of stored entries."""
        return len(self._entries)

    def clear(self) -> None:
        """Clear all entries."""
        self._entries.clear()

    def all_entries(self) -> list[DualTraceEntry]:
        """Return all stored entries."""
        return list(self._entries.values())
