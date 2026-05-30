"""Verdict Combiner — Combines multiple model outputs via consensus strategies.

Supports majority voting, weighted averaging, best-of-N selection, and
cascade combination with confidence scoring.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class CombineStrategy(StrEnum):
    """Strategies for combining multiple model verdicts."""

    MAJORITY_VOTE = "majority_vote"
    WEIGHTED_VOTE = "weighted_vote"
    BEST_OF_N = "best_of_n"
    CASCADE = "cascade"
    UNANIMOUS = "unanimous"


@dataclass(frozen=True)
class ModelVerdict:
    """A single model's verdict on a task."""

    model_name: str
    model_tier: str
    output: str
    confidence: float  # 0.0-1.0
    latency_ms: float
    cost_usd: float
    success: bool = True
    error_message: str = ""


@dataclass
class CombinedVerdict:
    """Result of combining multiple model verdicts."""

    final_output: str
    strategy: CombineStrategy
    agreement_score: float  # 0.0-1.0, how much models agreed
    confidence: float  # 0.0-1.0
    participating_models: int
    dissenting_models: int
    total_cost_usd: float
    total_latency_ms: float
    verdicts: list[ModelVerdict] = field(default_factory=list)
    dissent_details: list[str] = field(default_factory=list)
    selected_model: str = ""


class VerdictCombiner:
    """Combines verdicts from multiple models using configurable strategies.

    Usage::

        combiner = VerdictCombiner()
        verdicts = [
            ModelVerdict("sonnet", "standard", "Use JWT...", 0.9, 150, 0.01),
            ModelVerdict("opus", "premium", "Use JWT...", 0.95, 300, 0.05),
        ]
        result = combiner.combine(verdicts, strategy=CombineStrategy.WEIGHTED_VOTE)
    """

    def __init__(
        self,
        min_agreement_threshold: float = 0.5,
        default_strategy: CombineStrategy = CombineStrategy.WEIGHTED_VOTE,
    ) -> None:
        self.min_agreement_threshold = min_agreement_threshold
        self.default_strategy = default_strategy
        self._tier_weights: dict[str, float] = {
            "agentic": 1.0,
            "premium": 0.9,
            "standard": 0.7,
            "fast": 0.5,
            "haiku": 0.4,
            "local_slm": 0.2,
        }

    def combine(
        self,
        verdicts: list[ModelVerdict],
        strategy: CombineStrategy | None = None,
    ) -> CombinedVerdict:
        """Combine multiple model verdicts into a final answer.

        Args:
            verdicts: List of model verdicts to combine
            strategy: Combination strategy (defaults to self.default_strategy)

        Returns:
            CombinedVerdict with final output and metadata
        """
        if not verdicts:
            return CombinedVerdict(
                final_output="",
                strategy=strategy or self.default_strategy,
                agreement_score=0.0,
                confidence=0.0,
                participating_models=0,
                dissenting_models=0,
                total_cost_usd=0.0,
                total_latency_ms=0.0,
            )

        strategy = strategy or self.default_strategy
        successful = [v for v in verdicts if v.success]

        if not successful:
            return self._fallback_result(verdicts, strategy)

        combine_fn = {
            CombineStrategy.MAJORITY_VOTE: self._majority_vote,
            CombineStrategy.WEIGHTED_VOTE: self._weighted_vote,
            CombineStrategy.BEST_OF_N: self._best_of_n,
            CombineStrategy.CASCADE: self._cascade,
            CombineStrategy.UNANIMOUS: self._unanimous,
        }.get(strategy, self._weighted_vote)

        return combine_fn(successful, verdicts)

    def _majority_vote(
        self, successful: list[ModelVerdict], all_verdicts: list[ModelVerdict]
    ) -> CombinedVerdict:
        """Simple majority voting on the output."""
        outputs: dict[str, list[ModelVerdict]] = {}
        for v in successful:
            key = v.output.strip()[:200]
            outputs.setdefault(key, []).append(v)

        # Find the output with the most votes
        best_key = max(outputs, key=lambda k: len(outputs[k]))
        winners = outputs[best_key]
        agreement = len(winners) / len(successful)

        avg_confidence = sum(v.confidence for v in winners) / len(winners)

        return CombinedVerdict(
            final_output=winners[0].output,
            strategy=CombineStrategy.MAJORITY_VOTE,
            agreement_score=agreement,
            confidence=avg_confidence * agreement,
            participating_models=len(successful),
            dissenting_models=len(all_verdicts) - len(winners),
            total_cost_usd=sum(v.cost_usd for v in all_verdicts),
            total_latency_ms=sum(v.latency_ms for v in all_verdicts),
            verdicts=all_verdicts,
            selected_model=winners[0].model_name,
        )

    def _weighted_vote(
        self, successful: list[ModelVerdict], all_verdicts: list[ModelVerdict]
    ) -> CombinedVerdict:
        """Weighted voting based on model tier and confidence."""
        outputs: dict[str, float] = {}
        model_weights: dict[str, float] = {}
        output_samples: dict[str, str] = {}

        for v in successful:
            tier_weight = self._tier_weights.get(v.model_tier, 0.5)
            weight = tier_weight * v.confidence
            key = v.output.strip()[:200]
            outputs[key] = outputs.get(key, 0.0) + weight
            output_samples[key] = v.output
            model_weights[key] = max(model_weights.get(key, 0.0), weight)

        best_key = max(outputs, key=lambda k: outputs[k])
        max_weight = outputs[best_key]
        total_weight = sum(outputs.values())
        agreement = max_weight / total_weight if total_weight > 0 else 0.0

        top_model_weight = model_weights[best_key]
        confidence = min(1.0, agreement * (max_weight / max(1.0, top_model_weight)))

        return CombinedVerdict(
            final_output=output_samples[best_key],
            strategy=CombineStrategy.WEIGHTED_VOTE,
            agreement_score=agreement,
            confidence=confidence,
            participating_models=len(successful),
            dissenting_models=len(all_verdicts) - sum(
                1 for v in successful if v.output.strip()[:200] == best_key
            ),
            total_cost_usd=sum(v.cost_usd for v in all_verdicts),
            total_latency_ms=sum(v.latency_ms for v in all_verdicts),
            verdicts=all_verdicts,
            selected_model=max(
                successful, key=lambda v: self._tier_weights.get(v.model_tier, 0.5) * v.confidence
            ).model_name,
        )

    def _best_of_n(
        self, successful: list[ModelVerdict], all_verdicts: list[ModelVerdict]
    ) -> CombinedVerdict:
        """Select the best single verdict based on confidence and tier."""
        best = max(
            successful,
            key=lambda v: self._tier_weights.get(v.model_tier, 0.5) * v.confidence,
        )
        return CombinedVerdict(
            final_output=best.output,
            strategy=CombineStrategy.BEST_OF_N,
            agreement_score=1.0,
            confidence=best.confidence,
            participating_models=len(successful),
            dissenting_models=len(all_verdicts) - 1,
            total_cost_usd=sum(v.cost_usd for v in all_verdicts),
            total_latency_ms=sum(v.latency_ms for v in all_verdicts),
            verdicts=all_verdicts,
            selected_model=best.model_name,
        )

    def _cascade(
        self, successful: list[ModelVerdict], all_verdicts: list[ModelVerdict]
    ) -> CombinedVerdict:
        """Cascade: prefer highest-tier model, fall back if confidence is low."""
        tier_order = ["agentic", "premium", "standard", "fast", "haiku", "local_slm"]
        sorted_verdicts = sorted(
            successful,
            key=lambda v: (tier_order.index(v.model_tier) if v.model_tier in tier_order else 999),
        )

        selected = sorted_verdicts[0]
        if selected.confidence < 0.5 and len(sorted_verdicts) > 1:
            # Fall back to next tier
            for v in sorted_verdicts[1:]:
                if v.confidence >= 0.7:
                    selected = v
                    break

        return CombinedVerdict(
            final_output=selected.output,
            strategy=CombineStrategy.CASCADE,
            agreement_score=0.8 if selected.confidence >= 0.7 else 0.5,
            confidence=selected.confidence,
            participating_models=len(successful),
            dissenting_models=len(all_verdicts) - 1,
            total_cost_usd=sum(v.cost_usd for v in all_verdicts),
            total_latency_ms=sum(v.latency_ms for v in all_verdicts),
            verdicts=all_verdicts,
            selected_model=selected.model_name,
        )

    def _unanimous(
        self, successful: list[ModelVerdict], all_verdicts: list[ModelVerdict]
    ) -> CombinedVerdict:
        """Require unanimous agreement. Returns empty on disagreement."""
        if not successful:
            return self._fallback_result(all_verdicts, CombineStrategy.UNANIMOUS)

        first_output = successful[0].output.strip()[:200]
        all_agree = all(v.output.strip()[:200] == first_output for v in successful)

        if all_agree:
            avg_conf = sum(v.confidence for v in successful) / len(successful)
            return CombinedVerdict(
                final_output=successful[0].output,
                strategy=CombineStrategy.UNANIMOUS,
                agreement_score=1.0,
                confidence=avg_conf,
                participating_models=len(successful),
                dissenting_models=len(all_verdicts) - len(successful),
                total_cost_usd=sum(v.cost_usd for v in all_verdicts),
                total_latency_ms=sum(v.latency_ms for v in all_verdicts),
                verdicts=all_verdicts,
                selected_model="consensus",
            )

        # No consensus — return empty with low confidence
        return CombinedVerdict(
            final_output="",
            strategy=CombineStrategy.UNANIMOUS,
            agreement_score=0.0,
            confidence=0.0,
            participating_models=len(successful),
            dissenting_models=len(successful),
            total_cost_usd=sum(v.cost_usd for v in all_verdicts),
            total_latency_ms=sum(v.latency_ms for v in all_verdicts),
            verdicts=all_verdicts,
            dissent_details=["Models did not reach unanimous agreement"],
        )

    def _fallback_result(
        self, verdicts: list[ModelVerdict], strategy: CombineStrategy
    ) -> CombinedVerdict:
        """Create a result when all verdicts failed."""
        return CombinedVerdict(
            final_output="",
            strategy=strategy,
            agreement_score=0.0,
            confidence=0.0,
            participating_models=0,
            dissenting_models=len(verdicts),
            total_cost_usd=sum(v.cost_usd for v in verdicts),
            total_latency_ms=sum(v.latency_ms for v in verdicts),
            verdicts=verdicts,
            dissent_details=["All models failed to produce a valid verdict"],
        )
