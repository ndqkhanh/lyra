"""Counterfactual reasoning — what-if query answering and abduction-action-prediction."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from scipy import stats

from .errors import CounterfactualError
from .scm import StructuralCausalModel

logger = logging.getLogger(__name__)

__all__ = [
    "CounterfactualQuery",
    "CounterfactualResult",
    "CounterfactualConfig",
    "CounterfactualReasoner",
]


# ── Data Types ────────────────────────────────────────────────────────────────


@dataclass
class CounterfactualQuery:
    """A counterfactual "what-if" question.

    Example: "Given that the patient received treatment A and outcome Y was
    observed, what would Y have been if they received treatment B instead?"

    Attributes:
        variable: The variable to query (e.g. "Y").
        evidence: Dict of observed values at the time of the original event.
        intervention: Dict of values to intervene on (what we change).
    """

    variable: str
    evidence: dict[str, float] = field(default_factory=dict)
    intervention: dict[str, float] = field(default_factory=dict)


@dataclass
class CounterfactualResult:
    """Result of a counterfactual query.

    Attributes:
        query: The original query.
        expected_value: Expected counterfactual outcome.
        distribution: Samples from the counterfactual distribution.
        confidence: Estimated confidence [0, 1].
        explanation: Human-readable explanation string.
        metadata: Additional diagnostic information.
    """

    query: CounterfactualQuery
    expected_value: float
    distribution: np.ndarray | None = None
    confidence: float = 0.5
    explanation: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        return (
            f"CounterfactualResult(E[{self.query.variable}]={self.expected_value:.4f}, "
            f"confidence={self.confidence:.2f})"
        )


@dataclass
class CounterfactualConfig:
    """Configuration for counterfactual reasoning.

    Attributes:
        n_samples: Number of Monte Carlo samples for distribution estimation.
        confidence_level: Confidence interval width (e.g. 0.95).
        random_seed: Seed for reproducibility.
        abductive_noise_tolerance: Tolerance for noise estimation.
        max_iterations: Max iterations for noise inversion.
    """

    n_samples: int = 5000
    confidence_level: float = 0.95
    random_seed: int | None = None
    abductive_noise_tolerance: float = 1e-6
    max_iterations: int = 100


# ── Counterfactual Reasoner ───────────────────────────────────────────────────


class CounterfactualReasoner:
    """Counterfactual reasoning engine using the abduction-action-prediction framework.

    This implements the standard three-step counterfactual inference procedure:

    1. **Abduction**: Infer the posterior distribution of exogenous noise
       variables conditioned on observed evidence.
    2. **Action**: Apply the intervention ``do(X=x)`` by replacing the
       structural equations for intervened variables.
    3. **Prediction**: Compute the counterfactual outcome distribution
       using the modified SCM and the inferred noise posterior.

    Typical usage::

        reasoner = CounterfactualReasoner(scm)
        query = CounterfactualQuery(
            variable="Y",
            evidence={"X": 0.5, "Y": 2.1},
            intervention={"X": 1.0},
        )
        result = reasoner.query(query)
        print(f"Expected Y if X=1.0: {result.expected_value}")
    """

    def __init__(
        self,
        scm: StructuralCausalModel,
        config: CounterfactualConfig | None = None,
    ) -> None:
        self._scm = scm
        self._config = config or CounterfactualConfig()
        self._rng = np.random.default_rng(self._config.random_seed)

    @property
    def config(self) -> CounterfactualConfig:
        return self._config

    @property
    def scm(self) -> StructuralCausalModel:
        return self._scm

    # ── Query API ────────────────────────────────────────────────────────

    def query(self, query: CounterfactualQuery) -> CounterfactualResult:
        """Answer a single counterfactual query.

        Args:
            query: The what-if question to answer.

        Returns:
            ``CounterfactualResult`` with expected value, distribution, and confidence.
        """
        # Step 1: Abduction — infer noise posterior
        noise_posterior = self.abduce(query.evidence)

        # Step 2: Action — apply intervention
        # Step 3: Prediction — compute counterfactual distribution
        cf_samples = self._compute_counterfactual_distribution(
            noise_posterior, query.intervention, query.variable
        )

        expected_value = float(np.mean(cf_samples))
        confidence = self._compute_confidence(cf_samples)

        explanation = self._generate_explanation(query, expected_value, confidence)

        return CounterfactualResult(
            query=query,
            expected_value=expected_value,
            distribution=cf_samples,
            confidence=confidence,
            explanation=explanation,
            metadata={
                "noise_posterior_vars": list(noise_posterior.keys()),
                "n_abduction_samples": len(cf_samples),
                "std": float(np.std(cf_samples)),
            },
        )

    async def query_async(self, query: CounterfactualQuery) -> CounterfactualResult:
        """Async version for long-running queries."""
        return self.query(query)

    def batch_query(self, queries: list[CounterfactualQuery]) -> list[CounterfactualResult]:
        """Answer multiple counterfactual queries.

        Args:
            queries: List of what-if questions.

        Returns:
            List of ``CounterfactualResult`` objects.
        """
        return [self.query(q) for q in queries]

    async def batch_query_async(
        self, queries: list[CounterfactualQuery]
    ) -> list[CounterfactualResult]:
        """Async batch counterfactual query."""
        return self.batch_query(queries)

    # ── Abduction Step ───────────────────────────────────────────────────

    def abduce(self, evidence: dict[str, float]) -> dict[str, np.ndarray]:
        """Infer the posterior distribution of exogenous noise given evidence.

        This inverts the structural equations to find the noise values
        that would produce the observed evidence.

        Args:
            evidence: Dict mapping variable names to observed values.

        Returns:
            Dict mapping exogenous noise variable names to sample arrays
            representing the noise posterior.

        Raises:
            CounterfactualError: If the SCM is incompatible with the evidence.
        """
        if not evidence:
            raise CounterfactualError("At least one piece of evidence is required for abduction.")

        # Validate evidence
        for var_name in evidence:
            if var_name not in self._scm.endogenous_vars:
                raise CounterfactualError(f"Variable '{var_name}' is not in the SCM.")

        n = self._config.n_samples
        noise_posterior: dict[str, np.ndarray] = {}

        # For each exogenous variable, determine noise posterior
        for exo_name, exo_var in self._scm.exogenous_vars.items():
            noise_posterior[exo_name] = exo_var.sample_noise(n)

        # Adjust noise posterior based on evidence
        # Strategy: invert equations for variables with known parents
        ev_order = self._evidence_inversion_order(evidence)

        for var_name in ev_order:
            eq = self._scm.equations.get(var_name)
            if eq is None:
                continue

            observed_val = evidence[var_name]
            var_info = self._scm.endogenous_vars[var_name]

            # Build parent values for this variable
            # Parents could be endogenous (use evidence or prior) or exogenous (noise)
            parent_values: dict[str, np.ndarray] = {}
            for p in var_info.parents:
                if p in evidence:
                    parent_values[p] = np.full(n, evidence[p])
                elif p in self._scm.exogenous_vars:
                    parent_values[p] = noise_posterior.get(p, np.zeros(n))
                elif p in self._scm.endogenous_vars:
                    # Recursively evaluate
                    parent_values[p] = self._evaluate_variable(p, evidence, noise_posterior)

            # Compute expected value of f(parents)
            expected_f = eq.function(parent_values)

            # The noise posterior for this variable is shifted so that
            # observed = f(parents) + noise => noise = observed - f(parents)
            noise_posterior[eq.noise_var] = observed_val - expected_f

        return noise_posterior

    def _evidence_inversion_order(self, evidence: dict[str, float]) -> list[str]:
        """Determine order to invert equations (topological)."""
        order = self._scm.evaluation_order
        return [v for v in order if v in evidence]

    def _evaluate_variable(
        self,
        var_name: str,
        evidence: dict[str, float],
        noise: dict[str, np.ndarray],
    ) -> np.ndarray:
        """Recursively evaluate an endogenous variable given evidence and noise."""
        if var_name in evidence:
            return np.full(self._config.n_samples, evidence[var_name])

        eq = self._scm.equations.get(var_name)
        if eq is None:
            return np.zeros(self._config.n_samples)

        var_info = self._scm.endogenous_vars[var_name]
        parent_vals: dict[str, np.ndarray] = {}
        for p in var_info.parents:
            if p in evidence:
                parent_vals[p] = np.full(self._config.n_samples, evidence[p])
            elif p in noise:
                parent_vals[p] = noise[p]
            else:
                parent_vals[p] = self._evaluate_variable(p, evidence, noise)

        return eq.function(parent_vals) + noise.get(eq.noise_var, np.zeros(self._config.n_samples))

    # ── Prediction Step ──────────────────────────────────────────────────

    def _compute_counterfactual_distribution(
        self,
        noise_posterior: dict[str, np.ndarray],
        intervention: dict[str, float],
        target_var: str,
    ) -> np.ndarray:
        """Compute counterfactual outcomes using modified SCM.

        Args:
            noise_posterior: Abduced noise posterior.
            intervention: Dict of ``{var: fixed_value}``.
            target_var: Variable to predict.

        Returns:
            1D numpy array of counterfactual samples.
        """
        n = self._config.n_samples
        values: dict[str, np.ndarray] = {}

        # Apply intervention to the SCM context
        intervened_vars = set(intervention.keys())
        order = self._scm.evaluation_order

        for var_name in order:
            if var_name in intervened_vars:
                values[var_name] = np.full(n, intervention[var_name])
                continue

            eq = self._scm.equations.get(var_name)
            if eq is None:
                continue

            var_info = self._scm.endogenous_vars[var_name]

            # Gather parent values
            parent_values: dict[str, np.ndarray] = {}
            for p in var_info.parents:
                if p in values:
                    parent_values[p] = values[p]
                elif p in noise_posterior:
                    parent_values[p] = noise_posterior[p]
                elif p in self._scm.exogenous_vars:
                    parent_values[p] = noise_posterior.get(
                        p, self._scm.exogenous_vars[p].sample_noise(n)
                    )
                else:
                    parent_values[p] = np.zeros(n)

            # Add noise (use posterior or fresh)
            noise_vals = noise_posterior.get(eq.noise_var, np.zeros(n))
            values[var_name] = eq.evaluate(parent_values, noise_vals)

        return values.get(target_var, np.zeros(n))

    # ── Confidence Scoring ───────────────────────────────────────────────

    def _compute_confidence(self, samples: np.ndarray) -> float:
        """Compute confidence score for counterfactual prediction.

        Factors:
        - Sample variance (lower variance = higher confidence)
        - Distribution normality (unimodal = higher confidence)
        """
        std = float(np.std(samples))
        n = len(samples)

        # Variance component
        if std < 1e-10:
            var_score = 1.0
        else:
            var_score = 1.0 / (1.0 + std)

        # Normality component (via skew + kurtosis)
        if n > 3:
            skew = float(stats.skew(samples))
            kurt = float(stats.kurtosis(samples))
            normality_penalty = (abs(skew) + abs(kurt)) / 10.0
            normality_score = max(0.0, 1.0 - normality_penalty)
        else:
            normality_score = 0.5

        # Sample size component
        size_score = min(1.0, np.log(n + 1) / np.log(1001))

        confidence = 0.4 * var_score + 0.3 * normality_score + 0.3 * size_score
        return float(np.clip(confidence, 0.0, 1.0))

    # ── Explanation ──────────────────────────────────────────────────────

    def _generate_explanation(
        self,
        query: CounterfactualQuery,
        expected_value: float,
        confidence: float,
    ) -> str:
        """Generate a human-readable explanation of the counterfactual."""
        evidence_desc = ", ".join(f"{k}={v}" for k, v in query.evidence.items())
        intervention_desc = ", ".join(f"{k}={v}" for k, v in query.intervention.items())

        parts = []
        parts.append(f"Given observed evidence ({evidence_desc}), ")
        parts.append(f"if we intervene to set ({intervention_desc}), ")
        parts.append(f"the expected value of {query.variable} is {expected_value:.4f}.")
        parts.append(f" (confidence: {confidence:.1%})")

        return "".join(parts)

    # ── Individual Treatment Effect via Counterfactual ───────────────────

    def estimate_ite(
        self,
        evidence_list: list[dict[str, float]],
        treatment_var: str,
        outcome_var: str,
        treatment_value: float = 1.0,
        control_value: float = 0.0,
    ) -> np.ndarray:
        """Estimate Individual Treatment Effects using counterfactual reasoning.

        For each individual (described by evidence), compute:
        ``ITE_i = E[Y | do(T=1), evidence_i] - E[Y | do(T=0), evidence_i]``

        Args:
            evidence_list: List of per-individual evidence dicts.
            treatment_var: The treatment variable.
            outcome_var: The outcome variable.
            treatment_value: Value for the treatment condition.
            control_value: Value for the control condition.

        Returns:
            1D array of per-individual ITE estimates.
        """
        ite = np.zeros(len(evidence_list))

        for i, evidence in enumerate(evidence_list):
            q_treat = CounterfactualQuery(
                variable=outcome_var,
                evidence=evidence,
                intervention={treatment_var: treatment_value},
            )
            q_control = CounterfactualQuery(
                variable=outcome_var,
                evidence=evidence,
                intervention={treatment_var: control_value},
            )

            r_treat = self.query(q_treat)
            r_control = self.query(q_control)
            ite[i] = r_treat.expected_value - r_control.expected_value

        return ite

    def __repr__(self) -> str:
        return f"CounterfactualReasoner(scm={self._scm})"
