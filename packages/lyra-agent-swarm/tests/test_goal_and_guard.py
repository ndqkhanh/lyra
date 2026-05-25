"""Tests for Plan 11: Goal System and Continuous Guard."""

from __future__ import annotations

import time

import pytest

from lyra_agent_swarm.continuous_guard import (
    DESTRUCTIVE_PATTERNS,
    MAX_CONSECUTIVE_FAILURES,
    MAX_COST_PER_HOUR_USD,
    MAX_FILES_PER_HOUR,
    ContinuousGuard,
    GuardAction,
    GuardReason,
    GuardState,
    GuardVerdict,
    OperationRecord,
    create_default_guard,
    create_lenient_guard,
    create_strict_guard,
)
from lyra_agent_swarm.goal_system import (
    GOAL_TEMPLATES,
    Goal,
    GoalAgentType,
    GoalCriteria,
    GoalEvent,
    GoalManager,
    GoalMetrics,
    GoalPriority,
    GoalStatus,
)


# ═══════════════════════════════════════════════════════════════════════════
# Goal System Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestGoalStatus:
    def test_all_statuses_present(self):
        assert GoalStatus.ACTIVE.value == "active"
        assert GoalStatus.PAUSED.value == "paused"
        assert GoalStatus.COMPLETED.value == "completed"
        assert GoalStatus.FAILED.value == "failed"
        assert GoalStatus.BLOCKED.value == "blocked"
        assert GoalStatus.CANCELLED.value == "cancelled"

    def test_status_is_enum(self):
        assert isinstance(GoalStatus.ACTIVE, GoalStatus)


class TestGoalPriority:
    def test_priority_ordering(self):
        assert GoalPriority.P0.value < GoalPriority.P1.value
        assert GoalPriority.P1.value < GoalPriority.P2.value
        assert GoalPriority.P2.value < GoalPriority.P3.value

    def test_default_is_p2(self):
        g = Goal(title="test")
        assert g.priority == GoalPriority.P2


class TestGoalAgentType:
    def test_all_types_present(self):
        types = {t.value for t in GoalAgentType}
        assert types >= {"code", "research", "design", "sre", "review", "auto"}


class TestGoalCriteria:
    def test_create_criterion(self):
        c = GoalCriteria(description="All tests pass")
        assert c.description == "All tests pass"
        assert not c.verified

    def test_criterion_verified(self):
        c = GoalCriteria(description="Tests pass", verified=True)
        assert c.verified

    def test_criterion_is_frozen(self):
        c = GoalCriteria(description="Tests pass")
        with pytest.raises(Exception):
            c.verified = True


class TestGoalMetrics:
    def test_default_metrics(self):
        m = GoalMetrics()
        assert m.turns_completed == 0
        assert m.tokens_used == 0
        assert m.cost_usd == 0.0
        assert m.files_changed == 0
        assert m.tests_passing == 0
        assert m.completion_pct == 0.0

    def test_custom_metrics(self):
        m = GoalMetrics(turns_completed=10, cost_usd=1.50, completion_pct=75.0)
        assert m.turns_completed == 10
        assert m.cost_usd == 1.50
        assert m.completion_pct == 75.0

    def test_metrics_is_frozen(self):
        m = GoalMetrics()
        with pytest.raises(Exception):
            m.turns_completed = 5


class TestGoalEvent:
    def test_create_event(self):
        e = GoalEvent(timestamp=1234567890.0, event_type="created", details="Goal created")
        assert e.timestamp == 1234567890.0
        assert e.event_type == "created"
        assert e.details == "Goal created"

    def test_event_has_metrics_snapshot(self):
        m = GoalMetrics(tokens_used=500)
        e = GoalEvent(timestamp=time.time(), event_type="progress", details="Working", metrics_snapshot=m)
        assert e.metrics_snapshot.tokens_used == 500


class TestGoalModel:
    def test_create_minimal_goal(self):
        g = Goal(title="Test goal")
        assert g.id.startswith("goal_")
        assert g.title == "Test goal"
        assert g.status == GoalStatus.ACTIVE
        assert g.priority == GoalPriority.P2

    def test_create_full_goal(self):
        g = Goal(
            title="Full goal",
            description="Detailed description",
            criteria=(GoalCriteria("Criterion 1"), GoalCriteria("Criterion 2", verified=True)),
            priority=GoalPriority.P0,
            agent_type=GoalAgentType.CODE,
            max_budget_usd=10.0,
            max_turns=50,
        )
        assert g.description == "Detailed description"
        assert len(g.criteria) == 2
        assert g.priority == GoalPriority.P0
        assert g.agent_type == GoalAgentType.CODE
        assert g.max_budget_usd == 10.0
        assert g.max_turns == 50

    def test_goal_is_frozen(self):
        g = Goal(title="Test")
        with pytest.raises(Exception):
            g.title = "changed"

    def test_is_overdue_with_deadline(self):
        past = time.time() - 3600
        g = Goal(title="Overdue", deadline=past)
        assert g.is_overdue

    def test_is_not_overdue_without_deadline(self):
        g = Goal(title="No deadline")
        assert not g.is_overdue

    def test_is_not_overdue_with_future_deadline(self):
        future = time.time() + 86400
        g = Goal(title="Future", deadline=future)
        assert not g.is_overdue

    def test_is_budget_exhausted(self):
        g = Goal(title="Expensive", max_budget_usd=5.0, metrics=GoalMetrics(cost_usd=6.0))
        assert g.is_budget_exhausted

    def test_is_budget_not_exhausted(self):
        g = Goal(title="Cheap", max_budget_usd=5.0, metrics=GoalMetrics(cost_usd=2.0))
        assert not g.is_budget_exhausted

    def test_is_turns_exhausted(self):
        g = Goal(title="Many turns", max_turns=100, metrics=GoalMetrics(turns_completed=100))
        assert g.is_turns_exhausted

    def test_is_turns_not_exhausted(self):
        g = Goal(title="Few turns", max_turns=100, metrics=GoalMetrics(turns_completed=50))
        assert not g.is_turns_exhausted

    def test_criteria_met_count(self):
        g = Goal(
            title="Count criteria",
            criteria=(
                GoalCriteria("A", verified=True),
                GoalCriteria("B", verified=False),
                GoalCriteria("C", verified=True),
            ),
        )
        assert g.criteria_met == 2
        assert g.criteria_total == 3


class TestGoalTemplates:
    def test_migrate_template(self):
        tmpl = GOAL_TEMPLATES["migrate"]
        assert tmpl["agent_type"] == GoalAgentType.CODE
        assert not tmpl["auto_approve"]
        assert len(tmpl["criteria"]) == 4

    def test_research_template(self):
        tmpl = GOAL_TEMPLATES["research"]
        assert tmpl["agent_type"] == GoalAgentType.RESEARCH
        assert tmpl["auto_approve"]

    def test_investigate_template(self):
        tmpl = GOAL_TEMPLATES["investigate"]
        assert tmpl["agent_type"] == GoalAgentType.CODE
        assert "Root cause identified" in tmpl["criteria"]

    def test_refactor_template(self):
        tmpl = GOAL_TEMPLATES["refactor"]
        assert "All existing tests pass" in tmpl["criteria"]

    def test_implement_feature_template(self):
        tmpl = GOAL_TEMPLATES["implement-feature"]
        assert len(tmpl["criteria"]) == 5

    def test_security_audit_template(self):
        tmpl = GOAL_TEMPLATES["security-audit"]
        assert tmpl["agent_type"] == GoalAgentType.REVIEW
        assert "Secret scanning completed" in tmpl["criteria"]

    def test_all_templates_have_required_keys(self):
        for name, tmpl in GOAL_TEMPLATES.items():
            assert "agent_type" in tmpl, f"{name} missing agent_type"
            assert "auto_approve" in tmpl, f"{name} missing auto_approve"
            assert "criteria" in tmpl, f"{name} missing criteria"
            assert len(tmpl["criteria"]) >= 3, f"{name} has fewer than 3 criteria"


class TestGoalManagerCreate:
    def test_create_goal(self):
        mgr = GoalManager()
        g = mgr.create(title="My goal", description="Do something")
        assert g.title == "My goal"
        assert g.description == "Do something"
        assert g.status == GoalStatus.ACTIVE
        assert mgr.goal_count == 1

    def test_create_goal_with_criteria(self):
        mgr = GoalManager()
        g = mgr.create(title="With criteria", criteria=("C1", "C2", "C3"))
        assert len(g.criteria) == 3
        assert g.criteria[0].description == "C1"

    def test_create_goal_from_template(self):
        mgr = GoalManager()
        g = mgr.create(title="Migrate DB", template="migrate")
        assert g.agent_type == GoalAgentType.CODE
        assert not g.auto_approve
        assert len(g.criteria) == 4

    def test_create_goal_from_template_with_override_criteria(self):
        mgr = GoalManager()
        g = mgr.create(title="Research X", template="research", criteria=("Custom C1",))
        assert len(g.criteria) == 1
        assert g.criteria[0].description == "Custom C1"

    def test_create_goal_with_custom_priority(self):
        mgr = GoalManager()
        g = mgr.create(title="Critical", priority=GoalPriority.P0)
        assert g.priority == GoalPriority.P0

    def test_create_goal_has_history(self):
        mgr = GoalManager()
        g = mgr.create(title="With history")
        assert len(g.history) == 1
        assert g.history[0].event_type == "created"

    def test_create_goal_with_nonexistent_template(self):
        mgr = GoalManager()
        g = mgr.create(title="No template", template="nonexistent")
        assert g.agent_type == GoalAgentType.AUTO

    def test_create_sub_goal(self):
        mgr = GoalManager()
        parent = mgr.create(title="Parent")
        sub = mgr.create_sub_goal(parent.id, title="Child")
        assert sub is not None
        assert sub.parent_goal == parent.id
        updated_parent = mgr.get(parent.id)
        assert updated_parent is not None
        assert sub.id in updated_parent.sub_goals

    def test_create_sub_goal_nonexistent_parent(self):
        mgr = GoalManager()
        sub = mgr.create_sub_goal("nonexistent", title="Orphan")
        assert sub is None


class TestGoalManagerRead:
    def test_get_existing_goal(self):
        mgr = GoalManager()
        g = mgr.create(title="Exists")
        fetched = mgr.get(g.id)
        assert fetched is not None
        assert fetched.title == "Exists"

    def test_get_nonexistent_goal(self):
        mgr = GoalManager()
        assert mgr.get("nonexistent") is None

    def test_list_active(self):
        mgr = GoalManager()
        mgr.create(title="Active 1")
        mgr.create(title="Active 2")
        mgr.update_status(mgr.create(title="Done").id, GoalStatus.COMPLETED)
        assert len(mgr.list_active()) == 2

    def test_list_all(self):
        mgr = GoalManager()
        mgr.create(title="G1")
        mgr.create(title="G2")
        assert len(mgr.list_all()) == 2

    def test_list_by_status(self):
        mgr = GoalManager()
        g = mgr.create(title="Fail")
        mgr.update_status(g.id, GoalStatus.FAILED)
        assert len(mgr.list_by_status(GoalStatus.FAILED)) == 1
        assert len(mgr.list_by_status(GoalStatus.ACTIVE)) == 0

    def test_list_by_priority(self):
        mgr = GoalManager()
        mgr.create(title="P0", priority=GoalPriority.P0)
        mgr.create(title="P1", priority=GoalPriority.P1)
        mgr.create(title="P2", priority=GoalPriority.P2)
        assert len(mgr.list_by_priority(GoalPriority.P0)) == 1

    def test_get_goal_tree(self):
        mgr = GoalManager()
        root = mgr.create(title="Root")
        child = mgr.create_sub_goal(root.id, title="Child")
        assert child is not None
        grandchild = mgr.create_sub_goal(child.id, title="Grandchild")
        assert grandchild is not None
        tree = mgr.get_goal_tree(root.id)
        assert tree["goal"].title == "Root"
        assert len(tree["sub_goals"]) == 1
        assert tree["sub_goals"][0]["goal"].title == "Child"

    def test_get_goal_tree_nonexistent(self):
        mgr = GoalManager()
        assert mgr.get_goal_tree("nonexistent") == {}

    def test_empty_manager_stats(self):
        mgr = GoalManager()
        stats = mgr.stats()
        assert stats["total"] == 0
        assert stats["active"] == 0


class TestGoalManagerUpdate:
    def test_update_status(self):
        mgr = GoalManager()
        g = mgr.create(title="Progress")
        updated = mgr.update_status(g.id, GoalStatus.COMPLETED, reason="Done!")
        assert updated is not None
        assert updated.status == GoalStatus.COMPLETED
        assert updated.completed_at is not None
        assert len(updated.history) == 2

    def test_update_status_nonexistent(self):
        mgr = GoalManager()
        assert mgr.update_status("nonexistent", GoalStatus.COMPLETED) is None

    def test_update_metrics(self):
        mgr = GoalManager()
        g = mgr.create(title="Tracked")
        updated = mgr.update_metrics(g.id, turns_completed=5, cost_usd=1.25)
        assert updated is not None
        assert updated.metrics.turns_completed == 5
        assert updated.metrics.cost_usd == 1.25
        assert updated.metrics.tokens_used == 0

    def test_update_metrics_nonexistent(self):
        mgr = GoalManager()
        assert mgr.update_metrics("nonexistent", turns_completed=1) is None

    def test_verify_criterion(self):
        mgr = GoalManager()
        g = mgr.create(title="Verify me", criteria=("C1", "C2", "C3"))
        updated = mgr.verify_criterion(g.id, 0)
        assert updated is not None
        assert updated.criteria[0].verified
        assert not updated.criteria[1].verified

    def test_verify_criterion_nonexistent_goal(self):
        mgr = GoalManager()
        assert mgr.verify_criterion("nonexistent", 0) is None

    def test_verify_criterion_out_of_range(self):
        mgr = GoalManager()
        g = mgr.create(title="Range check", criteria=("C1",))
        assert mgr.verify_criterion(g.id, 5) is None

    def test_verify_all_criteria_auto_completes(self):
        mgr = GoalManager()
        g = mgr.create(title="Auto complete", criteria=("C1", "C2"))
        mgr.verify_criterion(g.id, 0)
        updated = mgr.verify_criterion(g.id, 1)
        assert updated is not None
        assert updated.status == GoalStatus.COMPLETED
        assert updated.completed_at is not None

    def test_cancel_goal(self):
        mgr = GoalManager()
        g = mgr.create(title="Cancel me")
        cancelled = mgr.cancel(g.id, reason="No longer needed")
        assert cancelled is not None
        assert cancelled.status == GoalStatus.CANCELLED

    def test_remove_goal(self):
        mgr = GoalManager()
        g = mgr.create(title="Remove me")
        assert mgr.goal_count == 1
        assert mgr.remove(g.id)
        assert mgr.goal_count == 0
        assert mgr.get(g.id) is None

    def test_remove_nonexistent(self):
        mgr = GoalManager()
        assert not mgr.remove("nonexistent")

    def test_pause_and_resume(self):
        mgr = GoalManager()
        g = mgr.create(title="Pausable")
        paused = mgr.update_status(g.id, GoalStatus.PAUSED)
        assert paused is not None
        assert paused.status == GoalStatus.PAUSED
        resumed = mgr.update_status(g.id, GoalStatus.ACTIVE, "Resuming")
        assert resumed is not None
        assert resumed.status == GoalStatus.ACTIVE


class TestGoalManagerQuery:
    def test_get_next_goal_returns_highest_priority(self):
        mgr = GoalManager()
        mgr.create(title="P1 goal", priority=GoalPriority.P1)
        mgr.create(title="P0 goal", priority=GoalPriority.P0)
        mgr.create(title="P2 goal", priority=GoalPriority.P2)
        next_goal = mgr.get_next_goal()
        assert next_goal is not None
        assert next_goal.priority == GoalPriority.P0

    def test_get_next_goal_empty(self):
        mgr = GoalManager()
        assert mgr.get_next_goal() is None

    def test_get_next_goal_skips_completed(self):
        mgr = GoalManager()
        g = mgr.create(title="Only active", priority=GoalPriority.P0)
        mgr.update_status(g.id, GoalStatus.COMPLETED)
        assert mgr.get_next_goal() is None

    def test_get_overdue_goals(self):
        mgr = GoalManager()
        past = time.time() - 1000
        mgr.create(title="Overdue", deadline=past)
        mgr.create(title="Not overdue", deadline=time.time() + 86400)
        overdue = mgr.get_overdue_goals()
        assert len(overdue) == 1
        assert overdue[0].title == "Overdue"

    def test_stats(self):
        mgr = GoalManager()
        mgr.create(title="A1")
        g2 = mgr.create(title="A2")
        mgr.update_status(g2.id, GoalStatus.COMPLETED)
        g3 = mgr.create(title="A3")
        mgr.update_status(g3.id, GoalStatus.FAILED)
        mgr.update_metrics(g2.id, cost_usd=1.50, tokens_used=1000)

        stats = mgr.stats()
        assert stats["total"] == 3
        assert stats["active"] == 1
        assert stats["completed"] == 1
        assert stats["failed"] == 1
        assert stats["total_cost_usd"] == 1.5
        assert stats["total_tokens"] == 1000

    def test_goal_count_property(self):
        mgr = GoalManager()
        assert mgr.goal_count == 0
        mgr.create(title="G1")
        mgr.create(title="G2")
        assert mgr.goal_count == 2


# ═══════════════════════════════════════════════════════════════════════════
# Continuous Guard Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestGuardConstants:
    def test_max_consecutive_failures_is_5(self):
        assert MAX_CONSECUTIVE_FAILURES == 5

    def test_max_cost_per_hour(self):
        assert MAX_COST_PER_HOUR_USD == 2.00

    def test_max_files_per_hour(self):
        assert MAX_FILES_PER_HOUR == 50

    def test_destructive_patterns_non_empty(self):
        assert len(DESTRUCTIVE_PATTERNS) >= 5


class TestGuardVerdict:
    def test_allow_verdict(self):
        v = GuardVerdict(action=GuardAction.ALLOW, reason=GuardReason.OK)
        assert v.is_allowed
        assert not v.is_blocked

    def test_block_verdict(self):
        v = GuardVerdict(action=GuardAction.BLOCK, reason=GuardReason.DESTRUCTIVE_PATTERN, detail="rm -rf detected")
        assert not v.is_allowed
        assert v.is_blocked
        assert v.detail == "rm -rf detected"

    def test_pause_verdict_is_blocked(self):
        v = GuardVerdict(action=GuardAction.PAUSE, reason=GuardReason.CONSECUTIVE_FAILURES)
        assert v.is_blocked

    def test_verdict_is_frozen(self):
        v = GuardVerdict(action=GuardAction.ALLOW, reason=GuardReason.OK)
        with pytest.raises(Exception):
            v.action = GuardAction.BLOCK

    def test_verdict_has_timestamp(self):
        v = GuardVerdict(action=GuardAction.ALLOW, reason=GuardReason.OK)
        assert v.timestamp > 0


class TestOperationRecord:
    def test_create_record(self):
        r = OperationRecord(command="ls -la", timestamp=time.time(), cost_usd=0.01, success=True)
        assert r.command == "ls -la"
        assert r.cost_usd == 0.01
        assert r.success

    def test_record_defaults(self):
        r = OperationRecord(command="echo hi", timestamp=time.time())
        assert r.cost_usd == 0.0
        assert r.files_touched == 0
        assert r.success

    def test_record_is_frozen(self):
        r = OperationRecord(command="cmd", timestamp=time.time())
        with pytest.raises(Exception):
            r.success = False


class TestGuardState:
    def test_default_state(self):
        s = GuardState()
        assert s.consecutive_failures == 0
        assert s.total_cost_usd == 0.0
        assert s.files_modified == 0
        assert s.operations_this_minute == 0
        assert not s.is_paused

    def test_paused_state(self):
        s = GuardState(
            consecutive_failures=5,
            is_paused=True,
            pause_reason="Too many failures",
        )
        assert s.is_paused
        assert s.pause_reason == "Too many failures"

    def test_state_is_frozen(self):
        s = GuardState()
        with pytest.raises(Exception):
            s.consecutive_failures = 3


class TestContinuousGuardInit:
    def test_create_default_guard(self):
        g = create_default_guard()
        assert not g.is_paused
        assert g.consecutive_failures == 0
        assert g.total_cost == 0.0

    def test_create_lenient_guard(self):
        g = create_lenient_guard()
        stats = g.stats()
        assert stats["cost_per_hour_limit"] == 10.0
        assert stats["files_per_hour_limit"] == 200

    def test_create_strict_guard(self):
        g = create_strict_guard()
        stats = g.stats()
        assert stats["cost_per_hour_limit"] == 0.50
        assert stats["files_per_hour_limit"] == 10
        assert stats["consecutive_failures"] == 0  # strict is 2 max

    def test_initial_state_is_clean(self):
        g = ContinuousGuard()
        state = g.state
        assert state.consecutive_failures == 0
        assert state.total_cost_usd == 0.0
        assert not state.is_paused


class TestContinuousGuardCheck:
    def test_safe_command_allowed(self):
        g = ContinuousGuard()
        v = g.check("ls -la")
        assert v.is_allowed
        assert v.reason == GuardReason.OK

    def test_destructive_rm_rf_blocked(self):
        g = ContinuousGuard()
        v = g.check("rm -rf /tmp/foo")
        assert not v.is_allowed
        assert v.reason == GuardReason.DESTRUCTIVE_PATTERN

    def test_destructive_drop_table_blocked(self):
        g = ContinuousGuard()
        v = g.check("DROP TABLE users")
        assert not v.is_allowed
        assert v.reason == GuardReason.DESTRUCTIVE_PATTERN

    def test_destructive_delete_from_blocked(self):
        g = ContinuousGuard()
        v = g.check("DELETE FROM orders WHERE id = 1")
        assert not v.is_allowed
        assert v.reason == GuardReason.DESTRUCTIVE_PATTERN

    def test_destructive_git_push_force_blocked(self):
        g = ContinuousGuard()
        v = g.check("git push -f origin main")
        assert not v.is_allowed
        assert v.reason == GuardReason.DESTRUCTIVE_PATTERN

    def test_destructive_git_reset_hard_blocked(self):
        g = ContinuousGuard()
        v = g.check("git reset --hard HEAD~1")
        assert not v.is_allowed
        assert v.reason == GuardReason.DESTRUCTIVE_PATTERN

    def test_destructive_truncate_blocked(self):
        g = ContinuousGuard()
        v = g.check("TRUNCATE TABLE logs")
        assert not v.is_allowed
        assert v.reason == GuardReason.DESTRUCTIVE_PATTERN

    def test_destructive_fork_bomb_blocked(self):
        g = ContinuousGuard()
        v = g.check(":(){ :|:& };:")
        assert not v.is_allowed

    def test_is_destructive_helper(self):
        g = ContinuousGuard()
        assert g.is_destructive("rm -rf /")
        assert not g.is_destructive("ls -la")

    def test_cost_limit_exceeded(self):
        g = ContinuousGuard()
        g.record("expensive", cost_usd=1.50)
        v = g.check("another", cost_estimate=1.00)
        assert not v.is_allowed
        assert v.reason == GuardReason.COST_LIMIT

    def test_cost_within_limit(self):
        g = ContinuousGuard()
        g.record("cheap", cost_usd=0.50)
        v = g.check("another", cost_estimate=0.50)
        assert v.is_allowed

    def test_file_limit_exceeded(self):
        g = ContinuousGuard()
        g.record("touch many", files_touched=40)
        v = g.check("more files", files_estimate=20)
        assert not v.is_allowed
        assert v.reason == GuardReason.FILE_LIMIT

    def test_file_limit_ok(self):
        g = ContinuousGuard()
        g.record("touch few", files_touched=10)
        v = g.check("more files", files_estimate=5)
        assert v.is_allowed

    def test_rate_limit_check(self):
        g = ContinuousGuard(max_ops_per_minute=2)
        g.record("op1")
        g.record("op2")
        v = g.check("op3")
        assert v.reason == GuardReason.RATE_LIMIT

    def test_paused_guard_blocks(self):
        g = ContinuousGuard(max_consecutive_failures=1)
        g.acknowledge_failure()
        v = g.check("ls")
        assert not v.is_allowed
        assert v.reason == GuardReason.CONSECUTIVE_FAILURES
        assert v.action == GuardAction.PAUSE


class TestContinuousGuardRecord:
    def test_record_success(self):
        g = ContinuousGuard()
        state = g.record("ls -la", cost_usd=0.01, files_touched=0, success=True)
        assert state.consecutive_failures == 0
        assert state.total_cost_usd == 0.01
        assert len(g.history) == 1

    def test_record_failure_increments_counter(self):
        g = ContinuousGuard()
        g.record("bad command", success=False)
        assert g.consecutive_failures == 1
        g.record("another bad", success=False)
        assert g.consecutive_failures == 2

    def test_record_success_resets_counter(self):
        g = ContinuousGuard()
        g.record("fail1", success=False)
        g.record("fail2", success=False)
        assert g.consecutive_failures == 2
        g.record("good", success=True)
        assert g.consecutive_failures == 0

    def test_record_pauses_after_max_failures(self):
        g = ContinuousGuard(max_consecutive_failures=3)
        g.record("f1", success=False)
        g.record("f2", success=False)
        g.record("f3", success=False)
        assert g.is_paused

    def test_record_tracks_cost(self):
        g = ContinuousGuard()
        g.record("a", cost_usd=0.25)
        g.record("b", cost_usd=0.75)
        assert g.total_cost == 1.00

    def test_record_tracks_files(self):
        g = ContinuousGuard()
        g.record("edit a", files_touched=3)
        g.record("edit b", files_touched=5)
        assert g.files_modified == 8


class TestContinuousGuardControl:
    def test_resume_resets_failure_counter(self):
        g = ContinuousGuard(max_consecutive_failures=2)
        g.record("f1", success=False)
        g.record("f2", success=False)
        assert g.is_paused
        state = g.resume()
        assert not state.is_paused
        assert state.consecutive_failures == 0

    def test_reset_quotas(self):
        g = ContinuousGuard()
        g.record("expensive", cost_usd=1.50, files_touched=30, success=False)
        assert g.total_cost > 0
        assert g.files_modified > 0
        state = g.reset_quotas()
        assert state.total_cost_usd == 0.0
        assert state.files_modified == 0
        assert state.consecutive_failures == 0
        assert not state.is_paused

    def test_acknowledge_failure(self):
        g = ContinuousGuard()
        state = g.acknowledge_failure()
        assert state.consecutive_failures == 1
        g.acknowledge_failure()
        assert g.consecutive_failures == 2


class TestContinuousGuardStats:
    def test_stats_returns_all_keys(self):
        g = ContinuousGuard()
        stats = g.stats()
        expected_keys = {
            "consecutive_failures", "total_cost_usd", "files_modified",
            "operations_this_minute", "is_paused", "pause_reason",
            "total_operations", "success_rate", "cost_per_hour_limit",
            "files_per_hour_limit",
        }
        assert set(stats.keys()) >= expected_keys

    def test_stats_success_rate_all_success(self):
        g = ContinuousGuard()
        g.record("a", success=True)
        g.record("b", success=True)
        assert g.stats()["success_rate"] == 1.0

    def test_stats_success_rate_mixed(self):
        g = ContinuousGuard()
        g.record("a", success=True)
        g.record("b", success=True)
        g.record("c", success=False)
        assert g.stats()["success_rate"] == pytest.approx(2 / 3, 0.01)

    def test_stats_success_rate_empty(self):
        g = ContinuousGuard()
        assert g.stats()["success_rate"] == 1.0


class TestContinuousGuardHistory:
    def test_history_returns_tuple(self):
        g = ContinuousGuard()
        g.record("a")
        g.record("b")
        h = g.history
        assert isinstance(h, tuple)
        assert len(h) == 2

    def test_recent_verdicts(self):
        g = ContinuousGuard()
        verdict = g.check("ls")
        assert len(g.recent_verdicts) == 1
        assert g.recent_verdicts[0] == verdict


class TestContinuousGuardEdgeCases:
    def test_empty_command(self):
        g = ContinuousGuard()
        v = g.check("")
        assert v.is_allowed

    def test_headerlike_command_not_blocked(self):
        g = ContinuousGuard()
        # "DELETE" in a header context shouldn't match if not followed by FROM
        v = g.check("echo 'DELETE'")
        # Pattern r"DELETE\s+FROM\s+\w+" requires FROM — so this passes
        assert v.is_allowed

    def test_rm_without_recursive_flag(self):
        g = ContinuousGuard()
        v = g.check("rm file.txt")
        assert v.is_allowed

    def test_multiple_records(self):
        g = ContinuousGuard()
        for i in range(20):
            g.record(f"cmd_{i}", success=True)
        assert len(g.history) == 20

    def test_consecutive_failures_boundary(self):
        g = ContinuousGuard(max_consecutive_failures=5)
        for _ in range(4):
            g.record("fail", success=False)
        assert not g.is_paused
        g.record("fail", success=False)
        assert g.is_paused
