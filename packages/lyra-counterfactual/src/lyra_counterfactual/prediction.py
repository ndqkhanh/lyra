"""Prediction step — counterfactual outcome computation with uncertainty quantification."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from lyra_causal_graph.scm import StructuralCausalModel
from scipy import stats

from .errors import PredictionError

logger = logging.getLogger(__name__)

__all__ = [
    "PredictionConfig",
    "PredictionResult",
    "PredictionEngine",
    "UncertaintyMetrics",
]


# ── Configuration ─────────────────────────────────────────────────────────────


@dataclass
class PredictionConfig:
    """Configuration for counterfactual prediction.

    Attributes:
        n_samples: Number of Monte Carlo samples.
        confidence_level: Confidence interval width (e.g. 0.95 for 95%).
        compute_full_distribution: Whether to retain full sample arrays.
        uncertainty_methods: List of uncertainty metrics to compute.
        random_seed: Seed for reproducibility.
    """

    n_samples: int = 5000
    confidence_level: float = 0.95
    compute_full_distribution: bool = True
    uncertainty_methods: list[str] = field(
        default_factory=lambda: ["std", "entropy", "quantile_range"]
    )
    random_seed: int | None = None


@dataclass
class UncertaintyMetrics:
    """Aggregate uncertainty quantification for a prediction.

    Attributes:
        std: Standard deviation of the outcome distribution.
        variance: Variance.
        entropy: Differential entropy estimate (higher = more uncertain).
        quantile_range: Inter-quantile range.
        coefficient_of_variation: Std / mean (relative uncertainty).
        skewness: Distribution skew.
        kurtosis: Distribution excess kurtosis.
    """

    std: float = 0.0
    variance: float = 0.0
    entropy: float = 0.0
    quantile_range: float = 0.0
    coefficient_of_variation: float = 0.0
    skewness: float = 0.0
    kurtosis: float = 0.0


@dataclass
class PredictionResult:
    """Result of the prediction step.

    Attributes:
        target_var: The variable being predicted.
        expected_value: Point estimate (mean).
        median: Median of the outcome distribution.
        samples: Full sample array (if ``compute_full_distribution`` is True).
        uncertainty: ``UncertaintyMetrics`` object.
        ci_lower: Lower confidence bound.
        ci_upper: Upper confidence bound.
        distribution_type: Detected distribution type (e.g. "gaussian", "bimodal").
        metadata: Additional diagnostic info.
    """

    target_var: str
    expected_value: float
    median: float = 0.0
    samples: np.ndarray | None = None
    uncertainty: UncertaintyMetrics = field(default_factory=UncertaintyMetrics)
    ci_lower: float = 0.0
    ci_upper: float = 0.0
    distribution_type: str = "unknown"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        return (
            f"PredictionResult({self.target_var}: "
            f"E={self.expected_value:.4f}, "
            f"95% CI=[{self.ci_lower:.4f}, {self.ci_upper:.4f}])"
        )


# ── Prediction Engine ────────────────────────────────────────────────────────


class PredictionEngine:
    """Compute counterfactual outcomes and quantify uncertainty.

    This is the final "prediction" step in the abduction-action-prediction
    framework. Given a noise posterior (from abduction) and an intervention
    (from action), it computes the counterfactual distribution of the
    target outcome variable.

    Typical usage::

        engine = PredictionEngine(scm)
        result = engine.predict(
            noise_posterior=abd_result.noise_posterior,
            intervention={"X": 1.0},
            target_var="Y",
        )
        print(f"Expected Y: {result.expected_value} +/- {result.uncertainty.std}")
    """

    def __init__(
        self,
        scm: StructuralCausalModel,
        config: PredictionConfig | None = None,
    ) -> None:
        if scm is None:
            raise PredictionError("SCM must not be None.")
        self._scm = scm
        self._config = config or PredictionConfig()
        self._rng = np.random.default_rng(self._config.random_seed)

    @property
    def config(self) -> PredictionConfig:
        return self._config

    @property
    def scm(self) -> StructuralCausalModel:
        return self._scm

    # ── Core Prediction ─────────────────────────────────────────────────

    def predict(
        self,
        noise_posterior: dict[str, np.ndarray],
        intervention: dict[str, float],
        target_var: str,
    ) -> PredictionResult:
        """Compute the counterfactual outcome distribution.

        Args:
            noise_posterior: Abduced noise posterior (from ``AbductionEngine``).
            intervention: Intervened values (from ``ActionPredictor``).
            target_var: The outcome variable to predict.

        Returns:
            ``PredictionResult`` with distribution and uncertainty metrics.

        Raises:
            PredictionError: If inputs are invalid or computation fails.
        """
        self._validate(noise_posterior, intervention, target_var)

        n = self._config.n_samples
        values: dict[str, np.ndarray] = {}

        # Resample noise from posterior
        for exo_name in self._scm.exogenous_vars:
            if exo_name in noise_posterior:
                post_vals = noise_posterior[exo_name]
                if len(post_vals) > 0:
                    values[exo_name] = self._rng.choice(post_vals, size=n, replace=True)
                else:
                    values[exo_name] = np.zeros(n)
            else:
                # Prior sample
                values[exo_name] = self._scm.exogenous_vars[exo_name].sample_noise(n)

        # Evaluate SCM with intervention
        intervened_vars = set(intervention.keys())

        for var_name in self._scm.evaluation_order:
            if var_name in intervened_vars:
                values[var_name] = np.full(n, intervention[var_name])
                continue

            eq = self._scm.equations.get(var_name)
            if eq is None:
                continue

            var_info = self._scm.endogenous_vars[var_name]
            parent_values: dict[str, np.ndarray] = {}

            for parent in var_info.parents:
                if parent in values:
                    parent_values[parent] = values[parent]
                elif parent in noise_posterior:
                    parent_values[parent] = self._rng.choice(
                        noise_posterior[parent], size=n, replace=True
                    )
                elif parent in self._scm.exogenous_vars:
                    parent_values[parent] = values.get(parent, np.zeros(n))
                else:
                    parent_values[parent] = np.zeros(n)

            noise_vals = values.get(eq.noise_var, np.zeros(n))
            values[var_name] = eq.evaluate(parent_values, noise_vals)

        outcome_samples = values.get(target_var)
        if outcome_samples is None:
            raise PredictionError(f"Failed to compute values for target variable '{target_var}'.")

        # Compute statistics
        expected = float(np.mean(outcome_samples))
        median = float(np.median(outcome_samples))
        uncertainty = self._compute_uncertainty(outcome_samples)

        alpha = 1 - self._config.confidence_level
        ci_lower = float(np.percentile(outcome_samples, 100 * alpha / 2))
        ci_upper = float(np.percentile(outcome_samples, 100 * (1 - alpha / 2)))

        distribution_type = self._detect_distribution_type(outcome_samples)

        result = PredictionResult(
            target_var=target_var,
            expected_value=expected,
            median=median,
            samples=outcome_samples if self._config.compute_full_distribution else None,
            uncertainty=uncertainty,
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            distribution_type=distribution_type,
            metadata={
                "n_samples": n,
                "confidence_level": self._config.confidence_level,
                "intervention": intervention,
            },
        )

        logger.debug(
            "Prediction for %s: %.4f [%.4f, %.4f]", target_var, expected, ci_lower, ci_upper
        )
        return result

    async def predict_async(
        self,
        noise_posterior: dict[str, np.ndarray],
        intervention: dict[str, float],
        target_var: str,
    ) -> PredictionResult:
        """Async version of ``predict()``."""
        return self.predict(noise_posterior, intervention, target_var)

    def batch_predict(
        self,
        scenarios: list[dict[str, Any]],
    ) -> list[PredictionResult]:
        """Batch prediction for multiple scenarios.

        Args:
            scenarios: List of dicts with keys:
                - ``noise_posterior``: Abduced noise posterior.
                - ``intervention``: Intervened values.
                - ``target_var``: Outcome variable.

        Returns:
            List of ``PredictionResult``.
        """
        results: list[PredictionResult] = []
        for scenario in scenarios:
            result = self.predict(
                noise_posterior=scenario["noise_posterior"],
                intervention=scenario["intervention"],
                target_var=scenario["target_var"],
            )
            results.append(result)
        return results

    # ── Uncertainty Quantification ──────────────────────────────────────

    def _compute_uncertainty(self, samples: np.ndarray) -> UncertaintyMetrics:
        """Compute comprehensive uncertainty metrics from outcome samples.

        Args:
            samples: 1D numpy array of outcome samples.

        Returns:
            ``UncertaintyMetrics`` dataclass.
        """
        if len(samples) < 2:
            return UncertaintyMetrics()

        std = float(np.std(samples))
        variance = float(np.var(samples))
        mean = float(np.mean(samples))

        # Coefficient of variation
        cv = (std / abs(mean)) if abs(mean) > 1e-10 else float("inf")

        # Entropy (differential, via histogram)
        entropy = 0.0
        if "entropy" in self._config.uncertainty_methods and len(samples) >= 10:
            hist, bin_edges = np.histogram(samples, bins="auto", density=True)
            bin_widths = np.diff(bin_edges)
            # Differential entropy: -sum(p * log(p) * width) for p > 0
            nonzero = hist > 0
            if nonzero.any():
                entropy = -float(
                    np.sum(hist[nonzero] * np.log(hist[nonzero] + 1e-10) * bin_widths[0])
                )

        # Quantile range
        quantile_range = 0.0
        if "quantile_range" in self._config.uncertainty_methods:
            quantile_range = float(np.percentile(samples, 90) - np.percentile(samples, 10))

        # Shape
        skewness = 0.0
        kurtosis = 0.0
        if len(samples) >= 4:
            skewness = float(stats.skew(samples))
            kurtosis = float(stats.kurtosis(samples))

        return UncertaintyMetrics(
            std=std,
            variance=variance,
            entropy=entropy,
            quantile_range=quantile_range,
            coefficient_of_variation=cv,
            skewness=skewness,
            kurtosis=kurtosis,
        )

    def _detect_distribution_type(self, samples: np.ndarray) -> str:
        """Heuristically classify the outcome distribution shape.

        Returns one of: "gaussian", "bimodal", "skewed", "heavy_tailed", "uniform"
        """
        if len(samples) < 10:
            return "insufficient_data"

        skew = stats.skew(samples)
        kurt = stats.kurtosis(samples)

        # Check for bimodality
        hist, _ = np.histogram(samples, bins=min(50, len(samples) // 10))
        # Simple bimodality check: two prominent peaks
        peaks = 0
        for i in range(1, len(hist) - 1):
            if hist[i] > hist[i - 1] and hist[i] > hist[i + 1]:
                if hist[i] > np.mean(hist) * 1.5:
                    peaks += 1
        if peaks >= 2:
            return "bimodal"

        # Check for skew
        if abs(skew) > 1.0:
            return "skewed"

        # Check for heavy tails
        if abs(kurt) > 3.0:
            return "heavy_tailed"

        # Check for uniformity
        if abs(kurt + 1.2) < 0.3:  # Uniform has kurtosis ≈ -1.2
            return "uniform"

        # Default to Gaussian
        if abs(skew) < 0.5 and abs(kurt) < 1.0:
            return "gaussian"

        return "unknown"

    # ── Comparison Utilities ────────────────────────────────────────────

    def compare_scenarios(
        self,
        results: list[PredictionResult],
        names: list[str] | None = None,
    ) -> dict[str, Any]:
        """Compare multiple prediction scenarios.

        Args:
            results: List of prediction results to compare.
            names: Optional labels for each result.

        Returns:
            Comparison dict with pairwise differences and rankings.
        """
        if names is None:
            names = [f"Scenario_{i}" for i in range(len(results))]

        comparison: dict[str, Any] = {
            "scenarios": [],
            "pairwise_differences": {},
            "best_scenario": None,
            "worst_scenario": None,
        }

        # Collect scenario summaries
        best_idx = 0
        worst_idx = 0
        best_val = -float("inf")
        worst_val = float("inf")

        for i, (result, name) in enumerate(zip(results, names, strict=False)):
            summary = {
                "name": name,
                "target": result.target_var,
                "expected": result.expected_value,
                "ci_lower": result.ci_lower,
                "ci_upper": result.ci_upper,
                "std": result.uncertainty.std,
            }
            comparison["scenarios"].append(summary)

            if result.expected_value > best_val:
                best_val = result.expected_value
                best_idx = i
            if result.expected_value < worst_val:
                worst_val = result.expected_value
                worst_idx = i

        comparison["best_scenario"] = names[best_idx] if results else None
        comparison["worst_scenario"] = names[worst_idx] if results else None

        # Pairwise differences
        for i in range(len(results)):
            for j in range(i + 1, len(results)):
                if results[i].samples is not None and results[j].samples is not None:
                    diff = results[i].expected_value - results[j].expected_value
                    prob_i_better = float(np.mean(results[i].samples > results[j].samples))
                    comparison["pairwise_differences"][f"{names[i]} vs {names[j]}"] = {
                        "mean_difference": diff,
                        "prob_first_better": prob_i_better,
                    }

        return comparison

    def probability_better_than(
        self,
        result: PredictionResult,
        threshold: float,
    ) -> float:
        """Probability that the outcome exceeds a threshold.

        Args:
            result: Prediction result.
            threshold: Threshold value.

        Returns:
            Probability in [0, 1].
        """
        if result.samples is None:
            # Approximate using normal CDF
            z = (threshold - result.expected_value) / max(result.uncertainty.std, 1e-10)
            return 1.0 - float(stats.norm.cdf(z))

        return float(np.mean(result.samples > threshold))

    # ── Helpers ─────────────────────────────────────────────────────────

    def _validate(
        self,
        noise_posterior: dict[str, np.ndarray],
        intervention: dict[str, float],
        target_var: str,
    ) -> None:
        """Validate prediction inputs."""
        if not noise_posterior:
            raise PredictionError("Noise posterior is required. Run abduction first.")

        if not intervention:
            raise PredictionError("At least one intervention is required.")

        if target_var not in self._scm.endogenous_vars:
            raise PredictionError(f"Target variable '{target_var}' not found in SCM.")

        for var_name in intervention:
            if var_name not in self._scm.endogenous_vars:
                raise PredictionError(f"Intervention variable '{var_name}' not found in SCM.")

    def __repr__(self) -> str:
        return f"PredictionEngine(scm={self._scm})"
