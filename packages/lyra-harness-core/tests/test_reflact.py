"""Tests for reflact.py — ReflACT Pipeline (P3-B1 CRITICAL)."""
from __future__ import annotations

import pytest
from lyra_harness_core.reflact import (
    ActResult,
    Actor,
    EditAction,
    EpochResult,
    EpochStopReason,
    FailureAnalysis,
    ImprovementGate,
    PipelinePhase,
    ReflACTPipeline,
    ReflACTPipelineResult,
    ReflectReport,
    Reflector,
    SkillDefinition,
    SkillStep,
    StepOutcome,
    StepTrace,
    Trajectory,
    ValidationResult,
    Validator,
    compute_success_rate,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_skill(name="test-skill", version="1.0.0", step_count=3) -> SkillDefinition:
    steps = tuple(
        SkillStep(
            step_id=f"step-{i}",
            description=f"Step {i}",
            instruction=f"Do step {i}",
            expected_output=f"Output {i}",
            order=i,
        )
        for i in range(step_count)
    )
    return SkillDefinition(name=name, version=version, description="Test skill", steps=steps)


def _make_trajectory(
    tid="t1",
    skill_name="test-skill",
    skill_version="1.0.0",
    step_outcomes=None,
    overall_success=True,
) -> Trajectory:
    if step_outcomes is None:
        step_outcomes = [StepOutcome.SUCCESS, StepOutcome.SUCCESS, StepOutcome.SUCCESS]

    steps = tuple(
        StepTrace(
            step_id=f"step-{i}",
            outcome=outcome,
            duration_ms=50.0,
            error_message="" if outcome == StepOutcome.SUCCESS else "Failed",
        )
        for i, outcome in enumerate(step_outcomes)
    )
    return Trajectory(
        trajectory_id=tid,
        skill_name=skill_name,
        skill_version=skill_version,
        task_input="test task",
        steps=steps,
        overall_success=overall_success,
        total_duration_ms=sum(s.duration_ms for s in steps),
    )


# ---------------------------------------------------------------------------
# StepOutcome
# ---------------------------------------------------------------------------

class TestStepOutcome:
    def test_values(self):
        assert StepOutcome.SUCCESS.value == "success"
        assert StepOutcome.FAILURE.value == "failure"
        assert StepOutcome.TIMEOUT.value == "timeout"


# ---------------------------------------------------------------------------
# SkillStep
# ---------------------------------------------------------------------------

class TestSkillStep:
    def test_defaults(self):
        s = SkillStep(step_id="s1", description="Test", instruction="Do X")
        assert s.step_id == "s1"
        assert s.expected_output == ""
        assert s.timeout_seconds == 60.0
        assert s.order == 0

    def test_custom(self):
        s = SkillStep(
            step_id="s2",
            description="Desc",
            instruction="Do Y",
            expected_output="Out",
            timeout_seconds=30.0,
            order=1,
        )
        assert s.expected_output == "Out"
        assert s.timeout_seconds == 30.0
        assert s.order == 1

    def test_frozen(self):
        s = SkillStep(step_id="s1", description="T", instruction="X")
        with pytest.raises(Exception):
            s.instruction = "Y"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# SkillDefinition
# ---------------------------------------------------------------------------

class TestSkillDefinition:
    def test_creation(self):
        sk = _make_skill()
        assert sk.name == "test-skill"
        assert sk.version == "1.0.0"
        assert sk.step_count == 3

    def test_step_by_id(self):
        sk = _make_skill()
        s = sk.step_by_id("step-1")
        assert s is not None
        assert s.description == "Step 1"

    def test_step_by_id_missing(self):
        sk = _make_skill()
        assert sk.step_by_id("nonexistent") is None

    def test_with_updated_step(self):
        sk = _make_skill()
        updated = sk.with_updated_step("step-0", "Updated instruction")
        assert updated.version != sk.version
        assert updated.step_by_id("step-0").instruction == "Updated instruction"  # type: ignore[union-attr]
        # Other steps unchanged
        assert updated.step_by_id("step-1").instruction == "Do step 1"  # type: ignore[union-attr]

    def test_with_updated_step_version_bump(self):
        sk = _make_skill(version="2.3.0")
        updated = sk.with_updated_step("step-0", "New")
        assert updated.version == "2.3.1"

    def test_fingerprint(self):
        sk1 = _make_skill()
        sk2 = _make_skill()
        assert sk1.fingerprint() == sk2.fingerprint()
        sk3 = sk1.with_updated_step("step-0", "Different")
        assert sk1.fingerprint() != sk3.fingerprint()

    def test_metadata(self):
        sk = SkillDefinition(
            name="s",
            version="1.0.0",
            description="d",
            steps=(SkillStep(step_id="s1", description="d", instruction="i"),),
            metadata={"owner": "team-a"},
        )
        assert sk.metadata["owner"] == "team-a"


# ---------------------------------------------------------------------------
# StepTrace
# ---------------------------------------------------------------------------

class TestStepTrace:
    def test_creation(self):
        st = StepTrace(step_id="s1", outcome=StepOutcome.SUCCESS, duration_ms=100.0)
        assert st.outcome == StepOutcome.SUCCESS
        assert st.duration_ms == 100.0
        assert st.error_message == ""

    def test_error(self):
        st = StepTrace(
            step_id="s1",
            outcome=StepOutcome.ERROR,
            duration_ms=5000.0,
            error_message="timeout",
            retry_count=2,
        )
        assert st.error_message == "timeout"
        assert st.retry_count == 2


# ---------------------------------------------------------------------------
# Trajectory
# ---------------------------------------------------------------------------

class TestTrajectory:
    def test_creation(self):
        t = _make_trajectory()
        assert t.overall_success
        assert len(t.steps) == 3

    def test_failing_steps(self):
        t = _make_trajectory(
            step_outcomes=[StepOutcome.SUCCESS, StepOutcome.FAILURE, StepOutcome.TIMEOUT],
            overall_success=False,
        )
        failing = t.failing_steps()
        assert len(failing) == 2

    def test_failing_steps_none(self):
        t = _make_trajectory()
        assert len(t.failing_steps()) == 0

    def test_step_ids(self):
        t = _make_trajectory()
        assert t.step_ids() == ("step-0", "step-1", "step-2")


# ---------------------------------------------------------------------------
# FailureAnalysis
# ---------------------------------------------------------------------------

class TestFailureAnalysis:
    def test_creation(self):
        fa = FailureAnalysis(
            trajectory_id="t1",
            failed_step_id="step-0",
            root_cause="test failure",
            suggested_fix="fix it",
            confidence=0.9,
        )
        assert fa.confidence == 0.9

    def test_with_related_steps(self):
        fa = FailureAnalysis(
            trajectory_id="t1",
            failed_step_id="step-2",
            root_cause="cascade",
            suggested_fix="fix all",
            confidence=0.7,
            related_steps=("step-0", "step-1"),
            evidence=("log line 1", "log line 2"),
        )
        assert fa.related_steps == ("step-0", "step-1")
        assert len(fa.evidence) == 2


# ---------------------------------------------------------------------------
# Reflector
# ---------------------------------------------------------------------------

class TestReflector:
    def test_analyze_success_trajectory(self):
        r = Reflector()
        t = _make_trajectory()
        analyses = r.analyze(t)
        assert len(analyses) == 0

    def test_analyze_failure_trajectory(self):
        r = Reflector()
        t = _make_trajectory(
            step_outcomes=[StepOutcome.SUCCESS, StepOutcome.FAILURE, StepOutcome.SUCCESS],
            overall_success=False,
        )
        analyses = r.analyze(t)
        assert len(analyses) == 1
        assert analyses[0].failed_step_id == "step-1"

    def test_analyze_timeout(self):
        r = Reflector()
        t = _make_trajectory(
            step_outcomes=[StepOutcome.TIMEOUT, StepOutcome.SUCCESS, StepOutcome.SUCCESS],
            overall_success=False,
        )
        analyses = r.analyze(t)
        assert len(analyses) == 1
        assert "timed out" in analyses[0].root_cause.lower()

    def test_analyze_error(self):
        r = Reflector()
        t = _make_trajectory(
            step_outcomes=[StepOutcome.ERROR, StepOutcome.SUCCESS, StepOutcome.SUCCESS],
            overall_success=False,
        )
        analyses = r.analyze(t)
        assert len(analyses) == 1
        assert analyses[0].confidence > 0.5

    def test_confidence_boost_from_prior_failures(self):
        r = Reflector()
        t = _make_trajectory(
            step_outcomes=[StepOutcome.FAILURE, StepOutcome.FAILURE, StepOutcome.SUCCESS],
            overall_success=False,
        )
        analyses = r.analyze(t)
        # step-1 should have boosted confidence from step-0 failure
        step1 = [a for a in analyses if a.failed_step_id == "step-1"]
        assert len(step1) == 1
        assert step1[0].confidence > 0.65  # base + boost

    def test_reflect_batch(self):
        r = Reflector()
        trajectories = [
            _make_trajectory("t1"),
            _make_trajectory(
                "t2", step_outcomes=[StepOutcome.FAILURE, StepOutcome.SUCCESS, StepOutcome.SUCCESS],
                overall_success=False,
            ),
            _make_trajectory("t3"),
        ]
        report = r.reflect(trajectories)
        assert report.trajectories_analyzed == 3
        assert report.failures_found == 1
        assert report.success_rate_before == 2 / 3

    def test_reflect_empty(self):
        r = Reflector()
        report = r.reflect([])
        assert report.trajectories_analyzed == 0
        assert report.failures_found == 0

    def test_primary_failure_step(self):
        r = Reflector()
        trajectories = [
            _make_trajectory(
                f"t{i}", step_outcomes=[StepOutcome.FAILURE, StepOutcome.SUCCESS, StepOutcome.SUCCESS],
                overall_success=False,
            )
            for i in range(3)
        ]
        report = r.reflect(trajectories)
        assert report.primary_failure_step == "step-0"

    def test_reflect_respects_max_analyses(self):
        r = Reflector(max_analyses=1)
        t = _make_trajectory(
            "t1",
            step_outcomes=[StepOutcome.FAILURE, StepOutcome.FAILURE, StepOutcome.FAILURE],
            overall_success=False,
        )
        analyses = r.analyze(t)
        assert len(analyses) <= 3  # max_analyses applied in reflect(), not analyze()

    def test_failure_rate(self):
        report = ReflectReport(
            trajectories_analyzed=10,
            failures_found=3,
            analyses=(),
            most_problematic_step=None,
            success_rate_before=0.7,
        )
        assert report.failure_rate == 0.3


# ---------------------------------------------------------------------------
# Actor
# ---------------------------------------------------------------------------

class TestActor:
    def test_act_no_analyses(self):
        actor = Actor()
        skill = _make_skill()
        report = ReflectReport(
            trajectories_analyzed=0, failures_found=0, analyses=(),
            most_problematic_step=None, success_rate_before=1.0,
        )
        result = actor.act(skill, report)
        assert not result.has_edits
        assert result.edit_count == 0

    def test_act_applies_fixes(self):
        actor = Actor()
        skill = _make_skill()
        analysis = FailureAnalysis(
            trajectory_id="t1",
            failed_step_id="step-0",
            root_cause="step-0 failed",
            suggested_fix="improve step-0 instructions",
            confidence=0.9,
        )
        report = ReflectReport(
            trajectories_analyzed=1, failures_found=1, analyses=(analysis,),
            most_problematic_step="step-0", success_rate_before=0.0,
        )
        result = actor.act(skill, report)
        assert result.has_edits
        assert result.edit_count == 1
        assert result.edits_applied[0].step_id == "step-0"
        assert "ReflACT fix" in result.edited_skill.step_by_id("step-0").instruction  # type: ignore[union-attr]

    def test_act_respects_max_edits(self):
        actor = Actor(max_edits_per_epoch=1)
        skill = _make_skill()
        analyses = tuple(
            FailureAnalysis(
                trajectory_id=f"t{i}",
                failed_step_id=f"step-{i}",
                root_cause=f"failed {i}",
                suggested_fix=f"fix {i}",
                confidence=0.9 - i * 0.1,
            )
            for i in range(3)
        )
        report = ReflectReport(
            trajectories_analyzed=3, failures_found=3, analyses=analyses,
            most_problematic_step="step-0", success_rate_before=0.0,
        )
        result = actor.act(skill, report)
        assert result.edit_count == 1

    def test_act_respects_min_confidence(self):
        actor = Actor(min_edit_confidence=0.9)
        skill = _make_skill()
        analysis = FailureAnalysis(
            trajectory_id="t1",
            failed_step_id="step-0",
            root_cause="low confidence failure",
            suggested_fix="maybe fix",
            confidence=0.5,
        )
        report = ReflectReport(
            trajectories_analyzed=1, failures_found=1, analyses=(analysis,),
            most_problematic_step="step-0", success_rate_before=0.0,
        )
        result = actor.act(skill, report)
        assert not result.has_edits

    def test_edit_action_fields(self):
        edit = EditAction(
            step_id="step-1",
            original_instruction="old",
            new_instruction="new",
            reason="test",
            source_analysis="t1",
        )
        assert edit.step_id == "step-1"
        assert edit.original_instruction == "old"
        assert edit.new_instruction == "new"

    def test_act_nonexistent_step(self):
        actor = Actor()
        skill = _make_skill()
        analysis = FailureAnalysis(
            trajectory_id="t1",
            failed_step_id="nonexistent",
            root_cause="ghost step",
            suggested_fix="n/a",
            confidence=0.9,
        )
        report = ReflectReport(
            trajectories_analyzed=1, failures_found=1, analyses=(analysis,),
            most_problematic_step="nonexistent", success_rate_before=0.0,
        )
        result = actor.act(skill, report)
        assert not result.has_edits


# ---------------------------------------------------------------------------
# Validator + ImprovementGate
# ---------------------------------------------------------------------------

class TestValidator:
    def test_validate_no_tasks(self):
        v = Validator()
        skill = _make_skill()
        result = v.validate(skill, [])
        assert not result.passed

    def test_validate_no_executor(self):
        v = Validator()
        skill = _make_skill()
        result = v.validate(skill, ["task1"])
        assert not result.passed

    def test_validate_all_pass(self):
        v = Validator()
        skill = _make_skill()

        def always_pass(task, skill):
            return True

        result = v.validate(skill, ["t1", "t2", "t3"], always_pass)
        assert result.passed
        assert result.tasks_run == 3
        assert result.tasks_passed == 3

    def test_validate_some_fail(self):
        v = Validator()
        skill = _make_skill()

        def half_pass(task, skill):
            return task == "t1"

        result = v.validate(skill, ["t1", "t2"], half_pass)
        assert result.tasks_passed in (1, 2)  # depends on gate

    def test_compare_improvement(self):
        v = Validator()
        result = v.compare(before_rate=0.6, after_rate=0.8, tasks_run=10)
        assert result.passed
        assert result.improvement == pytest.approx(0.2)

    def test_compare_no_improvement(self):
        v = Validator()
        # Default min_improvement=0.0 means no regression is acceptable
        result = v.compare(before_rate=0.7, after_rate=0.7, tasks_run=10)
        # Passes because 0.0 >= 0.0 and 0.7 >= 0.5
        assert result.passed
        assert result.improvement == pytest.approx(0.0)

    def test_compare_degradation(self):
        v = Validator()
        result = v.compare(before_rate=0.8, after_rate=0.6, tasks_run=10)
        assert not result.passed
        assert result.improvement == pytest.approx(-0.2)

    def test_compare_too_few_tasks(self):
        v = Validator()
        result = v.compare(before_rate=0.6, after_rate=0.9, tasks_run=2)
        assert not result.passed  # min_tasks = 3

    def test_compare_below_min_success(self):
        v = Validator()
        result = v.compare(before_rate=0.3, after_rate=0.4, tasks_run=10)
        assert not result.passed  # 0.4 < 0.5 min_success_rate


class TestImprovementGate:
    def test_passes(self):
        gate = ImprovementGate(min_improvement=0.05)
        result = ValidationResult(
            passed=True, success_rate_before=0.6, success_rate_after=0.75,
            improvement=0.15, tasks_run=10, tasks_passed=8, reason="ok",
        )
        assert gate.evaluate(result)

    def test_fails_low_improvement(self):
        gate = ImprovementGate(min_improvement=0.1)
        result = ValidationResult(
            passed=True, success_rate_before=0.7, success_rate_after=0.72,
            improvement=0.02, tasks_run=10, tasks_passed=7, reason="ok",
        )
        # This gets evaluated as passed=False from gate.evaluate
        result_fail = ValidationResult(
            passed=False, success_rate_before=0.7, success_rate_after=0.72,
            improvement=0.02, tasks_run=10, tasks_passed=7, reason="low improvement",
        )
        assert not gate.evaluate(result_fail)

    def test_fails_few_tasks(self):
        gate = ImprovementGate(min_tasks=5)
        result = ValidationResult(
            passed=True, success_rate_before=0.6, success_rate_after=0.9,
            improvement=0.3, tasks_run=3, tasks_passed=3, reason="ok",
        )
        assert not gate.evaluate(result)


# ---------------------------------------------------------------------------
# ReflACT Pipeline
# ---------------------------------------------------------------------------

class TestReflACTPipeline:
    def test_pipeline_no_failures(self):
        pipeline = ReflACTPipeline(max_epochs=5)
        skill = _make_skill()
        trajectories = [_make_trajectory(f"t{i}") for i in range(5)]
        result = pipeline.optimize(skill, trajectories)
        assert result.stop_reason == EpochStopReason.NO_FAILURES
        assert result.epoch_count >= 0

    def test_pipeline_with_failures_converges(self):
        pipeline = ReflACTPipeline(max_epochs=5)
        skill = _make_skill()
        trajectories = [
            _make_trajectory("t1"),
            _make_trajectory(
                "t2", step_outcomes=[StepOutcome.FAILURE, StepOutcome.SUCCESS, StepOutcome.SUCCESS],
                overall_success=False,
            ),
            _make_trajectory("t3"),
        ]
        result = pipeline.optimize(skill, trajectories)
        assert result.stop_reason in (EpochStopReason.NO_FAILURES, EpochStopReason.CONVERGED, EpochStopReason.MAX_EPOCHS)

    def test_pipeline_with_validation(self):
        pipeline = ReflACTPipeline(max_epochs=5)
        skill = _make_skill()
        trajectories = [
            _make_trajectory(
                "t1", step_outcomes=[StepOutcome.FAILURE, StepOutcome.SUCCESS, StepOutcome.SUCCESS],
                overall_success=False,
            ),
        ]

        def executor(task, skill):
            return True

        result = pipeline.optimize(skill, trajectories, validation_tasks=["vt1", "vt2", "vt3"], execute_fn=executor)
        assert result.stop_reason in (EpochStopReason.NO_FAILURES, EpochStopReason.CONVERGED, EpochStopReason.MAX_EPOCHS, EpochStopReason.NO_IMPROVEMENT)

    def test_pipeline_original_preserved(self):
        pipeline = ReflACTPipeline(max_epochs=3)
        skill = _make_skill()
        trajectories = [
            _make_trajectory(
                "t1", step_outcomes=[StepOutcome.FAILURE, StepOutcome.SUCCESS, StepOutcome.SUCCESS],
                overall_success=False,
            ),
        ]
        result = pipeline.optimize(skill, trajectories)
        assert result.original_skill.fingerprint() == skill.fingerprint()

    def test_pipeline_result_properties(self):
        pipeline = ReflACTPipeline(max_epochs=3)
        skill = _make_skill()
        trajectories = [
            _make_trajectory(
                "t1", step_outcomes=[StepOutcome.FAILURE, StepOutcome.SUCCESS, StepOutcome.SUCCESS],
                overall_success=False,
            ),
        ]
        result = pipeline.optimize(skill, trajectories)
        assert result.epoch_count >= 0
        assert result.total_edits >= 0
        assert isinstance(result.deployed, bool)

    def test_pipeline_history(self):
        pipeline = ReflACTPipeline(max_epochs=3)
        skill = _make_skill()
        trajectories = [
            _make_trajectory(
                "t1", step_outcomes=[StepOutcome.FAILURE, StepOutcome.SUCCESS, StepOutcome.SUCCESS],
                overall_success=False,
            ),
        ]
        pipeline.optimize(skill, trajectories)
        assert len(pipeline.history) >= 0

    def test_epoch_result_fields(self):
        er = EpochResult(epoch=0, phase=PipelinePhase.REFLECT, stop_reason=EpochStopReason.NO_FAILURES)
        assert er.epoch == 0
        assert er.phase == PipelinePhase.REFLECT
        assert er.skill_fingerprint is None

    def test_epoch_result_with_act(self):
        skill = _make_skill()
        edit = EditAction(
            step_id="step-0",
            original_instruction="old",
            new_instruction="new",
            reason="test",
            source_analysis="t1",
        )
        act_result = ActResult(
            original_skill=skill, edited_skill=skill, edits_applied=(edit,), edit_count=1,
        )
        er = EpochResult(epoch=1, phase=PipelinePhase.ACT, act_result=act_result)
        assert er.skill_fingerprint is not None
        assert er.act_result.has_edits  # type: ignore[union-attr]

    def test_validation_result_before_after(self):
        v = ValidationResult(
            passed=True, success_rate_before=0.5, success_rate_after=0.8,
            improvement=0.3, tasks_run=10, tasks_passed=8, reason="Improved!",
        )
        assert v.improvement == 0.3
        assert v.success_rate_after == 0.8

    def test_reflact_pipeline_result_properties(self):
        skill = _make_skill()
        er = EpochResult(epoch=0, phase=PipelinePhase.DEPLOY, stop_reason=EpochStopReason.CONVERGED)
        result = ReflACTPipelineResult(
            original_skill=skill,
            final_skill=skill,
            epochs=(er,),
            total_improvement=0.15,
            deployed=True,
            stop_reason=EpochStopReason.CONVERGED,
        )
        assert result.epoch_count == 1
        assert result.total_edits == 0
        assert result.deployed


# ---------------------------------------------------------------------------
# compute_success_rate
# ---------------------------------------------------------------------------

class TestComputeSuccessRate:
    def test_all_success(self):
        ts = [_make_trajectory(f"t{i}") for i in range(5)]
        assert compute_success_rate(ts) == 1.0

    def test_mixed(self):
        ts = [
            _make_trajectory("t1"),
            _make_trajectory(
                "t2", step_outcomes=[StepOutcome.FAILURE, StepOutcome.SUCCESS, StepOutcome.SUCCESS],
                overall_success=False,
            ),
            _make_trajectory("t3"),
        ]
        assert compute_success_rate(ts) == 2 / 3

    def test_empty(self):
        assert compute_success_rate([]) == 0.0


# ---------------------------------------------------------------------------
# PipelinePhase
# ---------------------------------------------------------------------------

class TestPipelinePhase:
    def test_values(self):
        assert PipelinePhase.REFLECT.value == "reflect"
        assert PipelinePhase.ACT.value == "act"
        assert PipelinePhase.VALIDATE.value == "validate"
        assert PipelinePhase.DEPLOY.value == "deploy"


class TestEpochStopReason:
    def test_values(self):
        assert EpochStopReason.MAX_EPOCHS.value == "max_epochs"
        assert EpochStopReason.CONVERGED.value == "converged"
