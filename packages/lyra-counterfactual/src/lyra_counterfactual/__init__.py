"""Lyra Counterfactual — 'What if' simulation engine over causal graphs and SCMs.

This package provides a comprehensive counterfactual reasoning framework built
on top of ``lyra-causal-graph``:

- **Counterfactual Engine**: Orchestrates the three-step
  abduction-action-prediction pipeline with both legacy ``CausalGraph``
  and modern ``StructuralCausalModel`` backends.
- **Abduction**: Infer posterior distributions over exogenous noise variables
  given observed evidence. Supports inversion, MCMC, optimization, rejection,
  and variational strategies.
- **Action Prediction**: Apply interventions to SCMs and predict outcomes.
  Features batch evaluation, action ranking by expected outcome, pairwise
  and grid what-if analysis.
- **Prediction**: Compute counterfactual outcome distributions with
  comprehensive uncertainty quantification (entropy, quantile ranges,
  distribution shape detection).

Key design principles:
- All modules use type hints and comprehensive docstrings.
- Structured logging via ``logging.getLogger(__name__)``.
- Custom exception hierarchy in ``errors.py``.
- Async/await support for long-running operations.
- Configuration via frozen dataclasses with sensible defaults.
"""

from __future__ import annotations

# ── Errors ────────────────────────────────────────────────────────────────────

from .errors import (
    AbductionError,
    ActionPredictionError,
    ConfidenceError,
    CounterfactualEngineError,
    PredictionError,
    SCMIntegrationError,
)

# ── Abduction ─────────────────────────────────────────────────────────────────

from .abduction import (
    AbductionConfig,
    AbductionEngine,
    AbductionResult,
    AbductionStrategy,
)

# ── Action Prediction ─────────────────────────────────────────────────────────

from .action_prediction import (
    ActionConfig,
    ActionPrediction,
    ActionPredictor,
)

# ── Prediction ────────────────────────────────────────────────────────────────

from .prediction import (
    PredictionConfig,
    PredictionEngine,
    PredictionResult,
    UncertaintyMetrics,
)

# ── Main Counterfactual Engine ────────────────────────────────────────────────

from .counterfactual import (
    CounterfactualEngine,
    CounterfactualEngineConfig,
    CounterfactualResult,
    Intervention,
)

__all__ = [
    # Main engine
    "CounterfactualEngine",
    "CounterfactualEngineConfig",
    "CounterfactualResult",
    "Intervention",
    # Errors
    "CounterfactualEngineError",
    "AbductionError",
    "ActionPredictionError",
    "PredictionError",
    "SCMIntegrationError",
    "ConfidenceError",
    # Abduction
    "AbductionEngine",
    "AbductionConfig",
    "AbductionResult",
    "AbductionStrategy",
    # Action
    "ActionPredictor",
    "ActionConfig",
    "ActionPrediction",
    # Prediction
    "PredictionEngine",
    "PredictionConfig",
    "PredictionResult",
    "UncertaintyMetrics",
]
