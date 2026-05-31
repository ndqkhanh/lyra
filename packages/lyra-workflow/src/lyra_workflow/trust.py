"""
Attention Trust (A-Trust) — weighted inter-agent message routing via Gricean trust dimensions.

Implements the Attention-based Trust Management protocol (ACL 2026 Main):
agents weight incoming messages by trust scores rather than treating all messages
equally. Six orthogonal trust dimensions derived from Grice's communication theory:

1. **Quality**: Is the message factually accurate and verifiable?
2. **Quantity**: Is the message appropriately detailed (not too terse, not too verbose)?
3. **Relevance**: Does the message address the current context or task?
4. **Manner**: Is the message clear, well-structured, and unambiguous?
5. **Sincerity**: Does the message reflect the agent's genuine belief (no deception)?
6. **Competence**: Does the agent have the capability to produce this message reliably?

Integration with existing AVP:
- ``CriticVerdict.confidence`` is a scalar; A-Trust extends it to a 6-dimension vector.
- ``TrustWeightedRouter`` wraps agent message routing with trust-based weighting,
  complementing the AdversarialVerifier's consensus mechanism.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from enum import Enum
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# TrustDimension — 6 Gricean dimensions
# ---------------------------------------------------------------------------


class TrustDimension(str, Enum):
    """Six Gricean trust dimensions for inter-agent message evaluation.

    Based on Grice's maxims of communication, adapted for multi-agent trust:

    - **QUALITY**: Truthfulness and factual accuracy of the message.
    - **QUANTITY**: Appropriate level of detail (not too terse, not too verbose).
    - **RELEVANCE**: How well the message addresses the current task or context.
    - **MANNER**: Clarity, structure, and lack of ambiguity.
    - **SINCERITY**: Whether the message reflects genuine belief (no deception).
    - **COMPETENCE**: Whether the agent has the capability to produce a reliable message.
    """

    QUALITY = "quality"
    QUANTITY = "quantity"
    RELEVANCE = "relevance"
    MANNER = "manner"
    SINCERITY = "sincerity"
    COMPETENCE = "competence"


# ---------------------------------------------------------------------------
# TrustScore — 6 Gricean dimensions
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TrustScore:
    """A 6-dimensional trust score for an agent message.

    Each dimension is a float in [0.0, 1.0] where 0.0 = no trust and
    1.0 = complete trust. Dimensions are derived from Grice's maxims.

    Attributes:
        quality: Factual accuracy and verifiability of the message.
        quantity: Appropriate level of detail (not too terse, not too verbose).
        relevance: How well the message addresses the current context/task.
        manner: Clarity, structure, and unambiguity of the message.
        sincerity: Whether the message reflects the agent's genuine belief.
        competence: Whether the agent has the capability to produce a reliable message.
    """

    quality: float = 0.5
    quantity: float = 0.5
    relevance: float = 0.5
    manner: float = 0.5
    sincerity: float = 0.5
    competence: float = 0.5

    def __post_init__(self) -> None:
        """Clamp all dimensions to [0.0, 1.0]."""
        for dim in ("quality", "quantity", "relevance", "manner", "sincerity", "competence"):
            val = getattr(self, dim)
            if not 0.0 <= val <= 1.0:
                object.__setattr__(self, dim, max(0.0, min(1.0, val)))

    @property
    def overall(self) -> float:
        """Aggregate trust score — geometric mean of all six dimensions.

        Geometric mean ensures that a single near-zero dimension drags the
        overall score down significantly (unlike arithmetic mean which could
        hide a critical deficiency).
        """
        product = (
            self.quality * self.quantity * self.relevance
            * self.manner * self.sincerity * self.competence
        )
        return product ** (1.0 / 6.0)

    @property
    def dimensions(self) -> dict[str, float]:
        """Return all dimensions as a dict for serialization."""
        return {
            "quality": round(self.quality, 3),
            "quantity": round(self.quantity, 3),
            "relevance": round(self.relevance, 3),
            "manner": round(self.manner, 3),
            "sincerity": round(self.sincerity, 3),
            "competence": round(self.competence, 3),
        }

    def to_dict(self) -> dict[str, float]:
        """Full serialization including overall score."""
        d = self.dimensions
        d["overall"] = round(self.overall, 3)
        return d

    @staticmethod
    def equal(value: float = 0.7) -> TrustScore:
        """Create a TrustScore with all dimensions set to the same value."""
        return TrustScore(
            quality=value, quantity=value, relevance=value,
            manner=value, sincerity=value, competence=value,
        )

    @staticmethod
    def neutral() -> TrustScore:
        """Create a neutral TrustScore (all dimensions 0.5 — maximum uncertainty)."""
        return TrustScore.equal(0.5)


# ---------------------------------------------------------------------------
# TrustHistory — per-agent trust trajectory
# ---------------------------------------------------------------------------


@dataclass
class TrustHistory:
    """Tracks the trust trajectory of a single agent over time.

    Attributes:
        agent_id: Unique identifier for the agent.
        scores: Chronological list of TrustScores received.
        window_size: Maximum number of recent scores to retain (None = unlimited).
    """

    agent_id: str
    scores: list[TrustScore] = field(default_factory=list)
    window_size: int | None = 50

    def record(self, score: TrustScore) -> None:
        """Add a trust score observation.

        If window_size is set, older scores beyond the window are dropped
        so the history reflects only recent behavior.
        """
        self.scores.append(score)
        if self.window_size is not None and len(self.scores) > self.window_size:
            self.scores = self.scores[-self.window_size:]

    @property
    def current(self) -> TrustScore:
        """Most recent trust score, or neutral if no scores exist."""
        if not self.scores:
            return TrustScore.neutral()
        return self.scores[-1]

    @property
    def average(self) -> TrustScore:
        """Average trust score across the entire history (or neutral if empty)."""
        if not self.scores:
            return TrustScore.neutral()
        n = len(self.scores)
        return TrustScore(
            quality=sum(s.quality for s in self.scores) / n,
            quantity=sum(s.quantity for s in self.scores) / n,
            relevance=sum(s.relevance for s in self.scores) / n,
            manner=sum(s.manner for s in self.scores) / n,
            sincerity=sum(s.sincerity for s in self.scores) / n,
            competence=sum(s.competence for s in self.scores) / n,
        )

    @property
    def volatility(self) -> float:
        """Standard deviation of the overall trust score over time.

        High volatility indicates an agent whose trustworthiness fluctuates
        unpredictably — a signal for closer scrutiny.
        """
        if len(self.scores) < 2:
            return 0.0
        overalls = [s.overall for s in self.scores]
        mean = sum(overalls) / len(overalls)
        variance = sum((o - mean) ** 2 for o in overalls) / len(overalls)
        return math.sqrt(variance)

    @property
    def trend(self) -> float:
        """Simple linear trend of overall trust over the history.

        Positive = improving trust, negative = deteriorating trust.
        """
        if len(self.scores) < 2:
            return 0.0
        return self.scores[-1].overall - self.scores[0].overall

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict."""
        return {
            "agent_id": self.agent_id,
            "score_count": len(self.scores),
            "current": self.current.to_dict() if self.scores else None,
            "average": self.average.to_dict(),
            "volatility": round(self.volatility, 3),
            "trend": round(self.trend, 3),
        }


# ---------------------------------------------------------------------------
# AgentTrustProfile — per-agent per-dimension trust tracking
# ---------------------------------------------------------------------------


@dataclass
class AgentTrustProfile:
    """Tracks per-agent trust scores across all six dimensions over time.

    Maintains a separate ``TrustHistory`` for each Gricean dimension,
    enabling dimension-level analysis (e.g., "agent is factual but irrelevant").

    Attributes:
        agent_id: Unique identifier for the agent.
        dimension_histories: Map of dimension -> TrustHistory.
        window_size: Maximum number of recent scores per dimension.
    """

    agent_id: str
    dimension_histories: dict[TrustDimension, TrustHistory] = field(default_factory=dict)
    window_size: int = 50

    @classmethod
    def create(cls, agent_id: str, window_size: int = 50) -> AgentTrustProfile:
        """Create a profile with pre-initialized dimension histories."""
        profile = cls(agent_id=agent_id, window_size=window_size)
        for dim in TrustDimension:
            profile.dimension_histories[dim] = TrustHistory(
                agent_id=f"{agent_id}/{dim.value}",
                window_size=window_size,
            )
        return profile

    def record(self, score: TrustScore) -> None:
        """Record a trust score update, decomposing into per-dimension histories."""
        for dim in TrustDimension:
            val = getattr(score, dim.value)
            history = self.dimension_histories.setdefault(
                dim,
                TrustHistory(agent_id=f"{self.agent_id}/{dim.value}", window_size=self.window_size),
            )
            history.record(TrustScore.equal(val))

    @property
    def dimension_averages(self) -> dict[str, float]:
        """Per-dimension average trust scores over the tracked history."""
        return {
            dim.value: self.dimension_histories[dim].average.overall
            for dim in TrustDimension
        }

    @property
    def dimension_trends(self) -> dict[str, float]:
        """Per-dimension trust trend (positive = improving)."""
        return {
            dim.value: self.dimension_histories[dim].trend
            for dim in TrustDimension
        }

    @property
    def weakest_dimension(self) -> tuple[TrustDimension, float]:
        """Return the dimension with the lowest average trust score.

        Useful for targeted improvement: identifies the trust axis that
        most needs attention for this agent.
        """
        dim_scores = {
            dim: self.dimension_histories[dim].average.overall
            for dim in TrustDimension
        }
        worst = min(dim_scores, key=dim_scores.get)
        return worst, dim_scores[worst]

    @property
    def strongest_dimension(self) -> tuple[TrustDimension, float]:
        """Return the dimension with the highest average trust score."""
        dim_scores = {
            dim: self.dimension_histories[dim].average.overall
            for dim in TrustDimension
        }
        best = max(dim_scores, key=dim_scores.get)
        return best, dim_scores[best]

    def to_dict(self) -> dict[str, Any]:
        """Serialize profile to a plain dict."""
        return {
            "agent_id": self.agent_id,
            "dimension_averages": self.dimension_averages,
            "dimension_trends": self.dimension_trends,
            "weakest": self.weakest_dimension[0].value,
            "weakest_score": round(self.weakest_dimension[1], 3),
            "strongest": self.strongest_dimension[0].value,
            "strongest_score": round(self.strongest_dimension[1], 3),
        }


# ---------------------------------------------------------------------------
# TrustEvaluator — scores agent messages against trust dimensions
# ---------------------------------------------------------------------------


@dataclass
class TrustEvaluation:
    """Result of evaluating a single message against trust dimensions.

    Attributes:
        message_id: Unique identifier for the message.
        score: The computed TrustScore.
        breakdown: Optional human-readable reasoning per dimension.
        evaluator: Identifier for the evaluator (e.g. 'rule-based', 'critic-llm').
    """

    message_id: str
    score: TrustScore
    breakdown: dict[str, str] = field(default_factory=dict)
    evaluator: str = "rule-based"


class TrustEvaluator:
    """Evaluates agent messages against the six Gricean trust dimensions.

    Provides both a rule-based evaluator (for fast, zero-cost heuristic scoring)
    and an interface for LLM-powered critic evaluation.

    Usage::

        evaluator = TrustEvaluator()
        result = evaluator.evaluate(
            message_id="msg-1",
            content="The database connection pool has 32 connections.",
            agent_id="db-agent",
            context={"task": "audit database connections"},
        )
        print(result.score.overall)  # 0.0–1.0
    """

    # Heuristic thresholds for rule-based evaluation

    # Quality: keywords indicating factual content
    _QUALITY_INDICATORS: frozenset[str] = frozenset({
        "verified", "confirmed", "measured", "observed", "documented",
        "evidence", "source", "citation", "reference", "data shows",
        "according to", "found that", "demonstrates", "validated",
    })

    # Anti-quality: hedging or weasel words
    _QUALITY_ANTI_INDICATORS: frozenset[str] = frozenset({
        "maybe", "perhaps", "might", "could be", "possibly", "i think",
        "i believe", "not sure", "uncertain", "unclear",
    })

    # Quantity indicators
    _QUANTITY_BAD_SHORT: int = 10    # Fewer words than this = too terse
    _QUANTITY_BAD_LONG: int = 2000  # More words than this = too verbose

    # Relevance indicators: keywords that signal staying on topic
    _RELEVANCE_INDICATORS: frozenset[str] = frozenset({
        "therefore", "consequently", "as a result", "in conclusion",
        "regarding", "with respect to", "pertains to",
    })

    # Anti-relevance: topic drift signals
    _RELEVANCE_ANTI_INDICATORS: frozenset[str] = frozenset({
        "by the way", "incidentally", "unrelated", "off topic",
        "digression", "aside",
    })

    # Manner indicators: clarity signals
    _MANNER_INDICATORS: frozenset[str] = frozenset({
        "first", "second", "third", "finally", "in summary",
        "specifically", "notably", "importantly", "namely",
        "for example", "for instance", "in other words",
    })

    # Anti-manner: ambiguity signals
    _MANNER_ANTI_INDICATORS: frozenset[str] = frozenset({
        "etc", "and so on", "something like", "kind of", "sort of",
        "vague", "ambiguous", "unclear",
    })

    # Sincerity indicators
    _SINCERITY_INDICATORS: frozenset[str] = frozenset({
        "i confirmed", "i verified", "i checked", "i observed",
        "to the best of my knowledge", "honestly", "transparently",
    })

    # Anti-sincerity: hedging that may indicate deception
    _SINCERITY_ANTI_INDICATORS: frozenset[str] = frozenset({
        "truthfully", "to be honest", "honestly speaking",
        "i would never", "believe me",
    })

    def __init__(self, llm_evaluator: Callable[[str, str], TrustScore] | None = None) -> None:
        """
        Args:
            llm_evaluator: Optional callable that takes (message_content, context)
                and returns a TrustScore. If provided, ``evaluate_llm()`` uses it.
        """
        self._llm_evaluator = llm_evaluator

    def evaluate(
        self,
        message_id: str,
        content: str,
        agent_id: str = "",
        context: str = "",
    ) -> TrustEvaluation:
        """Rule-based heuristic evaluation of a message across all six dimensions.

        This is fast, zero-cost, and suitable for every-message screening.
        For deeper evaluation, use ``evaluate_llm()`` when LLM budget permits.
        """
        words = content.lower().split()
        word_count = len(words)

        quality = self._score_quality(content, words)
        quantity = self._score_quantity(word_count)
        relevance = self._score_relevance(content, words, context)
        manner = self._score_manner(content, words)
        sincerity = self._score_sincerity(content, words)
        competence = self._score_competence(content, words, agent_id)

        score = TrustScore(
            quality=quality,
            quantity=quantity,
            relevance=relevance,
            manner=manner,
            sincerity=sincerity,
            competence=competence,
        )

        breakdown = {
            "quality": self._qualitative(quality, "factual precision"),
            "quantity": self._qualitative(quantity, "information density"),
            "relevance": self._qualitative(relevance, "topic adherence"),
            "manner": self._qualitative(manner, "clarity"),
            "sincerity": self._qualitative(sincerity, "candor"),
            "competence": self._qualitative(competence, "domain capability"),
        }

        return TrustEvaluation(
            message_id=message_id,
            score=score,
            breakdown=breakdown,
            evaluator="rule-based",
        )

    def evaluate_llm(
        self,
        message_id: str,
        content: str,
        agent_id: str = "",
        context: str = "",
    ) -> TrustEvaluation:
        """LLM-powered evaluation of a message (if an LLM evaluator is configured).

        Falls back to rule-based evaluation if no LLM evaluator is set.
        """
        if self._llm_evaluator is None:
            return self.evaluate(message_id, content, agent_id, context)

        score = self._llm_evaluator(content, context)
        return TrustEvaluation(
            message_id=message_id,
            score=score,
            evaluator="llm",
        )

    # ── Per-dimension scoring ──────────────────────────────────────

    def _score_quality(self, content: str, words: list[str]) -> float:
        """Score factual quality: evidence indicators vs hedging."""
        has_evidence = sum(1 for ind in self._QUALITY_INDICATORS if ind in content.lower())
        has_hedging = sum(1 for anti in self._QUALITY_ANTI_INDICATORS if anti in content.lower())

        # Start at neutral
        score = 0.5
        # Boost for evidence (max +0.4 from 4+ indicators)
        score += min(has_evidence * 0.1, 0.4)
        # Penalize for hedging (max -0.4)
        score -= min(has_hedging * 0.15, 0.4)
        return max(0.0, min(1.0, score))

    def _score_quantity(self, word_count: int) -> float:
        """Score appropriate information density.

        Follows an inverted-U curve: too few words = terse/unhelpful,
        too many = verbose/unfocused.
        """
        if word_count < self._QUANTITY_BAD_SHORT:
            return max(0.0, word_count / self._QUANTITY_BAD_SHORT)

        if word_count <= 200:
            return 1.0  # Sweet spot: 10-200 words

        if word_count <= self._QUANTITY_BAD_LONG:
            # Linear decay from 1.0 to 0.5
            return 1.0 - 0.5 * (word_count - 200) / (self._QUANTITY_BAD_LONG - 200)

        # Beyond 2000 words: rapidly diminishing
        decay = min(0.5 + 0.5 * (word_count - self._QUANTITY_BAD_LONG) / 1000, 1.0)
        return max(0.0, 1.0 - decay)

    def _score_relevance(self, content: str, words: list[str], context: str) -> float:
        """Score topic relevance by keyword overlap and drift signals."""
        score = 0.5

        # Boost for relevance-indicating phrases
        relevance_matches = sum(
            1 for ind in self._RELEVANCE_INDICATORS if ind in content.lower()
        )
        score += min(relevance_matches * 0.1, 0.3)

        # Penalize for topic drift
        drift_matches = sum(
            1 for anti in self._RELEVANCE_ANTI_INDICATORS if anti in content.lower()
        )
        score -= min(drift_matches * 0.2, 0.4)

        # Cross-reference with context words for topical alignment
        if context:
            context_words = set(context.lower().split())
            if words:
                overlap = sum(1 for w in words if w in context_words)
                topicality = min(overlap / max(len(words), 1) * 5.0, 0.2)
                score += topicality

        return max(0.0, min(1.0, score))

    def _score_manner(self, content: str, words: list[str]) -> float:
        """Score clarity and structure."""
        score = 0.5

        # Boost for structural indicators
        structure_matches = sum(
            1 for ind in self._MANNER_INDICATORS if ind in content.lower()
        )
        score += min(structure_matches * 0.1, 0.3)

        # Penalize for ambiguity
        ambiguity_matches = sum(
            1 for anti in self._MANNER_ANTI_INDICATORS if anti in content.lower()
        )
        score -= min(ambiguity_matches * 0.2, 0.4)

        # Length penalty for walls of text (poor manner)
        if len(words) > 500 and sum(len(w) for w in words) / max(len(words), 1) > 6:
            score -= 0.1  # Long, dense text likely lacks structure

        return max(0.0, min(1.0, score))

    def _score_sincerity(self, content: str, words: list[str]) -> float:
        """Score sincerity: genuine indicators vs protest-too-much signals."""
        score = 0.6  # Slight positive prior (agents are presumed sincere)

        sincerity_matches = sum(
            1 for ind in self._SINCERITY_INDICATORS if ind in content.lower()
        )
        score += min(sincerity_matches * 0.1, 0.3)

        # Penalize for excessive protestations of honesty
        anti_matches = sum(
            1 for anti in self._SINCERITY_ANTI_INDICATORS if anti in content.lower()
        )
        score -= min(anti_matches * 0.2, 0.4)

        return max(0.0, min(1.0, score))

    def _score_competence(self, content: str, words: list[str], agent_id: str) -> float:
        """Score agent competence based on message characteristics.

        Competence is inferred from domain-specific language, precision,
        and consistency. In production this would be informed by the
        agent's historical performance.
        """
        score = 0.5

        # Technical precision: presence of numbers, data, code-like tokens
        numeric_tokens = sum(1 for w in words if any(c.isdigit() for c in w))
        if words:
            precision = min(numeric_tokens / max(len(words), 1) * 10.0, 0.3)
            score += precision

        # Penalize for explicit uncertainty about own capability
        uncertainty_phrases = {"i don't know", "i'm not capable", "i cannot", "i'm unable"}
        has_uncertainty = any(phrase in content.lower() for phrase in uncertainty_phrases)
        if has_uncertainty:
            score -= 0.3

        return max(0.0, min(1.0, score))

    @staticmethod
    def _qualitative(value: float, label: str) -> str:
        """Map a numeric score to a qualitative label."""
        if value >= 0.9:
            return f"excellent {label}"
        if value >= 0.7:
            return f"good {label}"
        if value >= 0.5:
            return f"adequate {label}"
        if value >= 0.3:
            return f"poor {label}"
        return f"critical {label} deficiency"


# ---------------------------------------------------------------------------
# TrustWeightedRouter — trust-based inter-agent message routing
# ---------------------------------------------------------------------------


@dataclass
class WeightedMessage:
    """A message with its computed trust weight.

    Attributes:
        message_id: Unique message identifier.
        sender_id: The originating agent.
        content: The message text.
        trust_score: The evaluated trust score for this message.
        weight: The final routing weight (trust score * any additional factor).
        metadata: Arbitrary key-value metadata.
    """

    message_id: str
    sender_id: str
    content: str
    trust_score: TrustScore
    weight: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)


class TrustWeightedRouter:
    """Routes inter-agent messages with trust-based weighting.

    Maintains per-agent trust histories, evaluates incoming messages against
    the six Gricean trust dimensions, and computes routing weights. Messages
    from low-trust agents are downweighted; messages from high-trust agents
    are amplified.

    Integrates with the existing AVP by extending CriticVerdict's scalar
    ``confidence`` into the full 6-dimension TrustScore vector.

    Usage::

        router = TrustWeightedRouter(TrustEvaluator())
        weighted = router.route(
            message_id="msg-42",
            content="The auth module has a timing side-channel at line 203.",
            sender_id="security-agent",
        )
        # weighted.weight is < 1.0 if trust is low
        routing_payload = {
            "content": weighted.content,
            "trust_weight": weighted.weight,
            "trust_breakdown": weighted.trust_score.dimensions,
        }
    """

    def __init__(
        self,
        evaluator: TrustEvaluator | None = None,
        default_weight: float = 1.0,
        min_weight: float = 0.05,
    ) -> None:
        """
        Args:
            evaluator: TrustEvaluator instance. If None, a default rule-based
                evaluator is created.
            default_weight: Default routing weight for messages from unknown agents.
            min_weight: Minimum routing weight (never fully silence an agent).
        """
        self._evaluator = evaluator or TrustEvaluator()
        self._histories: dict[str, TrustHistory] = {}
        self._profiles: dict[str, AgentTrustProfile] = {}
        self._default_weight = default_weight
        self._min_weight = min_weight
        self._routed_count: int = 0

    # ── Public API ─────────────────────────────────────────────────

    def route(
        self,
        message_id: str,
        content: str,
        sender_id: str,
        context: str = "",
    ) -> WeightedMessage:
        """Evaluate and route a message with trust-based weighting.

        1. Evaluates the message against the six trust dimensions.
        2. Records the evaluation in the sender's trust history and profile.
        3. Computes the routing weight from the historical trust trajectory.
        4. Returns a WeightedMessage with the final weight.

        Args:
            message_id: Unique identifier for this message.
            content: The message content to evaluate.
            sender_id: The agent that sent this message.
            context: Optional task context for relevance scoring.

        Returns:
            A WeightedMessage with the computed trust weight.
        """
        self._routed_count += 1

        # Evaluate
        evaluation = self._evaluator.evaluate(
            message_id=message_id,
            content=content,
            agent_id=sender_id,
            context=context,
        )

        # Record in history
        history = self._get_or_create_history(sender_id)
        history.record(evaluation.score)

        # Record in per-dimension profile
        profile = self._get_or_create_profile(sender_id)
        profile.record(evaluation.score)

        # Compute weight
        weight = self._compute_weight(sender_id, history, evaluation)

        return WeightedMessage(
            message_id=message_id,
            sender_id=sender_id,
            content=content,
            trust_score=evaluation.score,
            weight=weight,
            metadata={
                "breakdown": evaluation.breakdown,
                "evaluator": evaluation.evaluator,
                "volatility": history.volatility,
                "trend": history.trend,
                "weakest_dimension": profile.weakest_dimension[0].value,
                "strongest_dimension": profile.strongest_dimension[0].value,
            },
        )

    def route_batch(
        self,
        messages: list[dict[str, str]],
        context: str = "",
    ) -> list[WeightedMessage]:
        """Evaluate and weight a batch of messages.

        Each dict must have keys: ``message_id``, ``content``, ``sender_id``.

        Returns messages sorted by weight descending (highest trust first).
        """
        weighted = []
        for msg in messages:
            weighted.append(self.route(
                message_id=msg["message_id"],
                content=msg["content"],
                sender_id=msg["sender_id"],
                context=context,
            ))
        weighted.sort(key=lambda wm: wm.weight, reverse=True)
        return weighted

    def get_history(self, agent_id: str) -> TrustHistory | None:
        """Return the trust history for a given agent, or None."""
        return self._histories.get(agent_id)

    def get_profile(self, agent_id: str) -> AgentTrustProfile | None:
        """Return the per-dimension trust profile for a given agent, or None."""
        return self._profiles.get(agent_id)

    def get_all_histories(self) -> dict[str, TrustHistory]:
        """Return a copy of all trust histories."""
        return dict(self._histories)

    def get_all_profiles(self) -> dict[str, AgentTrustProfile]:
        """Return a copy of all agent trust profiles."""
        return dict(self._profiles)

    @property
    def stats(self) -> dict[str, Any]:
        """Aggregate routing statistics."""
        histories = self.get_all_histories()
        profiles = self.get_all_profiles()
        return {
            "routed_total": self._routed_count,
            "agents_tracked": len(histories),
            "histories": {aid: h.to_dict() for aid, h in histories.items()},
            "profiles": {aid: p.to_dict() for aid, p in profiles.items()},
            "average_trust": (
                sum(h.average.overall for h in histories.values()) / len(histories)
                if histories else 0.0
            ),
        }

    # ── Weight computation ─────────────────────────────────────────

    def _compute_weight(
        self,
        agent_id: str,
        history: TrustHistory,
        evaluation: TrustEvaluation,
    ) -> float:
        """Compute the final routing weight from trust history.

        Weight is the geometric mean of:
        1. The current message's overall trust score
        2. The agent's average trust score (historical baseline)
        3. A volatility penalty (high volatility = less reliable)

        Clamped to [min_weight, 1.0].
        """
        current_overall = evaluation.score.overall
        avg_overall = history.average.overall

        # Volatility penalty: subtract up to 0.2 for high volatility
        volatility_penalty = min(history.volatility * 0.5, 0.2)

        raw_weight = (current_overall * avg_overall) ** 0.5 - volatility_penalty
        return max(self._min_weight, min(1.0, raw_weight))

    def _get_or_create_history(self, agent_id: str) -> TrustHistory:
        if agent_id not in self._histories:
            self._histories[agent_id] = TrustHistory(agent_id=agent_id)
        return self._histories[agent_id]

    def _get_or_create_profile(self, agent_id: str) -> AgentTrustProfile:
        if agent_id not in self._profiles:
            self._profiles[agent_id] = AgentTrustProfile.create(agent_id=agent_id)
        return self._profiles[agent_id]


# ---------------------------------------------------------------------------
# Integration helpers — bridge AVP CriticVerdict to A-Trust
# ---------------------------------------------------------------------------


def trust_from_critic_verdicts(verdicts: list[dict[str, Any]]) -> TrustScore:
    """Derive a TrustScore from AVP critic verdicts.

    Maps the AVP's confidence and evidence_tier fields to Gricean dimensions.

    If any verdict dict contains a ``trust_dimensions`` key (from
    CriticVerdict.trust_dimensions), those per-dimension scores are used
    directly for the applicable dimensions (quality, quantity, relevance,
    manner, sincerity, competence), with confidence/consensus filling gaps.

    - **quality**: Average of all critic confidence scores.
    - **competence**: evidence_tier mapping (A=1.0, B=0.8, C=0.6, D=0.3).
    - **sincerity**: Consistency among critic votes (low disagreement = high sincerity).
    - **relevance, quantity, manner**: Set to neutral (0.5) — AVP critics do not
      evaluate these dimensions directly; they must be filled by the TrustEvaluator.

    Args:
        verdicts: List of AVP verdict dicts (from AdversarialVerifier.verify()).

    Returns:
        A TrustScore integrating AVP critic signals.
    """
    if not verdicts:
        return TrustScore.neutral()

    # Check if any verdict has direct trust_dimensions (from CriticVerdict field)
    direct_td = _extract_direct_trust_dimensions(verdicts)
    if direct_td:
        return direct_td

    # Fallback: derive from confidence and evidence_tier
    # Quality: mean confidence
    confidences = [v.get("confidence", 0.5) for v in verdicts]
    quality = sum(confidences) / len(confidences)

    # Competence: best evidence tier among accepting critics
    evidence_tiers = {"A": 1.0, "B": 0.8, "C": 0.6, "D": 0.3}
    tier_scores = [
        evidence_tiers.get(v.get("evidence_tier", "C"), 0.6)
        for v in verdicts
    ]
    competence = max(tier_scores)

    # Sincerity: consensus consistency
    verdict_values = [v.get("verdict") for v in verdicts if v.get("verdict")]
    unique_verdicts = len(set(verdict_values))
    if unique_verdicts <= 1:
        sincerity = 0.9  # Full consensus = high sincerity
    elif unique_verdicts == 2:
        sincerity = 0.6  # Partial split
    else:
        sincerity = 0.3  # 3-way split = low sincerity

    return TrustScore(
        quality=quality,
        quantity=0.5,
        relevance=0.5,
        manner=0.5,
        sincerity=sincerity,
        competence=competence,
    )


def _extract_direct_trust_dimensions(verdicts: list[dict[str, Any]]) -> TrustScore | None:
    """Extract trust dimensions directly from verdicts with trust_dimensions field.

    Returns a TrustScore if at least one verdict has the field, else None.
    Averages per-dimension scores across all verdicts that provide them.
    """
    verdicts_with_td = [
        v for v in verdicts
        if isinstance(v.get("trust_dimensions"), dict)
    ]
    if not verdicts_with_td:
        return None

    # Average per-dimension values across all verdicts that provide them
    dim_sums: dict[str, float] = {}
    dim_counts: dict[str, int] = {}
    for v in verdicts_with_td:
        td = v["trust_dimensions"]
        for dim in ("quality", "quantity", "relevance", "manner", "sincerity", "competence"):
            val = td.get(dim)
            if val is not None and isinstance(val, (int, float)):
                dim_sums[dim] = dim_sums.get(dim, 0.0) + float(val)
                dim_counts[dim] = dim_counts.get(dim, 0) + 1

    if not dim_sums:
        return None

    return TrustScore(
        quality=dim_sums.get("quality", 0.5) / max(dim_counts.get("quality", 1), 1),
        quantity=dim_sums.get("quantity", 0.5) / max(dim_counts.get("quantity", 1), 1),
        relevance=dim_sums.get("relevance", 0.5) / max(dim_counts.get("relevance", 1), 1),
        manner=dim_sums.get("manner", 0.5) / max(dim_counts.get("manner", 1), 1),
        sincerity=dim_sums.get("sincerity", 0.5) / max(dim_counts.get("sincerity", 1), 1),
        competence=dim_sums.get("competence", 0.5) / max(dim_counts.get("competence", 1), 1),
    )
