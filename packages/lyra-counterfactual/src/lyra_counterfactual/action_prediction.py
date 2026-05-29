"""Action step — compute intervened SCM outputs and rank actions by expected outcome."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from lyra_causal_graph.scm import StructuralCausalModel

from .errors import ActionPredictionError

logger = logging.getLogger(__name__)

__all__ = [
    "ActionConfig",
    "ActionPrediction",
    "ActionPredictor",
]


# ── Configuration ─────────────────────────────────────────────────────────────


@dataclass
class ActionConfig:
    """Configuration for the action prediction step.

    Attributes:
        n_eval_samples: Number of Monte Carlo samples for outcome evaluation.
        rank_by: Metric to rank actions by ("expected_value", "upper_ci", "lower_ci",
        "probability_improvement").
        default_intervention_strength: Default intervention magnitude.
        random_seed: Seed for reproducibility.
    """

    n_eval_samples: int = 5000
    rank_by: str = "expected_value"
    default_intervention_strength: float = 1.0
    random_seed: int | None = None


@dataclass
class ActionPrediction:
    """Result of applying an action (intervention) and predicting its outcome.

    Attributes:
        action_name: Human-readable action/experiment name.
        intervention: The intervention applied ``{var: value}``.
        target_var: The outcome variable of interest.
        expected_value: Expected outcome value.
        std: Standard deviation of the outcome distribution.
        ci_lower: Lower bound of 95% confidence interval.
        ci_upper: Upper bound of 95% confidence interval.
        outcome_samples: Full outcome sample array.
        probability_improvement: Probability of improvement over baseline.
        metadata: Additional diagnostic info.
    """

    action_name: str
    intervention: dict[str, float]
    target_var: str
    expected_value: float
    std: float = 0.0
    ci_lower: float = 0.0
    ci_upper: float = 0.0
    outcome_samples: np.ndarray | None = None
    probability_improvement: float = 0.5
    metadata: dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        return (
            f"ActionPrediction({self.action_name}: "
            f"E[{self.target_var}]={self.expected_value:.4f} +/- {self.std:.4f})"
        )


# ── Action Predictor ─────────────────────────────────────────────────────────


class ActionPredictor:
    """Applies interventions to an SCM and predicts outcomes.

    Performs the "action" step of the abduction-action-prediction framework:
    for each candidate intervention, compute the interventional distribution
    of the target outcome variable.

    Typical usage::

        predictor = ActionPredictor(scm, noise_posterior=abduction_result.noise_posterior)
        results = predictor.evaluate_actions([
            {"name": "Increase X", "intervention": {"X": 2.0}, "target": "Y"},
            {"name": "Decrease X", "intervention": {"X": -1.0}, "target": "Y"},
        ])
        best = predictor.rank_actions(results)[0]
    """

    def __init__(
        self,
        scm: StructuralCausalModel,
        noise_posterior: dict[str, np.ndarray] | None = None,
        config: ActionConfig | None = None,
    ) -> None:
        if scm is None:
            raise ActionPredictionError("SCM must not be None.")
        self._scm = scm
        self._noise_posterior = noise_posterior or {}
        self._config = config or ActionConfig()
        self._rng = np.random.default_rng(self._config.random_seed)

    @property
    def config(self) -> ActionConfig:
        return self._config

    @property
    def noise_posterior(self) -> dict[str, np.ndarray]:
        return dict(self._noise_posterior)

    def set_noise_posterior(self, posterior: dict[str, np.ndarray]) -> None:
        """Set or update the noise posterior from an abduction step."""
        self._noise_posterior = posterior

    # ── Single Action ───────────────────────────────────────────────────

    def predict(
        self,
        intervention: dict[str, float],
        target_var: str,
        action_name: str = "action",
    ) -> ActionPrediction:
        """Predict the outcome of a single intervention.

        Args:
            intervention: Dict mapping variable names to fixed values.
            target_var: The outcome variable to predict.
            action_name: Label for this action.

        Returns:
            ``ActionPrediction`` with expected outcome and distribution.

        Raises:
            ActionPredictionError: If target or intervention variables are invalid.
        """
        self._validate(intervention, target_var)

        n = self._config.n_eval_samples
        values: dict[str, np.ndarray] = {}

        # Initialize exogenous noise
        for exo_name, exo_var in self._scm.exogenous_vars.items():
            if exo_name in self._noise_posterior:
                # Resample from posterior
                post_vals = self._noise_posterior[exo_name]
                values[exo_name] = self._rng.choice(post_vals, size=n, replace=True)
            else:
                # Use prior
                values[exo_name] = exo_var.sample_noise(n)

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
                else:
                    parent_values[parent] = np.zeros(n)

            noise_vals = values.get(eq.noise_var, np.zeros(n))
            values[var_name] = eq.evaluate(parent_values, noise_vals)

        outcome_samples = values.get(target_var, np.zeros(n))

        expected = float(np.mean(outcome_samples))
        std = float(np.std(outcome_samples))

        from scipy import stats

        ci_mult = stats.norm.ppf(0.975)
        ci_lower = expected - ci_mult * std / np.sqrt(n)
        ci_upper = expected + ci_mult * std / np.sqrt(n)

        return ActionPrediction(
            action_name=action_name,
            intervention=intervention,
            target_var=target_var,
            expected_value=expected,
            std=std,
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            outcome_samples=outcome_samples,
            probability_improvement=0.5,  # updated in evaluate_actions
            metadata={"n_samples": n},
        )

    async def predict_async(
        self,
        intervention: dict[str, float],
        target_var: str,
        action_name: str = "action",
    ) -> ActionPrediction:
        """Async version of ``predict()``."""
        return self.predict(intervention, target_var, action_name)

    # ── Batch Evaluation ────────────────────────────────────────────────

    def evaluate_actions(
        self,
        action_specs: list[dict[str, Any]],
        baseline: dict[str, float] | None = None,
    ) -> list[ActionPrediction]:
        """Evaluate multiple candidate actions.

        Args:
            action_specs: List of dicts with keys:
                - ``name`` (str): Action label.
                - ``intervention`` (dict): Var-to-value mapping.
                - ``target`` (str): Outcome variable.
            baseline: Optional baseline intervention for calculating
                      probability of improvement.

        Returns:
            List of ``ActionPrediction`` results.
        """
        results: list[ActionPrediction] = []

        # Compute baseline if provided
        baseline_pred = None
        if baseline is not None and action_specs:
            first_spec = action_specs[0]
            baseline_pred = self.predict(
                baseline,
                first_spec.get("target", ""),
                action_name="baseline",
            )

        for spec in action_specs:
            name = spec.get("name", "action")
            intervention = spec.get("intervention", {})
            target = spec.get("target", "")

            pred = self.predict(intervention, target, action_name=name)

            # Calculate probability of improvement over baseline
            if (
                baseline_pred is not None
                and pred.outcome_samples is not None
                and baseline_pred.outcome_samples is not None
            ):
                # P(Y_action > Y_baseline)
                prob_improvement = float(
                    np.mean(pred.outcome_samples > baseline_pred.outcome_samples)
                )
                pred.probability_improvement = prob_improvement

            results.append(pred)

        return results

    async def evaluate_actions_async(
        self,
        action_specs: list[dict[str, Any]],
        baseline: dict[str, float] | None = None,
    ) -> list[ActionPrediction]:
        """Async version of ``evaluate_actions()``."""
        return self.evaluate_actions(action_specs, baseline)

    # ── Action Ranking ──────────────────────────────────────────────────

    def rank_actions(
        self,
        predictions: list[ActionPrediction],
        rank_by: str | None = None,
    ) -> list[ActionPrediction]:
        """Rank action predictions by the configured metric.

        Args:
            predictions: List of predictions to rank.
            rank_by: Override ranking metric.

        Returns:
            Sorted list of ``ActionPrediction`` (best first).
        """
        metric = rank_by or self._config.rank_by
        allowed = {"expected_value", "upper_ci", "lower_ci", "probability_improvement"}

        if metric not in allowed:
            raise ActionPredictionError(
                f"Unknown ranking metric '{metric}'. Choose from: {allowed}"
            )

        # Actually for all metrics, higher is better.

        sort_key: Any
        if metric == "expected_value":

            def sort_key(p):
                return p.expected_value  # noqa: E731

        elif metric == "upper_ci":

            def sort_key(p):
                return p.ci_upper  # noqa: E731

        elif metric == "lower_ci":

            def sort_key(p):
                return p.ci_lower  # noqa: E731

        elif metric == "probability_improvement":

            def sort_key(p):
                return p.probability_improvement  # noqa: E731

        else:

            def sort_key(p):
                return p.expected_value  # noqa: E731

        return sorted(predictions, key=sort_key, reverse=True)

    def best_action(
        self,
        predictions: list[ActionPrediction],
    ) -> ActionPrediction | None:
        """Return the highest-ranked action prediction.

        Args:
            predictions: List of predictions.

        Returns:
            The best ``ActionPrediction`` or ``None`` if list is empty.
        """
        ranked = self.rank_actions(predictions)
        return ranked[0] if ranked else None

    # ── Scenario Analysis ───────────────────────────────────────────────

    def what_if_grid(
        self,
        var_name: str,
        values: list[float],
        target_var: str,
    ) -> list[ActionPrediction]:
        """Evaluate a grid of intervention values for a single variable.

        Useful for understanding how varying a treatment affects the outcome.

        Args:
            var_name: Variable to intervene on.
            values: List of values to try.
            target_var: Outcome variable.

        Returns:
            List of ``ActionPrediction`` for each value.
        """
        specs = [
            {
                "name": f"do({var_name}={v})",
                "intervention": {var_name: v},
                "target": target_var,
            }
            for v in values
        ]
        return self.evaluate_actions(specs)

    def what_if_pairwise(
        self,
        interventions: dict[str, list[float]],
        target_var: str,
    ) -> list[ActionPrediction]:
        """Evaluate pairwise combinations of intervention variables.

        Args:
            interventions: Dict mapping var names to lists of values.
            target_var: Outcome variable.

        Returns:
            List of ``ActionPrediction`` for each combination.
        """
        import itertools

        var_names = list(interventions.keys())
        value_lists = [interventions[v] for v in var_names]

        specs = []
        for combo in itertools.product(*value_lists):
            intervention = dict(zip(var_names, combo, strict=False))
            name = "do(" + ", ".join(f"{k}={v}" for k, v in intervention.items()) + ")"
            specs.append(
                {
                    "name": name,
                    "intervention": intervention,
                    "target": target_var,
                }
            )

        return self.evaluate_actions(specs)

    # ── Helpers ─────────────────────────────────────────────────────────

    def _validate(self, intervention: dict[str, float], target_var: str) -> None:
        """Validate inputs before prediction."""
        if not intervention:
            raise ActionPredictionError("At least one intervention variable is required.")

        for var_name in intervention:
            if var_name not in self._scm.endogenous_vars:
                raise ActionPredictionError(f"Intervention variable '{var_name}' not found in SCM.")

        if target_var not in self._scm.endogenous_vars:
            raise ActionPredictionError(f"Target variable '{target_var}' not found in SCM.")

    def __repr__(self) -> str:
        has_posterior = len(self._noise_posterior) > 0
        return f"ActionPredictor(scm={self._scm}, has_posterior={has_posterior})"
