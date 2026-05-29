"""Tests for Sibyl-style Scientific Trial-and-Error Harnesses.

Covers TrialHarness, SibylPipeline, ExperimentTrial, TrialFailure, TrialConfig,
and ExperimentStatus — the full experiment → evolve → retry loop.
"""

from __future__ import annotations

import pytest
from lyra_research.sibyl_harness import (
    ExperimentStatus,
    ExperimentTrial,
    SibylPipeline,
    TrialConfig,
    TrialFailure,
    TrialHarness,
)

# ── TrialConfig ─────────────────────────────────────────────────────────


class TestTrialConfig:
    def test_default_config(self):
        cfg = TrialConfig()
        assert cfg.max_steps == 10
        assert cfg.timeout_seconds == 300.0
        assert "search" in cfg.allowed_tools
        assert cfg.sandbox_type == "isolated"

    def test_custom_config(self):
        cfg = TrialConfig(
            max_steps=5,
            timeout_seconds=60.0,
            allowed_tools=["execute"],
            resource_limit_mb=256,
            sandbox_type="shared",
        )
        assert cfg.max_steps == 5
        assert cfg.resource_limit_mb == 256
        assert cfg.sandbox_type == "shared"

    def test_capture_traces_enabled_by_default(self):
        cfg = TrialConfig()
        assert cfg.capture_traces is True


# ── TrialFailure ────────────────────────────────────────────────────────


class TestTrialFailure:
    def test_failure_contains_error_info(self):
        f = TrialFailure(
            step=3,
            error_type="boundary_condition",
            error_message="Hypothesis too complex",
            context={"hypothesis_length": 80},
            attempted_action="verify",
        )
        assert f.step == 3
        assert f.error_type == "boundary_condition"
        assert f.context["hypothesis_length"] == 80
        assert f.attempted_action == "verify"

    def test_failure_default_context(self):
        f = TrialFailure(step=0, error_type="timeout", error_message="timed out")
        assert f.context == {}
        assert f.attempted_action == ""


# ── ExperimentTrial ─────────────────────────────────────────────────────


class TestExperimentTrial:
    def test_trial_starts_in_planned_status(self):
        t = ExperimentTrial(id="t1", hypothesis="H", config=TrialConfig())
        assert t.status == ExperimentStatus.PLANNED
        assert t.result is None
        assert t.evolved_approach is None
        assert t.trace == []
        assert t.failures == []

    def test_trial_fields_mutable(self):
        t = ExperimentTrial(id="t1", hypothesis="H", config=TrialConfig())
        t.status = ExperimentStatus.RUNNING
        t.trace.append({"step": 0, "action": "simulate"})
        assert t.status == ExperimentStatus.RUNNING
        assert len(t.trace) == 1


# ── TrialHarness ────────────────────────────────────────────────────────


class TestTrialHarness:
    @pytest.mark.asyncio
    async def test_run_simple_trial_succeeds(self):
        harness = TrialHarness()
        trial = await harness.run_trial("A simple hypothesis")
        assert trial.status == ExperimentStatus.SUCCEEDED
        assert trial.result is not None
        assert "Hypothesis verified" in trial.result

    @pytest.mark.asyncio
    async def test_run_complex_hypothesis_fails_and_evolves(self):
        harness = TrialHarness()
        long_hypothesis = (
            "Transformers with multi-head attention achieve superior "
            "performance on long-range dependency tasks compared to RNNs and LSTMs"
        )
        trial = await harness.run_trial(long_hypothesis)
        assert trial.status == ExperimentStatus.FAILED
        assert len(trial.failures) > 0
        assert trial.evolved_approach is not None
        assert "Decompose hypothesis" in trial.evolved_approach

    @pytest.mark.asyncio
    async def test_trial_trace_captures_steps(self):
        harness = TrialHarness(TrialConfig(max_steps=5))
        trial = await harness.run_trial("Test hypothesis")
        assert len(trial.trace) == 5
        assert all("step" in entry for entry in trial.trace)

    @pytest.mark.asyncio
    async def test_trial_registered_in_harness(self):
        harness = TrialHarness()
        trial = await harness.run_trial("registered trial")
        assert trial.id in harness.trials
        assert harness.trials[trial.id] is trial

    def test_get_failure_patterns_empty(self):
        harness = TrialHarness()
        patterns = harness.get_failure_patterns()
        assert patterns == []

    @pytest.mark.asyncio
    async def test_get_failure_patterns_aggregates(self):
        harness = TrialHarness()
        long_h = "A" * 60  # triggers boundary_condition failure at step 2
        await harness.run_trial(long_h)
        await harness.run_trial(long_h + "B")
        patterns = harness.get_failure_patterns()
        assert len(patterns) == 1
        assert patterns[0]["pattern"] == "boundary_condition"
        assert patterns[0]["count"] == 2

    def test_custom_config_applied(self):
        cfg = TrialConfig(max_steps=3, sandbox_type="shared")
        harness = TrialHarness(config=cfg)
        assert harness.config.max_steps == 3
        assert harness.config.sandbox_type == "shared"


# ── SibylPipeline ───────────────────────────────────────────────────────


class TestSibylPipeline:
    @pytest.mark.asyncio
    async def test_simple_hypothesis_completes_without_evolution(self):
        pipeline = SibylPipeline()
        result = await pipeline.research_with_harness(
            "What is the effect of learning rate on transformers?",
            "lower learning rates improve stability",
        )
        assert result["question"] is not None
        assert len(result["trials"]) == 1
        assert "result" in result

    @pytest.mark.asyncio
    async def test_complex_hypothesis_triggers_evolution_loop(self):
        pipeline = SibylPipeline()
        result = await pipeline.research_with_harness(
            "How do attention mechanisms affect model performance?",
            "A" * 60,  # long hypothesis triggers boundary_condition → FAILED → evolve
        )
        assert len(result["trials"]) >= 1
        assert "evolved" in result
        assert result["evolved"] is not None
        assert "knowledge_gained" in result

    @pytest.mark.asyncio
    async def test_evolution_knowledge_accumulated(self):
        pipeline = SibylPipeline()
        await pipeline.research_with_harness("Q1", "A" * 60)
        await pipeline.research_with_harness("Q2", "B" * 60)
        # Both complex hypotheses trigger evolution
        assert len(pipeline.evolved_knowledge) == 2
        assert len(pipeline.completed_trials) >= 2

    @pytest.mark.asyncio
    async def test_successful_trial_returns_result_not_evolved(self):
        pipeline = SibylPipeline()
        result = await pipeline.research_with_harness("Q", "short hypothesis")
        assert "result" in result
        assert "knowledge_gained" not in result


# ── ExperimentStatus enum ───────────────────────────────────────────────


class TestExperimentStatus:
    def test_all_statuses(self):
        statuses = list(ExperimentStatus)
        assert ExperimentStatus.PLANNED in statuses
        assert ExperimentStatus.RUNNING in statuses
        assert ExperimentStatus.SUCCEEDED in statuses
        assert ExperimentStatus.FAILED in statuses
        assert ExperimentStatus.INCONCLUSIVE in statuses

    def test_status_values_distinct(self):
        values = [s.value for s in ExperimentStatus]
        assert len(values) == len(set(values))
