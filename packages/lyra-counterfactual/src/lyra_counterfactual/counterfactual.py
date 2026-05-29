"""Main counterfactual engine — integration, batch generation, confidence, and explanation."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from lyra_causal_graph.scm import StructuralCausalModel

from .abduction import AbductionConfig, AbductionEngine, AbductionResult
from .action_prediction import ActionConfig, ActionPredictor
from .errors import CounterfactualEngineError
from .prediction import PredictionConfig, PredictionEngine, PredictionResult

logger = logging.getLogger(__name__)

__all__ = [
    "CounterfactualEngineConfig",
    "CounterfactualResult",
    "Intervention",
    "CounterfactualEngine",
]


# ── Data Types ────────────────────────────────────────────────────────────────


@dataclass
class Intervention:
    """An intervention specification.

    Attributes:
        action_type: Type of action (e.g. "execute", "set", "perturb").
        source_id: Entity being acted on.
        target_id: Entity being affected.
        parameters: Intervention parameters (e.g. ``{"value": 1.0}``).
    """

    action_type: str
    source_id: str
    target_id: str
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass
class CounterfactualResult:
    """Result of a counterfactual simulation with confidence and explanation.

    Attributes:
        predicted_outcome: Natural language description of the predicted outcome.
        confidence: Confidence score [0, 1].
        causal_path: List of causal path steps.
        alternative_prob: Probability of alternative outcomes.
        expected_value: Numeric expected value (if SCM is available).
        distribution: Outcome distribution samples.
        uncertainty: Standard deviation of predictions.
        explanation: Human-readable explanation.
        metadata: Additional diagnostic info.
    """

    predicted_outcome: str
    confidence: float
    causal_path: list[str]
    alternative_prob: float = 0.0
    expected_value: float | None = None
    distribution: np.ndarray | None = None
    uncertainty: float = 0.0
    explanation: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        return (
            f"CounterfactualResult(confidence={self.confidence:.2f}, "
            f"outcome='{self.predicted_outcome[:60]}...')"
        )


@dataclass
class CounterfactualEngineConfig:
    """Configuration for the counterfactual engine.

    Attributes:
        abduction: Abduction configuration.
        action: Action prediction configuration.
        prediction: Prediction configuration.
        default_target: Default outcome variable.
        enable_explanations: Generate human-readable explanations.
        enable_batch_parallel: Process batch queries concurrently.
    """

    abduction: AbductionConfig = field(default_factory=AbductionConfig)
    action: ActionConfig = field(default_factory=ActionConfig)
    prediction: PredictionConfig = field(default_factory=PredictionConfig)
    default_target: str = "Y"
    enable_explanations: bool = True
    enable_batch_parallel: bool = False


# ── Counterfactual Engine ────────────────────────────────────────────────────


class CounterfactualEngine:
    """Main counterfactual reasoning engine integrating abduction, action, and prediction.

    This engine orchestrates the full three-step counterfactual inference pipeline:

    1. **Abduction**: Infer noise posterior from observed evidence.
    2. **Action**: Apply the intervention to the SCM.
    3. **Prediction**: Compute the counterfactual outcome distribution.

    It works with both legacy ``CausalGraph`` objects (from the original stub)
    and the new ``StructuralCausalModel``.

    Typical usage::

        # With SCM (recommended):
        engine = CounterfactualEngine(scm=my_scm)
        result = engine.simulate({"X": 1.5}, target_var="Y", evidence={"Y": 3.0})

        # With legacy CausalGraph:
        engine = CounterfactualEngine(causal_graph=my_graph)
        intervention = Intervention(action_type="execute", source_id="tool", target_id="file")
        result = await engine.simulate(intervention)

        # Batch:
        results = engine.batch_simulate([
            {"intervention": {"X": 1.0}, "evidence": {"Y": 2.0}},
            {"intervention": {"X": 2.0}, "evidence": {"Y": 2.0}},
        ])
    """

    def __init__(
        self,
        causal_graph: Any | None = None,  # Legacy CausalGraph or new CausalGraph
        scm: StructuralCausalModel | None = None,
        config: CounterfactualEngineConfig | None = None,
    ) -> None:
        self._legacy_graph = causal_graph
        self._scm = scm
        self._config = config or CounterfactualEngineConfig()

        # Initialize sub-engines
        self._abduction_engine: AbductionEngine | None = None
        self._action_predictor: ActionPredictor | None = None
        self._prediction_engine: PredictionEngine | None = None

        if scm is not None:
            self._abduction_engine = AbductionEngine(scm, self._config.abduction)
            self._action_predictor = ActionPredictor(scm, config=self._config.action)
            self._prediction_engine = PredictionEngine(scm, self._config.prediction)

    @property
    def config(self) -> CounterfactualEngineConfig:
        return self._config

    @property
    def graph(self) -> Any | None:
        """The causal graph (legacy or new)."""
        return self._legacy_graph

    @property
    def scm(self) -> StructuralCausalModel | None:
        """The structural causal model (if available)."""
        return self._scm

    def set_scm(self, scm: StructuralCausalModel) -> None:
        """Attach or replace the SCM, reinitializing sub-engines."""
        self._scm = scm
        self._abduction_engine = AbductionEngine(scm, self._config.abduction)
        self._action_predictor = ActionPredictor(scm, config=self._config.action)
        self._prediction_engine = PredictionEngine(scm, self._config.prediction)

    # ── Core API ────────────────────────────────────────────────────────

    def simulate(
        self,
        intervention: Any,
        target_var: str | None = None,
        evidence: dict[str, float] | None = None,
    ) -> CounterfactualResult:
        """Run a single counterfactual simulation.

        Accepts either:
        - A legacy ``Intervention`` object (when using CausalGraph)
        - A dict ``{var: value}`` (when using SCM)

        Args:
            intervention: Intervention spec (``Intervention`` or dict).
            target_var: Target outcome variable (required for SCM mode).
            evidence: Observed evidence for abduction (required for SCM mode).

        Returns:
            ``CounterfactualResult`` with outcome and confidence.

        Raises:
            CounterfactualEngineError: If inputs are invalid.
        """
        # Legacy mode
        if isinstance(intervention, Intervention):
            return self._legacy_simulate(intervention)

        # SCM mode
        if self._scm is None:
            raise CounterfactualEngineError(
                "Either attach an SCM via set_scm() or provide a legacy Intervention."
            )

        intervention_dict = intervention if isinstance(intervention, dict) else {}
        target = target_var or self._config.default_target
        evidence = evidence or {}

        return self._scm_simulate(intervention_dict, target, evidence)

    async def simulate_async(
        self,
        intervention: Any,
        target_var: str | None = None,
        evidence: dict[str, float] | None = None,
    ) -> CounterfactualResult:
        """Async version of ``simulate()``."""
        return self.simulate(intervention, target_var, evidence)

    def batch_simulate(
        self,
        scenarios: list[dict[str, Any]],
    ) -> list[CounterfactualResult]:
        """Run multiple counterfactual simulations in batch.

        Args:
            scenarios: List of dicts with keys:
                - ``intervention`` (dict): Intervention specification.
                - ``evidence`` (dict): Observed evidence.
                - ``target_var`` (str, optional): Target outcome variable.

        Returns:
            List of ``CounterfactualResult`` objects.
        """
        results: list[CounterfactualResult] = []
        for scenario in scenarios:
            result = self.simulate(
                intervention=scenario.get("intervention", {}),
                target_var=scenario.get("target_var"),
                evidence=scenario.get("evidence", {}),
            )
            results.append(result)
        return results

    async def batch_simulate_async(
        self,
        scenarios: list[dict[str, Any]],
    ) -> list[CounterfactualResult]:
        """Async batch counterfactual simulation."""
        import asyncio

        if self._config.enable_batch_parallel and self._scm is not None:
            # Run in parallel
            async def run_one(scenario):
                return self.simulate(
                    intervention=scenario.get("intervention", {}),
                    target_var=scenario.get("target_var"),
                    evidence=scenario.get("evidence", {}),
                )

            return await asyncio.gather(*[run_one(s) for s in scenarios])

        return self.batch_simulate(scenarios)

    # ── SCM-Based Simulation ────────────────────────────────────────────

    def _scm_simulate(
        self,
        intervention: dict[str, float],
        target_var: str,
        evidence: dict[str, float],
    ) -> CounterfactualResult:
        """Full three-step counterfactual inference with SCM."""
        if (
            self._abduction_engine is None
            or self._action_predictor is None
            or self._prediction_engine is None
        ):
            raise CounterfactualEngineError(
                "SCM sub-engines not initialized. Call set_scm() first."
            )

        # Step 1: Abduction
        if evidence:
            abd_result = self._abduction_engine.abduce(evidence)
            self._action_predictor.set_noise_posterior(abd_result.noise_posterior)
        else:
            # No evidence: use prior
            n = self._config.prediction.n_samples
            noise_posterior = {}
            for exo_name, exo_var in self._scm.exogenous_vars.items():
                noise_posterior[exo_name] = exo_var.sample_noise(n)
            abd_result = AbductionResult(
                noise_posterior=noise_posterior,
                evidence_log_prob=0.0,
                converged=True,
                diagnostics={"strategy": "prior"},
            )
            self._action_predictor.set_noise_posterior(noise_posterior)

        # Step 2 & 3: Action + Prediction
        # We do this in one go via the prediction engine for efficiency
        pred_result = self._prediction_engine.predict(
            noise_posterior=abd_result.noise_posterior,
            intervention=intervention,
            target_var=target_var,
        )

        # Build causal path description
        causal_path = self._build_causal_path(intervention, target_var)

        # Build explanation
        explanation = self._build_explanation(
            intervention, target_var, pred_result, evidence, abd_result
        )

        return CounterfactualResult(
            predicted_outcome=self._format_outcome(target_var, pred_result),
            confidence=self._compute_confidence_scm(pred_result, abd_result),
            causal_path=causal_path,
            alternative_prob=self._compute_alternative_prob(pred_result),
            expected_value=pred_result.expected_value,
            distribution=pred_result.samples,
            uncertainty=pred_result.uncertainty.std,
            explanation=explanation,
            metadata={
                "target_var": target_var,
                "intervention": intervention,
                "evidence": evidence,
                "abduction_strategy": abd_result.diagnostics.get("strategy", "unknown"),
                "distribution_type": pred_result.distribution_type,
                "ci_lower": pred_result.ci_lower,
                "ci_upper": pred_result.ci_upper,
            },
        )

    # ── Legacy Simulation (backward compatible) ────────────────────────

    def _legacy_simulate(self, intervention: Intervention) -> CounterfactualResult:
        """Legacy simulation using CausalGraph (from original stub)."""
        if self._legacy_graph is None:
            raise CounterfactualEngineError("No causal graph attached.")

        path = self._trace_causal_path(intervention)
        confidence = self._estimate_legacy_confidence(intervention, path)

        return CounterfactualResult(
            predicted_outcome=self._legacy_predict_outcome(intervention, path),
            confidence=confidence,
            causal_path=path,
            metadata={"mode": "legacy"},
        )

    def _trace_causal_path(self, intervention: Intervention) -> list[str]:
        """Trace causal path using legacy graph API."""
        path: list[str] = []
        source_actions = self._legacy_graph.get_actions_for_entity(intervention.source_id)
        for action in source_actions:
            if action.action_type == intervention.action_type:
                path.append(f"{intervention.source_id}->{action.target_id}")
                outcome = self._legacy_graph.get_outcome_for_action(action.id)
                if outcome:
                    path.append(f"outcome:{outcome.result[:50]}")
        if not path:
            path.append(
                f"{intervention.source_id}->? (no prior {intervention.action_type} actions)"
            )
        return path

    def _estimate_legacy_confidence(self, intervention: Intervention, path: list[str]) -> float:
        """Estimate confidence using transfer entropy."""
        te = self._legacy_graph.compute_li_cte(intervention.source_id, intervention.target_id)
        base = 0.5 + (te * 0.4)
        return min(base, 0.95)

    def _legacy_predict_outcome(self, intervention: Intervention, path: list[str]) -> str:
        if "execute" in intervention.action_type or "call" in intervention.action_type:
            return f"Simulated {intervention.action_type} on {intervention.target_id}"
        return f"Would affect {intervention.target_id} via {intervention.action_type}"

    # ── Confidence Scoring (SCM mode) ──────────────────────────────────

    def _compute_confidence_scm(
        self,
        pred_result: PredictionResult,
        abd_result: AbductionResult,
    ) -> float:
        """Compute a confidence score combining multiple signals.

        Factors:
        - Abduction convergence (did noise posterior fit evidence?)
        - Prediction uncertainty (how tight is the outcome distribution?)
        - Distribution type (bimodal = lower confidence)
        """
        scores: list[float] = []

        # Abduction quality (20%)
        if abd_result.converged:
            scores.append(0.2)
        else:
            scores.append(0.1)

        # Prediction precision (40%)
        std = pred_result.uncertainty.std
        if std < 0.1:
            scores.append(0.4)
        elif std < 1.0:
            scores.append(0.3)
        elif std < 5.0:
            scores.append(0.2)
        else:
            scores.append(0.1)

        # Distribution shape (20%)
        dist_type = pred_result.distribution_type
        if dist_type == "gaussian":
            scores.append(0.2)
        elif dist_type == "skewed":
            scores.append(0.15)
        elif dist_type == "bimodal":
            scores.append(0.1)
        else:
            scores.append(0.15)

        # Sample size (20%)
        n = pred_result.metadata.get("n_samples", self._config.prediction.n_samples)
        size_score = min(0.2, 0.2 * np.log10(n) / 4)
        scores.append(size_score)

        confidence = sum(scores)
        return float(np.clip(confidence, 0.0, 1.0))

    def _compute_alternative_prob(self, pred_result: PredictionResult) -> float:
        """Probability of alternative outcomes (for multimodal distributions)."""
        if pred_result.samples is None:
            return 0.0

        if pred_result.distribution_type == "bimodal":
            # For bimodal, fraction not in primary mode
            median = np.median(pred_result.samples)
            in_primary = np.abs(pred_result.samples - median) < pred_result.uncertainty.std
            return float(1.0 - np.mean(in_primary))

        return 0.0

    # ── Explanation Generation ──────────────────────────────────────────

    def _build_explanation(
        self,
        intervention: dict[str, float],
        target_var: str,
        pred_result: PredictionResult,
        evidence: dict[str, float],
        abd_result: AbductionResult,
    ) -> str:
        """Generate a human-readable explanation of the counterfactual result."""
        if not self._config.enable_explanations:
            return ""

        parts = []

        # Context
        if evidence:
            evidence_str = ", ".join(f"{k}={v}" for k, v in evidence.items())
            parts.append(f"Given observed evidence ({evidence_str}), ")

        # Intervention
        intervention_str = ", ".join(f"do({k}={v})" for k, v in intervention.items())
        parts.append(f"if we intervene with {intervention_str}, ")

        # Outcome
        parts.append(
            f"the expected value of {target_var} is {pred_result.expected_value:.4f} "
            f"(95% CI: [{pred_result.ci_lower:.4f}, {pred_result.ci_upper:.4f}]). "
        )

        # Interpretation
        if evidence and target_var in evidence:
            diff = pred_result.expected_value - evidence[target_var]
            if abs(diff) < pred_result.uncertainty.std:
                parts.append("This intervention has negligible effect.")
            elif diff > 0:
                parts.append(f"This intervention would increase {target_var}.")
            else:
                parts.append(f"This intervention would decrease {target_var}.")

        return "".join(parts)

    def _build_causal_path(
        self,
        intervention: dict[str, float],
        target_var: str,
    ) -> list[str]:
        """Build causal path description from intervention to target."""
        path: list[str] = []

        for var_name, value in intervention.items():
            var_info = self._scm.endogenous_vars.get(var_name)
            if var_info:
                path.append(f"Set {var_name}={value} (was determined by: {var_info.parents})")

        # Find paths to target
        for var_name in intervention:
            target_parents = self._scm.endogenous_vars.get(target_var, None)
            if target_parents and var_name in target_parents.parents:
                path.append(f"{var_name} directly affects {target_var}")
            else:
                path.append(f"{var_name} indirectly affects {target_var}")

        return path

    def _format_outcome(self, target_var: str, pred_result: PredictionResult) -> str:
        """Format the predicted outcome as a readable string."""
        return (
            f"{target_var} = {pred_result.expected_value:.4f} "
            f"(95% CI: [{pred_result.ci_lower:.4f}, {pred_result.ci_upper:.4f}])"
        )

    # ── Sensitivity Analysis ────────────────────────────────────────────

    def sensitivity_analysis(
        self,
        var_name: str,
        values: list[float],
        target_var: str | None = None,
        evidence: dict[str, float] | None = None,
    ) -> list[CounterfactualResult]:
        """Analyze how sensitive the outcome is to different intervention values.

        Args:
            var_name: Variable to vary.
            values: Values to test.
            target_var: Outcome variable.
            evidence: Fixed evidence.

        Returns:
            List of ``CounterfactualResult`` for each value.
        """
        target = target_var or self._config.default_target
        results: list[CounterfactualResult] = []

        for val in values:
            result = self.simulate(
                intervention={var_name: val},
                target_var=target,
                evidence=evidence,
            )
            results.append(result)

        return results

    def __repr__(self) -> str:
        mode = "scm" if self._scm else ("legacy" if self._legacy_graph else "unconfigured")
        return f"CounterfactualEngine(mode={mode})"
