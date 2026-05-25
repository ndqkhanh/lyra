"""Intervention modeling — do-calculus, treatment effect estimation, and adjustment."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Union

import numpy as np
from scipy import stats

from .causal_graph import CausalGraph, EdgeType
from .errors import AdjustmentError, EstimationError, InterventionError
from .scm import StructuralCausalModel

logger = logging.getLogger(__name__)

__all__ = [
    "InterventionConfig",
    "InterventionResult",
    "TreatmentEffect",
    "InterventionModel",
    "AdjustmentMethod",
    "BackdoorAdjuster",
    "FrontdoorAdjuster",
]


# ── Configuration & Data Types ────────────────────────────────────────────────


class AdjustmentMethod(Enum):
    """Available adjustment strategies for causal effect estimation."""

    BACKDOOR = "backdoor"
    FRONTDOOR = "frontdoor"
    INVERSE_PROPENSITY = "ipw"
    DO_CALCULUS = "do-calculus"
    REGRESSION = "regression"


@dataclass
class InterventionConfig:
    """Configuration for intervention modeling.

    Attributes:
        adjustment_method: Default adjustment strategy.
        confidence_level: Confidence interval width (e.g. 0.95).
        n_bootstrap: Number of bootstrap resamples for uncertainty.
        stabilize_weights: Clip propensity weights to reduce variance.
        max_propensity_weight: Maximum allowed propensity weight.
        random_seed: Seed for reproducibility.
        min_samples: Minimum samples required for estimation.
    """

    adjustment_method: AdjustmentMethod = AdjustmentMethod.BACKDOOR
    confidence_level: float = 0.95
    n_bootstrap: int = 1000
    stabilize_weights: bool = True
    max_propensity_weight: float = 10.0
    random_seed: Optional[int] = None
    min_samples: int = 10


@dataclass
class InterventionResult:
    """Result of an intervention query ``P(Y | do(X=x))``.

    Attributes:
        treatment: Treatment variable name.
        outcome: Outcome variable name.
        treatment_value: Value treatment was set to.
        ate: Average Treatment Effect estimate.
        ci_lower: Lower bound of confidence interval.
        ci_upper: Upper bound of confidence interval.
        method: Adjustment method used.
        standard_error: Standard error of the estimate.
        adjusted_values: Adjusted outcomes per sample.
        metadata: Additional information.
    """

    treatment: str
    outcome: str
    treatment_value: float
    ate: float
    ci_lower: float
    ci_upper: float
    method: AdjustmentMethod
    standard_error: float = 0.0
    adjusted_values: Optional[np.ndarray] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        return (
            f"InterventionResult(do({self.treatment}={self.treatment_value}), "
            f"ATE={self.ate:.4f} [{self.ci_lower:.4f}, {self.ci_upper:.4f}])"
        )


@dataclass
class TreatmentEffect:
    """Container for various treatment effect estimates.

    Attributes:
        ate: Average Treatment Effect: ``E[Y(1) - Y(0)]``.
        att: Average Treatment Effect on the Treated.
        atu: Average Treatment Effect on the Untreated.
        cate: Conditional ATE for subgroups.
        ite: Individual Treatment Effects (one per sample).
    """

    ate: float
    att: Optional[float] = None
    atu: Optional[float] = None
    cate: Optional[dict[str, float]] = None
    ite: Optional[np.ndarray] = None


# ── Intervention Model ────────────────────────────────────────────────────────


class InterventionModel:
    """Core intervention engine implementing do-calculus and adjustment methods.

    Supports:
    - do-calculus queries via backdoor/front-door/IPW adjustment
    - ATE, CATE, ITE estimation
    - Bootstrap-based confidence intervals
    - Integration with both CausalGraph and StructuralCausalModel

    Typical usage::

        model = InterventionModel()
        result = model.estimate_ate(data, "X", "Y")
        # Or with a causal graph:
        result = model.do(data, "X", value=1.0, outcome="Y", graph=causal_graph)
    """

    def __init__(self, config: Optional[InterventionConfig] = None) -> None:
        self._config = config or InterventionConfig()

    @property
    def config(self) -> InterventionConfig:
        return self._config

    # ── do-calculus Query ────────────────────────────────────────────────

    def do(
        self,
        data: dict[str, np.ndarray],
        treatment: str,
        value: float,
        outcome: str,
        graph: Optional[CausalGraph] = None,
        scm: Optional[StructuralCausalModel] = None,
        method: Optional[AdjustmentMethod] = None,
    ) -> InterventionResult:
        """Estimate ``E[outcome | do(treatment=value)]``.

        Args:
            data: Dict mapping variable names to 1D numpy arrays.
            treatment: The variable being intervened on.
            value: The value to set the treatment to.
            outcome: The outcome variable.
            graph: Optional causal graph for adjustment set discovery.
            scm: Optional SCM for SCM-based intervention.
            method: Override adjustment method.

        Returns:
            ``InterventionResult`` with ATE and confidence intervals.

        Raises:
            InterventionError: If required data is missing or insufficient.
        """
        _validate_data(data, treatment, outcome, self._config.min_samples)

        selected_method = method or self._config.adjustment_method

        if scm is not None:
            return self._scm_intervention(scm, treatment, value, outcome)

        if graph is not None:
            return self._graph_based_intervention(data, treatment, value, outcome, graph, selected_method)

        # Fallback: regression-based estimation without graph
        return self._regression_intervention(data, treatment, value, outcome)

    async def do_async(
        self,
        data: dict[str, np.ndarray],
        treatment: str,
        value: float,
        outcome: str,
        graph: Optional[CausalGraph] = None,
        scm: Optional[StructuralCausalModel] = None,
        method: Optional[AdjustmentMethod] = None,
    ) -> InterventionResult:
        """Async version of ``do()`` for long-running computations."""
        return self.do(data, treatment, value, outcome, graph, scm, method)

    # ── Treatment Effect Estimation ──────────────────────────────────────

    def estimate_ate(
        self,
        data: dict[str, np.ndarray],
        treatment: str,
        outcome: str,
        graph: Optional[CausalGraph] = None,
        covariates: Optional[list[str]] = None,
    ) -> float:
        """Estimate the Average Treatment Effect (ATE).

        ``ATE = E[Y(1) - Y(0)]``

        Args:
            data: Observed data.
            treatment: Treatment variable (binary or continuous).
            outcome: Outcome variable.
            graph: Optional causal graph.
            covariates: Optional adjustment set.

        Returns:
            The ATE estimate.
        """
        result_1 = self.do(data, treatment, 1.0, outcome, graph)
        result_0 = self.do(data, treatment, 0.0, outcome, graph)
        return result_1.ate - result_0.ate

    def estimate_cate(
        self,
        data: dict[str, np.ndarray],
        treatment: str,
        outcome: str,
        group_var: str,
        graph: Optional[CausalGraph] = None,
    ) -> dict[str, float]:
        """Estimate Conditional Average Treatment Effects by subgroup.

        Args:
            data: Observed data.
            treatment: Treatment variable.
            outcome: Outcome variable.
            group_var: Variable defining subgroups.
            graph: Optional causal graph.

        Returns:
            Dict mapping group labels to CATE estimates.
        """
        if group_var not in data:
            raise EstimationError(f"Group variable '{group_var}' not found in data.")

        groups = np.unique(data[group_var])
        cate: dict[str, float] = {}

        for group_val in groups:
            mask = data[group_var] == group_val
            sub_data = {k: v[mask] for k, v in data.items()}
            if len(next(iter(sub_data.values()))) < self._config.min_samples:
                logger.warning("Group '%s' has too few samples; skipping.", group_val)
                continue
            result_1 = self.do(sub_data, treatment, 1.0, outcome, graph)
            result_0 = self.do(sub_data, treatment, 0.0, outcome, graph)
            cate[str(group_val)] = result_1.ate - result_0.ate

        return cate

    def estimate_ite(
        self,
        data: dict[str, np.ndarray],
        treatment: str,
        outcome: str,
        graph: Optional[CausalGraph] = None,
    ) -> np.ndarray:
        """Estimate Individual Treatment Effects.

        Uses a simple difference-in-observed-outcomes approach. For more
        sophisticated ITE estimation, use the counterfactual module.

        Args:
            data: Observed data.
            treatment: Treatment variable.
            outcome: Outcome variable.
            graph: Optional causal graph.

        Returns:
            1D numpy array of per-sample ITE estimates.
        """
        Treatment = data[treatment]
        Outcome = data[outcome]

        n = len(Treatment)
        ite = np.zeros(n)

        # Simple matching estimator: for each unit, find nearest neighbour
        # with opposite treatment status
        treated_idx = np.where(Treatment > np.median(Treatment))[0]
        control_idx = np.where(Treatment <= np.median(Treatment))[0]

        for i in range(n):
            if i in treated_idx:
                # Find closest control unit
                diffs = np.abs(Treatment[i] - Treatment[control_idx])
                if len(diffs) > 0:
                    nearest = control_idx[np.argmin(diffs)]
                    ite[i] = Outcome[i] - Outcome[nearest]
            else:
                diffs = np.abs(Treatment[i] - Treatment[treated_idx])
                if len(diffs) > 0:
                    nearest = treated_idx[np.argmin(diffs)]
                    ite[i] = Outcome[nearest] - Outcome[i]

        return ite

    def estimate_all_effects(
        self,
        data: dict[str, np.ndarray],
        treatment: str,
        outcome: str,
        graph: Optional[CausalGraph] = None,
        group_var: Optional[str] = None,
    ) -> TreatmentEffect:
        """Compute ATE, ATT, ATU, CATE (if group_var given), and ITE.

        Args:
            data: Observed data.
            treatment: Treatment variable.
            outcome: Outcome variable.
            graph: Optional causal graph.
            group_var: Optional subgroup variable for CATE.

        Returns:
            ``TreatmentEffect`` dataclass.
        """
        Treatment = data[treatment]
        Outcome = data[outcome]

        ate = self.estimate_ate(data, treatment, outcome, graph)

        median_t = np.median(Treatment)
        treated_mask = Treatment > median_t
        untreated_mask = ~treated_mask

        # ATT
        att = None
        if treated_mask.sum() >= self._config.min_samples:
            t_data = {k: v[treated_mask] for k, v in data.items()}
            r1 = self.do(t_data, treatment, 1.0, outcome, graph)
            r0 = self.do(t_data, treatment, 0.0, outcome, graph)
            att = r1.ate - r0.ate

        # ATU
        atu = None
        if untreated_mask.sum() >= self._config.min_samples:
            u_data = {k: v[untreated_mask] for k, v in data.items()}
            r1 = self.do(u_data, treatment, 1.0, outcome, graph)
            r0 = self.do(u_data, treatment, 0.0, outcome, graph)
            atu = r1.ate - r0.ate

        # CATE
        cate = None
        if group_var and group_var in data:
            cate = self.estimate_cate(data, treatment, outcome, group_var, graph)

        # ITE
        ite = self.estimate_ite(data, treatment, outcome, graph)

        return TreatmentEffect(ate=ate, att=att, atu=atu, cate=cate, ite=ite)

    # ── Internal Methods ─────────────────────────────────────────────────

    def _scm_intervention(
        self, scm: StructuralCausalModel, treatment: str, value: float, outcome: str
    ) -> InterventionResult:
        """Use SCM for intervention estimation."""
        n_samples = 5000
        intervened = scm.intervene({treatment: value}).sample(n=n_samples)
        y_vals = intervened[outcome]
        ate = float(np.mean(y_vals))
        se = float(np.std(y_vals) / np.sqrt(n_samples))
        z = stats.norm.ppf(1 - (1 - self._config.confidence_level) / 2)

        return InterventionResult(
            treatment=treatment,
            outcome=outcome,
            treatment_value=value,
            ate=ate,
            ci_lower=ate - z * se,
            ci_upper=ate + z * se,
            method=AdjustmentMethod.DO_CALCULUS,
            standard_error=se,
            adjusted_values=y_vals,
        )

    def _graph_based_intervention(
        self,
        data: dict[str, np.ndarray],
        treatment: str,
        value: float,
        outcome: str,
        graph: CausalGraph,
        method: AdjustmentMethod,
    ) -> InterventionResult:
        """Use causal graph to identify adjustment sets."""
        if method == AdjustmentMethod.BACKDOOR:
            return BackdoorAdjuster().adjust(data, treatment, value, outcome, graph, self._config)
        elif method == AdjustmentMethod.FRONTDOOR:
            return FrontdoorAdjuster().adjust(data, treatment, value, outcome, graph, self._config)
        elif method == AdjustmentMethod.INVERSE_PROPENSITY:
            return self._ipw_estimate(data, treatment, value, outcome, graph)
        else:
            return self._regression_intervention(data, treatment, value, outcome)

    def _ipw_estimate(
        self,
        data: dict[str, np.ndarray],
        treatment: str,
        value: float,
        outcome: str,
        graph: CausalGraph,
    ) -> InterventionResult:
        """Inverse Probability Weighting estimation."""
        Treatment = data[treatment]
        Outcome = data[outcome]
        parents = graph.parents(treatment)

        # Estimate propensity scores via logistic regression
        if parents:
            parent_matrix = np.column_stack([data[p] for p in parents])
            parent_matrix = np.column_stack([np.ones(len(Treatment)), parent_matrix])
        else:
            parent_matrix = np.ones((len(Treatment), 1))

        try:
            beta = np.linalg.lstsq(parent_matrix, Treatment, rcond=None)[0]
            propensity = parent_matrix @ beta
        except np.linalg.LinAlgError:
            propensity = np.full_like(Treatment, np.mean(Treatment))

        # IPW weights
        weights = np.where(
            np.abs(Treatment - value) < np.std(Treatment) / 2,
            1.0 / np.maximum(np.abs(propensity), 1e-10),
            0.0,
        )

        if self._config.stabilize_weights:
            weights = np.clip(weights, 0, self._config.max_propensity_weight)

        weights = weights / weights.sum() * len(Treatment)

        ate = float(np.average(Outcome, weights=weights))
        se = float(np.std(Outcome) / np.sqrt(len(Outcome)))
        z = stats.norm.ppf(1 - (1 - self._config.confidence_level) / 2)

        return InterventionResult(
            treatment=treatment,
            outcome=outcome,
            treatment_value=value,
            ate=ate,
            ci_lower=ate - z * se,
            ci_upper=ate + z * se,
            method=AdjustmentMethod.INVERSE_PROPENSITY,
            standard_error=se,
        )

    def _regression_intervention(
        self,
        data: dict[str, np.ndarray],
        treatment: str,
        value: float,
        outcome: str,
    ) -> InterventionResult:
        """Fallback regression-based intervention estimation."""
        Treatment = data[treatment]
        Outcome = data[outcome]
        n = len(Treatment)

        X = np.column_stack([np.ones(n), Treatment])
        try:
            beta = np.linalg.lstsq(X, Outcome, rcond=None)[0]
        except np.linalg.LinAlgError:
            ate = float(np.mean(Outcome))
            se = float(np.std(Outcome) / np.sqrt(n))
        else:
            ate = float(beta[0] + beta[1] * value)
            residuals = Outcome - (X @ beta)
            se = float(np.std(residuals) / np.sqrt(n))

        z = stats.norm.ppf(1 - (1 - self._config.confidence_level) / 2)

        return InterventionResult(
            treatment=treatment,
            outcome=outcome,
            treatment_value=value,
            ate=ate,
            ci_lower=ate - z * se,
            ci_upper=ate + z * se,
            method=AdjustmentMethod.REGRESSION,
            standard_error=se,
        )


# ── Backdoor Adjustment ──────────────────────────────────────────────────────


class BackdoorAdjuster:
    """Backdoor adjustment for causal effect estimation.

    The backdoor criterion: a set ``Z`` satisfies the backdoor criterion
    relative to ``(X, Y)`` if:
    1. No node in ``Z`` is a descendant of ``X``.
    2. ``Z`` blocks every path between ``X`` and ``Y`` with an arrow into ``X``.

    ``P(Y | do(X=x)) = sum_z P(Y | X=x, Z=z) * P(Z=z)``
    """

    def find_adjustment_set(self, graph: CausalGraph, treatment: str, outcome: str) -> list[str]:
        """Find a valid backdoor adjustment set.

        Args:
            graph: The causal graph.
            treatment: Treatment variable.
            outcome: Outcome variable.

        Returns:
            List of variable names comprising the adjustment set.

        Raises:
            AdjustmentError: If no valid backdoor set can be found.
        """
        # Backdoor set = parents of treatment that are not descendants
        candidate_parents = graph.parents(treatment)
        descendants_of_treatment = graph.descendants(treatment)

        adjustment_set = [p for p in candidate_parents if p not in descendants_of_treatment]

        if not adjustment_set:
            # Broader search: find all nodes that block backdoor paths
            ancestors_of_treatment = graph.ancestors(treatment)
            adjustment_set = sorted(
                ancestors_of_treatment - descendants_of_treatment - {treatment, outcome}
            )

        if not adjustment_set:
            # If no confounders exist (simple X->Y), no adjustment needed
            # Return empty set and estimate directly
            logger.debug(
                "No confounders found for (%s -> %s); no adjustment needed.",
                treatment, outcome,
            )
            return []

        logger.debug(
            "Backdoor adjustment set for %s->%s: %s",
            treatment, outcome, adjustment_set,
        )
        return adjustment_set

    def adjust(
        self,
        data: dict[str, np.ndarray],
        treatment: str,
        value: float,
        outcome: str,
        graph: CausalGraph,
        config: InterventionConfig,
    ) -> InterventionResult:
        """Perform backdoor adjustment.

        ``E[Y | do(X=x)] = E_Z[E[Y | X=x, Z]]``
        """
        adj_set = self.find_adjustment_set(graph, treatment, outcome)
        Treatment = data[treatment]
        Outcome = data[outcome]
        n = len(Treatment)

        # Build regression with adjustment variables
        covar_names = [treatment] + adj_set
        X = np.column_stack([np.ones(n)] + [data[c] for c in covar_names])

        try:
            beta = np.linalg.lstsq(X, Outcome, rcond=None)[0]
        except np.linalg.LinAlgError:
            raise AdjustmentError("Backdoor adjustment failed: singular matrix.")

        # Predict at treatment=value, averaged over adjustment set
        # E[Y | do(X=x)] = (1/n) * sum_i E[Y | X=x, Z=z_i]
        X_do = np.column_stack([np.ones(n), np.full(n, value)] + [data[c] for c in adj_set])
        adjusted_y = X_do @ beta
        ate = float(np.mean(adjusted_y))

        residuals = Outcome - (X @ beta)
        se = float(np.std(residuals) / np.sqrt(n))
        z = stats.norm.ppf(1 - (1 - config.confidence_level) / 2)

        # Bootstrap CI
        ci_lower, ci_upper = self._bootstrap_ci(
            data, treatment, value, outcome, adj_set, config
        )

        return InterventionResult(
            treatment=treatment,
            outcome=outcome,
            treatment_value=value,
            ate=ate,
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            method=AdjustmentMethod.BACKDOOR,
            standard_error=se,
            adjusted_values=adjusted_y,
            metadata={"adjustment_set": adj_set},
        )

    def _bootstrap_ci(
        self,
        data: dict[str, np.ndarray],
        treatment: str,
        value: float,
        outcome: str,
        adj_set: list[str],
        config: InterventionConfig,
    ) -> tuple[float, float]:
        """Bootstrap confidence interval for backdoor adjustment."""
        n = len(data[treatment])
        estimates: list[float] = []
        rng = np.random.default_rng(config.random_seed)

        for _ in range(min(config.n_bootstrap, 200)):  # cap for performance
            idx = rng.choice(n, size=n, replace=True)
            boot_data = {k: v[idx] for k, v in data.items()}
            boot_T = boot_data[treatment]
            boot_O = boot_data[outcome]
            X = np.column_stack([np.ones(n), boot_T] + [boot_data[c] for c in adj_set])
            try:
                beta = np.linalg.lstsq(X, boot_O, rcond=None)[0]
                X_do = np.column_stack([np.ones(n), np.full(n, value)] + [boot_data[c] for c in adj_set])
                est = float(np.mean(X_do @ beta))
                estimates.append(est)
            except np.linalg.LinAlgError:
                continue

        if len(estimates) < 2:
            ate = float(np.mean(estimates)) if estimates else 0.0
            return ate, ate

        alpha = 1 - config.confidence_level
        ci_lower = float(np.percentile(estimates, 100 * alpha / 2))
        ci_upper = float(np.percentile(estimates, 100 * (1 - alpha / 2)))
        return ci_lower, ci_upper


# ── Frontdoor Adjustment ──────────────────────────────────────────────────────


class FrontdoorAdjuster:
    """Frontdoor adjustment for causal effect estimation.

    The frontdoor criterion applies when there is an unobserved confounder
    but a mediator ``M`` satisfies:
    1. ``M`` mediates all causal paths from ``X`` to ``Y``.
    2. There is no unblocked backdoor path from ``X`` to ``M``.
    3. All backdoor paths from ``M`` to ``Y`` are blocked by ``X``.

    ``P(Y | do(X=x)) = sum_m P(m | do(X=x)) * sum_x' P(Y | X=x', M=m) * P(X=x')``
    """

    def find_mediator(self, graph: CausalGraph, treatment: str, outcome: str) -> str:
        """Find a valid frontdoor mediator.

        Args:
            graph: The causal graph.
            treatment: Treatment variable.
            outcome: Outcome variable.

        Returns:
            Name of the mediator variable.

        Raises:
            AdjustmentError: If no valid mediator is found.
        """
        # A mediator lies on a directed path from treatment to outcome
        paths = graph.find_all_paths(treatment, outcome)
        for path in paths:
            if len(path) >= 3:
                mediator = path[1]
                # Check: all causal paths from X to Y go through M
                if self._is_valid_mediator(graph, treatment, outcome, mediator):
                    return mediator

        raise AdjustmentError(
            f"No valid frontdoor mediator found for ({treatment} -> {outcome})."
        )

    def _is_valid_mediator(
        self, graph: CausalGraph, treatment: str, outcome: str, mediator: str
    ) -> bool:
        """Check frontdoor criterion for a candidate mediator."""
        # (1) No backdoor path from X to M (or M is a direct child of X)
        #     Check: all parents of X are not connected to M (simplified)
        # (2) All backdoor paths from M to Y are blocked by X
        parents_of_treatment = graph.parents(treatment)
        parents_of_mediator = graph.parents(mediator)
        # If M's only parent is X, condition 1 holds
        if not parents_of_mediator or (len(parents_of_mediator) == 1 and treatment in parents_of_mediator):
            return True
        # Check if backdoor from M->Y is blocked by X
        return treatment in graph.parents(outcome) or treatment in graph.parents(mediator)

    def adjust(
        self,
        data: dict[str, np.ndarray],
        treatment: str,
        value: float,
        outcome: str,
        graph: CausalGraph,
        config: InterventionConfig,
    ) -> InterventionResult:
        """Perform frontdoor adjustment.

        ``E[Y | do(X=x)] = sum_m P(m | do(X=x)) * E[Y | do(M=m)]``
        """
        mediator = self.find_mediator(graph, treatment, outcome)
        Treatment = data[treatment]
        Mediator = data[mediator]
        Outcome = data[outcome]
        n = len(Treatment)

        # Step 1: E[M | do(X=x)] = E[M | X=x] (no backdoor X->M)
        M_given_X = np.polyfit(Treatment, Mediator, 1)
        m_do = np.polyval(M_given_X, value)  # scalar

        # Step 2: E[Y | do(M=m)] via backdoor on M->Y (blocked by X)
        X_my = np.column_stack([np.ones(n), Mediator, Treatment])
        try:
            beta_my = np.linalg.lstsq(X_my, Outcome, rcond=None)[0]
        except np.linalg.LinAlgError:
            raise AdjustmentError("Frontdoor adjustment failed: singular matrix.")

        # Step 3: Combine
        X_do = np.column_stack([np.ones(n), np.full(n, m_do), Treatment])
        adjusted_y = X_do @ beta_my
        ate = float(np.mean(adjusted_y))

        se = float(np.std(adjusted_y) / np.sqrt(n))
        z = stats.norm.ppf(1 - (1 - config.confidence_level) / 2)

        return InterventionResult(
            treatment=treatment,
            outcome=outcome,
            treatment_value=value,
            ate=ate,
            ci_lower=ate - z * se,
            ci_upper=ate + z * se,
            method=AdjustmentMethod.FRONTDOOR,
            standard_error=se,
            adjusted_values=adjusted_y,
            metadata={"mediator": mediator},
        )


# ── Helpers ───────────────────────────────────────────────────────────────────


def _validate_data(
    data: dict[str, np.ndarray],
    treatment: str,
    outcome: str,
    min_samples: int,
) -> None:
    """Validate input data for intervention estimation."""
    if treatment not in data:
        raise InterventionError(f"Treatment variable '{treatment}' not found in data.")
    if outcome not in data:
        raise InterventionError(f"Outcome variable '{outcome}' not found in data.")

    n = len(data[treatment])
    if n < min_samples:
        raise InterventionError(f"Need at least {min_samples} samples; got {n}.")

    for var_name, arr in data.items():
        if len(arr) != n:
            raise InterventionError(
                f"Variable '{var_name}' has {len(arr)} samples, expected {n}."
            )
