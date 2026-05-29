"""Extended tests for Science Pipeline + Experiment Registry integration."""

from __future__ import annotations

import pytest
from lyra_science_pipeline import Hypothesis, SciencePipeline, TrialHarness


# ── Helpers ────────────────────────────────────────────────────────────


def _make_pipeline() -> SciencePipeline:
    return SciencePipeline()


# ── Science Pipeline ───────────────────────────────────────────────────


class TestSciencePipelinePropose:
    def test_propose_hypothesis_returns_hypothesis(self):
        sp = _make_pipeline()
        h = sp.propose_hypothesis("Larger models generalize better", "model_size", "generalization", "positive correlation")
        assert isinstance(h, Hypothesis)
        assert h.status == "proposed"
        assert h.confidence == 0.5

    def test_propose_multiple_hypotheses_increments_ids(self):
        sp = _make_pipeline()
        h1 = sp.propose_hypothesis("H1", "iv1", "dv1", "effect1")
        h2 = sp.propose_hypothesis("H2", "iv2", "dv2", "effect2")
        assert h1.id == "H1"
        assert h2.id == "H2"
        assert len(sp.hypotheses) == 2

    def test_hypothesis_fields_preserved(self):
        sp = _make_pipeline()
        h = sp.propose_hypothesis("Statement", "independent_var", "dependent_var", "expected_effect")
        assert h.statement == "Statement"
        assert h.independent_var == "independent_var"
        assert h.dependent_var == "dependent_var"
        assert h.expected_effect == "expected_effect"


class TestSciencePipelineHarness:
    def test_create_harness_defaults(self):
        sp = _make_pipeline()
        h = sp.create_harness("docker", {"cpu": 4})
        assert h.sandbox_type == "docker"
        assert h.variables == {"cpu": 4}
        assert h.max_steps == 10
        assert h.constraints == []

    def test_create_harness_with_constraints(self):
        sp = _make_pipeline()
        harness = sp.create_harness("modal", {"gpu": "a100"})
        harness.constraints.extend(["max_memory_16gb", "timeout_300s"])
        assert len(harness.constraints) == 2

    def test_multiple_harnesses_independent(self):
        sp = _make_pipeline()
        h1 = sp.create_harness("docker", {"cpu": 2})
        h2 = sp.create_harness("modal", {"gpu": "a100"})
        assert h1.id != h2.id
        assert len(sp.trial_harnesses) == 2


class TestSciencePipelineExperiment:
    @pytest.mark.asyncio
    async def test_run_experiment_updates_hypothesis_status(self):
        sp = _make_pipeline()
        h = sp.propose_hypothesis("Testable claim", "iv", "dv", "effect")
        harness = sp.create_harness("docker", {})
        result = await sp.run_experiment(h.id, harness.id)
        assert result.hypothesis_id == h.id
        assert result.effect_size == 0.7  # simulated
        assert result.significance == 0.95  # simulated
        assert result.supports_hypothesis is True

    @pytest.mark.asyncio
    async def test_run_experiment_missing_hypothesis_raises(self):
        sp = _make_pipeline()
        harness = sp.create_harness("docker", {})
        with pytest.raises(ValueError, match="not found"):
            await sp.run_experiment("nonexistent", harness.id)

    @pytest.mark.asyncio
    async def test_run_experiment_confirms_hypothesis(self):
        sp = _make_pipeline()
        h = sp.propose_hypothesis("Valid claim", "iv", "dv", "effect")
        harness = sp.create_harness("docker", {})
        await sp.run_experiment(h.id, harness.id)
        assert h.status == "confirmed"
        assert h.confidence == 0.95

    def test_analyze_results_empty_pipeline(self):
        sp = _make_pipeline()
        analysis = sp.analyze_results()
        assert analysis == []

    @pytest.mark.asyncio
    async def test_analyze_results_after_experiments(self):
        sp = _make_pipeline()
        h1 = sp.propose_hypothesis("Claim A", "iv1", "dv1", "effect1")
        h2 = sp.propose_hypothesis("Claim B", "iv2", "dv2", "effect2")
        harness = sp.create_harness("docker", {})
        await sp.run_experiment(h1.id, harness.id)
        await sp.run_experiment(h2.id, harness.id)

        analysis = sp.analyze_results()
        assert len(analysis) == 2
        assert analysis[0]["hypothesis"] == "Claim A"
        assert analysis[0]["status"] == "confirmed"
        assert analysis[0]["experiments"] == 1

    def test_analyze_includes_conclusion(self):
        sp = _make_pipeline()
        sp.propose_hypothesis("Test", "iv", "dv", "effect")
        analysis = sp.analyze_results()
        assert len(analysis) == 1
        assert "conclusion" in analysis[0]


class TestTrialHarness:
    def test_trial_harness_immutable_fields(self):
        th = TrialHarness(id="th1", sandbox_type="docker")
        assert th.id == "th1"
        assert th.max_steps == 10

    def test_trial_harness_variables_mutable(self):
        th = TrialHarness(id="th1", sandbox_type="docker", variables={"key": "value"})
        th.variables["new_key"] = "new_value"
        assert th.variables["new_key"] == "new_value"


# ── Experiment Registry ────────────────────────────────────────────────


class TestExperimentRegistry:
    @pytest.fixture
    def registry(self):
        from lyra_experiment import AgentConfig, ExperimentRegistry
        return ExperimentRegistry(), AgentConfig

    def test_create_and_start_experiment(self, registry):
        reg, AgentConfig = registry
        control = AgentConfig(id="c1", name="control", model="haiku")
        variant = AgentConfig(id="v1", name="variant", model="sonnet")
        exp = reg.create_experiment("test-exp", control, variant)
        assert exp.status.name == "DRAFT"
        assert reg.start(exp.id) is True

    def test_record_and_get_results(self, registry):
        reg, AgentConfig = registry
        control = AgentConfig(id="c1", name="control")
        variant = AgentConfig(id="v1", name="variant")
        exp = reg.create_experiment("ab-test", control, variant)
        reg.start(exp.id)
        reg.record_result(exp.id, 0.8, is_variant=False)
        reg.record_result(exp.id, 0.9, is_variant=True)
        reg.record_result(exp.id, 0.85, is_variant=True)

        results = reg.get_results(exp.id)
        assert results is not None
        assert results["control"]["count"] == 1
        assert results["variant"]["count"] == 2
        assert results["winner"] == "variant"

    def test_promote_variant(self, registry):
        reg, AgentConfig = registry
        control = AgentConfig(id="c1", name="control")
        variant = AgentConfig(id="v1", name="variant")
        exp = reg.create_experiment("promote-test", control, variant, traffic_split=0.5)
        reg.start(exp.id)
        reg.record_result(exp.id, 0.5, is_variant=False)
        reg.record_result(exp.id, 0.95, is_variant=True)
        winner = reg.promote_variant(exp.id)
        assert winner is not None
        assert winner.id == "v1"

    def test_promote_variant_when_control_wins(self, registry):
        reg, AgentConfig = registry
        control = AgentConfig(id="c1", name="control")
        variant = AgentConfig(id="v1", name="variant")
        exp = reg.create_experiment("control-wins", control, variant)
        reg.start(exp.id)
        reg.record_result(exp.id, 0.95, is_variant=False)
        reg.record_result(exp.id, 0.5, is_variant=True)
        winner = reg.promote_variant(exp.id)
        assert winner is not None
        assert winner.id == "c1"

    def test_pause_experiment(self, registry):
        reg, AgentConfig = registry
        control = AgentConfig(id="c1", name="control")
        variant = AgentConfig(id="v1", name="variant")
        exp = reg.create_experiment("pause-test", control, variant)
        reg.start(exp.id)
        assert reg.pause(exp.id) is True

    def test_summary_stats(self, registry):
        reg, AgentConfig = registry
        for i in range(3):
            c = AgentConfig(id=f"c{i}", name=f"control-{i}")
            v = AgentConfig(id=f"v{i}", name=f"variant-{i}")
            exp = reg.create_experiment(f"exp-{i}", c, v)
            if i < 2:
                reg.start(exp.id)
        summary = reg.summary
        assert summary["total"] == 3
        assert summary["running"] == 2
        assert summary["completed"] == 0

    def test_get_results_nonexistent(self, registry):
        reg, _ = registry
        assert reg.get_results("nonexistent") is None

    def test_start_nonexistent_returns_false(self, registry):
        reg, _ = registry
        assert reg.start("nonexistent") is False
