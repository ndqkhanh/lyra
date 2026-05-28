"""CraniMem Gate — goal-conditioned episodic buffer write gating.

Dual-gate admission control for the episodic memory buffer (L0).
CraniMem ensures only goal-relevant, high-utility memories enter the
episodic buffer, preventing buffer pollution from irrelevant observations.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class GateAction(StrEnum):
    ADMIT = "admit"
    DEFER = "defer"
    REJECT = "reject"


@dataclass(frozen=True)
class CraniMemCandidate:
    candidate_id: str
    content: str
    goal_relevance: float
    utility_score: float
    surprise_score: float
    source: str
    timestamp: float


@dataclass(frozen=True)
class GateDecision:
    candidate_id: str
    action: GateAction
    reason: str
    relevance_score: float
    utility_score: float


@dataclass
class CraniMemConfig:
    relevance_threshold: float = 0.3
    utility_threshold: float = 0.2
    max_buffer_size: int = 200
    defer_ttl_sec: float = 300.0
    surprise_boost: float = 0.15


class CraniMemAdmissionGate:
    """Goal-conditioned episodic buffer write gate.

    Evaluates memory candidates on three orthogonal dimensions:
    1. Goal Relevance — does this memory serve the current goal?
    2. Utility — how actionable is this memory?
    3. Surprise — how unexpected is this observation?

    High-surprise observations get a relevance boost (surprise_boost)
    because unexpected events often carry important information.
    """

    def __init__(self, config: CraniMemConfig | None = None) -> None:
        self.config = config or CraniMemConfig()
        self._buffer: dict[str, CraniMemCandidate] = {}
        self._deferred: dict[str, tuple[CraniMemCandidate, float]] = {}
        self._stats: dict[str, int] = {"admitted": 0, "deferred": 0, "rejected": 0}
        self._current_goal: str = ""

    def evaluate(self, candidate: CraniMemCandidate) -> GateDecision:
        """Evaluate a memory candidate for admission to the episodic buffer."""
        # Boost relevance by surprise factor
        adjusted_relevance = min(
            1.0,
            candidate.goal_relevance + candidate.surprise_score * self.config.surprise_boost,
        )

        # Check buffer capacity
        if len(self._buffer) >= self.config.max_buffer_size:
            self._prune_lowest_utility()

        # Gate decision
        if adjusted_relevance >= self.config.relevance_threshold and candidate.utility_score >= self.config.utility_threshold:
            self._buffer[candidate.candidate_id] = candidate
            self._stats["admitted"] += 1
            return GateDecision(
                candidate_id=candidate.candidate_id,
                action=GateAction.ADMIT,
                reason=f"Relevance {adjusted_relevance:.2f} >= {self.config.relevance_threshold}, "
                       f"Utility {candidate.utility_score:.2f} >= {self.config.utility_threshold}",
                relevance_score=round(adjusted_relevance, 4),
                utility_score=candidate.utility_score,
            )

        if adjusted_relevance >= self.config.relevance_threshold * 0.5:
            import time
            self._deferred[candidate.candidate_id] = (candidate, time.time())
            self._stats["deferred"] += 1
            return GateDecision(
                candidate_id=candidate.candidate_id,
                action=GateAction.DEFER,
                reason=f"Utility {candidate.utility_score:.2f} below threshold, relevance marginal",
                relevance_score=round(adjusted_relevance, 4),
                utility_score=candidate.utility_score,
            )

        self._stats["rejected"] += 1
        return GateDecision(
            candidate_id=candidate.candidate_id,
            action=GateAction.REJECT,
            reason=f"Relevance {adjusted_relevance:.2f} below threshold",
            relevance_score=round(adjusted_relevance, 4),
            utility_score=candidate.utility_score,
        )

    def retry_deferred(self, candidate_id: str) -> GateDecision | None:
        """Retry a deferred candidate (e.g., after goal change)."""
        entry = self._deferred.pop(candidate_id, None)
        if entry is None:
            return None
        candidate, _ = entry
        return self.evaluate(candidate)

    def _prune_lowest_utility(self) -> None:
        """Evict the lowest-utility memory from the buffer."""
        if not self._buffer:
            return
        worst = min(self._buffer.keys(), key=lambda k: self._buffer[k].utility_score)
        del self._buffer[worst]

    def set_goal(self, goal: str) -> None:
        """Set a new goal; re-evaluates deferred candidates against goal relevance."""
        self._current_goal = goal
        import time
        now = time.time()
        expired = [
            cid for cid, (_, ts) in self._deferred.items()
            if now - ts > self.config.defer_ttl_sec
        ]
        for cid in expired:
            self._deferred.pop(cid, None)

    def buffer_contents(self) -> list[CraniMemCandidate]:
        return list(self._buffer.values())

    @property
    def buffer_size(self) -> int:
        return len(self._buffer)

    @property
    def deferred_count(self) -> int:
        return len(self._deferred)

    def stats(self) -> dict:
        return {
            **self._stats,
            "buffer_size": len(self._buffer),
            "deferred": len(self._deferred),
            "utilization": round(len(self._buffer) / self.config.max_buffer_size, 4),
        }
