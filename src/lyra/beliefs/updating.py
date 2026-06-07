"""Belief updating strategies: Bayesian, evidence weighting, source reliability, temporal decay,
consensus building."""

from __future__ import annotations

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .belief_system import (
    Belief,
    BeliefSource,
    BeliefStatus,
    BeliefSystem,
    UpdateMethod,
)

logger = logging.getLogger(__name__)


# ── Data classes ────────────────────────────────────────────────────────


@dataclass
class SourceProfile:
    """Profile tracking source reliability over time.

    Attributes:
        source_name: Unique source identifier.
        accuracy_history: Recorded accuracy values.
        report_count: Number of reports from this source.
        last_seen: When last reported.
        reliability_score: Computed reliability (0-1).
        bias_estimate: Estimated directional bias (-1 to 1).
    """

    source_name: str
    accuracy_history: deque[float] = field(default_factory=lambda: deque(maxlen=100))
    report_count: int = 0
    last_seen: float = field(default_factory=time.time)
    reliability_score: float = 0.5
    bias_estimate: float = 0.0


@dataclass
class EvidencePacket:
    """A packet of evidence for belief update.

    Attributes:
        statement: The evidence statement.
        strength: How strong the evidence is (0-1).
        supports: Whether the evidence supports (True) or opposes (False).
        source: Where the evidence came from.
        source_reliability: Source reliability rating.
        timestamp: When collected.
    """

    statement: str
    strength: float = 0.5
    supports: bool = True
    source: str = "unknown"
    source_reliability: float = 0.5
    timestamp: float = field(default_factory=time.time)


@dataclass
class ConsensusResult:
    """Result of consensus building across sources.

    Attributes:
        topic: What was being evaluated.
        sources_consulted: Source names.
        individual_judgments: Source -> judgment mapping.
        consensus_value: Aggregated consensus.
        agreement_level: Level of agreement (0 = full disagreement, 1 = full agreement).
        confidence: Confidence in the consensus.
    """

    topic: str
    sources_consulted: list[str] = field(default_factory=list)
    individual_judgments: dict[str, float] = field(default_factory=dict)
    consensus_value: float = 0.5
    agreement_level: float = 0.0
    confidence: float = 0.5


# ── Belief Updater ─────────────────────────────────────────────────────


class BeliefUpdater:
    """Manages belief updating with multiple strategies.

    Supports Bayesian updating, evidence strength weighting, source reliability tracking, temporal
    decay, and consensus building across multiple sources.
    """

    def __init__(self, belief_system: BeliefSystem) -> None:
        self.belief_system = belief_system
        self._sources: dict[str, SourceProfile] = {}
        self._evidence_log: deque[EvidencePacket] = deque(maxlen=5000)
        self._consensus_results: deque[ConsensusResult] = deque(maxlen=100)

    # ── Bayesian updating ──────────────────────────────────────────────

    def bayesian_update(
        self,
        belief_id: str,
        likelihood_ratio: float,
        evidence_strength: float = 0.5,
    ) -> Belief:
        """Update belief using Bayes' rule.

        P(H|E) = P(E|H) * P(H) / P(E)

        Args:
            belief_id: Belief to update.
            likelihood_ratio: P(E|H)/P(E) - how much more likely the
                             evidence is under the hypothesis.
            evidence_strength: Weight of the evidence (0-1).

        Returns:
            Updated belief.
        """
        return self.belief_system.update_bayesian(belief_id, evidence_strength, likelihood_ratio)

    def jeffreys_update(
        self,
        belief_id: str,
        new_confidence: float,
        evidence_reliability: float = 0.5,
    ) -> Belief:
        """Update using Jeffrey's rule for uncertain evidence.

        Args:
            belief_id: Belief to update.
            new_confidence: Desired confidence given new evidence.
            evidence_reliability: How reliable the evidence is (0-1).

        Returns:
            Updated belief.
        """
        return self.belief_system.update_jeffreys(belief_id, new_confidence, evidence_reliability)

    # ── Evidence weighting ─────────────────────────────────────────────

    def update_with_evidence(
        self,
        belief_id: str,
        evidence: list[EvidencePacket],
    ) -> Belief:
        """Update a belief using weighted evidence packets.

        Each evidence packet contributes based on its strength,
        supporting/opposing direction, and source reliability.

        Args:
            belief_id: Belief to update.
            evidence: List of evidence packets.

        Returns:
            Updated belief.
        """
        belief = self.belief_system.get(belief_id)

        for packet in evidence:
            self._evidence_log.append(packet)

            weight = packet.strength * packet.source_reliability
            direction = 1.0 if packet.supports else -1.0

            # Scale confidence adjustment
            adjustment = direction * weight * 0.2

            belief.confidence = max(0.0, min(1.0, belief.confidence + adjustment))

            # Update evidence lists
            if packet.supports:
                if packet.statement not in belief.evidence:
                    belief.evidence.append(packet.statement)
            else:
                if packet.statement not in belief.counter_evidence:
                    belief.counter_evidence.append(packet.statement)

        belief.last_updated = time.time()

        self.belief_system._record_update(
            belief_id,
            UpdateMethod.EVIDENCE_WEIGHTING,
            belief.confidence,
            belief.confidence,
            {"evidence_count": len(evidence)},
        )

        return belief

    # ── Source reliability tracking ────────────────────────────────────

    def register_source(self, source_name: str) -> SourceProfile:
        """Register a belief source for reliability tracking.

        Args:
            source_name: Unique source identifier.

        Returns:
            Source profile.
        """
        if source_name not in self._sources:
            self._sources[source_name] = SourceProfile(source_name=source_name)
        return self._sources[source_name]

    def record_source_accuracy(
        self,
        source_name: str,
        was_accurate: bool,
        bias: float = 0.0,
    ) -> None:
        """Record an accuracy observation for a source.

        Args:
            source_name: Source identifier.
            was_accurate: Whether the report was accurate.
            bias: Observed directional bias (-1 to 1).
        """
        source = self._sources.get(source_name)
        if source is None:
            source = self.register_source(source_name)

        source.accuracy_history.append(1.0 if was_accurate else 0.0)
        source.report_count += 1
        source.last_seen = time.time()

        # Update reliability score (exponential moving average)
        alpha = 0.1
        source.reliability_score = (
            alpha * (1.0 if was_accurate else 0.0) + (1.0 - alpha) * source.reliability_score
        )

        # Update bias estimate
        source.bias_estimate = alpha * bias + (1.0 - alpha) * source.bias_estimate

    def get_source_reliability(self, source_name: str) -> float:
        """Get the reliability score for a source.

        Args:
            source_name: Source identifier.

        Returns:
            Reliability score (0-1). Returns 0.5 for unknown sources.
        """
        source = self._sources.get(source_name)
        return source.reliability_score if source else 0.5

    def get_trusted_sources(self, min_reliability: float = 0.7) -> list[str]:
        """Get sources that meet a reliability threshold.

        Args:
            min_reliability: Minimum reliability score.

        Returns:
            List of trusted source names.
        """
        return [
            name
            for name, prof in self._sources.items()
            if prof.reliability_score >= min_reliability
        ]

    # ── Temporal decay ─────────────────────────────────────────────────

    def apply_temporal_decay(
        self,
        half_life_seconds: float = 86400.0 * 7,  # 7 days default
    ) -> int:
        """Apply temporal decay to all beliefs.

        Beliefs that haven't been updated recently lose confidence
        following an exponential decay curve. Active beliefs decay
        more slowly than inactive ones.

        Args:
            half_life_seconds: Time after which confidence halves.

        Returns:
            Number of beliefs whose confidence was adjusted.
        """
        now = time.time()
        adjusted_count = 0
        decay_rate = np.log(2) / half_life_seconds

        for belief in self.belief_system._beliefs.values():
            if belief.status != BeliefStatus.ACTIVE:
                continue

            age_seconds = now - belief.last_updated

            if age_seconds > half_life_seconds * 0.1:  # Only decay after 10% of half-life
                # Exponential decay
                decay_factor = np.exp(-decay_rate * age_seconds)

                # Don't let confidence go below a floor
                floor = 0.05 if belief.source == BeliefSource.LEARNED else 0.2
                new_confidence = max(
                    floor,
                    belief.confidence * (0.3 + 0.7 * decay_factor),
                )

                if abs(new_confidence - belief.confidence) > 0.001:
                    belief.confidence = new_confidence
                    adjusted_count += 1

        if adjusted_count > 0:
            logger.info(
                "Temporal decay applied to %d beliefs (half_life=%.1fh)",
                adjusted_count,
                half_life_seconds / 3600,
            )

        return adjusted_count

    def get_belief_age(self, belief_id: str) -> float:
        """Get the age of a belief in seconds since last update.

        Args:
            belief_id: Belief identifier.

        Returns:
            Age in seconds.
        """
        belief = self.belief_system.get(belief_id)
        return time.time() - belief.last_updated

    def get_stale_beliefs(
        self,
        max_age_seconds: float = 86400.0 * 30,
    ) -> list[Belief]:
        """Get beliefs that haven't been updated recently.

        Args:
            max_age_seconds: Maximum acceptable age.

        Returns:
            List of stale beliefs.
        """
        now = time.time()
        return [
            b for b in self.belief_system.get_active() if (now - b.last_updated) > max_age_seconds
        ]

    # ── Consensus building ─────────────────────────────────────────────

    def build_consensus(
        self,
        topic: str,
        source_judgments: dict[str, float],
    ) -> ConsensusResult:
        """Build consensus across multiple sources on a topic.

        Weights each source's judgment by its reliability and computes
        agreement levels.

        Args:
            topic: The topic being evaluated.
            source_judgments: Dict of source_name -> judgment (0-1).

        Returns:
            Consensus result.
        """
        if not source_judgments:
            return ConsensusResult(topic=topic)

        weighted_sum = 0.0
        total_weight = 0.0
        judgments_list: list[float] = []

        for source_name, judgment in source_judgments.items():
            reliability = self.get_source_reliability(source_name)
            bias = self._sources.get(source_name, SourceProfile(source_name)).bias_estimate

            # Adjust judgment by estimated bias
            adjusted = max(0.0, min(1.0, judgment - bias * 0.2))
            weight = reliability

            weighted_sum += adjusted * weight
            total_weight += weight
            judgments_list.append(adjusted)

        consensus = weighted_sum / max(total_weight, 1e-10)

        # Agreement level: 1 - normalized std (1 = perfect agreement)
        if len(judgments_list) > 1:
            std = float(np.std(judgments_list))
            agreement = 1.0 - min(1.0, std * 2.0)
        else:
            agreement = 1.0

        # Confidence in consensus depends on number of sources and agreement
        confidence = (
            0.3 * min(1.0, len(source_judgments) / 5)
            + 0.4 * agreement
            + 0.3 * (total_weight / max(len(source_judgments), 1))
        )

        result = ConsensusResult(
            topic=topic,
            sources_consulted=list(source_judgments.keys()),
            individual_judgments=source_judgments,
            consensus_value=float(consensus),
            agreement_level=float(agreement),
            confidence=float(confidence),
        )
        self._consensus_results.append(result)

        # Create or update a belief from this consensus
        domain = "consensus"
        existing_beliefs = [
            b
            for b in self.belief_system._beliefs.values()
            if b.domain == domain and topic.lower() in b.statement.lower()
        ]

        if existing_beliefs:
            existing_beliefs[0].confidence = consensus
            existing_beliefs[0].last_updated = time.time()
        else:
            self.belief_system.create_belief(
                domain=domain,
                statement=f"Consensus on {topic}: agreement={agreement:.2f}",
                confidence=consensus,
                source=BeliefSource.INFERRED,
                source_reliability=confidence,
            )

        logger.info(
            "Consensus on '%s': %.3f (agreement=%.2f, sources=%d)",
            topic,
            consensus,
            agreement,
            len(source_judgments),
        )

        return result

    def get_consensus(self, topic: str) -> ConsensusResult | None:
        """Get the most recent consensus on a topic.

        Args:
            topic: The topic.

        Returns:
            Most recent ConsensusResult or None.
        """
        for result in reversed(self._consensus_results):
            if topic.lower() in result.topic.lower():
                return result
        return None

    # ── Statistics ─────────────────────────────────────────────────────

    @property
    def source_count(self) -> int:
        """Number of registered sources."""
        return len(self._sources)

    @property
    def evidence_count(self) -> int:
        """Number of evidence packets logged."""
        return len(self._evidence_log)

    @property
    def summary(self) -> dict[str, Any]:
        """Get updater summary."""
        trusted = self.get_trusted_sources()
        stale = self.get_stale_beliefs()

        source_stats = {}
        for name, prof in self._sources.items():
            source_stats[name] = {
                "reliability": prof.reliability_score,
                "bias": prof.bias_estimate,
                "reports": prof.report_count,
            }

        return {
            "sources_tracked": self.source_count,
            "trusted_sources": len(trusted),
            "avg_reliability": (
                float(np.mean([p.reliability_score for p in self._sources.values()]))
                if self._sources
                else 0.0
            ),
            "evidence_packets": self.evidence_count,
            "consensus_results": len(self._consensus_results),
            "stale_beliefs": len(stale),
            "source_details": source_stats,
        }
