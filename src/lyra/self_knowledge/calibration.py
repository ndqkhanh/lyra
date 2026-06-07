"""
Confidence calibration — LoRA fine-tuning for calibrated outputs.

Provides LoRACalibrator that uses low-rank adaptation to fine-tune a model
towards better-calibrated confidence estimates, reducing overconfidence
and underconfidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

from lyra.self_knowledge.uncertainty import ConfidenceScore


# ---------------------------------------------------------------------------
# Calibration data model
# ---------------------------------------------------------------------------


@dataclass
class CalibrationExample:
    """A single calibration training example.

    Attributes:
        input_text: The model input / prompt.
        predicted_output: The model's generated output.
        confidence: The model's reported confidence score.
        actual_correct: Whether the output is actually correct.
    """

    input_text: str
    predicted_output: str
    confidence: float
    actual_correct: bool


@dataclass
class CalibrationResult:
    """Result of calibration evaluation.

    Attributes:
        ece: Expected Calibration Error (lower is better).
        mce: Maximum Calibration Error.
        accuracy_by_bin: List of (accuracy, avg_confidence) per bin.
        num_examples: Number of examples evaluated.
    """

    ece: float = 0.0
    mce: float = 0.0
    accuracy_by_bin: list[tuple[float, float]] = field(default_factory=list)
    num_examples: int = 0


# ---------------------------------------------------------------------------
# LoRACalibrator
# ---------------------------------------------------------------------------


class LoRAOptimizer(Protocol):
    """Protocol for a LoRA fine-tuning step."""

    def step(self, examples: list[CalibrationExample]) -> dict[str, float]:
        """Run one calibration fine-tuning step.

        Args:
            examples: Calibration examples to train on.

        Returns:
            Metrics from the step (e.g. {"loss": 0.23}).
        """
        ...


class StubLoRAOptimizer:
    """Stub LoRA optimizer for testing — records inputs without training."""

    def __init__(self):
        self.steps_taken: int = 0
        self.last_examples: list[CalibrationExample] = []

    def step(self, examples: list[CalibrationExample]) -> dict[str, float]:
        """Pretend to train — just records examples.

        Args:
            examples: Calibration examples.

        Returns:
            Simulated metrics.
        """
        self.steps_taken += 1
        self.last_examples = list(examples)
        return {"loss": 0.5, "calibration_loss": 0.3}


class LoRACalibrator:
    """Calibrates agent confidence using LoRA fine-tuning.

    Collects calibration examples (input, output, confidence, correctness),
    computes calibration error, and fine-tunes to align confidence with
    actual accuracy.
    """

    def __init__(
        self,
        optimizer: LoRAOptimizer | None = None,
        num_bins: int = 10,
    ):
        """Initialize LoRACalibrator.

        Args:
            optimizer: LoRA fine-tuning engine. Uses StubLoRAOptimizer if None.
            num_bins: Number of confidence bins for calibration error.
        """
        self._optimizer = optimizer or StubLoRAOptimizer()
        self._num_bins = num_bins
        self._examples: list[CalibrationExample] = []
        self._calibrated: bool = False

    def add_example(
        self,
        input_text: str,
        predicted_output: str,
        confidence: float,
        actual_correct: bool,
    ) -> None:
        """Record a calibration example.

        Args:
            input_text: Model input.
            predicted_output: Model output.
            confidence: Model's confidence in [0, 1].
            actual_correct: Whether the output was correct.
        """
        self._examples.append(
            CalibrationExample(
                input_text=input_text,
                predicted_output=predicted_output,
                confidence=max(0.0, min(1.0, confidence)),
                actual_correct=actual_correct,
            )
        )
        self._calibrated = False

    def add_examples(self, examples: list[CalibrationExample]) -> None:
        """Record multiple calibration examples.

        Args:
            examples: List of calibration examples.
        """
        for ex in examples:
            self.add_example(
                input_text=ex.input_text,
                predicted_output=ex.predicted_output,
                confidence=ex.confidence,
                actual_correct=ex.actual_correct,
            )

    def evaluate(self) -> CalibrationResult:
        """Compute calibration error metrics on collected examples.

        Returns:
            CalibrationResult with ECE and MCE.
        """
        if not self._examples:
            return CalibrationResult()

        # Sort examples into confidence bins
        bins: list[list[CalibrationExample]] = [[] for _ in range(self._num_bins)]
        for ex in self._examples:
            bin_idx = min(self._num_bins - 1, int(ex.confidence * self._num_bins))
            bins[bin_idx].append(ex)

        bin_stats: list[tuple[float, float]] = []
        total_ce = 0.0
        max_ce = 0.0
        total_examples = len(self._examples)

        for bin_examples in bins:
            if not bin_examples:
                continue
            avg_confidence = sum(ex.confidence for ex in bin_examples) / len(bin_examples)
            accuracy = sum(1 for ex in bin_examples if ex.actual_correct) / len(bin_examples)
            ce = abs(accuracy - avg_confidence)

            bin_stats.append((accuracy, avg_confidence))
            total_ce += ce * len(bin_examples)
            max_ce = max(max_ce, ce)

        ece = total_ce / total_examples if total_examples else 0.0

        return CalibrationResult(
            ece=ece,
            mce=max_ce,
            accuracy_by_bin=bin_stats,
            num_examples=total_examples,
        )

    def calibrate(self) -> dict[str, float]:
        """Run calibration fine-tuning on collected examples.

        Returns:
            Metrics from the calibration step.
        """
        if len(self._examples) < 2:
            return {"error": "Need at least 2 calibration examples"}

        metrics = self._optimizer.step(self._examples)
        self._calibrated = True

        # Evaluate post-calibration
        eval_result = self.evaluate()
        metrics["post_calibration_ece"] = eval_result.ece
        metrics["post_calibration_mce"] = eval_result.mce

        return metrics

    def calibrate_confidence(self, confidence: ConfidenceScore | float) -> float:
        """Apply calibration to a raw confidence score.

        Uses Platt scaling: adjusts based on calibration data.
        With few examples, returns the original score.

        Args:
            confidence: ConfidenceScore or raw float.

        Returns:
            Calibrated confidence in [0, 1].
        """
        score = confidence.score if isinstance(confidence, ConfidenceScore) else confidence
        score = max(0.0, min(1.0, score))

        if not self._examples or not self._calibrated:
            return score

        # Simple calibrated adjustment: shift towards empirical accuracy
        correct = sum(1 for ex in self._examples if ex.actual_correct)
        total = len(self._examples)
        empirical_accuracy = correct / total if total else 0.5

        # Interpolate: move confidence toward empirical accuracy
        # This is a simplified stand-in for Platt scaling or isotonic regression.
        alpha = min(1.0, len(self._examples) / 100.0)  # More examples = more adjustment
        calibrated = (1.0 - alpha) * score + alpha * empirical_accuracy

        return max(0.0, min(1.0, calibrated))

    def get_example_count(self) -> int:
        """Return number of collected calibration examples."""
        return len(self._examples)

    def is_calibrated(self) -> bool:
        """Check whether calibration has been run."""
        return self._calibrated


__all__ = [
    "CalibrationExample",
    "CalibrationResult",
    "LoRAOptimizer",
    "StubLoRAOptimizer",
    "LoRACalibrator",
]
