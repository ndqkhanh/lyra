"""Tests for SDLC automation modules."""
from __future__ import annotations

from lyra_core.sdlc.test_pipeline import (
    PipelineConfig,
    StageStatus,
    PipelineRunner,
)
from lyra_core.sdlc.quality_gates import (
    Gate,
    GateSeverity,
    QualityGateRunner,
)
from lyra_core.sdlc.changelog_generator import (
    ChangeType,
    ChangelogGenerator,
)
from lyra_core.sdlc.release_manager import (
    BumpType,
    ReleaseManager,
    VersionBumper,
)
from lyra_core.sdlc.hooks import (
    HookManager,
    HookStatus,
    PreCommitHook,
    PrePushHook,
)


class TestPipelineRunner:
    def test_empty_pipeline(self):
        config = PipelineConfig(stages=())
        pipeline = PipelineRunner(config=config)
        result = pipeline.run()
        assert result.overall_status == StageStatus.SKIPPED
        assert len(result.stages) == 0

    def test_skipped_stage_no_handler(self):
        config = PipelineConfig(stages=("unit",))
        pipeline = PipelineRunner(config=config)
        result = pipeline.run()
        assert result.stages[0].status == StageStatus.SKIPPED

    def test_passing_stage(self):
        config = PipelineConfig(stages=("unit",))
        pipeline = PipelineRunner(config=config)
        pipeline.register_stage("unit", lambda: {"status": "passed", "total": 10, "passed": 10, "failed": 0})
        result = pipeline.run()
        assert result.stages[0].status == StageStatus.PASSED
        assert result.total_tests == 10
        assert result.total_passed == 10

    def test_failing_stage(self):
        config = PipelineConfig(stages=("unit",))
        pipeline = PipelineRunner(config=config)

        def _fail():
            raise RuntimeError("test failure")

        pipeline.register_stage("unit", _fail)
        result = pipeline.run()
        assert result.stages[0].status == StageStatus.FAILED
        assert result.overall_status == StageStatus.FAILED

    def test_fail_fast_stops_on_failure(self):
        config = PipelineConfig(stages=("unit", "integration"), fail_fast=True)
        pipeline = PipelineRunner(config=config)

        def _fail():
            raise RuntimeError("fail")
        called = {"integration": False}

        def _integration():
            called["integration"] = True
            return {"status": "passed"}

        pipeline.register_stage("unit", _fail)
        pipeline.register_stage("integration", _integration)
        result = pipeline.run()
        assert result.overall_status == StageStatus.FAILED
        assert not called["integration"]

    def test_multiple_stages(self):
        config = PipelineConfig(stages=("unit", "integration"))
        pipeline = PipelineRunner(config=config)
        pipeline.register_stage("unit", lambda: {"status": "passed", "total": 5, "passed": 5, "failed": 0})
        pipeline.register_stage("integration", lambda: {"status": "passed", "total": 3, "passed": 3, "failed": 0})
        result = pipeline.run()
        assert result.overall_status == StageStatus.PASSED
        assert result.total_tests == 8


class TestQualityGates:
    def test_gate_passes_when_above_threshold(self):
        gate = Gate("coverage", GateSeverity.BLOCKER, 80.0, "gte")
        result = gate.evaluate(85.0)
        assert result.passed

    def test_gate_fails_when_below_threshold(self):
        gate = Gate("coverage", GateSeverity.BLOCKER, 80.0, "gte")
        result = gate.evaluate(75.0)
        assert not result.passed
        assert result.is_blocker

    def test_lte_comparator(self):
        gate = Gate("security_issues", GateSeverity.BLOCKER, 0.0, "lte")
        assert gate.evaluate(0.0).passed
        assert not gate.evaluate(1.0).passed

    def test_warning_gate_not_blocker(self):
        gate = Gate("doc_coverage", GateSeverity.WARNING, 70.0, "gte")
        result = gate.evaluate(50.0)
        assert not result.passed
        assert not result.is_blocker

    def test_runner_all_pass(self):
        runner = QualityGateRunner()
        runner.add_gate(Gate("coverage", GateSeverity.BLOCKER, 80.0, "gte"))
        runner.add_gate(Gate("lint", GateSeverity.BLOCKER, 100.0, "gte"))
        runner.run({"coverage": 85.0, "lint": 100.0})
        assert runner.passed
        assert runner.blocker_count == 0

    def test_runner_blocker_fails(self):
        runner = QualityGateRunner()
        runner.add_gate(Gate("coverage", GateSeverity.BLOCKER, 80.0, "gte"))
        runner.run({"coverage": 50.0})
        assert not runner.passed
        assert runner.blocker_count == 1

    def test_default_gates(self):
        runner = QualityGateRunner.default_gates()
        assert len(runner.gates) >= 4

    def test_multiple_severities(self):
        runner = QualityGateRunner()
        runner.add_gate(Gate("coverage", GateSeverity.BLOCKER, 80.0, "gte"))
        runner.add_gate(Gate("complexity", GateSeverity.WARNING, 20.0, "lte"))
        runner.run({"coverage": 90.0, "complexity": 25.0})
        assert runner.passed
        assert runner.warning_count == 1


class TestChangelogGenerator:
    def test_parse_feat_commit(self):
        gen = ChangelogGenerator()
        entry = gen.parse_commit("feat(auth): add OAuth2 support")
        assert entry is not None
        assert entry.change_type == ChangeType.FEAT
        assert entry.scope == "auth"

    def test_parse_fix_commit(self):
        gen = ChangelogGenerator()
        entry = gen.parse_commit("fix: resolve null pointer in parser")
        assert entry is not None
        assert entry.change_type == ChangeType.FIX
        assert entry.scope == ""

    def test_parse_breaking_change(self):
        gen = ChangelogGenerator()
        entry = gen.parse_commit("feat!(api): redesign endpoint structure")
        assert entry is not None
        assert entry.breaking

    def test_parse_invalid_commit_returns_none(self):
        gen = ChangelogGenerator()
        entry = gen.parse_commit("random message without format")
        assert entry is None

    def test_parse_commits_batch(self):
        gen = ChangelogGenerator()
        entries = gen.parse_commits([
            "feat: add login",
            "fix: patch auth bug",
            "not a conventional commit",
        ])
        assert len(entries) == 2

    def test_generate_markdown(self):
        gen = ChangelogGenerator()
        gen.parse_commit("feat(ui): add dark mode")
        gen.parse_commit("fix: resolve crash on startup")
        output = gen.generate("1.0.0")
        assert "1.0.0" in output
        assert "Features" in output
        assert "Bug Fixes" in output
        assert "dark mode" in output


class TestReleaseManager:
    def test_bump_patch(self):
        vb = VersionBumper()
        assert vb.bump("1.2.3", BumpType.PATCH) == "1.2.4"

    def test_bump_minor(self):
        vb = VersionBumper()
        assert vb.bump("1.2.3", BumpType.MINOR) == "1.3.0"

    def test_bump_major(self):
        vb = VersionBumper()
        assert vb.bump("1.2.3", BumpType.MAJOR) == "2.0.0"

    def test_bump_invalid_version(self):
        import pytest
        vb = VersionBumper()
        with pytest.raises(ValueError):
            vb.bump("invalid", BumpType.PATCH)

    def test_suggest_major_on_breaking(self):
        vb = VersionBumper()
        assert vb.suggest_bump(["feat!: breaking api change"]) == BumpType.MAJOR

    def test_suggest_minor_on_feat(self):
        vb = VersionBumper()
        assert vb.suggest_bump(["feat: add new endpoint"]) == BumpType.MINOR

    def test_suggest_patch_by_default(self):
        vb = VersionBumper()
        assert vb.suggest_bump(["fix: typo"]) == BumpType.PATCH

    def test_release_success(self):
        rm = ReleaseManager()
        result = rm.release("1.0.0", BumpType.MINOR)
        assert result.success
        assert result.new_version == "1.1.0"

    def test_release_auto_suggest(self):
        rm = ReleaseManager()
        result = rm.release("1.0.0", commit_messages=["feat: add feature"])
        assert result.success
        assert result.new_version == "1.1.0"


class TestHooks:
    def test_pre_commit_default_checks(self):
        hook = PreCommitHook()
        assert "lint" in hook.checks
        assert "security" in hook.checks

    def test_pre_commit_run(self):
        hook = PreCommitHook()
        results = hook.run(["test.py"])
        assert len(results) == 3
        assert all(r.status == HookStatus.PASSED for r in results)

    def test_pre_push_run(self):
        hook = PrePushHook()
        results = hook.run("main")
        assert len(results) == 3
        assert all(r.status == HookStatus.PASSED for r in results)

    def test_hook_manager_pre_commit(self):
        hm = HookManager()
        results = hm.run_pre_commit()
        assert len(results) == 3

    def test_hook_manager_pre_push(self):
        hm = HookManager()
        results = hm.run_pre_push()
        assert len(results) == 3

    def test_hook_manager_all_passed(self):
        hm = HookManager()
        hm.run_pre_commit()
        assert hm.all_passed

    def test_hook_manager_history(self):
        hm = HookManager()
        hm.run_pre_commit()
        hm.run_pre_push()
        assert len(hm.recent_results) == 6

    def test_hook_manager_clear(self):
        hm = HookManager()
        hm.run_pre_commit()
        hm.clear_history()
        assert len(hm.recent_results) == 0
