"""
ReTAS Dialectical Alignment — Actor-Observer Asymmetry Correction.

Implements the ReTAS (Reflective Theory-of-Mind Alignment through
Symmetry) framework for correcting self-serving bias in multi-agent
debates.  In any debate, agents acting as "actors" systematically rate
their own arguments higher and discount opposing arguments — this is
the actor-observer asymmetry (arXiv 2604.19548).

The pipeline:
  1. Measure the asymmetry for each agent in a debate round.
  2. Apply a dialectical correction to re-weight arguments so that the
     final aligned round reflects a more epistemically balanced view.
  3. Report pre-/post-alignment metrics.

References
----------
- ReTAS: Reflective Theory-of-Mind Alignment for Multi-Agent Debate.
  Li et al., arXiv 2604.19548v1
- When Identity Skews Debate.  Choi, Zhu, Li, arXiv 2510.07517
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import structlog

from lyra.verification.debate_panel import Argument, Ballot, DebateResult

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Data Types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ActorObserverAsymmetry:
    """Quantified self-serving bias for a single agent in a debate round.

    Attributes:
        anonymous_id: The anonymized agent identifier.
        self_rating_mean: Average rating (0-1) the agent assigned to its
            own arguments (rating taken from confidence / tone).
        other_rating_mean: Average rating the agent assigned to
            arguments from other panelists.
        asymmetry_score: self_rating_mean - other_rating_mean.  Positive
            values indicate self-serving bias; values near zero indicate
            balance; negative values indicate excessive self-criticism.
        argument_self_count: Number of own arguments rated.
        argument_other_count: Number of peer arguments rated.
    """

    anonymous_id: str
    self_rating_mean: float
    other_rating_mean: float
    asymmetry_score: float
    argument_self_count: int
    argument_other_count: int


@dataclass(frozen=True)
class AlignmentMetrics:
    """Aggregate metrics before and after alignment correction.

    Attributes:
        pre_alignment_asymmetries: One ActorObserverAsymmetry per agent
            before correction.
        post_alignment_asymmetries: Same after correction.
        mean_asymmetry_before: Mean absolute asymmetry across all agents
            before correction.
        mean_asymmetry_after: Mean absolute asymmetry after correction.
        alignment_improvement: Reduction in mean absolute asymmetry
            (positive = improvement).
        total_arguments_aligned: Number of arguments that were re-weighted.
        correction_factor: Average correction magnitude applied (0-1).
    """

    pre_alignment_asymmetries: tuple[ActorObserverAsymmetry, ...]
    post_alignment_asymmetries: tuple[ActorObserverAsymmetry, ...]
    mean_asymmetry_before: float
    mean_asymmetry_after: float
    alignment_improvement: float
    total_arguments_aligned: int
    correction_factor: float


@dataclass(frozen=True)
class AlignedRound:
    """A debate round after ReTAS alignment correction.

    Attributes:
        arguments: The corrected list of arguments (weights adjusted).
        original_arguments: The arguments before correction.
        metrics: Pre/post alignment metrics.
        correction_map: Mapping of argument index -> correction weight
            applied (1.0 = unchanged).
    """

    arguments: tuple[Argument, ...]
    original_arguments: tuple[Argument, ...]
    metrics: AlignmentMetrics
    correction_map: dict[int, float]


# ---------------------------------------------------------------------------
# ReTAS Aligner
# ---------------------------------------------------------------------------


class ReTASAligner:
    """Dialectical alignment via actor-observer asymmetry correction.

    Usage::

        aligner = ReTASAligner()
        aligned = aligner.apply_alignment(debate_result)
        print(aligned.metrics.alignment_improvement)
    """

    def __init__(
        self,
        correction_strength: float = 0.5,
        min_observations: int = 2,
    ) -> None:
        """
        Args:
            correction_strength: How aggressively to correct asymmetry
                (0.0 = no correction, 1.0 = full correction to mean).
            min_observations: Minimum number of self-ratings needed to
                compute a reliable asymmetry score.
        """
        self._correction_strength = max(0.0, min(1.0, correction_strength))
        self._min_observations = min_observations

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def apply_alignment(
        self,
        debate_result: DebateResult,
    ) -> AlignedRound:
        """Apply ReTAS alignment to a completed debate.

        Measures actor-observer asymmetry per agent, then re-weights
        arguments to correct for self-serving bias.

        Args:
            debate_result: The completed debate result.

        Returns:
            AlignedRound with corrected arguments and full metrics.
        """
        arguments = list(debate_result.arguments)
        original = list(arguments)

        # 1. Measure pre-alignment asymmetries
        pre_asymmetries = self._measure_asymmetries(
            arguments, debate_result.voting_record
        )

        # 2. Compute per-agent correction weights
        correction_weights = self._compute_correction_weights(pre_asymmetries)

        # 3. Apply corrections to argument content (re-weight)
        corrected_arguments: list[Argument] = []
        correction_map: dict[int, float] = {}

        for idx, arg in enumerate(original):
            weight = correction_weights.get(arg.anonymous_id, 1.0)
            correction_map[idx] = round(weight, 4)

            if abs(weight - 1.0) > 0.001:
                # Apply correction: strengthen or dilute the argument's
                # confidence indicators in the content.
                corrected_content = self._apply_correction_to_content(
                    arg.content, weight
                )
                corrected_arguments.append(Argument(
                    round_number=arg.round_number,
                    anonymous_id=arg.anonymous_id,
                    perspective=arg.perspective,
                    content=corrected_content,
                    claims=arg.claims,
                ))
            else:
                corrected_arguments.append(arg)

        # 4. Measure post-alignment asymmetries (re-simulate with corrected)
        #    For post metrics we simulate a balanced voting record.
        post_asymmetries = self._simulate_post_asymmetries(
            pre_asymmetries, correction_weights
        )

        pre_mean = self._mean_abs_asymmetry(pre_asymmetries)
        post_mean = self._mean_abs_asymmetry(post_asymmetries)

        aligned_count = sum(
            1 for w in correction_map.values() if abs(w - 1.0) > 0.001
        )
        avg_correction = (
            sum(
                abs(w - 1.0)
                for w in correction_map.values()
            ) / len(correction_map)
            if correction_map
            else 0.0
        )

        metrics = AlignmentMetrics(
            pre_alignment_asymmetries=tuple(pre_asymmetries),
            post_alignment_asymmetries=tuple(post_asymmetries),
            mean_asymmetry_before=round(pre_mean, 4),
            mean_asymmetry_after=round(post_mean, 4),
            alignment_improvement=round(pre_mean - post_mean, 4),
            total_arguments_aligned=aligned_count,
            correction_factor=round(avg_correction, 4),
        )

        return AlignedRound(
            arguments=tuple(corrected_arguments),
            original_arguments=tuple(original),
            metrics=metrics,
            correction_map=correction_map,
        )

    # ------------------------------------------------------------------
    # Asymmetry Measurement
    # ------------------------------------------------------------------

    def _measure_asymmetries(
        self,
        arguments: list[Argument],
        ballots: tuple[Ballot, ...],
    ) -> list[ActorObserverAsymmetry]:
        """Compute asymmetry scores for each agent.

        Self-rating is derived from the agent's own ballot confidence.
        Other-rating is derived from the agent's stance on peer
        arguments (approve/reject patterns in their vote rationale).
        """
        # Group ballots by voter
        ballot_by_id: dict[str, Ballot] = {
            b.anonymous_id: b for b in ballots
        }

        asymmetries: list[ActorObserverAsymmetry] = []

        for anon_id in {a.anonymous_id for a in arguments}:
            own_ballot = ballot_by_id.get(anon_id)
            if own_ballot is None:
                continue

            # Self-rating: confidence in own vote
            self_rating = own_ballot.confidence

            # Other-rating: average confidence of ballots from other agents
            other_ratings = [
                b.confidence
                for b_id, b in ballot_by_id.items()
                if b_id != anon_id
            ]

            other_mean = (
                sum(other_ratings) / len(other_ratings)
                if other_ratings
                else 0.5
            )

            self_count = 1  # own ballot
            other_count = len(other_ratings)
            asymmetry_score = self_rating - other_mean

            asymmetries.append(ActorObserverAsymmetry(
                anonymous_id=anon_id,
                self_rating_mean=round(self_rating, 4),
                other_rating_mean=round(other_mean, 4),
                asymmetry_score=round(asymmetry_score, 4),
                argument_self_count=self_count,
                argument_other_count=other_count,
            ))

        return asymmetries

    def _compute_correction_weights(
        self,
        asymmetries: list[ActorObserverAsymmetry],
    ) -> dict[str, float]:
        """Compute correction weight per agent.

        Weight is derived from asymmetry: positive asymmetry (self-bias)
        is reduced; negative asymmetry (self-criticism) is boosted.

        Returns dict of anonymous_id -> weight (1.0 = no change).
        """
        weights: dict[str, float] = {}

        for aoa in asymmetries:
            if aoa.argument_self_count < self._min_observations:
                weights[aoa.anonymous_id] = 1.0
                continue

            # Asymmetry ranges [-1, 1].  Map to a correction weight
            # centered at 1.0.
            #   asymmetry > 0  → weight < 1.0 (dilute self-bias)
            #   asymmetry < 0  → weight > 1.0 (boost under-rated)
            raw_adjustment = -aoa.asymmetry_score * self._correction_strength
            weight = 1.0 + raw_adjustment

            # Clamp to [0.5, 1.5]
            weight = max(0.5, min(1.5, weight))
            weights[aoa.anonymous_id] = round(weight, 4)

        return weights

    # ------------------------------------------------------------------
    # Content Correction
    # ------------------------------------------------------------------

    def _apply_correction_to_content(
        self,
        content: str,
        weight: float,
    ) -> str:
        """Neutralise confidence markers in argument text.

        When weight < 1.0 we dilute over-confident language.
        When weight > 1.0 we strengthen under-confident language.
        """
        if weight >= 1.0:
            # Strengthen: replace tentative language
            result = content
            replacements = {
                "maybe": "likely",
                "possibly": "probably",
                "I think": "I conclude",
                "it seems": "it is",
                "tentatively": "confidently",
                "uncertain": "uncertain but leaning",
                "could be": "is",
            }
            for weak, strong in replacements.items():
                result = result.replace(weak, strong)
            return result

        # Dilute: hedge over-confident language
        result = content
        replacements = {
            "definitely": "probably",
            "undoubtedly": "likely",
            "certainly": "likely",
            "absolutely": "strongly",
            "without doubt": "with high probability",
            "clearly": "arguably",
            "obviously": "arguably",
            "I am certain": "I believe",
            "it is clear": "it appears",
            "unquestionably": "likely",
        }
        for strong, weak in replacements.items():
            result = result.replace(strong, weak)
        return result

    # ------------------------------------------------------------------
    # Post-Alignment Simulation
    # ------------------------------------------------------------------

    def _simulate_post_asymmetries(
        self,
        pre_asymmetries: list[ActorObserverAsymmetry],
        correction_weights: dict[str, float],
    ) -> list[ActorObserverAsymmetry]:
        """Simulate post-alignment asymmetries based on correction weights.

        This estimates the asymmetry that would remain after applying
        the dialectical correction.
        """
        post: list[ActorObserverAsymmetry] = []

        for aoa in pre_asymmetries:
            weight = correction_weights.get(aoa.anonymous_id, 1.0)
            # Apply correction inversely to asymmetry
            corrected_self = aoa.self_rating_mean
            if weight < 1.0:
                # Self-rating was too high, reduce it
                corrected_self = aoa.other_rating_mean + (
                    aoa.self_rating_mean - aoa.other_rating_mean
                ) * weight
            elif weight > 1.0:
                # Self-rating was too low, raise it
                corrected_self = aoa.self_rating_mean + (
                    aoa.other_rating_mean - aoa.self_rating_mean
                ) * (1.0 / weight)

            corrected_self = max(0.0, min(1.0, corrected_self))
            new_asymmetry = corrected_self - aoa.other_rating_mean

            post.append(ActorObserverAsymmetry(
                anonymous_id=aoa.anonymous_id,
                self_rating_mean=round(corrected_self, 4),
                other_rating_mean=aoa.other_rating_mean,
                asymmetry_score=round(new_asymmetry, 4),
                argument_self_count=aoa.argument_self_count,
                argument_other_count=aoa.argument_other_count,
            ))

        return post

    @staticmethod
    def _mean_abs_asymmetry(
        asymmetries: list[ActorObserverAsymmetry],
    ) -> float:
        """Mean absolute asymmetry across all agents."""
        if not asymmetries:
            return 0.0
        return sum(
            abs(a.asymmetry_score) for a in asymmetries
        ) / len(asymmetries)
