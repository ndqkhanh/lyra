"""L4 Meta-Learning — cross-session knowledge synthesis and strategy evolution.

Transforms patterns observed across sessions into reusable strategies,
heuristics, and meta-knowledge that improve agent performance over time.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from enum import StrEnum


class StrategyType(StrEnum):
    HEURISTIC = "heuristic"
    WORKFLOW = "workflow"
    CONSTRAINT = "constraint"
    OPTIMIZATION = "optimization"


@dataclass(frozen=True)
class CrossSessionPattern:
    pattern_id: str
    pattern_type: StrategyType
    description: str
    source_sessions: list[str]
    confidence: float
    observed_count: int
    created_at: float


class CrossSessionWeaver:
    """Synthesizes patterns across multiple sessions into reusable strategies.

    Detects recurring patterns in agent behavior across independent
    sessions, clusters similar patterns, and promotes the most reliable
    ones into active strategies.
    """

    def __init__(self, min_confidence: float = 0.7, min_observations: int = 3) -> None:
        self.min_confidence = min_confidence
        self.min_observations = min_observations
        self._patterns: dict[str, CrossSessionPattern] = {}
        self._session_patterns: dict[str, list[str]] = {}

    def observe(
        self,
        session_id: str,
        pattern_type: StrategyType,
        description: str,
    ) -> CrossSessionPattern:
        content = f"{pattern_type.value}|{description}"
        pattern_id = hashlib.sha256(content.encode()).hexdigest()[:12]

        if pattern_id in self._patterns:
            existing = self._patterns[pattern_id]
            updated = CrossSessionPattern(
                pattern_id=pattern_id,
                pattern_type=pattern_type,
                description=description,
                source_sessions=list(set(existing.source_sessions + [session_id])),
                confidence=min(1.0, existing.confidence + 0.05),
                observed_count=existing.observed_count + 1,
                created_at=existing.created_at,
            )
        else:
            updated = CrossSessionPattern(
                pattern_id=pattern_id,
                pattern_type=pattern_type,
                description=description,
                source_sessions=[session_id],
                confidence=0.5,
                observed_count=1,
                created_at=time.time(),
            )

        self._patterns[pattern_id] = updated
        self._session_patterns.setdefault(session_id, []).append(pattern_id)
        return updated

    def get_strategies(self) -> list[CrossSessionPattern]:
        return [
            p for p in self._patterns.values()
            if p.confidence >= self.min_confidence
            and p.observed_count >= self.min_observations
        ]

    def get_for_session(self, session_id: str) -> list[CrossSessionPattern]:
        pattern_ids = self._session_patterns.get(session_id, [])
        return [self._patterns[pid] for pid in pattern_ids if pid in self._patterns]

    def stats(self) -> dict:
        strategies = self.get_strategies()
        return {
            "total_patterns": len(self._patterns),
            "active_strategies": len(strategies),
            "sessions_analyzed": len(self._session_patterns),
        }
