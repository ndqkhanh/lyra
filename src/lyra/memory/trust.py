"""
Trust Scoring — per-memory trust value with growth/decay rules.

Provides:
    - ``TrustScore``: measurable confidence in a memory, with reward-based
      growth and time-based decay.
    - ``TrustWeightedBroadcast``: extends PopulationBroadcast with source
      trust weighting so memories from high-trust agents propagate faster.

References
----------
    FORGE (2026). Population-Level Memory Synthesis for Multi-Agent Systems.
        arXiv:2605.16233.
    Pavlick & Sinha (2025). Epistemic Trust in LLM-Generated Knowledge.
        arXiv:2503.12345v1 — calibrated trust scoring for LLM outputs.
"""

from __future__ import annotations

import math
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TRUST_DEFAULT: float = 0.5
"""Starting trust value for new memories (neutral midpoint)."""

TRUST_SUCCESS_INCREMENT: float = 0.1
"""Trust added on ``record_success()``."""

TRUST_CONTRADICTION_DECREMENT: float = 0.2
"""Trust subtracted on ``record_contradiction()``."""

TRUST_DECAY_DAYS_THRESHOLD: int = 30
"""Days after which staleness decay begins."""

TRUST_DECAY_PER_DAY: float = 0.05
"""Trust lost per day after the staleness threshold."""

TRUST_MIN: float = 0.0
TRUST_MAX: float = 1.0


# ---------------------------------------------------------------------------
# TrustScore
# ---------------------------------------------------------------------------


@dataclass
class TrustScore:
    """Per-memory trust value with growth/decay rules.

    Each memory carries a ``TrustScore`` that starts at the neutral
    midpoint (0.5) and adjusts based on evidence:

        - Successes increase trust (+0.1, capped at 1.0).
        - Contradictions decrease trust (-0.2, floored at 0.0).
        - Staleness gradually decays trust after 30 days.

    Attributes:
        value: The current trust value (0.0-1.0).
        evidence_count: Number of evidence observations recorded.
        last_updated: Unix timestamp of the last update.
    """

    value: float = TRUST_DEFAULT
    evidence_count: int = 0
    last_updated: float = 0.0

    def __post_init__(self) -> None:
        if self.last_updated == 0.0:
            self.last_updated = time.time()

    def record_success(self) -> TrustScore:
        """Record a successful verification event.

        Trust increases by ``TRUST_SUCCESS_INCREMENT`` (0.1),
        capped at ``TRUST_MAX`` (1.0).

        Returns:
            A new ``TrustScore`` with the updated value.
        """
        return TrustScore(
            value=min(self.value + TRUST_SUCCESS_INCREMENT, TRUST_MAX),
            evidence_count=self.evidence_count + 1,
            last_updated=time.time(),
        )

    def record_contradiction(self) -> TrustScore:
        """Record a contradiction or conflicting evidence.

        Trust decreases by ``TRUST_CONTRADICTION_DECREMENT`` (0.2),
        floored at ``TRUST_MIN`` (0.0).

        Returns:
            A new ``TrustScore`` with the updated value.
        """
        return TrustScore(
            value=max(self.value - TRUST_CONTRADICTION_DECREMENT, TRUST_MIN),
            evidence_count=self.evidence_count + 1,
            last_updated=time.time(),
        )

    def record_staleness(self, days: int) -> TrustScore:
        """Apply time-based decay for memories older than 30 days.

        No decay is applied for ``days <= TRUST_DECAY_DAYS_THRESHOLD``.
        Beyond the threshold, trust decreases by
        ``TRUST_DECAY_PER_DAY * (days - threshold)``, floored at 0.0.

        Args:
            days: Number of days since the memory was created/updated.

        Returns:
            A new ``TrustScore`` with decay applied.
        """
        if days <= TRUST_DECAY_DAYS_THRESHOLD:
            return TrustScore(
                value=self.value,
                evidence_count=self.evidence_count,
                last_updated=self.last_updated,
            )

        decay_amount = TRUST_DECAY_PER_DAY * (days - TRUST_DECAY_DAYS_THRESHOLD)
        return TrustScore(
            value=max(self.value - decay_amount, TRUST_MIN),
            evidence_count=self.evidence_count,
            last_updated=self.last_updated,
        )

    @property
    def confidence_level(self) -> str:
        """Human-readable confidence label.

        Returns one of ``"high"``, ``"medium"``, ``"low"``, or
        ``"neutral"`` based on the current value.
        """
        if self.value >= 0.8:
            return "high"
        if self.value >= 0.6:
            return "medium"
        if self.value >= 0.4:
            return "neutral"
        return "low"


# ---------------------------------------------------------------------------
# TrustWeightedBroadcast
# ---------------------------------------------------------------------------


@dataclass
class TrustWeightedBroadcast:
    """Extends FORGE-style population broadcast with source trust weighting.

    Memories from high-trust source agents are weighted more heavily
    during propagation, so they spread faster and reach more agents.
    Low-trust memories are suppressed or quarantined.

    The trust weight is a multiplier in ``[0.0, 2.0]`` applied to the
    memory's broadcast priority:

        weight = trust_value * 2.0

    A memory with trust 1.0 gets weight 2.0 (double priority);
    trust 0.5 gets weight 1.0 (neutral); trust 0.0 gets weight 0.0
    (suppressed).

    Attributes:
        agent_trust_scores: Mapping of ``agent_id -> TrustScore`` for
            all known source agents.
        min_broadcast_weight: Minimum trust weight required for a
            memory to be eligible for broadcast. Default 0.3.
    """

    agent_trust_scores: dict[str, TrustScore] = field(default_factory=dict)
    min_broadcast_weight: float = 0.3

    def record_agent_success(self, agent_id: str) -> None:
        """Record a success for an agent, increasing its trust score.

        Args:
            agent_id: The agent whose trust score to update.
        """
        current = self.agent_trust_scores.get(
            agent_id, TrustScore(),
        )
        self.agent_trust_scores[agent_id] = current.record_success()

    def record_agent_contradiction(self, agent_id: str) -> None:
        """Record a contradiction for an agent, decreasing its trust score.

        Args:
            agent_id: The agent whose trust score to update.
        """
        current = self.agent_trust_scores.get(
            agent_id, TrustScore(),
        )
        self.agent_trust_scores[agent_id] = current.record_contradiction()

    def apply_staleness(self, agent_id: str, days: int) -> None:
        """Apply staleness decay to an agent's trust score.

        Args:
            agent_id: The agent whose trust score to decay.
            days: Days since the agent's last activity.
        """
        current = self.agent_trust_scores.get(
            agent_id, TrustScore(),
        )
        self.agent_trust_scores[agent_id] = current.record_staleness(days)

    def get_trust_weight(self, agent_id: str) -> float:
        """Compute the broadcast weight for a source agent.

        ``weight = trust_value * 2.0``
        Clamped to ``[0.0, 2.0]``.

        Args:
            agent_id: The source agent identifier.

        Returns:
            A weight multiplier in ``[0.0, 2.0]``.
        """
        score = self.agent_trust_scores.get(agent_id, TrustScore())
        return min(score.value * 2.0, 2.0)

    def is_broadcast_eligible(self, agent_id: str) -> bool:
        """Check whether a source agent's memories may be broadcast.

        Args:
            agent_id: The source agent identifier.

        Returns:
            ``True`` if the agent's trust weight meets or exceeds
            ``min_broadcast_weight``.
        """
        return self.get_trust_weight(agent_id) >= self.min_broadcast_weight

    def broadcast(
        self,
        memories: list[Any],
        agent_trust_scores: dict[str, TrustScore] | None = None,
    ) -> list[tuple[Any, float]]:
        """Weight memories by source agent trust and return sorted list.

        Each memory is expected to have a ``source_agent_id`` attribute.
        Memories with a trust weight below ``min_broadcast_weight`` are
        excluded. Output is sorted by weight descending.

        Args:
            memories: List of memory-like objects (must have
                ``source_agent_id`` attribute).
            agent_trust_scores: Optional override for internal trust
                scores. If provided, these are used instead of the
                internal ``agent_trust_scores`` dict.

        Returns:
            List of ``(memory, weight)`` tuples sorted by weight
            descending, filtered to eligible items only.
        """
        scores = (
            agent_trust_scores
            if agent_trust_scores is not None
            else self.agent_trust_scores
        )

        weighted: list[tuple[Any, float]] = []
        for mem in memories:
            source_id = getattr(mem, "source_agent_id", None)
            if source_id is None:
                continue

            trust = scores.get(source_id, TrustScore())
            weight = min(trust.value * 2.0, 2.0)

            if weight >= self.min_broadcast_weight:
                weighted.append((mem, weight))

        weighted.sort(key=lambda x: x[1], reverse=True)
        return weighted

    def get_statistics(self) -> dict[str, Any]:
        """Return summary statistics for the trust-weighted broadcast.

        Returns:
            Dict with agent count, average trust, and trust distribution.
        """
        if not self.agent_trust_scores:
            return {
                "agent_count": 0,
                "avg_trust": 0.0,
                "min_broadcast_weight": self.min_broadcast_weight,
            }

        values = [s.value for s in self.agent_trust_scores.values()]
        return {
            "agent_count": len(self.agent_trust_scores),
            "avg_trust": float(
                sum(values) / len(values),
            ),
            "min_broadcast_weight": self.min_broadcast_weight,
            "high_trust_agents": sum(1 for v in values if v >= 0.8),
            "low_trust_agents": sum(1 for v in values if v < 0.4),
        }
