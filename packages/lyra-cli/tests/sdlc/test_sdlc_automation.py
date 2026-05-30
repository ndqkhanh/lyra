"""Tests for SDLC automation — pipeline, gates, release, and hooks."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from lyra_cli.sdlc.gates import GateCheck, GateResult, GateSeverity, GateStatus, QualityGate
from lyra_cli.sdlc.hooks import HookEvent, HookResult, HookScript, HooksManager
from lyra_cli.sdlc.pipeline import (
    Pipeline,
    PipelineStatus,
    StageDefinition,
    StageResult,
    StageType,
)
from lyra_cli.sdlc.release import (
    BumpLevel,
    ReleaseManager,
    ReleaseNotes,
    Version,
)


# ── Pipeline Tests ──


class TestPipeline:
    @pytest.fixture
    def pipeline(self):
        return Pipeline("ci-test")

    def test_empty_pipeline(self, pipeline):
        assert pipeline.stage_count == 0

    def test_add_stage(self, pipeline):
        pipeline.add_stage(StageDefinition("lint", StageType.LINT, "true"))
        assert pipeline.stage_count == 1

    def test_remove_stage(self, pipeline):
        pipeline.add_stage(StageDefinition("lint", StageType.LINT, "true"))
        pipeline.remove_stage("lint")
        assert pipeline.stage_count == 0

    def test_run_all_pass(self, pipeline):
        pipeline.add_stage(StageDefinition("check1", StageType.LINT, "true"))
        pipeline.add_stage(StageDefinition("check2", StageType.TEST, "true"))
        result = pipeline.run()
        assert result.status == PipelineStatus.PASSED
        assert len(result.stages) == 2

    def test_run_with_failure(self, pipeline):
        pipeline.add_stage(StageDefinition("pass", StageType.LINT, "true"))
        pipeline.add_stage(StageDefinition("fail", StageType.TEST, "false"))
        result = pipeline.run()
        assert result.status == PipelineStatus.FAILED
        assert result.stages[1].status == PipelineStatus.FAILED

    def test_run_with_skip(self, pipeline):
        pipeline.add_stage(StageDefinition("s1", StageType.LINT, "true"))
        pipeline.add_stage(StageDefinition("s2", StageType.TEST, "true"))
        result = pipeline.run(skip_stages={"s2"})
        assert result.stages[1].status == PipelineStatus.SKIPPED

    def test_allow_failure_stage(self, pipeline):
        pipeline.add_stage(StageDefinition("opt", StageType.CUSTOM, "false", allow_failure=True))
        result = pipeline.run()
        assert result.status == PipelineStatus.PASSED

    def test_run_id_increments(self, pipeline):
        pipeline.add_stage(StageDefinition("s", StageType.LINT, "true"))
        r1 = pipeline.run()
        r2 = pipeline.run()
        assert r1.run_id != r2.run_id
        assert r1.run_id.endswith("001")
        assert r2.run_id.endswith("002")


class TestStageResult:
    def test_result_immutability(self):
        r = StageResult(stage="test", stage_type=StageType.LINT, status=PipelineStatus.PASSED, duration_ms=1.0)
        with pytest.raises(Exception):
            r.status = PipelineStatus.FAILED


# ── Quality Gate Tests ──


class TestQualityGate:
    @pytest.fixture
    def gate(self):
        return QualityGate("pre-merge", min_score=0.7)

    def test_empty_gate(self, gate):
        result = gate.evaluate({})
        assert result.overall == GateStatus.FAILED  # 0.0 < 0.7
        assert result.score == 0.0

    def test_single_check_pass(self, gate):
        gate.add_check("coverage", weight=1.0, threshold=0.8)
        result = gate.evaluate({"coverage": 0.85})
        assert result.overall == GateStatus.PASSED

    def test_single_check_fail(self, gate):
        gate.add_check("coverage", weight=1.0, threshold=0.8)
        result = gate.evaluate({"coverage": 0.5})
        assert result.overall == GateStatus.FAILED

    def test_multiple_checks_weighted(self, gate):
        gate.add_check("coverage", weight=0.4, threshold=0.8)
        gate.add_check("lint", weight=0.3, threshold=0.0)
        gate.add_check("security", weight=0.3, threshold=0.9)
        result = gate.evaluate({"coverage": 0.85, "lint": 0, "security": 0.95})
        assert result.overall == GateStatus.PASSED

    def test_blocker_fails_gate(self, gate):
        gate.add_check("security", weight=0.5, threshold=0.9, severity=GateSeverity.BLOCKER)
        result = gate.evaluate({"security": 0.5})
        assert result.overall == GateStatus.FAILED

    def test_skipped_missing_metric(self, gate):
        gate.add_check("coverage")
        result = gate.evaluate({})
        assert result.checks[0].status == GateStatus.SKIPPED

    def test_lower_is_better(self, gate):
        gate.add_check("error_count", weight=1.0, threshold=5.0, higher_is_better=False)
        result = gate.evaluate({"error_count": 3.0})
        assert result.overall == GateStatus.PASSED

    def test_lower_is_better_fail(self, gate):
        gate.add_check("error_count", weight=1.0, threshold=5.0, higher_is_better=False)
        result = gate.evaluate({"error_count": 10.0})
        assert result.overall == GateStatus.FAILED


class TestGateResult:
    def test_result_immutability(self):
        r = GateResult(gate_name="test", checks=(), overall=GateStatus.PASSED, score=1.0)
        with pytest.raises(Exception):
            r.overall = GateStatus.FAILED


# ── Release Manager Tests ──


class TestVersion:
    def test_parse_simple(self):
        v = Version.parse("1.2.3")
        assert v.major == 1
        assert v.minor == 2
        assert v.patch == 3

    def test_parse_prerelease(self):
        v = Version.parse("2.0.0-beta.1")
        assert v.major == 2
        assert v.prerelease == "beta.1"

    def test_parse_invalid(self):
        with pytest.raises(ValueError, match="Invalid version"):
            Version.parse("not.a.version")

    def test_str(self):
        assert str(Version(1, 2, 3)) == "1.2.3"

    def test_str_prerelease(self):
        assert str(Version(2, 0, 0, "rc1")) == "2.0.0-rc1"

    def test_bump_patch(self):
        v = Version.parse("1.2.3").bump(BumpLevel.PATCH)
        assert str(v) == "1.2.4"

    def test_bump_minor(self):
        v = Version.parse("1.2.3").bump(BumpLevel.MINOR)
        assert str(v) == "1.3.0"

    def test_bump_major(self):
        v = Version.parse("1.2.3").bump(BumpLevel.MAJOR)
        assert str(v) == "2.0.0"

    def test_immutability(self):
        v = Version(1, 0, 0)
        with pytest.raises(Exception):
            v.major = 2


class TestReleaseManager:
    @pytest.fixture
    def mgr(self):
        return ReleaseManager("1.0.0")

    def test_current_version(self, mgr):
        assert mgr.current_version == "1.0.0"

    def test_bump_version(self, mgr):
        v = mgr.bump_version(BumpLevel.MINOR)
        assert str(v) == "1.1.0"
        assert mgr.current_version == "1.1.0"

    def test_add_change(self, mgr):
        mgr.add_change("Added feature X", category="feature")
        notes = mgr.generate_release_notes(title="v1.0.1")
        assert len(notes.changelog[-1].changes) == 1

    def test_breaking_change(self, mgr):
        mgr.add_change("Changed API signature", breaking=True)
        notes = mgr.generate_release_notes()
        assert len(notes.breaking_changes) == 1

    def test_format_markdown(self, mgr):
        mgr.add_change("New feature", category="feature")
        notes = mgr.generate_release_notes(title="Test Release")
        formatted = mgr.format_notes(notes, fmt="markdown")
        assert "# Test Release" in formatted
        assert "New feature" in formatted

    def test_format_text(self, mgr):
        mgr.add_change("Bug fix")
        notes = mgr.generate_release_notes(title="Test")
        formatted = mgr.format_notes(notes, fmt="text")
        assert "RELEASE: Test" in formatted

    def test_changelog_accumulates(self, mgr):
        mgr.add_change("First change")
        mgr.generate_release_notes(title="v1.0.1")
        mgr.bump_version(BumpLevel.PATCH)
        mgr.add_change("Second change")
        notes = mgr.generate_release_notes(title="v1.0.2")
        assert len(notes.changelog) == 2


class TestReleaseNotes:
    def test_immutability(self):
        notes = ReleaseNotes(
            version=Version(1, 0, 0), title="Test", highlights=("h1",),
            changelog=(), breaking_changes=(), contributors=(), generated_at=1.0,
        )
        with pytest.raises(Exception):
            notes.title = "other"


# ── Hooks Tests ──


class TestHooksManager:
    @pytest.fixture
    def hooks_mgr(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / ".git" / "hooks").mkdir(parents=True)
            yield HooksManager(repo_path=str(repo))

    def test_add_hook(self, hooks_mgr):
        hooks_mgr.add_hook(HookScript(HookEvent.PRE_COMMIT, "lint", "true"))
        hooks = hooks_mgr.get_hooks(HookEvent.PRE_COMMIT)
        assert len(hooks) == 1

    def test_remove_hook(self, hooks_mgr):
        hooks_mgr.add_hook(HookScript(HookEvent.PRE_COMMIT, "lint", "true"))
        hooks_mgr.remove_hook(HookEvent.PRE_COMMIT, "lint")
        assert len(hooks_mgr.get_hooks(HookEvent.PRE_COMMIT)) == 0

    def test_get_all_hooks(self, hooks_mgr):
        hooks_mgr.add_hook(HookScript(HookEvent.PRE_COMMIT, "a", "true"))
        hooks_mgr.add_hook(HookScript(HookEvent.PRE_PUSH, "b", "true"))
        assert len(hooks_mgr.get_hooks()) == 2

    def test_run_hook_success(self, hooks_mgr):
        hooks_mgr.add_hook(HookScript(HookEvent.PRE_COMMIT, "ok", "true"))
        results = hooks_mgr.run_hook(HookEvent.PRE_COMMIT)
        assert len(results) == 1
        assert results[0].passed

    def test_run_hook_failure(self, hooks_mgr):
        hooks_mgr.add_hook(HookScript(HookEvent.PRE_COMMIT, "bad", "false"))
        results = hooks_mgr.run_hook(HookEvent.PRE_COMMIT)
        assert not results[0].passed

    def test_disabled_hook_skipped(self, hooks_mgr):
        hooks_mgr.add_hook(HookScript(HookEvent.PRE_COMMIT, "skip", "true", enabled=False))
        results = hooks_mgr.run_hook(HookEvent.PRE_COMMIT)
        assert len(results) == 0

    def test_install_creates_hooks(self, hooks_mgr):
        hooks_mgr.add_hook(HookScript(HookEvent.PRE_COMMIT, "lint", "echo lint"))
        installed = hooks_mgr.install()
        assert HookEvent.PRE_COMMIT.value in installed


class TestHookEvent:
    def test_values(self):
        assert HookEvent.PRE_COMMIT == "pre-commit"
        assert HookEvent.PRE_PUSH == "pre-push"


class TestHookResult:
    def test_result_immutability(self):
        r = HookResult(event=HookEvent.PRE_COMMIT, passed=True)
        with pytest.raises(Exception):
            r.passed = False


class TestBumpLevel:
    def test_values(self):
        assert BumpLevel.MAJOR == "major"
        assert BumpLevel.MINOR == "minor"
        assert BumpLevel.PATCH == "patch"
