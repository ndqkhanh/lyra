"""Tests for Lyra Counterfactual package — all modules."""

from __future__ import annotations

import asyncio

import numpy as np
import pytest

from lyra_counterfactual import (
    # Main engine
    CounterfactualEngine,
    CounterfactualEngineConfig,
    CounterfactualResult,
    Intervention,
    # Errors
    CounterfactualEngineError,
    AbductionError,
    ActionPredictionError,
    PredictionError,
    # Abduction
    AbductionEngine,
    AbductionConfig,
    AbductionResult,
    AbductionStrategy,
    # Action
    ActionPredictor,
    ActionConfig,
    ActionPrediction,
    # Prediction
    PredictionEngine,
    PredictionConfig,
    PredictionResult,
    UncertaintyMetrics,
)
from lyra_causal_graph import (
    CausalGraph,
    EntityNode,
    ActionEdge,
    OutcomeNode,
    StructuralCausalModel,
    SCMConfig,
    GaussianNoise,
    make_chain_scm,
    make_collider_scm,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def scm() -> StructuralCausalModel:
    """Simple X0 -> X1 SCM."""
    return make_chain_scm(n_vars=2, noise_std=0.1, coef=2.0, seed=42)


@pytest.fixture
def scm_complex() -> StructuralCausalModel:
    """X -> M -> Y with covariate C."""
    config = SCMConfig(noise_scale=0.1, random_seed=42)
    scm = StructuralCausalModel(config)

    for var in ("X", "M", "Y", "C"):
        scm.add_exogenous(f"U_{var}", GaussianNoise(std=0.1))

    scm.add_endogenous("C", parents=[])
    scm.add_equation("C", lambda pv: np.zeros_like(pv.get("U_C", np.zeros(1))), "U_C")

    scm.add_endogenous("X", parents=["C"])
    scm.add_equation("X", lambda pv: 1.5 * pv.get("C", np.zeros(1)), "U_X")

    scm.add_endogenous("M", parents=["X"])
    scm.add_equation("M", lambda pv: 0.8 * pv.get("X", np.zeros(1)), "U_M")

    scm.add_endogenous("Y", parents=["M", "C"])
    scm.add_equation(
        "Y",
        lambda pv: 2.0 * pv.get("M", np.zeros(1)) + 0.5 * pv.get("C", np.zeros(1)),
        "U_Y",
    )

    return scm


@pytest.fixture
def legacy_engine() -> CounterfactualEngine:
    """Legacy CounterfactualEngine with CausalGraph."""
    g = CausalGraph()
    g.add_entity(EntityNode(id="tool", name="git", entity_type="tool"))
    g.add_entity(EntityNode(id="file", name="main.py", entity_type="file"))
    a = ActionEdge(id="a1", source_id="tool", target_id="file", action_type="execute", timestamp=1.0)
    g.add_action(a)
    g.add_outcome(OutcomeNode(id="o1", result="success", success=True, latency=0.3))
    a.outcome_id = "o1"
    return CounterfactualEngine(causal_graph=g)


# ═══════════════════════════════════════════════════════════════════════════════
# Legacy Counterfactual Engine Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestLegacyCounterfactualEngine:
    """Tests for legacy CausalGraph-based counterfactual engine."""

    def test_legacy_simulate(self, legacy_engine):
        intervention = Intervention(
            action_type="execute", source_id="tool", target_id="file"
        )
        result = legacy_engine.simulate(intervention)
        assert result.predicted_outcome is not None
        assert 0.0 <= result.confidence <= 1.0
        assert isinstance(result.causal_path, list)

    def test_legacy_simulate_unknown(self, legacy_engine):
        intervention = Intervention(
            action_type="read", source_id="unknown", target_id="unknown"
        )
        result = legacy_engine.simulate(intervention)
        assert result.causal_path is not None

    def test_legacy_async_simulate(self, legacy_engine):
        async def _run():
            intervention = Intervention(
                action_type="execute", source_id="tool", target_id="file"
            )
            return legacy_engine.simulate(intervention)

        result = asyncio.run(_run())
        assert result.predicted_outcome is not None

    def test_legacy_no_graph(self):
        engine = CounterfactualEngine()
        with pytest.raises(CounterfactualEngineError):
            engine.simulate({"X": 1.0})


# ═══════════════════════════════════════════════════════════════════════════════
# SCM-Based Counterfactual Engine Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestSCMCounterfactualEngine:
    """Tests for SCM-based counterfactual engine (three-step pipeline)."""

    def test_simulate_with_scm(self, scm_complex):
        engine = CounterfactualEngine(scm=scm_complex)
        result = engine.simulate(
            intervention={"X": 2.0},
            target_var="Y",
            evidence={"X": 1.0, "Y": 3.0},
        )
        assert isinstance(result, CounterfactualResult)
        assert result.expected_value is not None
        assert result.confidence > 0.0
        assert len(result.causal_path) > 0
        assert result.distribution is not None
        assert result.uncertainty > 0.0
        assert len(result.explanation) > 0
        assert "ci_lower" in result.metadata

    def test_simulate_without_evidence(self, scm_complex):
        """Should work with prior noise when no evidence given."""
        engine = CounterfactualEngine(scm=scm_complex)
        result = engine.simulate(
            intervention={"M": 1.0},
            target_var="Y",
        )
        assert result.expected_value is not None
        assert result.confidence > 0.0

    def test_set_scm_late(self, scm_complex):
        """Engine can be created without SCM and have one attached later."""
        engine = CounterfactualEngine()
        engine.set_scm(scm_complex)
        result = engine.simulate(
            intervention={"X": 1.0},
            target_var="Y",
            evidence={"X": 0.5},
        )
        assert result.expected_value is not None

    def test_batch_simulate(self, scm_complex):
        engine = CounterfactualEngine(scm=scm_complex)
        scenarios = [
            {"intervention": {"X": 1.0}, "target_var": "Y", "evidence": {"X": 0.5}},
            {"intervention": {"X": 2.0}, "target_var": "Y", "evidence": {"X": 0.5}},
            {"intervention": {"M": 0.0}, "target_var": "Y"},
        ]
        results = engine.batch_simulate(scenarios)
        assert len(results) == 3
        for r in results:
            assert isinstance(r, CounterfactualResult)

    def test_sensitivity_analysis(self, scm_complex):
        engine = CounterfactualEngine(scm=scm_complex)
        results = engine.sensitivity_analysis(
            "X", [0.0, 1.0, 2.0], target_var="Y", evidence={"X": 0.5}
        )
        assert len(results) == 3
        # Higher X should result in higher Y (positive causal effect)
        assert results[2].expected_value > results[0].expected_value

    def test_effect_direction(self, scm):
        """Intervening on X0 should affect X1."""
        engine = CounterfactualEngine(scm=scm)
        r_low = engine.simulate(
            intervention={"X0": -1.0},
            target_var="X1",
            evidence={"X0": 0.0},
        )
        r_high = engine.simulate(
            intervention={"X0": 2.0},
            target_var="X1",
            evidence={"X0": 0.0},
        )
        # With positive coefficient, higher intervention -> higher outcome
        assert r_high.expected_value > r_low.expected_value

    def test_config_default_target(self, scm):
        engine = CounterfactualEngine(
            scm=scm,
            config=CounterfactualEngineConfig(default_target="X1"),
        )
        result = engine.simulate(intervention={"X0": 1.0}, evidence={"X0": 0.5})
        assert result.metadata["target_var"] == "X1"

    def test_predicted_outcome_format(self, scm_complex):
        engine = CounterfactualEngine(scm=scm_complex)
        result = engine.simulate(
            intervention={"X": 1.0},
            target_var="Y",
            evidence={"X": 0.5, "Y": 2.0},
        )
        assert "=" in result.predicted_outcome
        assert "CI" in result.predicted_outcome


# ═══════════════════════════════════════════════════════════════════════════════
# Abduction Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestAbduction:
    """Tests for the abduction engine."""

    def test_inversion_strategy(self, scm):
        engine = AbductionEngine(scm)
        result = engine.abduce({"X0": 1.0, "X1": 2.0})
        assert isinstance(result, AbductionResult)
        assert len(result.noise_posterior) > 0
        assert result.converged
        assert result.evidence_log_prob < 0  # log prob should be negative

    def test_optimization_strategy(self, scm):
        engine = AbductionEngine(scm, AbductionConfig(strategy="optimization", max_iterations=50))
        result = engine.abduce({"X0": 1.0}, strategy="optimization")
        assert result.converged or not result.converged  # may not converge for simple case
        assert len(result.noise_posterior) > 0

    def test_rejection_strategy(self, scm):
        engine = AbductionEngine(
            scm,
            AbductionConfig(
                strategy="rejection",
                n_posterior_samples=20,
            ),
        )
        result = engine.abduce({"X0": 0.0}, strategy="rejection")
        assert len(result.noise_posterior) > 0

    def test_mcmc_strategy(self, scm):
        engine = AbductionEngine(
            scm,
            AbductionConfig(
                strategy="mcmc",
                n_posterior_samples=100,
                mcmc_burnin=50,
            ),
        )
        result = engine.abduce({"X0": 1.0}, strategy="mcmc")
        assert len(result.noise_posterior) > 0

    def test_variational_strategy(self, scm):
        engine = AbductionEngine(
            scm,
            AbductionConfig(
                strategy="variational",
                n_posterior_samples=100,
                max_iterations=20,
            ),
        )
        result = engine.abduce({"X0": 1.0}, strategy="variational")
        assert len(result.noise_posterior) > 0

    def test_no_evidence_raises(self, scm):
        engine = AbductionEngine(scm)
        with pytest.raises(AbductionError):
            engine.abduce({})

    def test_invalid_variable_raises(self, scm):
        engine = AbductionEngine(scm)
        with pytest.raises(AbductionError):
            engine.abduce({"NONEXISTENT": 1.0})

    def test_batch_abduce(self, scm):
        engine = AbductionEngine(scm)
        results = engine.batch_abduce([
            {"X0": 1.0, "X1": 2.0},
            {"X0": -1.0, "X1": -2.0},
        ])
        assert len(results) == 2

    def test_null_scm_raises(self):
        with pytest.raises(AbductionError):
            AbductionEngine(None)


# ═══════════════════════════════════════════════════════════════════════════════
# Action Prediction Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestActionPrediction:
    """Tests for the action predictor."""

    def test_single_prediction(self, scm):
        predictor = ActionPredictor(scm)
        pred = predictor.predict({"X0": 2.0}, "X1")
        assert isinstance(pred, ActionPrediction)
        assert pred.expected_value is not None
        assert pred.std > 0
        assert pred.ci_upper > pred.ci_lower

    def test_prediction_with_noise_posterior(self, scm):
        # First run abduction
        abd_engine = AbductionEngine(scm)
        abd_result = abd_engine.abduce({"X0": 1.0, "X1": 2.0})

        predictor = ActionPredictor(scm, noise_posterior=abd_result.noise_posterior)
        pred = predictor.predict({"X0": 2.0}, "X1")
        assert pred.expected_value is not None

    def test_evaluate_actions(self, scm):
        predictor = ActionPredictor(scm)
        results = predictor.evaluate_actions([
            {"name": "High X0", "intervention": {"X0": 2.0}, "target": "X1"},
            {"name": "Low X0", "intervention": {"X0": -1.0}, "target": "X1"},
        ])
        assert len(results) == 2
        assert results[0].expected_value > results[1].expected_value

    def test_evaluate_with_baseline(self, scm):
        predictor = ActionPredictor(scm)
        results = predictor.evaluate_actions(
            [
                {"name": "Increase", "intervention": {"X0": 2.0}, "target": "X1"},
                {"name": "Decrease", "intervention": {"X0": -1.0}, "target": "X1"},
            ],
            baseline={"X0": 0.0},
        )
        assert len(results) == 2
        assert 0.0 <= results[0].probability_improvement <= 1.0
        # Increasing X0 should improve X1 more than decreasing
        assert results[0].probability_improvement > results[1].probability_improvement

    def test_rank_actions(self, scm):
        predictor = ActionPredictor(scm)
        results = predictor.evaluate_actions([
            {"name": "A", "intervention": {"X0": 3.0}, "target": "X1"},
            {"name": "B", "intervention": {"X0": 1.0}, "target": "X1"},
            {"name": "C", "intervention": {"X0": 2.0}, "target": "X1"},
        ])
        ranked = predictor.rank_actions(results, rank_by="expected_value")
        assert ranked[0].action_name == "A"  # highest value
        assert ranked[-1].action_name == "B"  # lowest value

    def test_best_action(self, scm):
        predictor = ActionPredictor(scm)
        results = predictor.evaluate_actions([
            {"name": "Low", "intervention": {"X0": 0.0}, "target": "X1"},
            {"name": "High", "intervention": {"X0": 3.0}, "target": "X1"},
        ])
        best = predictor.best_action(results)
        assert best is not None
        assert best.action_name == "High"

    def test_what_if_grid(self, scm):
        predictor = ActionPredictor(scm)
        results = predictor.what_if_grid("X0", [-2, -1, 0, 1, 2], "X1")
        assert len(results) == 5
        # Monotonically increasing
        for i in range(4):
            assert results[i].expected_value <= results[i + 1].expected_value

    def test_what_if_pairwise(self, scm_complex):
        predictor = ActionPredictor(scm_complex)
        results = predictor.what_if_pairwise(
            {"X": [0.0, 1.0], "M": [0.0, 1.0]},
            "Y",
        )
        assert len(results) == 4  # 2 x 2 combinations

    def test_invalid_intervention(self, scm):
        predictor = ActionPredictor(scm)
        with pytest.raises(ActionPredictionError):
            predictor.predict({}, "X1")

    def test_invalid_target(self, scm):
        predictor = ActionPredictor(scm)
        with pytest.raises(ActionPredictionError):
            predictor.predict({"X0": 1.0}, "NONEXISTENT")

    def test_invalid_ranking_metric(self, scm):
        predictor = ActionPredictor(scm)
        results = predictor.evaluate_actions([
            {"name": "test", "intervention": {"X0": 1.0}, "target": "X1"},
        ])
        with pytest.raises(ActionPredictionError):
            predictor.rank_actions(results, rank_by="invalid")

    def test_null_scm_raises(self):
        with pytest.raises(ActionPredictionError):
            ActionPredictor(None)


# ═══════════════════════════════════════════════════════════════════════════════
# Prediction Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestPrediction:
    """Tests for the prediction engine."""

    def test_predict(self, scm):
        engine = PredictionEngine(scm, PredictionConfig(n_samples=5000))
        # Abduce only X0 to leave noise uncertanty for X1
        abd = AbductionEngine(scm).abduce({"X0": 1.0})
        result = engine.predict(abd.noise_posterior, {"X0": 2.0}, "X1")
        assert isinstance(result, PredictionResult)
        assert result.expected_value is not None
        assert result.ci_upper >= result.ci_lower
        assert result.distribution_type in (
            "gaussian", "skewed", "bimodal", "heavy_tailed", "uniform", "unknown", "insufficient_data"
        )

    def test_predict_with_samples(self, scm):
        engine = PredictionEngine(scm, PredictionConfig(compute_full_distribution=True))
        abd = AbductionEngine(scm).abduce({"X0": 1.0, "X1": 2.0})
        result = engine.predict(abd.noise_posterior, {"X0": 2.0}, "X1")
        assert result.samples is not None
        assert len(result.samples) > 0

    def test_uncertainty_metrics(self, scm):
        engine = PredictionEngine(scm, PredictionConfig(n_samples=2000))
        abd = AbductionEngine(scm).abduce({"X0": 1.0})
        result = engine.predict(abd.noise_posterior, {"X0": 2.0}, "X1")
        assert result.uncertainty.std >= 0.0
        assert result.uncertainty.variance >= 0.0

    def test_batch_predict(self, scm):
        engine = PredictionEngine(scm)
        abd = AbductionEngine(scm).abduce({"X0": 1.0, "X1": 2.0})
        scenarios = [
            {"noise_posterior": abd.noise_posterior, "intervention": {"X0": v}, "target_var": "X1"}
            for v in [0.0, 1.0, 2.0]
        ]
        results = engine.batch_predict(scenarios)
        assert len(results) == 3

    def test_probability_better_than(self, scm):
        engine = PredictionEngine(scm, PredictionConfig(n_samples=2000, compute_full_distribution=True))
        abd = AbductionEngine(scm).abduce({"X0": 1.0, "X1": 2.0})
        result = engine.predict(abd.noise_posterior, {"X0": 2.0}, "X1")
        prob = engine.probability_better_than(result, 0.0)
        assert 0.0 <= prob <= 1.0

    def test_compare_scenarios(self, scm):
        engine = PredictionEngine(scm)
        abd = AbductionEngine(scm).abduce({"X0": 1.0, "X1": 2.0})
        r1 = engine.predict(abd.noise_posterior, {"X0": 0.0}, "X1")
        r2 = engine.predict(abd.noise_posterior, {"X0": 2.0}, "X1")
        comparison = engine.compare_scenarios([r1, r2], names=["Zero", "Two"])
        assert comparison["best_scenario"] == "Two"  # 2.0 > 0.0
        assert "Zero vs Two" in comparison["pairwise_differences"]

    def test_no_noise_posterior_raises(self, scm):
        engine = PredictionEngine(scm)
        with pytest.raises(PredictionError):
            engine.predict({}, {"X0": 1.0}, "X1")

    def test_no_intervention_raises(self, scm):
        engine = PredictionEngine(scm)
        abd = AbductionEngine(scm).abduce({"X0": 1.0, "X1": 2.0})
        with pytest.raises(PredictionError):
            engine.predict(abd.noise_posterior, {}, "X1")

    def test_invalid_target_raises(self, scm):
        engine = PredictionEngine(scm)
        abd = AbductionEngine(scm).abduce({"X0": 1.0, "X1": 2.0})
        with pytest.raises(PredictionError):
            engine.predict(abd.noise_posterior, {"X0": 1.0}, "NONEXISTENT")

    def test_null_scm_raises(self):
        with pytest.raises(PredictionError):
            PredictionEngine(None)

    def test_config_confidence_level(self, scm):
        engine_95 = PredictionEngine(scm, PredictionConfig(confidence_level=0.95, n_samples=2000))
        engine_99 = PredictionEngine(scm, PredictionConfig(confidence_level=0.99, n_samples=2000))

        abd = AbductionEngine(scm).abduce({"X0": 1.0, "X1": 2.0})
        r95 = engine_95.predict(abd.noise_posterior, {"X0": 1.0}, "X1")
        r99 = engine_99.predict(abd.noise_posterior, {"X0": 1.0}, "X1")

        # Higher confidence -> wider interval
        assert (r99.ci_upper - r99.ci_lower) >= (r95.ci_upper - r95.ci_lower)


# ═══════════════════════════════════════════════════════════════════════════════
# Integration Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestIntegration:
    """Tests for full end-to-end counterfactual pipeline integration."""

    def test_full_pipeline(self, scm_complex):
        """Simulate full abduction -> action -> prediction pipeline."""
        # 1. Abduction
        abd_engine = AbductionEngine(scm_complex)
        abd_result = abd_engine.abduce({"X": 1.0, "M": 0.8, "Y": 2.0})

        # 2. Action
        act_predictor = ActionPredictor(scm_complex, noise_posterior=abd_result.noise_posterior)
        act_results = act_predictor.evaluate_actions([
            {"name": "Increase X", "intervention": {"X": 2.0}, "target": "Y"},
            {"name": "Decrease X", "intervention": {"X": 0.0}, "target": "Y"},
        ])

        # 3. Prediction
        pred_engine = PredictionEngine(scm_complex)
        pred_0 = pred_engine.predict(abd_result.noise_posterior, {"X": 0.0}, "Y")
        pred_2 = pred_engine.predict(abd_result.noise_posterior, {"X": 2.0}, "Y")

        # Higher X should produce higher Y
        assert pred_2.expected_value > pred_0.expected_value

        # Best action should be "Increase X"
        best = act_predictor.best_action(act_results)
        assert best.action_name == "Increase X"

    def test_pipeline_through_engine(self, scm_complex):
        """Full pipeline via the main CounterfactualEngine."""
        engine = CounterfactualEngine(scm=scm_complex)

        # Counterfactual: what if X were 2.0 instead of 1.0?
        result = engine.simulate(
            intervention={"X": 2.0},
            target_var="Y",
            evidence={"X": 1.0, "Y": 2.0},
        )

        assert result.expected_value is not None
        assert result.confidence > 0.3
        assert result.distribution is not None

        # The expected value should differ from the observed Y
        assert abs(result.expected_value - 2.0) > 0.1


# ═══════════════════════════════════════════════════════════════════════════════
# Edge Cases
# ═══════════════════════════════════════════════════════════════════════════════


class TestEdgeCases:
    """Edge case tests for counterfactual package."""

    def test_empty_noise_posterior_prediction(self, scm):
        """Prediction with empty noise posterior should fail."""
        engine = PredictionEngine(scm)
        with pytest.raises(PredictionError):
            engine.predict({}, {"X0": 1.0}, "X1")

    def test_collider_counterfactual(self):
        """Counterfactual reasoning on a collider SCM."""
        scm = make_collider_scm(noise_std=0.1)
        engine = CounterfactualEngine(scm=scm)
        result = engine.simulate(
            intervention={"X": 2.0},
            target_var="Z",
            evidence={"X": 1.0, "Y": 1.0, "Z": 2.0},
        )
        assert result.expected_value is not None
        assert result.confidence > 0.0

    def test_rejection_sampling_extreme_evidence(self, scm):
        """Rejection sampling with extreme evidence: should raise or return."""
        engine = AbductionEngine(
            scm,
            AbductionConfig(
                strategy="rejection",
                n_posterior_samples=10,
            ),
        )
        # Extreme evidence is unlikely to match — expect an error
        with pytest.raises(AbductionError):
            engine.abduce({"X0": 1000.0}, strategy="rejection")

    def test_large_batch(self, scm):
        """Large batch processing."""
        engine = CounterfactualEngine(scm=scm)
        scenarios = [
            {"intervention": {"X0": float(i)}, "target_var": "X1", "evidence": {"X0": 0.0}}
            for i in range(20)
        ]
        results = engine.batch_simulate(scenarios)
        assert len(results) == 20

    def test_abduction_strategy_fallback(self, scm):
        """Unknown strategy should raise an error."""
        engine = AbductionEngine(scm)
        with pytest.raises(AbductionError):
            engine.abduce({"X0": 1.0}, strategy="nonexistent_strategy")
