"""Tests for Phase 4.2a — Goal Decomposition Engine."""
from __future__ import annotations

import pytest

from lyra_core.auto.goal_decomposer import (
    Goal,
    GoalDecomposer,
    GoalProgressReport,
    GoalType,
    Milestone,
    MilestoneStatus,
)


@pytest.fixture
def decomposer():
    return GoalDecomposer()


class TestGoalDecomposer:
    """Unit tests for GoalDecomposer."""

    def test_decompose_feature_creates_milestones(self, decomposer):
        goal = decomposer.decompose("Implement user authentication with OAuth2")
        assert goal.goal_type == GoalType.FEATURE
        assert len(goal.milestones) > 0
        assert goal.overall_progress == 0.0

    def test_decompose_uses_default_hours(self, decomposer):
        goal = decomposer.decompose("Add new feature")
        total = sum(m.estimated_effort_hours for m in goal.milestones)
        assert total == pytest.approx(8.0, rel=0.1)

    def test_decompose_respects_estimated_hours(self, decomposer):
        goal = decomposer.decompose("Build pipeline", estimated_hours=24.0)
        total = sum(m.estimated_effort_hours for m in goal.milestones)
        assert total == pytest.approx(24.0, rel=0.1)

    def test_decompose_detects_debug_type(self, decomposer):
        goal = decomposer.decompose("Fix the authentication bug")
        assert goal.goal_type == GoalType.DEBUG

    def test_decompose_detects_perf_type(self, decomposer):
        goal = decomposer.decompose("Optimize database query speed")
        assert goal.goal_type == GoalType.PERF

    def test_decompose_detects_refactor_type(self, decomposer):
        goal = decomposer.decompose("Refactor the user module")
        assert goal.goal_type == GoalType.REFACTOR

    def test_decompose_detects_docs_type(self, decomposer):
        goal = decomposer.decompose("Write documentation for API")
        assert goal.goal_type == GoalType.DOCS

    def test_decompose_detects_deploy_type(self, decomposer):
        goal = decomposer.decompose("Deploy to production environment")
        assert goal.goal_type == GoalType.DEPLOY

    def test_decompose_detects_research_type(self, decomposer):
        goal = decomposer.decompose("Research new ML algorithms")
        assert goal.goal_type == GoalType.RESEARCH

    def test_decompose_explicit_type_override(self, decomposer):
        goal = decomposer.decompose(
            "Fix the bug in deployment",
            goal_type=GoalType.DEPLOY,
        )
        assert goal.goal_type == GoalType.DEPLOY

    def test_decompose_matches_keyword_in_value(self, decomposer):
        goal = decomposer.decompose("Set up infrastructure for monitoring")
        assert goal.goal_type == GoalType.INFRA

    def test_decompose_automation_keyword(self, decomposer):
        goal = decomposer.decompose("Automate the reporting process")
        assert goal.goal_type == GoalType.AUTOMATION

    def test_decompose_migration_keyword(self, decomposer):
        goal = decomposer.decompose("Migration from postgres to mysql")
        assert goal.goal_type == GoalType.MIGRATION

    def test_decompose_integration_keyword(self, decomposer):
        goal = decomposer.decompose("Integration with slack API")
        assert goal.goal_type == GoalType.INTEGRATION

    def test_decompose_optimization_keyword(self, decomposer):
        goal = decomposer.decompose("Optimization of image processing pipeline")
        assert goal.goal_type == GoalType.OPTIMIZATION

    def test_decompose_creates_dependency_chain(self, decomposer):
        goal = decomposer.decompose("Add login feature")
        for i, m in enumerate(goal.milestones):
            if i == 0:
                assert m.dependencies == ()
            else:
                assert len(m.dependencies) == 1

    def test_decompose_sets_tags(self, decomposer):
        goal = decomposer.decompose("Build API", tags=("api", "backend"))
        assert "api" in goal.tags
        assert "backend" in goal.tags

    def test_decompose_sets_target_completion(self, decomposer):
        ts = 1717200000.0
        goal = decomposer.decompose("Build API", target_completion=ts)
        assert goal.target_completion == ts

    def test_decompose_truncates_long_name(self, decomposer):
        long_desc = "A" * 200
        goal = decomposer.decompose(long_desc)
        assert len(goal.name) <= 80

    def test_decompose_increments_goal_count(self, decomposer):
        assert decomposer.goal_count == 0
        decomposer.decompose("Goal 1")
        decomposer.decompose("Goal 2")
        assert decomposer.goal_count == 2

    def test_update_milestone_progress(self, decomposer):
        goal = decomposer.decompose("Build feature X")
        first = goal.milestones[0]
        updated = decomposer.update_milestone(
            goal.goal_id, first.milestone_id,
            progress_pct=50.0,
        )
        assert updated is not None
        ms = [m for m in updated.milestones if m.milestone_id == first.milestone_id][0]
        assert ms.progress_pct == 50.0

    def test_update_milestone_status_transition(self, decomposer):
        goal = decomposer.decompose("Build feature Y")
        first = goal.milestones[0]
        updated = decomposer.update_milestone(
            goal.goal_id, first.milestone_id,
            status=MilestoneStatus.IN_PROGRESS,
        )
        ms = [m for m in updated.milestones if m.milestone_id == first.milestone_id][0]
        assert ms.status == MilestoneStatus.IN_PROGRESS
        assert ms.started_at is not None

    def test_update_milestone_completed_sets_timestamp(self, decomposer):
        goal = decomposer.decompose("Build feature Z")
        first = goal.milestones[0]
        updated = decomposer.update_milestone(
            goal.goal_id, first.milestone_id,
            status=MilestoneStatus.COMPLETED,
            progress_pct=100.0,
        )
        ms = [m for m in updated.milestones if m.milestone_id == first.milestone_id][0]
        assert ms.status == MilestoneStatus.COMPLETED
        assert ms.completed_at is not None

    def test_update_milestone_unknown_goal_returns_none(self, decomposer):
        result = decomposer.update_milestone("bad-id", "ms-xxx")
        assert result is None

    def test_update_milestone_recalculates_overall_progress(self, decomposer):
        goal = decomposer.decompose("Build feature Q")
        for ms in goal.milestones[:2]:
            decomposer.update_milestone(
                goal.goal_id, ms.milestone_id,
                status=MilestoneStatus.COMPLETED,
                progress_pct=100.0,
            )
        updated = decomposer.get_goal(goal.goal_id)
        assert updated is not None
        assert updated.overall_progress > 0.0

    def test_get_progress_report_empty(self, decomposer):
        report = decomposer.get_progress_report()
        assert report.overall_progress == 0.0
        assert report.total_milestones == 0

    def test_get_progress_report_with_goals(self, decomposer):
        decomposer.decompose("Goal A")
        decomposer.decompose("Goal B")
        report = decomposer.get_progress_report()
        assert report.total_milestones > 0
        assert report.completed_milestones == 0

    def test_get_progress_report_tracks_blocked(self, decomposer):
        goal = decomposer.decompose("Test goal")
        ms = goal.milestones[0]
        decomposer.update_milestone(
            goal.goal_id, ms.milestone_id,
            status=MilestoneStatus.BLOCKED,
        )
        report = decomposer.get_progress_report()
        assert report.blocked_count >= 1

    def test_get_goal_returns_none_for_unknown(self, decomposer):
        assert decomposer.get_goal("nonexistent") is None

    def test_goal_frozen(self, decomposer):
        goal = decomposer.decompose("Test")
        with pytest.raises(Exception):
            goal.overall_progress = 100.0  # type: ignore[misc]

    def test_milestone_frozen(self):
        ms = Milestone(
            milestone_id="ms-1",
            name="Test",
            description="desc",
            status=MilestoneStatus.PENDING,
            progress_pct=0.0,
            estimated_effort_hours=2.0,
            actual_effort_hours=0.0,
            dependencies=(),
            acceptance_criteria="Done",
            started_at=None,
            completed_at=None,
        )
        with pytest.raises(Exception):
            ms.progress_pct = 50.0  # type: ignore[misc]

    def test_decompose_all_goal_types(self, decomposer):
        type_map = {
            GoalType.FEATURE: "Implement feature X",
            GoalType.REFACTOR: "Refactor module Y",
            GoalType.DEBUG: "Fix bug in Z",
            GoalType.PERF: "Performance optimization",
            GoalType.INFRA: "Set up infrastructure",
            GoalType.DOCS: "Write documentation",
            GoalType.RESEARCH: "Research topic A",
            GoalType.DEPLOY: "Deploy v2.0",
            GoalType.AUTOMATION: "Automation of reports",
            GoalType.MIGRATION: "Migration from old system",
            GoalType.INTEGRATION: "Integration with service B",
            GoalType.OPTIMIZATION: "Optimization of pipeline",
        }
        for gt, desc in type_map.items():
            goal = decomposer.decompose(desc)
            assert goal.goal_type == gt

    def test_default_type_is_feature(self, decomposer):
        goal = decomposer.decompose("Make the thing work better")
        assert goal.goal_type == GoalType.FEATURE
