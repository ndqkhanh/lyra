"""Core belief management: representation, update (Bayesian, Jeffrey, AGM), revision, contraction,
expansion, consistency."""

from __future__ import annotations

import logging
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

import numpy as np

from .exceptions import (
    BeliefNotFoundError,
)

logger = logging.getLogger(__name__)


# ── Enums and data classes ──────────────────────────────────────────────


class BeliefSource(Enum):
    """How a belief was acquired."""

    LEARNED = auto()  # Learned from experience
    EXPERT_ENCODED = auto()  # Encoded by domain expert
    EXTRACTED = auto()  # Extracted from data
    INFERRED = auto()  # Derived via inference
    OBSERVED = auto()  # Direct observation
    IMPORTED = auto()  # Imported from external source


class BeliefStatus(Enum):
    """Lifecycle status of a belief."""

    ACTIVE = auto()
    RETRACTED = auto()
    SUPERSEDED = auto()
    DISPUTED = auto()
    EXPERIMENTAL = auto()


class UpdateMethod(Enum):
    """Methods for updating beliefs."""

    BAYESIAN = auto()  # Bayes' rule
    JEFFREYS = auto()  # Jeffrey's rule (uncertain evidence)
    AGM_EXPANSION = auto()  # AGM expansion
    AGM_REVISION = auto()  # AGM revision
    AGM_CONTRACTION = auto()  # AGM contraction
    EVIDENCE_WEIGHTING = auto()  # Weighted evidence


@dataclass
class Belief:
    """A single belief about the world.

    Attributes:
        belief_id: Unique identifier.
        domain: Knowledge domain.
        statement: The belief statement.
        confidence: Degree of belief (0.0 to 1.0).
        source: How the belief was acquired.
        evidence: Supporting evidence.
        counter_evidence: Evidence against.
        source_reliability: Reliability of the source (0-1).
        timestamp: When created.
        last_updated: Last update time.
        status: Lifecycle status.
        hit_count: How often retrieved.
        metadata: Additional context.
    """

    belief_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    domain: str = "general"
    statement: str = ""
    confidence: float = 0.5
    source: BeliefSource = BeliefSource.LEARNED
    evidence: list[str] = field(default_factory=list)
    counter_evidence: list[str] = field(default_factory=list)
    source_reliability: float = 0.5
    timestamp: float = field(default_factory=time.time)
    last_updated: float = field(default_factory=time.time)
    status: BeliefStatus = BeliefStatus.ACTIVE
    hit_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be in [0, 1], got {self.confidence}")
        if not 0.0 <= self.source_reliability <= 1.0:
            raise ValueError(f"Source reliability must be in [0, 1], got {self.source_reliability}")


@dataclass
class BeliefSet:
    """A collection of related beliefs (e.g., a theory, a domain model).

    Attributes:
        set_id: Unique identifier.
        name: Human-readable name.
        beliefs: List of belief IDs in this set.
        consistent: Whether the set is internally consistent.
        created_at: When created.
        metadata: Additional context.
    """

    set_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    beliefs: list[str] = field(default_factory=list)
    consistent: bool = True
    created_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


# ── Conditional probability table ──────────────────────────────────────


@dataclass
class ConditionalProbability:
    """P(effect | cause) for a conditional relationship.

    Attributes:
        cause: The causing belief/event.
        effect: The resulting belief/event.
        probability: P(effect | cause).
        evidence: Supporting evidence count.
    """

    cause: str
    effect: str
    probability: float = 0.5
    evidence_count: int = 0


# ── Belief System ──────────────────────────────────────────────────────


class BeliefSystem:
    """Core belief management system.

    Manages the lifecycle of beliefs: encoding, retrieval, update,
    revision, contraction, expansion, and consistency checking.
    Implements Bayesian, Jeffrey's rule, and AGM update methods.
    """

    def __init__(self) -> None:
        self._beliefs: dict[str, Belief] = {}
        self._domains: dict[str, list[str]] = defaultdict(list)
        self._sets: dict[str, BeliefSet] = {}
        self._conditionals: dict[tuple[str, str], ConditionalProbability] = {}
        self._update_history: deque[dict[str, Any]] = deque(maxlen=5000)
        self._counter: int = 0

    # ── Encoding ───────────────────────────────────────────────────────

    def add_belief(self, belief: Belief) -> Belief:
        """Add a belief to the system.

        Args:
            belief: The belief to add.

        Returns:
            The added belief.
        """
        self._validate_belief(belief)
        self._counter += 1
        self._beliefs[belief.belief_id] = belief
        self._domains[belief.domain].append(belief.belief_id)

        logger.debug(
            "Belief added: %s [%s] confidence=%.2f",
            belief.belief_id[:8],
            belief.domain,
            belief.confidence,
        )
        return belief

    def create_belief(
        self,
        domain: str,
        statement: str,
        confidence: float = 0.5,
        source: BeliefSource = BeliefSource.LEARNED,
        evidence: list[str] | None = None,
        source_reliability: float = 0.5,
    ) -> Belief:
        """Create and add a belief (convenience method).

        Args:
            domain: Knowledge domain.
            statement: The belief statement.
            confidence: Initial confidence (0-1).
            source: How acquired.
            evidence: Supporting evidence.
            source_reliability: Source trust (0-1).

        Returns:
            The created belief.
        """
        belief = Belief(
            domain=domain,
            statement=statement,
            confidence=confidence,
            source=source,
            evidence=evidence or [],
            source_reliability=source_reliability,
        )
        return self.add_belief(belief)

    def _validate_belief(self, belief: Belief) -> None:
        """Validate a belief before insertion."""
        if not belief.statement.strip():
            raise ValueError("Belief statement cannot be empty")

    # ── Retrieval ──────────────────────────────────────────────────────

    def get(self, belief_id: str) -> Belief:
        """Get a belief by ID.

        Raises:
            BeliefNotFoundError: If not found.
        """
        if belief_id not in self._beliefs:
            raise BeliefNotFoundError(belief_id)
        belief = self._beliefs[belief_id]
        belief.hit_count += 1
        return belief

    def get_all(self) -> list[Belief]:
        """Get all beliefs."""
        return list(self._beliefs.values())

    def get_by_domain(self, domain: str) -> list[Belief]:
        """Get all beliefs in a domain."""
        ids = self._domains.get(domain, [])
        return [self._beliefs[bid] for bid in ids if bid in self._beliefs]

    def get_active(self) -> list[Belief]:
        """Get all active (non-retracted) beliefs."""
        return [b for b in self._beliefs.values() if b.status == BeliefStatus.ACTIVE]

    def query(
        self,
        context: str,
        top_k: int = 5,
        domain: str | None = None,
    ) -> list[Belief]:
        """Retrieve relevant beliefs for a context via keyword matching.

        Args:
            context: The query context.
            top_k: Maximum results.
            domain: Optional domain filter.

        Returns:
            Ranked list of beliefs.
        """
        context_lower = context.lower()
        scored: list[tuple[float, Belief]] = []

        candidates = self.get_by_domain(domain) if domain else self._beliefs.values()

        for belief in candidates:
            if belief.status == BeliefStatus.RETRACTED:
                continue

            score = 0.0
            # Domain match
            if belief.domain in context_lower:
                score += 0.3

            # Keyword overlap
            belief_words = set(belief.statement.lower().split())
            context_words = set(context_lower.split())
            overlap = belief_words & context_words
            if overlap:
                score += 0.1 * len(overlap)

            # Confidence bonus
            score += belief.confidence * 0.5

            # Hit count bonus (recency/frequency heuristic)
            score += min(belief.hit_count, 50) * 0.01

            scored.append((score, belief))

        scored.sort(key=lambda x: -x[0])
        return [b for _, b in scored[:top_k]]

    # ── Update ─────────────────────────────────────────────────────────

    def update_bayesian(
        self, belief_id: str, evidence_strength: float, likelihood_ratio: float
    ) -> Belief:
        """Update a belief using Bayes' rule.

        P(H|E) = P(E|H) * P(H) / P(E)

        Where:
        - prior = current confidence
        - likelihood_ratio = P(E|H) / P(E) (how strongly evidence supports H)
        - evidence_strength = weight of new evidence (0-1)

        Args:
            belief_id: Belief to update.
            evidence_strength: Weight of the new evidence (0-1).
            likelihood_ratio: Ratio of how likely evidence is given belief.

        Returns:
            Updated belief.
        """
        belief = self.get(belief_id)
        prior = belief.confidence

        # Bayesian update with evidence weighting
        # posterior = (likelihood_ratio * prior) / (likelihood_ratio * prior + (1 - prior))
        numerator = likelihood_ratio * prior
        denominator = likelihood_ratio * prior + (1.0 - prior)

        if denominator < 1e-10:
            posterior = prior
        else:
            posterior = numerator / denominator

        # Blend with original based on evidence strength
        new_confidence = evidence_strength * posterior + (1.0 - evidence_strength) * prior
        new_confidence = max(0.0, min(1.0, new_confidence))

        old_confidence = belief.confidence
        belief.confidence = new_confidence
        belief.last_updated = time.time()

        self._record_update(
            belief_id,
            UpdateMethod.BAYESIAN,
            old_confidence,
            new_confidence,
            {
                "evidence_strength": evidence_strength,
                "likelihood_ratio": likelihood_ratio,
            },
        )

        logger.debug(
            "Bayesian update: %s %.3f -> %.3f", belief_id[:8], old_confidence, new_confidence
        )
        return belief

    def update_jeffreys(
        self, belief_id: str, new_confidence: float, evidence_reliability: float = 0.5
    ) -> Belief:
        """Update using Jeffrey's rule (uncertain evidence).

        Jeffrey's rule handles cases where evidence itself is uncertain.
        P'(H) = P(H|E) * P'(E) + P(H|~E) * P'(~E)

        Args:
            belief_id: Belief to update.
            new_confidence: New degree of belief given uncertain evidence.
            evidence_reliability: How reliable the evidence is (0-1).

        Returns:
            Updated belief.
        """
        belief = self.get(belief_id)
        old_confidence = belief.confidence

        # Weighted average with prior
        updated = (
            evidence_reliability * new_confidence + (1.0 - evidence_reliability) * old_confidence
        )
        updated = max(0.0, min(1.0, updated))

        belief.confidence = updated
        belief.last_updated = time.time()

        self._record_update(
            belief_id,
            UpdateMethod.JEFFREYS,
            old_confidence,
            updated,
            {
                "evidence_reliability": evidence_reliability,
                "target_confidence": new_confidence,
            },
        )

        return belief

    def update_agm(self, belief_id: str, method: UpdateMethod) -> Belief:
        """Update using AGM (Alchourron-Gardenfors-Makinson) framework.

        Supports expansion (adding new beliefs), revision (changing beliefs
        while maintaining consistency), and contraction (removing beliefs).

        Args:
            belief_id: Belief to operate on.
            method: AGM_EXTENSION, AGM_REVISION, or AGM_CONTRACTION.

        Returns:
            The affected belief.
        """
        belief = self.get(belief_id)

        if method == UpdateMethod.AGM_EXPANSION:
            # Expansion: simply accept the belief
            belief.status = BeliefStatus.ACTIVE
            belief.last_updated = time.time()

        elif method == UpdateMethod.AGM_REVISION:
            # Revision: check consistency and adjust conflicting beliefs
            conflicts = self.find_contradictions(belief_id)
            for conf in conflicts:
                # Downgrade conflicting beliefs
                other = self._beliefs[conf]
                other.confidence *= 0.5
                other.status = BeliefStatus.DISPUTED
            belief.last_updated = time.time()

        elif method == UpdateMethod.AGM_CONTRACTION:
            # Contraction: remove the belief while preserving minimal change
            belief.status = BeliefStatus.RETRACTED
            belief.confidence *= 0.3
            belief.last_updated = time.time()

        self._record_update(belief_id, method, belief.confidence, belief.confidence, {})
        return belief

    # ── Revision and contraction ───────────────────────────────────────

    def revise(self, belief_id: str, new_confidence: float) -> Belief:
        """Revise a belief to a new confidence while maintaining consistency.

        The minimal change principle is applied: only conflicting beliefs
        are adjusted, and they are adjusted minimally.

        Args:
            belief_id: Belief to revise.
            new_confidence: New confidence level.

        Returns:
            The revised belief.
        """
        belief = self.get(belief_id)
        old_confidence = belief.confidence
        belief.confidence = new_confidence
        belief.last_updated = time.time()

        # Find and resolve contradictions introduced by the revision
        contradictions = self.find_contradictions(belief_id)
        for contra_id in contradictions:
            contra = self._beliefs[contra_id]
            # Adjust contradictory belief towards the opposite
            shift = (new_confidence - old_confidence) * 0.5
            contra.confidence = max(0.0, min(1.0, contra.confidence - shift))
            contra.status = BeliefStatus.DISPUTED

        self._record_update(
            belief_id,
            UpdateMethod.AGM_REVISION,
            old_confidence,
            new_confidence,
            {
                "resolved_contradictions": len(contradictions),
            },
        )

        return belief

    def contract(self, belief_id: str) -> Belief:
        """Contract (remove/weaken) a belief using minimal change.

        Args:
            belief_id: Belief to contract.

        Returns:
            The contracted belief.
        """
        belief = self.get(belief_id)
        belief.status = BeliefStatus.RETRACTED
        belief.confidence = max(0.0, belief.confidence - 0.3)
        belief.last_updated = time.time()

        self._record_update(
            belief_id, UpdateMethod.AGM_CONTRACTION, belief.confidence + 0.3, belief.confidence, {}
        )

        return belief

    def expand(self, domain: str, statement: str, confidence: float = 0.5) -> Belief:
        """Expand the belief set with a new belief (AGM expansion).

        Args:
            domain: Knowledge domain.
            statement: The belief statement.
            confidence: Initial confidence.

        Returns:
            The new belief.
        """
        return self.create_belief(
            domain=domain,
            statement=statement,
            confidence=confidence,
            source=BeliefSource.LEARNED,
        )

    # ── Consistency ────────────────────────────────────────────────────

    def find_contradictions(self, belief_id: str) -> list[str]:
        """Find beliefs that contradict a given belief.

        Uses keyword negation detection (presence of opposing keywords
        in statements) as a heuristic for contradiction.

        Args:
            belief_id: The belief to check.

        Returns:
            List of contradictory belief IDs.
        """
        belief = self._beliefs.get(belief_id)
        if not belief:
            return []

        contradictions: list[str] = []
        statement_words = set(belief.statement.lower().split())

        # Negation words that indicate contradiction
        negation_pairs = [
            ({"always", "must"}, {"never", "must", "not"}),
            ({"good", "effective", "best"}, {"bad", "poor", "worst"}),
            ({"increase", "rise", "grow"}, {"decrease", "fall", "decline"}),
            ({"fast", "quick", "rapid"}, {"slow", "gradual"}),
        ]

        for other_id, other in self._beliefs.items():
            if other_id == belief_id or other.status == BeliefStatus.RETRACTED:
                continue

            if other.domain != belief.domain:
                continue

            other_words = set(other.statement.lower().split())
            overlap = statement_words & other_words

            # Check if the non-overlapping parts contain opposing keywords
            for pos_set, neg_set in negation_pairs:
                s_pos = statement_words & pos_set
                o_pos = other_words & pos_set
                s_neg = statement_words & neg_set
                o_neg = other_words & neg_set

                # Contradiction: one says positive, other says negative
                if (s_pos and o_neg) or (s_neg and o_pos):
                    if overlap and belief.confidence > 0.3 and other.confidence > 0.3:
                        contradictions.append(other_id)
                        break

        return contradictions

    def is_consistent(self) -> bool:
        """Check if the entire belief system is consistent."""
        for belief_id in self._beliefs:
            if self.find_contradictions(belief_id):
                return False
        return True

    # ── Conditional probabilities ──────────────────────────────────────

    def set_conditional(self, cause: str, effect: str, probability: float) -> None:
        """Set a conditional probability P(effect | cause).

        Args:
            cause: The causing belief/event.
            effect: The resulting belief/event.
            probability: P(effect | cause).
        """
        key = (cause, effect)
        if key in self._conditionals:
            existing = self._conditionals[key]
            existing.evidence_count += 1
            # Update as a weighted average
            existing.probability = (
                existing.probability * (existing.evidence_count - 1) + probability
            ) / existing.evidence_count
        else:
            self._conditionals[key] = ConditionalProbability(
                cause=cause, effect=effect, probability=probability, evidence_count=1
            )

    def get_conditional(self, cause: str, effect: str) -> float:
        """Get P(effect | cause).

        Returns:
            Conditional probability, or 0.5 if unknown.
        """
        entry = self._conditionals.get((cause, effect))
        return entry.probability if entry else 0.5

    # ── Belief sets ────────────────────────────────────────────────────

    def create_set(self, name: str, belief_ids: list[str]) -> BeliefSet:
        """Create a named belief set.

        Args:
            name: Set name.
            belief_ids: Beliefs to include.

        Returns:
            The created belief set.
        """
        bset = BeliefSet(name=name, beliefs=belief_ids)
        self._sets[bset.set_id] = bset
        return bset

    def get_set(self, set_id: str) -> BeliefSet | None:
        """Get a belief set by ID."""
        return self._sets.get(set_id)

    # ── History ────────────────────────────────────────────────────────

    def _record_update(
        self,
        belief_id: str,
        method: UpdateMethod,
        old_confidence: float,
        new_confidence: float,
        details: dict[str, Any],
    ) -> None:
        """Record an update in the history."""
        self._update_history.append(
            {
                "belief_id": belief_id,
                "method": method.name,
                "old_confidence": old_confidence,
                "new_confidence": new_confidence,
                "timestamp": time.time(),
                "details": details,
            }
        )

    def get_update_history(self, belief_id: str, limit: int = 50) -> list[dict[str, Any]]:
        """Get update history for a specific belief."""
        return [entry for entry in self._update_history if entry["belief_id"] == belief_id][-limit:]

    # ── Statistics ─────────────────────────────────────────────────────

    @property
    def belief_count(self) -> int:
        """Total number of beliefs."""
        return len(self._beliefs)

    @property
    def active_count(self) -> int:
        """Number of active beliefs."""
        return len(self.get_active())

    @property
    def domain_count(self) -> int:
        """Number of distinct domains."""
        return len(self._domains)

    @property
    def stats(self) -> dict[str, Any]:
        """Get belief system statistics."""
        by_source: dict[str, int] = {}
        by_domain: dict[str, int] = {}
        for b in self._beliefs.values():
            by_source[b.source.name] = by_source.get(b.source.name, 0) + 1
            by_domain[b.domain] = by_domain.get(b.domain, 0) + 1

        confidences = [b.confidence for b in self._beliefs.values()]
        return {
            "total_beliefs": self.belief_count,
            "active_beliefs": self.active_count,
            "domains": by_domain,
            "by_source": by_source,
            "avg_confidence": float(np.mean(confidences)) if confidences else 0.0,
            "consistent": self.is_consistent(),
            "conditionals": len(self._conditionals),
            "sets": len(self._sets),
            "total_updates": len(self._update_history),
        }
