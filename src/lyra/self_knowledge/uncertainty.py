"""
Uncertainty estimation — confidence calibration for agent outputs.

Provides UncertaintyEstimator for scoring confidence in agent predictions,
SelfConsistency for checking agreement across multiple samples,
MATUDecomposer for tensor-based uncertainty decomposition,
CaTSAdaptiveSampler for difficulty-adaptive sampling,
and AbstentionGate for refusing low-confidence answers.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol


# ---------------------------------------------------------------------------
# UncertaintyEstimator
# ---------------------------------------------------------------------------


@dataclass
class ConfidenceScore:
    """Confidence estimate for a single prediction.

    Attributes:
        score: Overall confidence in [0, 1].
        entropy: Predictive entropy (0 = certain, higher = uncertain).
        probability: Raw probability estimate, if available.
        components: Per-factor confidence breakdown.
    """

    score: float
    entropy: float = 0.0
    probability: float = 0.0
    components: dict[str, float] = field(default_factory=dict)


class UncertaintyEstimator:
    """Estimates confidence in agent outputs using multiple signals.

    Combines:
      - Model-reported logits / probabilities (if available).
      - Semantic entropy from multiple decoding passes.
      - Heuristic features (response length, token repetition, etc.).
    """

    def __init__(self, methods: list[str] | None = None):
        """Initialize UncertaintyEstimator.

        Args:
            methods: List of enabled uncertainty methods.
                Defaults to all available methods.
        """
        self._methods = methods or ["probability", "entropy", "heuristic"]

    def estimate(self, output: str, **kwargs: Any) -> ConfidenceScore:
        """Estimate confidence in a single output.

        Args:
            output: The generated output text.
            kwargs: Optional extra signals:
                - log_probs (list[float]): Token-level log probabilities.
                - probability (float): Aggregate probability estimate.

        Returns:
            ConfidenceScore with the aggregated estimate.
        """
        components: dict[str, float] = {}

        if "probability" in self._methods and "probability" in kwargs:
            prob = max(0.0, min(1.0, kwargs["probability"]))
            components["probability"] = prob

        if "entropy" in self._methods and "log_probs" in kwargs:
            log_probs = kwargs["log_probs"]
            if log_probs:
                entropy = -sum(lp for lp in log_probs if lp < 0) / max(len(log_probs), 1)
                components["entropy"] = 1.0 - min(1.0, entropy / 10.0)

        if "heuristic" in self._methods:
            heuristic_score = self._heuristic_confidence(output)
            components["heuristic"] = heuristic_score

        if not components:
            return ConfidenceScore(score=0.5, entropy=0.5, probability=0.5)

        # Weighted average across components
        score = sum(components.values()) / len(components)
        score = max(0.0, min(1.0, score))

        return ConfidenceScore(
            score=score,
            entropy=1.0 - score,
            probability=components.get("probability", score),
            components=components,
        )

    def estimate_batch(
        self, outputs: list[str], **kwargs: Any
    ) -> list[ConfidenceScore]:
        """Estimate confidence for a batch of outputs.

        Args:
            outputs: List of generated output strings.
            kwargs: Batch-level extra signals.

        Returns:
            List of ConfidenceScore values, one per output.
        """
        return [self.estimate(out, **kwargs) for out in outputs]

    @staticmethod
    def _heuristic_confidence(text: str) -> float:
        """Heuristic confidence based on output surface features.

        Longer, non-repetitive outputs with diverse vocabulary score higher.
        Very short or highly repetitive outputs score lower.
        """
        if not text or len(text.strip()) < 5:
            return 0.1

        words = text.split()
        if not words:
            return 0.1

        # Length score: diminishing returns beyond ~100 words
        length_score = min(1.0, len(words) / 100.0)

        # Repetition penalty: repeated n-grams reduce confidence
        unique_ratio = 1.0
        if len(words) >= 4:
            trigrams = {
                " ".join(words[i : i + 3]) for i in range(len(words) - 2)
            }
            total_trigrams = max(len(words) - 2, 1)
            unique_ratio = len(trigrams) / total_trigrams

        return (length_score * 0.4) + (unique_ratio * 0.6)


# ---------------------------------------------------------------------------
# SelfConsistency
# ---------------------------------------------------------------------------


@dataclass
class ConsistencyResult:
    """Result of self-consistency checking.

    Attributes:
        samples: The sampled outputs.
        agreement: Pairwise agreement score in [0, 1].
        majority_answer: The most common answer or None if tie.
        sample_indices: Indices of samples that agree with the majority.
    """

    samples: list[str]
    agreement: float
    majority_answer: str | None = None
    sample_indices: list[int] = field(default_factory=list)


class AnswerNormalizer(Protocol):
    """Protocol for normalising answers before comparison."""

    def normalize(self, text: str) -> str:
        """Normalize an answer string for equality comparison.

        Args:
            text: Raw answer text.

        Returns:
            Normalized answer string.
        """
        ...


class ExactMatchNormalizer:
    """Normalises answers by stripping whitespace and lowercasing."""

    def normalize(self, text: str) -> str:
        return text.strip().lower()


class SelfConsistency:
    """Samples multiple outputs and checks agreement between them.

    Higher agreement indicates higher confidence. Used to detect when the
    model is guessing or hallucinating.
    """

    def __init__(
        self,
        num_samples: int = 5,
        normalizer: AnswerNormalizer | None = None,
    ):
        """Initialize SelfConsistency.

        Args:
            num_samples: Number of samples to generate.
            normalizer: Answer normaliser for comparison.
        """
        self.num_samples = num_samples
        self._normalizer = normalizer or ExactMatchNormalizer()

    def check(
        self,
        sampler: Callable[[], str],
        normalizer: AnswerNormalizer | None = None,
    ) -> ConsistencyResult:
        """Generate multiple samples and compute agreement.

        Args:
            sampler: A zero-argument callable that returns one sample.
            normalizer: Optional overridden normaliser for this check.

        Returns:
            ConsistencyResult with agreement score and majority answer.
        """
        norm = normalizer or self._normalizer
        samples: list[str] = []
        for _ in range(self.num_samples):
            try:
                sample = sampler()
                samples.append(sample)
            except Exception:
                samples.append("")

        if not samples:
            return ConsistencyResult(
                samples=[], agreement=0.0, majority_answer=None
            )

        # Find the majority answer
        normalized = [norm.normalize(s) for s in samples]
        from collections import Counter

        counter = Counter(normalized)
        most_common = counter.most_common(1)
        majority_norm = most_common[0][0] if most_common else None
        majority_count = most_common[0][1] if most_common else 0

        # Agreement = proportion sharing the majority answer
        agreement = majority_count / len(samples) if samples else 0.0

        majority_indices = [
            i for i, n in enumerate(normalized) if n == majority_norm
        ]

        # Find the original text of the majority answer
        majority_answer: str | None = None
        for i, n in enumerate(normalized):
            if n == majority_norm:
                majority_answer = samples[i]
                break

        return ConsistencyResult(
            samples=samples,
            agreement=agreement,
            majority_answer=majority_answer,
            sample_indices=majority_indices,
        )


# ---------------------------------------------------------------------------
# MATUDecomposer
# ---------------------------------------------------------------------------


@dataclass
class DecomposedUncertainty:
    """Tensor-decomposed uncertainty estimates.

    Attributes:
        aleatoric: Data-inherent uncertainty in [0, 1].
        epistemic: Model-knowledge uncertainty in [0, 1].
        total: Combined uncertainty (aleatoric + epistemic scaled).
        components: Full decomposition vector.
    """

    aleatoric: float = 0.0
    epistemic: float = 0.0
    total: float = 0.0
    components: list[float] = field(default_factory=list)


class MATUDecomposer:
    """Matrix/Tensor decomposition for uncertainty quantification.

    Approximates aleatoric (data) vs epistemic (model) uncertainty
    using a low-rank tensor decomposition inspired by Monte Carlo
    Dropout and Test-Time Augmentation principles.
    """

    def __init__(self, rank: int = 4, n_components: int = 8):
        """Initialize MATUDecomposer.

        Args:
            rank: Rank for tensor approximation (higher = more expressive).
            n_components: Number of uncertainty components to extract.
        """
        self.rank = rank
        self.n_components = n_components

    def decompose(
        self,
        prediction_logits: list[list[float]],
        sample_logits: list[list[list[float]]] | None = None,
    ) -> DecomposedUncertainty:
        """Decompose uncertainty from logit tensors.

        In the absence of true tensor operations, approximates via
        variance across hypothetical components.

        Args:
            prediction_logits: Logits for the primary prediction,
                shape (n_classes,) or (n_tokens, n_classes).
            sample_logits: Optional list of logit samples from multiple
                forward passes, shape (n_samples, n_tokens, n_classes).

        Returns:
            DecomposedUncertainty with aleatoric/epistemic split.
        """
        if not prediction_logits:
            return DecomposedUncertainty()

        # Flatten logits and compute basic statistics
        flat_logits = [x for row in prediction_logits for x in (
            row if isinstance(row, list) else [row]
        )]
        if not flat_logits:
            return DecomposedUncertainty()

        mean_logit = sum(flat_logits) / len(flat_logits)
        variance = (
            sum((x - mean_logit) ** 2 for x in flat_logits)
            / len(flat_logits)
        )
        # Normalize variance to [0, 1]
        total_uncertainty = min(1.0, variance / 10.0)

        # If multiple samples are available, split into aleatoric/epistemic
        if sample_logits and len(sample_logits) > 1:
            # Aleatoric: average within-sample variance
            within_var = 0.0
            ns = 0
            for sample in sample_logits:
                flat_sample = [
                    x for row in sample for x in (
                        row if isinstance(row, list) else [row]
                    )
                ]
                if flat_sample:
                    s_mean = sum(flat_sample) / len(flat_sample)
                    s_var = sum((x - s_mean) ** 2 for x in flat_sample) / len(flat_sample)
                    within_var += s_var
                    ns += 1
            aleatoric = (within_var / max(ns, 1)) / 10.0 if ns > 0 else total_uncertainty
            aleatoric = min(1.0, aleatoric)

            # Epistemic: remaining uncertainty beyond aleatoric
            epistemic = max(0.0, total_uncertainty - aleatoric)
        else:
            aleatoric = total_uncertainty * 0.5
            epistemic = total_uncertainty * 0.5

        components = [
            aleatoric,
            epistemic,
            total_uncertainty,
            aleatoric * epistemic,
            1.0 - total_uncertainty,
        ]
        # Pad to n_components
        while len(components) < self.n_components:
            components.append(0.0)
        components = components[: self.n_components]

        return DecomposedUncertainty(
            aleatoric=aleatoric,
            epistemic=epistemic,
            total=total_uncertainty,
            components=components,
        )


# ---------------------------------------------------------------------------
# CaTSAdaptiveSampler
# ---------------------------------------------------------------------------


@dataclass
class AdaptiveSampleResult:
    """Result of adaptive sampling.

    Attributes:
        output: The selected output after adaptive sampling.
        samples_taken: Number of samples actually taken.
        difficulty: Estimated difficulty of the input.
        confidence: Confidence in the final output (0-1).
    """

    output: str
    samples_taken: int = 1
    difficulty: float = 0.5
    confidence: float = 1.0


class DifficultyEstimator(Protocol):
    """Protocol for estimating input difficulty."""

    def estimate(self, input_text: str) -> float:
        """Return difficulty score in [0, 1].

        Args:
            input_text: The input or prompt.

        Returns:
            Difficulty where 0 = trivial, 1 = extremely hard.
        """
        ...


class StubDifficultyEstimator:
    """Simple difficulty estimator based on input length and complexity."""

    def estimate(self, input_text: str) -> float:
        """Estimate difficulty from text features.

        Longer inputs with rare words score higher.
        """
        if not input_text:
            return 0.0

        words = input_text.split()
        if not words:
            return 0.0

        # Length factor (longer = harder)
        length_factor = min(1.0, len(words) / 200.0)

        # Vocabulary rarity factor (simulated)
        avg_word_len = sum(len(w) for w in words) / len(words)
        vocab_factor = min(1.0, (avg_word_len - 3) / 10.0)

        return (length_factor * 0.5) + (vocab_factor * 0.5)


class CaTSAdaptiveSampler:
    """Adaptive sampling based on input difficulty (CaTS: Cost-Aware Thompson Sampling).

    Takes more samples for hard inputs, fewer for easy ones,
    to balance cost and accuracy.
    """

    def __init__(
        self,
        min_samples: int = 1,
        max_samples: int = 10,
        difficulty_estimator: DifficultyEstimator | None = None,
    ):
        """Initialize CaTSAdaptiveSampler.

        Args:
            min_samples: Minimum samples to take (easy inputs).
            max_samples: Maximum samples to take (hard inputs).
            difficulty_estimator: Estimator for input difficulty.
        """
        self.min_samples = min_samples
        self.max_samples = max_samples
        self._difficulty_estimator = difficulty_estimator or StubDifficultyEstimator()

    def sample(
        self,
        input_text: str,
        sampler: Callable[[], str],
        consistency_threshold: float = 0.7,
        normalizer: AnswerNormalizer | None = None,
    ) -> AdaptiveSampleResult:
        """Sample adaptively based on input difficulty.

        Args:
            input_text: The input to estimate difficulty from.
            sampler: Zero-arg callable returning one sample.
            consistency_threshold: Agreement threshold to stop early.
            normalizer: Optional normaliser for agreement checking.

        Returns:
            AdaptiveSampleResult with the best output.
        """
        difficulty = self._difficulty_estimator.estimate(input_text)

        # Map difficulty to number of samples
        n_samples = self.min_samples + int(
            difficulty * (self.max_samples - self.min_samples)
        )
        n_samples = max(self.min_samples, min(self.max_samples, n_samples))

        norm = normalizer or ExactMatchNormalizer()
        samples: list[str] = []
        for i in range(n_samples):
            try:
                sample = sampler()
                samples.append(sample)
            except Exception:
                continue

            # Early stopping: check if we have enough agreement
            if len(samples) >= 3:
                normalized = [norm.normalize(s) for s in samples]
                from collections import Counter

                counter = Counter(normalized)
                top_count = counter.most_common(1)[0][1]
                agreement = top_count / len(samples)
                if agreement >= consistency_threshold and i >= self.min_samples - 1:
                    break

        if not samples:
            return AdaptiveSampleResult(
                output="", samples_taken=0, difficulty=difficulty, confidence=0.0
            )

        # Pick plurality answer
        normalized = [norm.normalize(s) for s in samples]
        from collections import Counter

        counter = Counter(normalized)
        top_norm = counter.most_common(1)[0][0]
        top_count = counter.most_common(1)[0][1]

        selected_output = next(
            s for i, s in enumerate(samples) if norm.normalize(s) == top_norm
        )
        confidence = top_count / len(samples)

        return AdaptiveSampleResult(
            output=selected_output,
            samples_taken=len(samples),
            difficulty=difficulty,
            confidence=confidence,
        )


# ---------------------------------------------------------------------------
# AbstentionGate
# ---------------------------------------------------------------------------


@dataclass
class AbstentionDecision:
    """Decision from the abstention gate.

    Attributes:
        should_abstain: Whether the system should refuse to answer.
        reason: Human-readable reason for the decision.
        confidence: The confidence score that triggered the decision.
        threshold: The threshold used for comparison.
    """

    should_abstain: bool
    reason: str = ""
    confidence: float = 0.0
    threshold: float = 0.0


class AbstentionGate:
    """Refuses to answer when confidence is too low.

    Configurable thresholds: abstain below a minimum confidence level,
    or flag for human review in a middle band.
    """

    def __init__(
        self,
        abstain_threshold: float = 0.3,
        flag_threshold: float = 0.6,
    ):
        """Initialize AbstentionGate.

        Args:
            abstain_threshold: Confidence below this triggers abstention.
            flag_threshold: Confidence below this but above abstain
                threshold triggers a flag (for human review).

        Raises:
            ValueError: If thresholds are out of order or out of [0, 1].
        """
        if not (0 <= abstain_threshold <= flag_threshold <= 1):
            raise ValueError(
                "Require 0 <= abstain_threshold <= flag_threshold <= 1, "
                f"got abstain={abstain_threshold}, flag={flag_threshold}"
            )
        self.abstain_threshold = abstain_threshold
        self.flag_threshold = flag_threshold

    def decide(
        self,
        confidence: ConfidenceScore | float,
    ) -> AbstentionDecision:
        """Decide whether to abstain, flag, or proceed.

        Args:
            confidence: ConfidenceScore or raw float.

        Returns:
            AbstentionDecision with abstention flag and reason.
        """
        score = confidence.score if isinstance(confidence, ConfidenceScore) else confidence
        score = max(0.0, min(1.0, score))

        if score < self.abstain_threshold:
            return AbstentionDecision(
                should_abstain=True,
                reason=(
                    f"Confidence {score:.3f} is below abstain threshold "
                    f"{self.abstain_threshold}"
                ),
                confidence=score,
                threshold=self.abstain_threshold,
            )

        if score < self.flag_threshold:
            return AbstentionDecision(
                should_abstain=False,
                reason=(
                    f"Confidence {score:.3f} is below flag threshold "
                    f"{self.flag_threshold} — recommend human review"
                ),
                confidence=score,
                threshold=self.flag_threshold,
            )

        return AbstentionDecision(
            should_abstain=False,
            reason=f"Confidence {score:.3f} is sufficient (>= {self.flag_threshold})",
            confidence=score,
            threshold=self.flag_threshold,
        )

    def evaluate_batch(
        self, scores: list[ConfidenceScore | float]
    ) -> list[AbstentionDecision]:
        """Evaluate abstention for a batch of confidence scores.

        Args:
            scores: List of ConfidenceScore or float values.

        Returns:
            List of AbstentionDecision, one per score.
        """
        return [self.decide(s) for s in scores]


__all__ = [
    "ConfidenceScore",
    "UncertaintyEstimator",
    "ConsistencyResult",
    "AnswerNormalizer",
    "ExactMatchNormalizer",
    "SelfConsistency",
    "DecomposedUncertainty",
    "MATUDecomposer",
    "AdaptiveSampleResult",
    "DifficultyEstimator",
    "StubDifficultyEstimator",
    "CaTSAdaptiveSampler",
    "AbstentionDecision",
    "AbstentionGate",
]
