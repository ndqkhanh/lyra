"""
Lyra Interpretability - Agent interpretability and decision tracing.

This package provides:
- Decision tracing with reasoning steps
- Feature attribution and importance scoring
- Saliency maps for token-level analysis
- Counterfactual explanations
- Comprehensive interpretability reports
- Natural language decision explanations
"""

from __future__ import annotations

import logging
import uuid
from collections import Counter
from dataclasses import dataclass
from enum import Enum
from time import time
from typing import Any

logger = logging.getLogger(__name__)

__version__ = "0.1.0"

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class AttributionMethod(str, Enum):
    """Supported feature attribution methods."""

    GRADIENT = "gradient"
    INTEGRATED_GRADIENTS = "integrated_gradients"
    SHAPLEY = "shapley"
    LIME = "lime"
    ATTENTION = "attention"
    OCCLUSION = "occlusion"


class ExplanationType(str, Enum):
    """Types of explanation an interpretability engine can produce."""

    DECISION_RATIONALE = "decision_rationale"
    FEATURE_IMPORTANCE = "feature_importance"
    COUNTERFACTUAL = "counterfactual"
    CHAIN_OF_THOUGHT = "chain_of_thought"
    CONFIDENCE_BREAKDOWN = "confidence_breakdown"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FeatureAttribution:
    """A single feature attribution with its importance score.

    Parameters
    ----------
    feature : str
        The name of the feature being attributed.
    score : float
        Importance score for this feature.
    method : str
        The attribution method used.
    rank : int
        Rank of this feature among all attributed features (1 = most important).
    evidence : str
        Optional evidence or reasoning supporting this attribution.
    """

    feature: str
    score: float
    method: str
    rank: int
    evidence: str = ""


@dataclass(frozen=True)
class DecisionTrace:
    """A complete record of an agent's decision and its reasoning chain.

    Parameters
    ----------
    decision_id : str
        Unique identifier for this decision.
    agent_id : str
        Identifier of the agent that made the decision.
    timestamp : float
        Unix timestamp when the decision was recorded.
    input_summary : str
        Summary of the input that triggered the decision.
    reasoning_steps : tuple[str, ...]
        Ordered list of reasoning steps leading to the decision.
    key_factors : tuple[FeatureAttribution, ...]
        Key factors that influenced the decision, with attributions.
    confidence : float
        Confidence score for the decision (0.0 to 1.0).
    alternatives_considered : tuple[str, ...]
        Alternative decisions that were considered.
    """

    decision_id: str
    agent_id: str
    timestamp: float
    input_summary: str
    reasoning_steps: tuple[str, ...]
    key_factors: tuple[FeatureAttribution, ...]
    confidence: float
    alternatives_considered: tuple[str, ...]


@dataclass(frozen=True)
class CounterfactualExplanation:
    """An explanation of what would change under a different scenario.

    Parameters
    ----------
    original_decision : str
        The decision that was actually made.
    counterfactual_scenario : str
        Description of the modified scenario.
    alternative_decision : str
        What the alternative decision would be in the counterfactual scenario.
    confidence_delta : float
        Change in confidence between original and alternative decision.
    key_changed_factors : tuple[str, ...]
        The factors that changed to produce this counterfactual.
    """

    original_decision: str
    counterfactual_scenario: str
    alternative_decision: str
    confidence_delta: float
    key_changed_factors: tuple[str, ...]


@dataclass(frozen=True)
class SaliencyMap:
    """Token-level saliency scores for a piece of text.

    Parameters
    ----------
    target_text : str
        The original text that was analyzed.
    tokens : tuple[str, ...]
        Tokenized form of the target text.
    scores : tuple[float, ...]
        Saliency score for each token.
    method : str
        The saliency computation method used.
    normalized : bool
        Whether the scores have been normalized to [0, 1].
    """

    target_text: str
    tokens: tuple[str, ...]
    scores: tuple[float, ...]
    method: str
    normalized: bool = True


@dataclass(frozen=True)
class InterpretabilityReport:
    """Aggregated interpretability report for an agent.

    Parameters
    ----------
    agent_id : str
        Identifier of the agent this report covers.
    timestamp : float
        Unix timestamp when the report was generated.
    decision_traces : tuple[DecisionTrace, ...]
        All decision traces included in this report.
    top_attributions : tuple[FeatureAttribution, ...]
        Top feature attributions across all decisions.
    counterfactuals : tuple[CounterfactualExplanation, ...]
        Counterfactual explanations generated for this agent.
    overall_transparency_score : float
        Overall transparency score for the agent (0.0 to 1.0).
    """

    agent_id: str
    timestamp: float
    decision_traces: tuple[DecisionTrace, ...]
    top_attributions: tuple[FeatureAttribution, ...]
    counterfactuals: tuple[CounterfactualExplanation, ...]
    overall_transparency_score: float


@dataclass(frozen=True)
class InterpretabilityConfig:
    """Configuration for the interpretability engine.

    Parameters
    ----------
    attribution_method : str
        Default attribution method to use.
    max_traces : int
        Maximum number of decision traces to retain.
    saliency_enabled : bool
        Whether saliency computation is enabled.
    counterfactual_enabled : bool
        Whether counterfactual generation is enabled.
    confidence_threshold : float
        Minimum confidence threshold for recording decisions.
    max_alternatives : int
        Maximum number of alternatives to consider per decision.
    """

    attribution_method: str = "SHAPLEY"
    max_traces: int = 1000
    saliency_enabled: bool = True
    counterfactual_enabled: bool = True
    confidence_threshold: float = 0.5
    max_alternatives: int = 5


# ---------------------------------------------------------------------------
# Domain keywords used by attributions and saliency
# ---------------------------------------------------------------------------

_DOMAIN_KEYWORDS: list[str] = [
    "safety",
    "security",
    "performance",
    "accuracy",
    "speed",
    "cost",
    "latency",
    "reliability",
    "scalability",
    "quality",
    "efficiency",
    "robustness",
    "usability",
    "privacy",
    "compliance",
    "maintainability",
    "availability",
    "throughput",
    "fidelity",
    "coverage",
]


def _tokenize(text: str) -> list[str]:
    """Split text into lowercase tokens on whitespace and common punctuation."""
    import re

    return [t for t in re.split(r"[,\s;:.!?()\[\]{}]+", text.lower()) if t]


def _score_keyword_density(tokens: list[str]) -> dict[str, float]:
    """Score each domain keyword found in tokens based on frequency and position.

    The score formula is:
        keyword_count * (1.0 - 0.1 * avg_position_ratio)

    where avg_position_ratio is the average normalized position of each
    occurrence (0.0 = first token, 1.0 = last token).  Earlier occurrences
    are weighted higher.
    """
    keyword_counter: dict[str, int] = Counter()
    position_sums: dict[str, float] = {}
    position_counts: dict[str, int] = {}

    for idx, token in enumerate(tokens):
        for kw in _DOMAIN_KEYWORDS:
            if kw in token or token in kw:
                keyword_counter[kw] += 1
                position_sums.setdefault(kw, 0.0)
                position_sums[kw] += idx
                position_counts.setdefault(kw, 0)
                position_counts[kw] += 1

    scores: dict[str, float] = {}
    num_tokens = max(len(tokens), 1)
    for kw, count in keyword_counter.items():
        avg_pos = position_sums.get(kw, 0.0) / max(position_counts.get(kw, 1), 1)
        pos_factor = 1.0 - 0.1 * (avg_pos / num_tokens)
        scores[kw] = count * pos_factor

    return scores


# ---------------------------------------------------------------------------
# InterpretabilityEngine
# ---------------------------------------------------------------------------


class InterpretabilityEngine:
    """Engine for tracing, attributing, and explaining agent decisions.

    The engine maintains internal stores of decision traces, counterfactuals,
    and aggregated statistics.  All public methods are designed to produce
    meaningful output even with stub-level heuristics.

    Parameters
    ----------
    config : InterpretabilityConfig | None
        Engine configuration.  Defaults are used when ``None``.
    """

    def __init__(self, config: InterpretabilityConfig | None = None) -> None:
        self._config = config or InterpretabilityConfig()
        self._traces: list[DecisionTrace] = []
        self._counterfactuals: list[CounterfactualExplanation] = []

    # -- Public API ---------------------------------------------------------

    def trace_decision(
        self,
        agent_id: str,
        input_text: str,
        reasoning: list[str],
        decision: str,
        confidence: float,
        alternatives: list[str] | None = None,
    ) -> DecisionTrace:
        """Record a full decision trace with reasoning steps.

        Parameters
        ----------
        agent_id : str
            Identifier of the agent making the decision.
        input_text : str
            The input that triggered this decision.
        reasoning : list[str]
            Ordered list of reasoning steps.
        decision : str
            The decision that was made.
        confidence : float
            Confidence score for the decision (0.0 to 1.0).
        alternatives : list[str] | None
            Alternative decisions that were considered.

        Returns
        -------
        DecisionTrace
            The newly created decision trace.
        """
        input_summary = (
            input_text[:100] + "..." if len(input_text) > 100 else input_text
        )
        reasoning_steps = tuple(reasoning)
        alt_tuple = tuple(
            (alternatives or [])[: self._config.max_alternatives]
        )

        # Derive feature attributions from the input text
        attributions = self.attribute_features(decision)
        key_factors = tuple(attributions)

        trace = DecisionTrace(
            decision_id=str(uuid.uuid4()),
            agent_id=agent_id,
            timestamp=time(),
            input_summary=input_summary,
            reasoning_steps=reasoning_steps,
            key_factors=key_factors,
            confidence=min(max(confidence, 0.0), 1.0),
            alternatives_considered=alt_tuple,
        )

        if confidence >= self._config.confidence_threshold:
            self._traces.append(trace)
            # Enforce max_traces cap
            if len(self._traces) > self._config.max_traces:
                self._traces = self._traces[-self._config.max_traces :]

        return trace

    def attribute_features(
        self,
        decision_text: str,
        method: str | None = None,
    ) -> list[FeatureAttribution]:
        """Score features based on domain keyword presence and position.

        Tokens in *decision_text* are matched against a curated set of
        domain keywords.  Each keyword found becomes a ``FeatureAttribution``
        with a score derived from its frequency and the position of its
        earliest occurrence (earlier tokens score higher).

        Parameters
        ----------
        decision_text : str
            The decision text to analyse.
        method : str | None
            Attribution method label.  Defaults to the engine's configured
            method.

        Returns
        -------
        list[FeatureAttribution]
            Ranked list of feature attributions, highest score first.
        """
        method = method or self._config.attribution_method
        tokens = _tokenize(decision_text)
        keyword_scores = _score_keyword_density(tokens)

        if not keyword_scores:
            return []

        # Build attributions sorted by descending score
        sorted_kws = sorted(keyword_scores.items(), key=lambda x: -x[1])
        attributions = [
            FeatureAttribution(
                feature=kw,
                score=score,
                method=method,
                rank=rank + 1,
                evidence=f"Keyword '{kw}' found with density score {score:.3f}",
            )
            for rank, (kw, score) in enumerate(sorted_kws)
        ]

        return attributions

    def generate_counterfactual(
        self,
        trace: DecisionTrace,
        changed_factor: str,
        new_value: str,
    ) -> CounterfactualExplanation:
        """Generate a counterfactual by modifying one factor of a decision.

        The alternative decision is estimated by removing the original
        attribution for *changed_factor* and adjusting the confidence.

        Parameters
        ----------
        trace : DecisionTrace
            The original decision trace to base the counterfactual on.
        changed_factor : str
            The factor being changed.
        new_value : str
            The new value for the changed factor.

        Returns
        -------
        CounterfactualExplanation
            The generated counterfactual explanation.
        """
        # Estimate alternative outcome: remove the changed factor's influence
        changed_factors = [changed_factor]
        alt_decision = f"Revised: {trace.input_summary} (with {changed_factor}={new_value})"

        # Confidence delta proportional to the factor's attribution score
        delta = 0.0
        for attr in trace.key_factors:
            if attr.feature == changed_factor:
                delta = -attr.score * 0.1
                break

        new_confidence = max(0.0, trace.confidence + delta)
        confidence_delta = new_confidence - trace.confidence

        cf = CounterfactualExplanation(
            original_decision=trace.input_summary,
            counterfactual_scenario=f"If {changed_factor} were '{new_value}' instead",
            alternative_decision=alt_decision,
            confidence_delta=confidence_delta,
            key_changed_factors=tuple(changed_factors),
        )

        self._counterfactuals.append(cf)
        return cf

    def compute_saliency(
        self,
        text: str,
        method: str | None = None,
    ) -> SaliencyMap:
        """Compute token-level saliency scores.

        Uses a TF-IDF-like heuristic where domain-relevant tokens receive
        boosted scores.  Scores are normalised to ``[0, 1]``.

        Parameters
        ----------
        text : str
            The text to compute saliency for.
        method : str | None
            Saliency method label.  Defaults to the engine's configured
            method.

        Returns
        -------
        SaliencyMap
            Token-level saliency map.
        """
        method = method or self._config.attribution_method
        tokens = _tokenize(text)

        if not tokens:
            return SaliencyMap(
                target_text=text,
                tokens=(),
                scores=(),
                method=method,
                normalized=True,
            )

        # Score each token: base frequency score + domain keyword boost
        freq = Counter(tokens)
        max_freq = max(freq.values())
        raw_scores: list[float] = []
        for token in tokens:
            base = freq[token] / max_freq
            boost = 0.5 if token in _DOMAIN_KEYWORDS else 0.0
            raw_scores.append(base + boost)

        # Normalise to [0, 1]
        max_score = max(raw_scores) if raw_scores else 1.0
        normalized_scores = tuple(s / max_score for s in raw_scores)

        return SaliencyMap(
            target_text=text,
            tokens=tuple(tokens),
            scores=normalized_scores,
            method=method,
            normalized=True,
        )

    def generate_report(self, agent_id: str) -> InterpretabilityReport:
        """Aggregate all traces, attributions, and counterfactuals into a report.

        Parameters
        ----------
        agent_id : str
            The agent to generate the report for.

        Returns
        -------
        InterpretabilityReport
            Comprehensive interpretability report.
        """
        # Filter traces for this agent
        agent_traces = tuple(t for t in self._traces if t.agent_id == agent_id)

        # Collect all attributions across traces, deduplicate by feature
        all_attributions: dict[str, FeatureAttribution] = {}
        for trace in agent_traces:
            for attr in trace.key_factors:
                if attr.feature not in all_attributions or attr.score > all_attributions[attr.feature].score:
                    all_attributions[attr.feature] = attr

        sorted_attributions = tuple(
            sorted(all_attributions.values(), key=lambda a: -a.score)
        )

        # Counterfactuals for this agent (all stored counterfactuals)
        agent_cfs = tuple(
            cf for cf in self._counterfactuals
        )

        # Transparency score: ratio of decisions with at least one attribution
        if len(agent_traces) > 0:
            traces_with_attribution = sum(
                1 for t in agent_traces if len(t.key_factors) > 0
            )
            transparency = traces_with_attribution / len(agent_traces)
        else:
            transparency = 1.0

        return InterpretabilityReport(
            agent_id=agent_id,
            timestamp=time(),
            decision_traces=agent_traces,
            top_attributions=sorted_attributions,
            counterfactuals=agent_cfs,
            overall_transparency_score=round(transparency, 4),
        )

    def explain_decision(self, agent_id: str, decision_id: str) -> str:
        """Return a human-readable explanation of a specific decision.

        Parameters
        ----------
        agent_id : str
            The agent that made the decision.
        decision_id : str
            Unique identifier of the decision to explain.

        Returns
        -------
        str
            Natural language explanation of the decision.
        """
        # Find the matching trace
        matches = [
            t
            for t in self._traces
            if t.agent_id == agent_id and t.decision_id == decision_id
        ]
        if not matches:
            return f"No decision found with ID '{decision_id}' for agent '{agent_id}'."

        trace = matches[0]

        lines: list[str] = []
        lines.append(f"Decision Explanation for agent '{agent_id}'")
        lines.append("-" * 50)
        lines.append(f"Input: {trace.input_summary}")
        lines.append(f"Confidence: {trace.confidence:.2%}")
        lines.append("")

        if trace.reasoning_steps:
            lines.append("Reasoning Chain:")
            for i, step in enumerate(trace.reasoning_steps, 1):
                lines.append(f"  {i}. {step}")

        if trace.key_factors:
            lines.append("")
            lines.append("Key Factors (ranked by importance):")
            for attr in trace.key_factors[:5]:
                lines.append(
                    f"  #{attr.rank} {attr.feature} (score: {attr.score:.3f})"
                )

        if trace.alternatives_considered:
            lines.append("")
            lines.append("Alternatives Considered:")
            for alt in trace.alternatives_considered:
                lines.append(f"  - {alt}")

        return "\n".join(lines)

    def get_stats(self) -> dict[str, Any]:
        """Return aggregate statistics for the engine.

        Returns
        -------
        dict[str, Any]
            Statistics including total traces, counterfactuals, average
            confidence, and average alternatives considered.
        """
        num_traces = len(self._traces)
        if num_traces > 0:
            avg_confidence = sum(t.confidence for t in self._traces) / num_traces
            avg_alternatives = sum(
                len(t.alternatives_considered) for t in self._traces
            ) / num_traces
        else:
            avg_confidence = 0.0
            avg_alternatives = 0.0

        return {
            "total_traces": num_traces,
            "total_counterfactuals": len(self._counterfactuals),
            "avg_confidence": round(avg_confidence, 4),
            "avg_alternatives_considered": round(avg_alternatives, 4),
        }


__all__ = [
    # Enums
    "AttributionMethod",
    "ExplanationType",
    # Data classes
    "FeatureAttribution",
    "DecisionTrace",
    "CounterfactualExplanation",
    "SaliencyMap",
    "InterpretabilityReport",
    "InterpretabilityConfig",
    # Engine
    "InterpretabilityEngine",
]
