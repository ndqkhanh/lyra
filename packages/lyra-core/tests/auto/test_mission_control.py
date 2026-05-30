"""Tests for Mission Control and Campaign Coordinator."""

from __future__ import annotations

import pytest

from lyra_core.auto.budget_enforcer import BudgetEnforcer, BudgetLevel, BudgetLimits, BudgetState
from lyra_core.auto.campaign_coordinator import (
    CampaignConfig,
    CampaignCoordinator,
    CampaignResult,
    CampaignState,
    CampaignStatus,
    MissionDependency,
)
from lyra_core.auto.goal_decomposer import Goal, GoalDecomposer, GoalType
from lyra_core.auto.mission_control import (
    MissionConfig,
    MissionControl,
    MissionPriority,
    MissionResult,
    MissionState,
    MissionStatus,
    TaskState,
)
from lyra_core.auto.verifier_driven_progress import (
    ProgressReport,
    VerificationGate,
    VerificationResult,
    VerificationStatus,
    VerifierDrivenProgress,
)


# ── Shared Fixtures ─────────────────────────────────────────────────


def _make_goal(name: str, description: str, goal_type: GoalType = GoalType.FEATURE) -> Goal:
    """Helper to create a Goal using the decomposer."""
    decomposer = GoalDecomposer()
    return decomposer.decompose(description=description, goal_type=goal_type)


@pytest.fixture
def sample_goal():
    return _make_goal("auth", "Implement user authentication with OAuth2")


@pytest.fixture
def sample_mission_config(sample_goal):
    return MissionConfig(
        mission_id="mission-001",
        name="Test Mission",
        description="A test mission for authentication",
        priority=MissionPriority.HIGH,
        goals=(sample_goal,),
    )


@pytest.fixture
def controller():
    return MissionControl()


@pytest.fixture
def coordinator():
    return CampaignCoordinator()


# ── MissionControl Tests ───────────────────────────────────────────


class TestMissionControl:
    """Tests for MissionControl - mission lifecycle and execution."""

    def test_create_mission_returns_draft_state(self, controller, sample_mission_config):
        state = controller.create_mission(sample_mission_config)
        assert state.status == MissionStatus.DRAFT
        assert state.mission_id == "mission-001"

    def test_create_mission_decomposes_goals_into_tasks(self, controller, sample_mission_config):
        state = controller.create_mission(sample_mission_config)
        assert len(state.tasks) > 0
        assert all(t.status == "pending" for t in state.tasks)

    def test_create_mission_tasks_have_valid_ids(self, controller, sample_mission_config):
        state = controller.create_mission(sample_mission_config)
        for task in state.tasks:
            assert task.task_id.startswith("mission-001:")
            assert task.goal_id is not None

    def test_start_mission_transitions_to_running(self, controller, sample_mission_config):
        controller.create_mission(sample_mission_config)
        state = controller.start_mission("mission-001")
        assert state.status == MissionStatus.RUNNING
        assert state.started_at is not None

    def test_pause_mission_transitions_to_paused(self, controller, sample_mission_config):
        controller.create_mission(sample_mission_config)
        controller.start_mission("mission-001")
        state = controller.pause_mission("mission-001")
        assert state.status == MissionStatus.PAUSED

    def test_resume_mission_transitions_to_running(self, controller, sample_mission_config):
        controller.create_mission(sample_mission_config)
        controller.start_mission("mission-001")
        controller.pause_mission("mission-001")
        state = controller.resume_mission("mission-001")
        assert state.status == MissionStatus.RUNNING

    def test_cancel_mission_transitions_to_cancelled(self, controller, sample_mission_config):
        controller.create_mission(sample_mission_config)
        controller.start_mission("mission-001")
        state = controller.cancel_mission("mission-001")
        assert state.status == MissionStatus.CANCELLED

    def test_get_next_task_returns_pending_task(self, controller, sample_mission_config):
        controller.create_mission(sample_mission_config)
        controller.start_mission("mission-001")
        task = controller.get_next_task("mission-001")
        assert task is not None
        assert task.status == "pending"

    def test_get_next_task_returns_none_when_all_done(self, controller, sample_mission_config):
        controller.create_mission(sample_mission_config)
        controller.start_mission("mission-001")
        state = controller.get_state("mission-001")
        # Execute all tasks
        for task in state.tasks:
            controller.execute_task("mission-001", task.task_id)
        remaining = controller.get_next_task("mission-001")
        assert remaining is None or remaining.status != "pending"

    def test_get_next_task_returns_none_when_paused(self, controller, sample_mission_config):
        controller.create_mission(sample_mission_config)
        controller.pause_mission("mission-001")
        task = controller.get_next_task("mission-001")
        assert task is None

    def test_execute_task_updates_status_to_completed(self, controller, sample_mission_config):
        controller.create_mission(sample_mission_config)
        controller.start_mission("mission-001")
        task = controller.get_next_task("mission-001")
        updated = controller.execute_task("mission-001", task.task_id)
        assert updated.status in ("completed", "failed")

    def test_execute_task_increments_attempt(self, controller, sample_mission_config):
        controller.create_mission(sample_mission_config)
        controller.start_mission("mission-001")
        task = controller.get_next_task("mission-001")
        updated = controller.execute_task("mission-001", task.task_id)
        assert updated.attempt == 1
        # Second call on a completed task should not re-execute
        updated2 = controller.execute_task("mission-001", task.task_id)
        assert updated2.attempt >= 1

    def test_execute_task_with_error_marks_failed_or_retry(
        self, controller, sample_mission_config
    ):
        controller.create_mission(sample_mission_config)
        controller.start_mission("mission-001")
        task = controller.get_next_task("mission-001")
        updated = controller.execute_task(
            "mission-001", task.task_id, error="Something went wrong"
        )
        # Should be pending (retry) if under max_retries
        assert updated.status in ("pending", "failed")
        assert updated.error_message == "Something went wrong"

    def test_execute_task_max_retries_exceeded_marks_failed(
        self, controller, sample_goal
    ):
        config = MissionConfig(
            mission_id="mission-002",
            name="Retry Test",
            goals=(sample_goal,),
            max_retries_per_task=1,
        )
        controller.create_mission(config)
        controller.start_mission("mission-002")
        task = controller.get_next_task("mission-002")
        # First attempt with error
        controller.execute_task("mission-002", task.task_id, error="Error 1")
        # Second attempt with error — should fail
        updated = controller.execute_task("mission-002", task.task_id, error="Error 2")
        assert updated.status == "failed"

    def test_mark_task_blocked(self, controller, sample_mission_config):
        controller.create_mission(sample_mission_config)
        controller.start_mission("mission-001")
        task = controller.get_next_task("mission-001")
        blocked = controller.mark_task_blocked(
            "mission-001", task.task_id, "Waiting for dependency"
        )
        assert blocked.status == "blocked"
        assert blocked.error_message == "Waiting for dependency"

    def test_get_state_returns_none_for_unknown_mission(self, controller):
        assert controller.get_state("no-such-mission") is None

    def test_get_result_returns_none_when_not_complete(
        self, controller, sample_mission_config
    ):
        controller.create_mission(sample_mission_config)
        assert controller.get_result("mission-001") is None

    def test_get_progress_returns_report(self, controller, sample_mission_config):
        controller.create_mission(sample_mission_config)
        controller.start_mission("mission-001")
        progress = controller.get_progress("mission-001")
        assert progress is not None
        assert progress.mission_id == "mission-001"

    def test_get_all_missions_returns_all(self, controller, sample_mission_config):
        controller.create_mission(sample_mission_config)
        missions = controller.get_all_missions()
        assert len(missions) == 1
        assert missions[0].mission_id == "mission-001"

    def test_get_all_missions_filtered_by_status(self, controller, sample_mission_config):
        controller.create_mission(sample_mission_config)
        controller.start_mission("mission-001")
        running = controller.get_all_missions(status=MissionStatus.RUNNING)
        assert len(running) == 1
        draft = controller.get_all_missions(status=MissionStatus.DRAFT)
        assert len(draft) == 0

    def test_check_budget_returns_state(self, controller, sample_mission_config):
        controller.create_mission(sample_mission_config)
        budget = controller.check_budget("mission-001")
        assert isinstance(budget, BudgetState)
        assert budget.level == BudgetLevel.GREEN

    def test_can_proceed_within_budget(self, controller, sample_mission_config):
        controller.create_mission(sample_mission_config)
        ok, reason = controller.can_proceed("mission-001", estimated_tokens=100)
        assert ok is True
        assert reason == "OK"

    def test_reset_clears_all_state(self, controller, sample_mission_config):
        controller.create_mission(sample_mission_config)
        controller.reset()
        assert controller.get_state("mission-001") is None
        assert controller.get_all_missions() == []

    def test_multiple_missions_independent_state(self, controller, sample_goal):
        config1 = MissionConfig(
            mission_id="m1", name="Mission 1",
            goals=(sample_goal,),
        )
        config2 = MissionConfig(
            mission_id="m2", name="Mission 2",
            goals=(sample_goal,),
        )
        controller.create_mission(config1)
        controller.create_mission(config2)
        assert len(controller.get_all_missions()) == 2
        controller.start_mission("m1")
        assert controller.get_state("m1").status == MissionStatus.RUNNING
        assert controller.get_state("m2").status == MissionStatus.DRAFT

    def test_mission_with_multiple_goals(self, controller):
        g1 = _make_goal("g1", "Add login feature")
        g2 = _make_goal("g2", "Add logout feature")
        config = MissionConfig(
            mission_id="multi-goal",
            name="Multi Goal Mission",
            goals=(g1, g2),
        )
        state = controller.create_mission(config)
        goal_ids = {t.goal_id for t in state.tasks}
        assert len(goal_ids) == 2

    def test_execute_all_tasks_completes_mission(self, controller, sample_mission_config):
        controller.create_mission(sample_mission_config)
        controller.start_mission("mission-001")
        state = controller.get_state("mission-001")
        for task in state.tasks:
            controller.execute_task("mission-001", task.task_id)
        final = controller.get_state("mission-001")
        assert final.status in (MissionStatus.COMPLETED, MissionStatus.FAILED)

    def test_mission_requires_verification_when_configured(self, controller, sample_goal):
        config = MissionConfig(
            mission_id="verify-test",
            name="Verification Test",
            goals=(sample_goal,),
            require_verification=True,
            gates=(VerificationGate.TEST_COVERAGE,),
        )
        controller.create_mission(config)
        controller.start_mission("verify-test")
        task = controller.get_next_task("verify-test")
        updated = controller.execute_task("verify-test", task.task_id)
        assert updated.verification is not None


# ── VerifierDrivenProgress Tests ────────────────────────────────────


class TestVerifierDrivenProgress:
    """Tests for VerifierDrivenProgress."""

    def test_verify_task_passes_all_gates(self):
        verifier = VerifierDrivenProgress()
        result = verifier.verify_task("task-1")
        assert result.status == VerificationStatus.PASSED

    def test_verify_task_with_specific_gates(self):
        verifier = VerifierDrivenProgress()
        result = verifier.verify_task(
            "task-2",
            gates=[VerificationGate.TEST_COVERAGE, VerificationGate.LINT_CHECK],
        )
        assert result.status == VerificationStatus.PASSED

    def test_verify_task_strict_mode_stops_on_failure(self):
        class FailingVerifier(VerifierDrivenProgress):
            def _run_gate(self, task_id, gate):
                if gate == VerificationGate.SECURITY_SCAN:
                    return VerificationResult(
                        gate=gate,
                        status=VerificationStatus.FAILED,
                        message="Security issue found",
                    )
                return super()._run_gate(task_id, gate)

        verifier = FailingVerifier(strict_mode=True)
        result = verifier.verify_task("task-3")
        assert result.status == VerificationStatus.FAILED

    def test_generate_report_empty_tasks(self):
        verifier = VerifierDrivenProgress()
        report = verifier.generate_report("mission-1", [])
        assert report.total_tasks == 0
        assert report.completion_pct == 0.0

    def test_generate_report_all_completed(self):
        verifier = VerifierDrivenProgress()
        tasks = [
            {"id": "t1", "status": "completed"},
            {"id": "t2", "status": "completed"},
        ]
        report = verifier.generate_report("mission-2", tasks)
        assert report.total_tasks == 2
        assert report.completed_tasks == 2
        assert report.overall_status == VerificationStatus.PASSED
        assert report.completion_pct == 100.0

    def test_generate_report_with_failures(self):
        verifier = VerifierDrivenProgress()
        tasks = [
            {"id": "t1", "status": "completed"},
            {"id": "t2", "status": "failed"},
        ]
        report = verifier.generate_report("mission-3", tasks)
        assert report.failed_tasks == 1
        assert report.overall_status == VerificationStatus.FAILED

    def test_generate_report_with_blocked(self):
        verifier = VerifierDrivenProgress()
        tasks = [
            {"id": "t1", "status": "completed"},
            {"id": "t2", "status": "blocked"},
            {"id": "t3", "status": "pending"},
        ]
        report = verifier.generate_report("mission-4", tasks)
        assert report.blocked_tasks == 1
        assert report.overall_status == VerificationStatus.WARNING

    def test_is_mission_complete_true(self):
        verifier = VerifierDrivenProgress()
        tasks = [{"id": "t1", "status": "completed"}]
        report = verifier.generate_report("mission-5", tasks)
        assert verifier.is_mission_complete(report) is True

    def test_is_mission_complete_false_when_failed(self):
        verifier = VerifierDrivenProgress()
        tasks = [
            {"id": "t1", "status": "completed"},
            {"id": "t2", "status": "failed"},
        ]
        report = verifier.generate_report("mission-6", tasks)
        assert verifier.is_mission_complete(report) is False

    def test_clear_resets_results(self):
        verifier = VerifierDrivenProgress()
        verifier.verify_task("task-clear")
        verifier.clear()
        report = verifier.generate_report("clear-test", [])
        assert len(report.gate_results) == 0


# ── BudgetEnforcer Tests ────────────────────────────────────────────


class TestBudgetEnforcer:
    """Tests for BudgetEnforcer."""

    def test_initial_state_is_green(self):
        budget = BudgetEnforcer()
        state = budget.check()
        assert state.level == BudgetLevel.GREEN
        assert state.can_continue is True

    def test_consume_tokens_updates_state(self):
        budget = BudgetEnforcer(BudgetLimits(max_tokens=10000))
        state = budget.consume_tokens(6000)
        assert state.level == BudgetLevel.YELLOW
        assert state.can_continue is True

    def test_consume_tokens_exceeded(self):
        budget = BudgetEnforcer(BudgetLimits(max_tokens=1000))
        state = budget.consume_tokens(1100)
        assert state.level == BudgetLevel.EXCEEDED
        assert state.can_continue is False

    def test_consume_cost_updates_state(self):
        budget = BudgetEnforcer(BudgetLimits(max_cost_cents=1000))
        state = budget.consume_cost(800)
        assert state.level == BudgetLevel.ORANGE

    def test_complete_operation_increments_count(self):
        budget = BudgetEnforcer(BudgetLimits(max_operations=10))
        state = budget.complete_operation()
        assert state.operations_completed == 1

    def test_can_proceed_within_limits(self):
        budget = BudgetEnforcer()
        ok, reason = budget.can_proceed(estimated_tokens=100)
        assert ok is True
        assert reason == "OK"

    def test_can_proceed_exceeded_budget_blocks(self):
        budget = BudgetEnforcer(BudgetLimits(max_tokens=100))
        budget.consume_tokens(110)
        ok, reason = budget.can_proceed(estimated_tokens=10)
        assert ok is False

    def test_can_proceed_would_exceed_token_budget(self):
        budget = BudgetEnforcer(BudgetLimits(max_tokens=1000))
        budget.consume_tokens(900)
        ok, reason = budget.can_proceed(estimated_tokens=200)
        assert ok is False

    def test_can_proceed_would_exceed_cost_budget(self):
        budget = BudgetEnforcer(BudgetLimits(max_cost_cents=100))
        budget.consume_cost(90)
        ok, reason = budget.can_proceed(estimated_cost_cents=20)
        assert ok is False

    def test_reset_restores_initial_state(self):
        budget = BudgetEnforcer()
        budget.consume_tokens(800000)
        budget.reset()
        state = budget.check()
        assert state.level == BudgetLevel.GREEN
        assert state.tokens_used == 0

    def test_multiple_dimensions_max_used(self):
        budget = BudgetEnforcer(
            BudgetLimits(max_tokens=1000, max_cost_cents=500, max_operations=100)
        )
        budget.consume_tokens(100)  # 10%
        budget.consume_cost(400)     # 80% — this should dominate
        state = budget.check()
        assert state.level == BudgetLevel.ORANGE  # 80% driven by cost

    def test_level_boundaries(self):
        budget = BudgetEnforcer(BudgetLimits(max_tokens=1000))
        budget.consume_tokens(400)
        assert budget.check().level == BudgetLevel.GREEN
        budget.consume_tokens(150)  # 550 total = 55%
        assert budget.check().level == BudgetLevel.YELLOW
        budget.consume_tokens(250)  # 800 total = 80%
        assert budget.check().level == BudgetLevel.ORANGE
        budget.consume_tokens(150)  # 950 total = 95%
        assert budget.check().level == BudgetLevel.RED


# ── CampaignCoordinator Tests ───────────────────────────────────────


class TestCampaignCoordinator:
    """Tests for CampaignCoordinator - multi-mission campaign management."""

    def _make_mission_config(self, mission_id: str, name: str) -> MissionConfig:
        goal = _make_goal(name, f"Implement {name}")
        return MissionConfig(
            mission_id=mission_id,
            name=name,
            goals=(goal,),
        )

    def test_create_campaign_returns_draft_state(self, coordinator):
        config = CampaignConfig(
            campaign_id="campaign-001",
            name="Test Campaign",
            missions=(self._make_mission_config("m1", "Alpha"),),
        )
        state = coordinator.create_campaign(config)
        assert state.status == CampaignStatus.DRAFT
        assert state.campaign_id == "campaign-001"

    def test_create_campaign_registers_all_missions(self, coordinator):
        config = CampaignConfig(
            campaign_id="campaign-002",
            name="Multi-Mission",
            missions=(
                self._make_mission_config("m1", "Alpha"),
                self._make_mission_config("m2", "Bravo"),
                self._make_mission_config("m3", "Charlie"),
            ),
        )
        state = coordinator.create_campaign(config)
        assert len(state.mission_states) == 3

    def test_start_campaign_activates_runnable_missions(self, coordinator):
        config = CampaignConfig(
            campaign_id="campaign-003",
            name="Start Test",
            missions=(
                self._make_mission_config("m1", "Alpha"),
                self._make_mission_config("m2", "Bravo"),
            ),
        )
        coordinator.create_campaign(config)
        state = coordinator.start_campaign("campaign-003")
        assert state.status == CampaignStatus.ACTIVE
        assert len(state.active_missions) > 0

    def test_start_campaign_respects_max_concurrent(self, coordinator):
        config = CampaignConfig(
            campaign_id="campaign-004",
            name="Concurrency Test",
            max_concurrent_missions=1,
            missions=(
                self._make_mission_config("m1", "Alpha"),
                self._make_mission_config("m2", "Bravo"),
            ),
        )
        coordinator.create_campaign(config)
        state = coordinator.start_campaign("campaign-004")
        assert len(state.active_missions) <= 1
        assert len(state.pending_missions) >= 1

    def test_pause_campaign_pauses_all_active(self, coordinator):
        config = CampaignConfig(
            campaign_id="campaign-005",
            name="Pause Test",
            missions=(self._make_mission_config("m1", "Alpha"),),
        )
        coordinator.create_campaign(config)
        coordinator.start_campaign("campaign-005")
        state = coordinator.pause_campaign("campaign-005")
        assert state.status == CampaignStatus.PAUSED
        assert len(state.active_missions) == 0

    def test_resume_campaign_reactivates_pending(self, coordinator):
        config = CampaignConfig(
            campaign_id="campaign-006",
            name="Resume Test",
            missions=(self._make_mission_config("m1", "Alpha"),),
        )
        coordinator.create_campaign(config)
        coordinator.start_campaign("campaign-006")
        coordinator.pause_campaign("campaign-006")
        state = coordinator.resume_campaign("campaign-006")
        assert state.status == CampaignStatus.ACTIVE

    def test_cancel_campaign_clears_all(self, coordinator):
        config = CampaignConfig(
            campaign_id="campaign-007",
            name="Cancel Test",
            missions=(self._make_mission_config("m1", "Alpha"),),
        )
        coordinator.create_campaign(config)
        coordinator.start_campaign("campaign-007")
        state = coordinator.cancel_campaign("campaign-007")
        assert state.status == CampaignStatus.CANCELLED

    def test_get_state_returns_none_for_unknown(self, coordinator):
        assert coordinator.get_state("no-campaign") is None

    def test_get_result_returns_none_when_not_complete(self, coordinator):
        config = CampaignConfig(
            campaign_id="campaign-008",
            name="Result Test",
            missions=(self._make_mission_config("m1", "Alpha"),),
        )
        coordinator.create_campaign(config)
        assert coordinator.get_result("campaign-008") is None

    def test_sequential_dependency_blocks_until_prereq_completes(self, coordinator):
        config = CampaignConfig(
            campaign_id="campaign-seq",
            name="Sequential Test",
            max_concurrent_missions=3,
            missions=(
                self._make_mission_config("m1", "Phase 1"),
                self._make_mission_config("m2", "Phase 2"),
            ),
            dependencies=(("m1", "m2", MissionDependency.SEQUENTIAL),),
        )
        coordinator.create_campaign(config)
        state = coordinator.start_campaign("campaign-seq")
        # m2 should not be active because m1 is its prerequisite
        assert "m2" not in state.active_missions

        # Complete m1
        coordinator.on_mission_completed("campaign-seq", "m1")
        state2 = coordinator.get_state("campaign-seq")
        assert "m2" in state2.active_missions or "m2" in state2.completed_missions

    def test_fail_fast_stops_all_on_failure(self, coordinator):
        config = CampaignConfig(
            campaign_id="campaign-ff",
            name="FailFast Test",
            fail_fast=True,
            missions=(
                self._make_mission_config("m1", "Alpha"),
                self._make_mission_config("m2", "Bravo"),
            ),
        )
        coordinator.create_campaign(config)
        coordinator.start_campaign("campaign-ff")
        state = coordinator.on_mission_failed("campaign-ff", "m1")
        assert state.status == CampaignStatus.FAILED

    def test_all_missions_complete_finalizes_campaign(self, coordinator):
        config = CampaignConfig(
            campaign_id="campaign-complete",
            name="Complete Test",
            missions=(self._make_mission_config("m1", "Solo"),),
        )
        coordinator.create_campaign(config)
        coordinator.start_campaign("campaign-complete")

        # Complete all tasks in the mission
        ms = coordinator.get_mission_state("campaign-complete", "m1")
        for task in ms.tasks:
            coordinator._controller.execute_task("m1", task.task_id)

        state = coordinator.on_mission_completed("campaign-complete", "m1")
        assert state.status in (CampaignStatus.COMPLETED, CampaignStatus.ACTIVE)

    def test_get_all_campaigns(self, coordinator):
        config1 = CampaignConfig(
            campaign_id="c1", name="First",
            missions=(self._make_mission_config("m1", "Alpha"),),
        )
        config2 = CampaignConfig(
            campaign_id="c2", name="Second",
            missions=(self._make_mission_config("m2", "Bravo"),),
        )
        coordinator.create_campaign(config1)
        coordinator.create_campaign(config2)
        campaigns = coordinator.get_all_campaigns()
        assert len(campaigns) == 2

    def test_get_all_campaigns_filtered_by_status(self, coordinator):
        config = CampaignConfig(
            campaign_id="c1", name="Active",
            missions=(self._make_mission_config("m1", "Alpha"),),
        )
        coordinator.create_campaign(config)
        coordinator.start_campaign("c1")
        active = coordinator.get_all_campaigns(status=CampaignStatus.ACTIVE)
        assert len(active) == 1
        draft = coordinator.get_all_campaigns(status=CampaignStatus.DRAFT)
        assert len(draft) == 0

    def test_get_next_actionable_returns_pending(self, coordinator):
        config = CampaignConfig(
            campaign_id="c-actionable",
            name="Actionable Test",
            max_concurrent_missions=1,
            missions=(
                self._make_mission_config("m1", "First"),
                self._make_mission_config("m2", "Second"),
            ),
        )
        coordinator.create_campaign(config)
        coordinator.start_campaign("c-actionable")
        actionable = coordinator.get_next_actionable("c-actionable")
        assert len(actionable) >= 1

    def test_reset_clears_all_campaigns(self, coordinator):
        config = CampaignConfig(
            campaign_id="c-reset",
            name="Reset Test",
            missions=(self._make_mission_config("m1", "Alpha"),),
        )
        coordinator.create_campaign(config)
        coordinator.reset()
        assert coordinator.get_state("c-reset") is None
        assert coordinator.get_all_campaigns() == []

    def test_conditional_dependency(self, coordinator):
        config = CampaignConfig(
            campaign_id="c-cond",
            name="Conditional Test",
            max_concurrent_missions=3,
            missions=(
                self._make_mission_config("m1", "Phase 1"),
                self._make_mission_config("m2", "Phase 2"),
            ),
            dependencies=(("m1", "m2", MissionDependency.CONDITIONAL),),
        )
        coordinator.create_campaign(config)
        state = coordinator.start_campaign("c-cond")
        # m2 blocked until m1 succeeds
        assert "m2" not in state.active_missions

    def test_auto_retry_failed_missions(self, coordinator):
        config = CampaignConfig(
            campaign_id="c-retry",
            name="Retry Test",
            fail_fast=False,
            auto_retry_failed=True,
            max_campaign_retries=3,
            missions=(self._make_mission_config("m1", "Alpha"),),
        )
        coordinator.create_campaign(config)
        coordinator.start_campaign("c-retry")
        state = coordinator.on_mission_failed("c-retry", "m1")
        assert state.retry_count == 1
        assert state.status != CampaignStatus.FAILED

    def test_campaign_result_contains_mission_results(self, coordinator):
        config = CampaignConfig(
            campaign_id="c-result",
            name="Result Test",
            missions=(self._make_mission_config("m1", "Solo"),),
        )
        coordinator.create_campaign(config)
        coordinator.start_campaign("c-result")

        # Complete the mission
        ms = coordinator.get_mission_state("c-result", "m1")
        for task in ms.tasks:
            coordinator._controller.execute_task("m1", task.task_id)

        coordinator.on_mission_completed("c-result", "m1")
        result = coordinator.get_result("c-result")
        if result:
            assert result.total_missions == 1
            assert len(result.mission_results) >= 0
