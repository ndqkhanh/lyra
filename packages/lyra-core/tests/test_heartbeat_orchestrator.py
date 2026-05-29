"""Tests for HeartbeatOrchestrator — list-decide-read collective intelligence loop."""

import pytest

from lyra_core.collective import (
    CollectiveState,
    Hypothesis,
    HypothesisTeam,
)
from lyra_core.collective.champion_tracker import ChampionTracker
from lyra_core.collective.heartbeat_orchestrator import (
    HeartbeatOrchestrator,
    WorkItem,
    WorkKind,
    WorkPriority,
)


@pytest.fixture
def state():
    """Fresh CollectiveState for each test."""
    return CollectiveState()


@pytest.fixture
def state_with_hypothesis(state):
    """State with one proposed hypothesis and team."""
    hyp = Hypothesis(
        id="h1",
        statement="Test-driven development reduces defect density in Python projects",
        proposed_by="agent_a",
        test_criteria="Measure defect density with and without TDD across 10 projects",
        priority=2,
    )
    state.propose_hypothesis(hyp, "agent_a")
    return state


@pytest.fixture
def orchestrator(state):
    """Fresh orchestrator for each test."""
    return HeartbeatOrchestrator(state, max_cycles=10)


class TestWorkItem:
    """Unit tests for WorkItem model."""

    def test_work_item_creation(self):
        item = WorkItem(
            id="w1",
            kind=WorkKind.VERIFY_HYPOTHESIS,
            priority=WorkPriority.HIGH,
            hypothesis_id="h1",
        )
        assert item.id == "w1"
        assert item.kind == WorkKind.VERIFY_HYPOTHESIS
        assert item.priority == WorkPriority.HIGH

    def test_priority_ordering(self):
        """CRITICAL < HIGH < MEDIUM < LOW."""
        items = [
            WorkItem(id="1", kind=WorkKind.EXPERIMENT, priority=WorkPriority.LOW),
            WorkItem(id="2", kind=WorkKind.EXPERIMENT, priority=WorkPriority.CRITICAL),
            WorkItem(id="3", kind=WorkKind.EXPERIMENT, priority=WorkPriority.MEDIUM),
            WorkItem(id="4", kind=WorkKind.EXPERIMENT, priority=WorkPriority.HIGH),
        ]
        priority_order = {
            WorkPriority.CRITICAL: 0,
            WorkPriority.HIGH: 1,
            WorkPriority.MEDIUM: 2,
            WorkPriority.LOW: 3,
        }
        sorted_items = sorted(items, key=lambda i: priority_order[i.priority])
        assert sorted_items[0].id == "2"  # CRITICAL first
        assert sorted_items[1].id == "4"  # HIGH second
        assert sorted_items[2].id == "3"  # MEDIUM third
        assert sorted_items[3].id == "1"  # LOW last


class TestHeartbeatOrchestratorInit:
    """Tests for orchestrator initialization."""

    def test_default_init(self, state):
        orch = HeartbeatOrchestrator(state)
        assert orch.cycle == 0
        assert orch.is_terminal is False
        assert orch.champions is not None

    def test_custom_champion_tracker(self, state):
        tracker = ChampionTracker(confirmation_threshold=5)
        orch = HeartbeatOrchestrator(state, champion_tracker=tracker)
        assert orch.champions.confirmation_threshold == 5

    def test_max_cycles_configurable(self, state):
        orch = HeartbeatOrchestrator(state, max_cycles=42)
        assert orch.max_cycles == 42


class TestListWork:
    """Tests for the LIST phase."""

    def test_list_empty_state(self, orchestrator):
        items = orchestrator._list_work()
        assert items == []

    def test_list_work_with_hypothesis(self, state_with_hypothesis):
        orch = HeartbeatOrchestrator(state_with_hypothesis)
        items = orch._list_work()
        assert len(items) >= 1
        verify_items = [i for i in items if i.kind == WorkKind.VERIFY_HYPOTHESIS]
        assert len(verify_items) >= 1

    def test_list_work_excludes_dead_ends(self, state):
        """Hypotheses matching known dead-ends should not be listed."""
        from lyra_core.collective import DeadEndEntry

        # Register a dead-end that will match via keyword overlap
        state.dead_ends.register(DeadEndEntry(
            id="de1",
            hypothesis="test driven development reduces defect density python",
            approach="tdd experiment measurement",
            failure_reason="already tried",
            discovered_by="agent_x",
        ))

        hyp = Hypothesis(
            id="h1",
            statement="test driven development reduces defect density python projects",
            proposed_by="agent_a",
            test_criteria="Measure defect density",
        )
        state.propose_hypothesis(hyp, "agent_a")
        orch = HeartbeatOrchestrator(state)
        items = orch._list_work()
        verify_items = [i for i in items if i.kind == WorkKind.VERIFY_HYPOTHESIS]
        assert len(verify_items) == 0

    def test_list_work_includes_stale_champion_reverification(self, state_with_hypothesis):
        orch = HeartbeatOrchestrator(
            state_with_hypothesis,
            staleness_threshold_s=0.0,
        )
        orch.champions.propose_champion("h1", "X causes Y", "agent_a")
        items = orch._list_work()
        reverify = [i for i in items if "reverify" in i.id]
        assert len(reverify) >= 1

    def test_list_includes_contested_champion_review(self, state_with_hypothesis):
        orch = HeartbeatOrchestrator(state_with_hypothesis)
        orch.champions.propose_champion("h1", "X causes Y", "agent_a")
        orch.champions.propose_champion("h2", "Z causes Y", "agent_b")

        items = orch._list_work()
        review_items = [i for i in items if i.kind == WorkKind.PEER_REVIEW]
        assert len(review_items) >= 1

    def test_list_includes_periodic_audit(self, state):
        orch = HeartbeatOrchestrator(state)
        orch._cycle = 5
        items = orch._list_work()
        audit_items = [i for i in items if i.kind == WorkKind.COVERAGE_AUDIT]
        assert len(audit_items) == 1


class TestDecideWork:
    """Tests for the DECIDE phase."""

    def test_decide_empty(self, orchestrator):
        selected = orchestrator._decide([])
        assert selected == []

    def test_decide_sorts_by_priority(self, state):
        """CRITICAL items are selected first; capacity limits total selected."""
        # Add an active team to increase capacity beyond 1
        hyp = Hypothesis(id="h1", statement="test", proposed_by="a", test_criteria="t")
        team = HypothesisTeam(id="team_h1", hypothesis=hyp, champion_id="agent_a")
        team.status = "working"
        state.teams["team_h1"] = team

        orch = HeartbeatOrchestrator(state)
        items = [
            WorkItem(id="low", kind=WorkKind.EXPERIMENT, priority=WorkPriority.LOW),
            WorkItem(id="critical", kind=WorkKind.VERIFY_HYPOTHESIS,
                    priority=WorkPriority.CRITICAL, hypothesis_id="h1"),
            WorkItem(id="medium", kind=WorkKind.EXPERIMENT, priority=WorkPriority.MEDIUM),
        ]
        selected = orch._decide(items)
        assert len(selected) >= 2
        assert selected[0].id == "critical"

    def test_decide_skips_dead_ends(self, state):
        from lyra_core.collective import DeadEndEntry

        hyp = Hypothesis(
            id="h1",
            statement="X causes Y through mechanism Z",
            proposed_by="agent_a",
            test_criteria="Test mechanism Z",
        )
        state.hypotheses["h1"] = hyp
        state.dead_ends.register(DeadEndEntry(
            id="de1",
            hypothesis="X causes Y through mechanism Z",
            approach="experiment",
            failure_reason="already falsified",
            discovered_by="agent_x",
        ))

        orch = HeartbeatOrchestrator(state)
        items = [
            WorkItem(id="verify_h1", kind=WorkKind.VERIFY_HYPOTHESIS,
                    priority=WorkPriority.HIGH, hypothesis_id="h1"),
        ]
        selected = orch._decide(items)
        assert len(selected) == 0


class TestExecuteFallback:
    """Tests for the fallback executor."""

    def test_fallback_scores_hypothesis(self, state_with_hypothesis):
        orch = HeartbeatOrchestrator(state_with_hypothesis)
        item = WorkItem(
            id="verify_h1",
            kind=WorkKind.VERIFY_HYPOTHESIS,
            hypothesis_id="h1",
        )
        result = orch._execute_fallback(item)
        assert result["success"] is True
        assert "score" in result
        assert 0.0 <= result["score"] <= 1.0

    def test_fallback_unknown_hypothesis(self, orchestrator):
        item = WorkItem(
            id="verify_unknown",
            kind=WorkKind.VERIFY_HYPOTHESIS,
            hypothesis_id="nonexistent",
        )
        result = orchestrator._execute_fallback(item)
        assert result["success"] is False

    def test_fallback_non_verify_work(self, orchestrator):
        item = WorkItem(
            id="audit_1",
            kind=WorkKind.COVERAGE_AUDIT,
        )
        result = orchestrator._execute_fallback(item)
        assert result["success"] is True
        assert result["output"] == "noop"


class TestRunCycle:
    """Integration tests for a full heartbeat cycle."""

    @pytest.mark.asyncio
    async def test_run_empty_state(self, state):
        orch = HeartbeatOrchestrator(state, max_cycles=5)
        result = await orch.run()
        assert result.cycle == 1
        assert result.work_items_listed == 0
        # Terminal fires on cycle >= 1 with no work AND no teams
        assert result.terminal is True

    @pytest.mark.asyncio
    async def test_run_with_hypothesis(self, state_with_hypothesis):
        orch = HeartbeatOrchestrator(state_with_hypothesis, max_cycles=10)
        result = await orch.run()
        assert result.cycle == 1
        assert result.work_items_listed >= 1
        assert result.work_items_completed >= 1

    @pytest.mark.asyncio
    async def test_run_verifies_hypothesis(self, state_with_hypothesis):
        orch = HeartbeatOrchestrator(state_with_hypothesis, max_cycles=10)
        result = await orch.run()
        assert result.hypotheses_verified >= 1 or result.hypotheses_falsified >= 1

    @pytest.mark.asyncio
    async def test_run_until_max_cycles(self, state_with_hypothesis):
        orch = HeartbeatOrchestrator(state_with_hypothesis, max_cycles=3)
        results = await orch.run_until_terminal()
        assert len(results) >= 1
        assert results[-1].terminal is True

    @pytest.mark.asyncio
    async def test_run_advances_collective_state_cycle(self, state_with_hypothesis):
        orch = HeartbeatOrchestrator(state_with_hypothesis, max_cycles=10)
        initial_cycle = state_with_hypothesis.cycle_count
        await orch.run()
        assert state_with_hypothesis.cycle_count > initial_cycle

    @pytest.mark.asyncio
    async def test_run_registers_dead_ends_on_falsification(self, state):
        """When a hypothesis is falsified by an executor, the READ phase registers it."""
        hyp = Hypothesis(
            id="h1",
            statement="A testable hypothesis for falsification testing",
            proposed_by="agent_a",
            test_criteria="Test falsification flow end to end",
            priority=1,
        )
        state.propose_hypothesis(hyp, "agent_a")

        orch = HeartbeatOrchestrator(state, max_cycles=10)

        # Register a custom executor that returns falsified
        async def falsifying_executor(item, team):
            return {
                "success": True,
                "output": "Evidence contradicts the hypothesis",
                "score": 0.2,
                "verified": False,
                "verifier_id": "test_verifier",
            }

        orch.set_executor(falsifying_executor)
        result = await orch.run()
        assert result.hypotheses_falsified >= 1
        # The _read_results phase registers falsified hypotheses as dead-ends
        assert result.dead_ends_registered >= 1

    @pytest.mark.asyncio
    async def test_run_with_custom_executor(self, state_with_hypothesis):
        """Register an async executor and verify it's called."""
        orch = HeartbeatOrchestrator(state_with_hypothesis, max_cycles=10)

        async def mock_executor(item, team):
            return {
                "success": True,
                "output": "mock result",
                "score": 0.95,
                "verified": True,
                "verifier_id": "mock_agent",
            }

        orch.set_executor(mock_executor)
        result = await orch.run()
        assert result.work_items_completed >= 1

    @pytest.mark.asyncio
    async def test_summary_reflects_state(self, state_with_hypothesis):
        orch = HeartbeatOrchestrator(state_with_hypothesis, max_cycles=10)
        await orch.run()
        s = orch.summary()
        assert s["cycle"] == 1
        assert "active_teams" in s
        assert "champions" in s


class TestTerminalConditions:
    """Tests for terminal condition detection."""

    @pytest.mark.asyncio
    async def test_terminates_at_max_cycles(self, state_with_hypothesis):
        orch = HeartbeatOrchestrator(state_with_hypothesis, max_cycles=2)
        await orch.run_until_terminal()
        assert orch.is_terminal is True

    @pytest.mark.asyncio
    async def test_terminates_no_work_no_teams(self, state):
        """Empty state terminates after first cycle."""
        orch = HeartbeatOrchestrator(state, max_cycles=10)
        result = await orch.run()
        assert result.terminal is True
        assert "no active teams" in result.terminal_reason


class TestResolveTeam:
    """Tests for team resolution logic."""

    def test_resolve_by_team_id(self, state, orchestrator):
        team = HypothesisTeam(
            id="team_h1",
            hypothesis=Hypothesis(id="h1", statement="test",
                                 proposed_by="a", test_criteria="t"),
            champion_id="agent_a",
        )
        state.teams["team_h1"] = team

        item = WorkItem(id="w1", kind=WorkKind.EXPERIMENT, team_id="team_h1")
        resolved = orchestrator._resolve_team(item)
        assert resolved is team

    def test_resolve_by_hypothesis_id(self, state, orchestrator):
        hyp = Hypothesis(id="h1", statement="test", proposed_by="a", test_criteria="t")
        team = HypothesisTeam(
            id="team_h1",
            hypothesis=hyp,
            champion_id="agent_a",
        )
        state.teams["team_h1"] = team

        item = WorkItem(id="w1", kind=WorkKind.VERIFY_HYPOTHESIS, hypothesis_id="h1")
        resolved = orchestrator._resolve_team(item)
        assert resolved is team

    def test_resolve_returns_none_for_nothing(self, state, orchestrator):
        item = WorkItem(id="w1", kind=WorkKind.EXPERIMENT)
        resolved = orchestrator._resolve_team(item)
        assert resolved is None
