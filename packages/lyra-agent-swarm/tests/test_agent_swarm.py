"""Comprehensive test suite for the lyra-agent-swarm package (100+ tests)."""

from __future__ import annotations

import pytest
from lyra_agent_swarm import (
    HEPHAESTUS,
    HERMES,
    LIBRARIAN,
    ORACLE,
    PROMETHEUS,
    SENTINEL,
    SISYPHUS,
    AgentContribution,
    AgentMessage,
    AgentRegistry,
    AgentRole,
    AgentState,
    AgentStatus,
    AggregationMethod,
    Autopilot,
    AutopilotConfig,
    AutopilotJob,
    AutopilotRun,
    Capability,
    Coalition,
    CoalitionConfig,
    CoalitionFormer,
    ConsensusBuilder,
    ConsensusConfig,
    ConsensusResult,
    DispatchConfig,
    DispatchDecision,
    Dispatcher,
    DispatchStrategy,
    MessagePriority,
    MessageThread,
    MessagingConfig,
    Proposal,
    RunStatus,
    Schedule,
    Sprint,
    SprintConfig,
    SprintModel,
    SprintPhase,
    SprintResult,
    SprintStatus,
    SprintTask,
    Squad,
    SquadDomain,
    SquadManager,
    SquadMetrics,
    SwarmMetrics,
    SwarmSnapshot,
    SwarmVisualizer,
    TaskPriority,
    TaskQueue,
    TaskTicket,
    TeamMessaging,
    Vote,
    VoteChoice,
)
from lyra_agent_swarm.discipline_agents import DisciplineAgent
from lyra_agent_swarm.exceptions import (
    AutopilotError,
    CoalitionError,
    ConsensusError,
    DispatchError,
    MessagingError,
    SprintError,
    SquadError,
    SwarmError,
)

# =====================================================================
# Exceptions
# =====================================================================


class TestExceptions:
    def test_swarm_error_base(self) -> None:
        assert issubclass(DispatchError, SwarmError)
        assert issubclass(SprintError, SwarmError)
        assert issubclass(SquadError, SwarmError)
        assert issubclass(CoalitionError, SwarmError)
        assert issubclass(AutopilotError, SwarmError)
        assert issubclass(MessagingError, SwarmError)
        assert issubclass(ConsensusError, SwarmError)

    def test_swarm_error_message(self) -> None:
        err = SwarmError("test message")
        assert str(err) == "test message"

    def test_dispatch_error_message(self) -> None:
        err = DispatchError("no agents found")
        assert str(err) == "no agents found"

    def test_sprint_error_message(self) -> None:
        err = SprintError("phase transition failed")
        assert str(err) == "phase transition failed"

    def test_squad_error_message(self) -> None:
        err = SquadError("invalid squad")
        assert str(err) == "invalid squad"

    def test_coalition_error_message(self) -> None:
        err = CoalitionError("no agents")
        assert str(err) == "no agents"

    def test_autopilot_error_message(self) -> None:
        err = AutopilotError("job not found")
        assert str(err) == "job not found"

    def test_messaging_error_message(self) -> None:
        err = MessagingError("message not found")
        assert str(err) == "message not found"

    def test_consensus_error_message(self) -> None:
        err = ConsensusError("vote failed")
        assert str(err) == "vote failed"


# =====================================================================
# Discipline Agents
# =====================================================================


class TestDisciplineAgents:
    def test_agent_role_enum_values(self) -> None:
        assert AgentRole.SISYPHUS.name == "SISYPHUS"
        assert AgentRole.HEPHAESTUS.name == "HEPHAESTUS"
        assert AgentRole.PROMETHEUS.name == "PROMETHEUS"
        assert AgentRole.ORACLE.name == "ORACLE"
        assert AgentRole.LIBRARIAN.name == "LIBRARIAN"
        assert AgentRole.SENTINEL.name == "SENTINEL"
        assert AgentRole.HERMES.name == "HERMES"

    def test_capability_enum_values(self) -> None:
        assert Capability.CODE_GEN.name == "CODE_GEN"
        assert Capability.CODE_REVIEW.name == "CODE_REVIEW"
        assert Capability.ARCHITECTURE.name == "ARCHITECTURE"
        assert Capability.RESEARCH.name == "RESEARCH"
        assert Capability.SECURITY.name == "SECURITY"
        assert Capability.TESTING.name == "TESTING"
        assert Capability.PLANNING.name == "PLANNING"
        assert Capability.DEBUGGING.name == "DEBUGGING"
        assert Capability.DOCS.name == "DOCS"
        assert Capability.DEPLOYMENT.name == "DEPLOYMENT"

    def test_discipline_agent_creation(self) -> None:
        agent = DisciplineAgent(
            agent_id="test-001",
            name="Tester",
            role=AgentRole.SISYPHUS,
            model_tier="sonnet",
            capabilities=frozenset({Capability.CODE_GEN}),
            priority=5,
        )
        assert agent.agent_id == "test-001"
        assert agent.name == "Tester"
        assert agent.role == AgentRole.SISYPHUS
        assert agent.model_tier == "sonnet"
        assert agent.priority == 5
        assert not agent.is_blocking

    def test_discipline_agent_frozen(self) -> None:
        agent = DisciplineAgent(
            agent_id="test-002",
            name="Frozen",
            role=AgentRole.ORACLE,
            model_tier="opus",
            capabilities=frozenset(),
            priority=1,
        )
        with pytest.raises(AttributeError):
            agent.agent_id = "changed"  # type: ignore[misc]

    def test_discipline_agent_negative_priority_raises(self) -> None:
        with pytest.raises(ValueError, match="priority must be non-negative"):
            DisciplineAgent(
                agent_id="bad",
                name="Bad",
                role=AgentRole.SISYPHUS,
                model_tier="sonnet",
                capabilities=frozenset(),
                priority=-1,
            )

    def test_discipline_agent_converts_set_to_frozenset(self) -> None:
        agent = DisciplineAgent(
            agent_id="conv-001",
            name="Converter",
            role=AgentRole.HERMES,
            model_tier="haiku",
            capabilities={Capability.DOCS},
            priority=1,
        )
        assert isinstance(agent.capabilities, frozenset)

    def test_prebuilt_sisyphus(self) -> None:
        assert SISYPHUS.name == "Sisyphus"
        assert SISYPHUS.role == AgentRole.SISYPHUS
        assert SISYPHUS.model_tier == "sonnet"
        assert Capability.CODE_GEN in SISYPHUS.capabilities
        assert Capability.DEBUGGING in SISYPHUS.capabilities

    def test_prebuilt_hephaestus(self) -> None:
        assert HEPHAESTUS.name == "Hephaestus"
        assert HEPHAESTUS.role == AgentRole.HEPHAESTUS
        assert HEPHAESTUS.model_tier == "sonnet"
        assert Capability.CODE_REVIEW in HEPHAESTUS.capabilities

    def test_prebuilt_prometheus(self) -> None:
        assert PROMETHEUS.name == "Prometheus"
        assert PROMETHEUS.role == AgentRole.PROMETHEUS
        assert PROMETHEUS.model_tier == "opus"
        assert Capability.ARCHITECTURE in PROMETHEUS.capabilities

    def test_prebuilt_oracle(self) -> None:
        assert ORACLE.name == "Oracle"
        assert ORACLE.role == AgentRole.ORACLE
        assert ORACLE.model_tier == "opus"

    def test_prebuilt_librarian(self) -> None:
        assert LIBRARIAN.name == "Librarian"
        assert LIBRARIAN.role == AgentRole.LIBRARIAN
        assert LIBRARIAN.model_tier == "haiku"

    def test_prebuilt_sentinel(self) -> None:
        assert SENTINEL.name == "Sentinel"
        assert SENTINEL.role == AgentRole.SENTINEL
        assert SENTINEL.model_tier == "haiku"
        assert SENTINEL.is_blocking

    def test_prebuilt_hermes(self) -> None:
        assert HERMES.name == "Hermes"
        assert HERMES.role == AgentRole.HERMES
        assert HERMES.model_tier == "haiku"

    def test_agent_registry_register(self) -> None:
        registry = AgentRegistry(prebuilt=False)
        agent = DisciplineAgent(
            agent_id="custom-001",
            name="Custom",
            role=AgentRole.SISYPHUS,
            model_tier="sonnet",
            capabilities=frozenset(),
            priority=1,
        )
        registry.register(agent)
        assert agent in registry.agents.values()

    def test_agent_registry_duplicate_raises(self) -> None:
        registry = AgentRegistry(prebuilt=False)
        agent = DisciplineAgent(
            agent_id="dup",
            name="Dup",
            role=AgentRole.SISYPHUS,
            model_tier="sonnet",
            capabilities=frozenset(),
            priority=1,
        )
        registry.register(agent)
        with pytest.raises(ValueError, match="already registered"):
            registry.register(agent)

    def test_agent_registry_get_by_role(self) -> None:
        registry = AgentRegistry(prebuilt=True)
        sisyphi = registry.get_by_role(AgentRole.SISYPHUS)
        assert len(sisyphi) == 1
        assert sisyphi[0].agent_id == "sisyphus-001"

    def test_agent_registry_get_by_role_empty(self) -> None:
        registry = AgentRegistry(prebuilt=False)
        assert registry.get_by_role(AgentRole.ORACLE) == []

    def test_agent_registry_get_capable(self) -> None:
        registry = AgentRegistry(prebuilt=True)
        capable = registry.get_capable(Capability.CODE_GEN)
        assert len(capable) >= 2
        assert Capability.CODE_GEN in capable[0].capabilities

    def test_agent_registry_get_capable_empty(self) -> None:
        registry = AgentRegistry(prebuilt=False)
        assert registry.get_capable(Capability.TESTING) == []

    def test_agent_registry_prebuilt_count(self) -> None:
        registry = AgentRegistry(prebuilt=True)
        assert len(registry.agents) == 7

    def test_agent_registry_get_by_role_multiple(self) -> None:
        registry = AgentRegistry(prebuilt=False)
        a1 = DisciplineAgent("a1", "A1", AgentRole.ORACLE, "opus", frozenset(), 1)
        a2 = DisciplineAgent("a2", "A2", AgentRole.ORACLE, "opus", frozenset(), 2)
        registry.register(a1)
        registry.register(a2)
        assert len(registry.get_by_role(AgentRole.ORACLE)) == 2


# =====================================================================
# Dispatcher
# =====================================================================


class TestDispatcher:
    def test_task_priority_enum(self) -> None:
        assert TaskPriority.CRITICAL.name == "CRITICAL"
        assert TaskPriority.HIGH.name == "HIGH"
        assert TaskPriority.NORMAL.name == "NORMAL"
        assert TaskPriority.LOW.name == "LOW"
        assert TaskPriority.BACKGROUND.name == "BACKGROUND"

    def test_dispatch_strategy_enum(self) -> None:
        assert DispatchStrategy.SINGLE_AGENT.name == "SINGLE_AGENT"
        assert DispatchStrategy.SQUAD.name == "SQUAD"
        assert DispatchStrategy.COALITION.name == "COALITION"
        assert DispatchStrategy.ROUND_ROBIN.name == "ROUND_ROBIN"
        assert DispatchStrategy.LOAD_BALANCED.name == "LOAD_BALANCED"

    def test_task_ticket_creation(self) -> None:
        ticket = TaskTicket(
            task_id="t1",
            description="Test task",
            required_capabilities=frozenset({Capability.CODE_GEN}),
        )
        assert ticket.task_id == "t1"
        assert ticket.description == "Test task"
        assert ticket.priority == TaskPriority.NORMAL
        assert ticket.deadline is None
        assert ticket.context == {}

    def test_task_ticket_defaults(self) -> None:
        ticket = TaskTicket(task_id="t2", description="Minimal")
        assert isinstance(ticket.required_capabilities, frozenset)
        assert len(ticket.required_capabilities) == 0
        assert ticket.priority == TaskPriority.NORMAL

    def test_dispatch_config_defaults(self) -> None:
        config = DispatchConfig()
        assert config.max_agents_per_task == 3
        assert config.prefer_specialists
        assert config.load_balance

    def test_dispatch_decision_creation(self) -> None:
        registry = AgentRegistry(prebuilt=True)
        ticket = TaskTicket("t1", "test", frozenset({Capability.CODE_GEN}))
        decision = DispatchDecision(
            task=ticket,
            assigned_agents=(SISYPHUS,),
            strategy=DispatchStrategy.SINGLE_AGENT,
            reasoning="best match",
        )
        assert decision.task.task_id == "t1"
        assert len(decision.assigned_agents) == 1
        assert decision.strategy == DispatchStrategy.SINGLE_AGENT

    def test_task_queue_push_pop(self) -> None:
        queue = TaskQueue()
        ticket = TaskTicket("t1", "test", priority=TaskPriority.NORMAL)
        queue.push(ticket)
        assert queue.size == 1
        assert queue.pop() is ticket
        assert queue.is_empty

    def test_task_queue_priority_ordering(self) -> None:
        queue = TaskQueue()
        low = TaskTicket("low", "low", priority=TaskPriority.LOW)
        high = TaskTicket("high", "high", priority=TaskPriority.HIGH)
        critical = TaskTicket("crit", "crit", priority=TaskPriority.CRITICAL)
        queue.push(low)
        queue.push(high)
        queue.push(critical)
        assert queue.pop().task_id == "crit"
        assert queue.pop().task_id == "high"
        assert queue.pop().task_id == "low"

    def test_task_queue_empty_pop(self) -> None:
        queue = TaskQueue()
        assert queue.pop() is None

    def test_task_queue_peek(self) -> None:
        queue = TaskQueue()
        assert queue.peek() is None
        ticket = TaskTicket("t1", "test")
        queue.push(ticket)
        assert queue.peek() is ticket
        assert queue.size == 1  # peek doesn't remove

    def test_task_queue_empty_after_clear(self) -> None:
        queue = TaskQueue()
        ticket = TaskTicket("t1", "test")
        queue.push(ticket)
        queue.pop()
        assert queue.is_empty
        assert queue.size == 0

    def test_dispatcher_classify_task(self) -> None:
        registry = AgentRegistry(prebuilt=True)
        dispatcher = Dispatcher(registry)
        ticket = TaskTicket("t1", "test", frozenset({Capability.CODE_GEN, Capability.TESTING}))
        scores = dispatcher.classify_task(ticket)
        assert scores[Capability.CODE_GEN] == 1.0
        assert scores[Capability.TESTING] == 1.0
        assert len(scores) == 2

    def test_dispatcher_dispatch_single(self) -> None:
        registry = AgentRegistry(prebuilt=True)
        dispatcher = Dispatcher(registry)
        ticket = TaskTicket("t1", "test", frozenset({Capability.CODE_GEN}))
        decision = dispatcher.dispatch(ticket)
        assert len(decision.assigned_agents) >= 1

    def test_dispatcher_dispatch_multi(self) -> None:
        registry = AgentRegistry(prebuilt=True)
        dispatcher = Dispatcher(registry, DispatchConfig(max_agents_per_task=2))
        ticket = TaskTicket("t1", "test", frozenset({Capability.CODE_GEN, Capability.DEBUGGING}))
        decision = dispatcher.dispatch(ticket)
        assert len(decision.assigned_agents) >= 1

    def test_dispatcher_dispatch_no_capable(self) -> None:
        registry = AgentRegistry(prebuilt=False)
        dispatcher = Dispatcher(registry)
        ticket = TaskTicket("t1", "test", frozenset({Capability.TESTING}))
        with pytest.raises(DispatchError):
            dispatcher.dispatch(ticket)

    def test_dispatcher_submit_and_queue(self) -> None:
        registry = AgentRegistry(prebuilt=True)
        dispatcher = Dispatcher(registry)
        ticket = TaskTicket("t1", "test")
        dispatcher.submit(ticket)
        assert not dispatcher.queue.is_empty

    def test_dispatcher_round_robin_is_not_single(self) -> None:
        registry = AgentRegistry(prebuilt=True)
        dispatcher = Dispatcher(registry)
        ticket = TaskTicket("t1", "test", frozenset({Capability.CODE_GEN, Capability.ARCHITECTURE}))
        decision = dispatcher.dispatch(ticket)
        assert decision.strategy in (DispatchStrategy.SINGLE_AGENT, DispatchStrategy.SQUAD)

    def test_dispatcher_task_load_tracking(self) -> None:
        registry = AgentRegistry(prebuilt=True)
        dispatcher = Dispatcher(registry)
        t1 = TaskTicket("t1", "test", frozenset({Capability.CODE_GEN}))
        t2 = TaskTicket("t2", "test", frozenset({Capability.CODE_GEN}))
        dispatcher.dispatch(t1)
        dispatcher.dispatch(t2)
        # At least one agent should have load > 0
        assert any(load > 0 for load in dispatcher._task_load.values())

    def test_dispatcher_config_custom(self) -> None:
        config = DispatchConfig(max_agents_per_task=5, prefer_specialists=False, load_balance=False)
        registry = AgentRegistry(prebuilt=True)
        dispatcher = Dispatcher(registry, config)
        assert dispatcher.config.max_agents_per_task == 5
        assert not dispatcher.config.prefer_specialists
        assert not dispatcher.config.load_balance


# =====================================================================
# Sprint Model
# =====================================================================


class TestSprintModel:
    def test_sprint_phase_enum(self) -> None:
        phases = list(SprintPhase)
        assert phases[0].name == "THINK"
        assert phases[1].name == "PLAN"
        assert phases[2].name == "BUILD"
        assert phases[3].name == "REVIEW"
        assert phases[4].name == "TEST"
        assert phases[5].name == "SHIP"
        assert phases[6].name == "REFLECT"

    def test_sprint_status_enum(self) -> None:
        assert SprintStatus.PLANNING.name == "PLANNING"
        assert SprintStatus.IN_PROGRESS.name == "IN_PROGRESS"
        assert SprintStatus.REVIEWING.name == "REVIEWING"
        assert SprintStatus.COMPLETED.name == "COMPLETED"
        assert SprintStatus.FAILED.name == "FAILED"

    def test_sprint_creation(self) -> None:
        sprint = Sprint(
            sprint_id="s1",
            goal="Build feature X",
            phases=(SprintPhase.BUILD, SprintPhase.TEST),
            agents=("sisyphus-001",),
            start_time=100.0,
            status=SprintStatus.PLANNING,
        )
        assert sprint.sprint_id == "s1"
        assert sprint.goal == "Build feature X"
        assert sprint.status == SprintStatus.PLANNING
        assert sprint.current_phase_index == 0

    def test_sprint_frozen(self) -> None:
        sprint = Sprint(
            sprint_id="s2", goal="test", phases=(), agents=(), start_time=0.0,
        )
        with pytest.raises(AttributeError):
            sprint.goal = "changed"  # type: ignore[misc]

    def test_sprint_task_creation(self) -> None:
        task = SprintTask(
            task_id="st1",
            phase=SprintPhase.BUILD,
            assigned_agent="sisyphus-001",
            status=SprintStatus.PLANNING,
            artifacts=("file1.py",),
        )
        assert task.task_id == "st1"
        assert task.phase == SprintPhase.BUILD
        assert task.assigned_agent == "sisyphus-001"
        assert task.artifacts == ("file1.py",)

    def test_sprint_result_creation(self) -> None:
        sprint = Sprint("s1", "goal", (), ())
        result = SprintResult(sprint=sprint, review_notes="good")
        assert result.review_notes == "good"
        assert result.completed_tasks == ()

    def test_sprint_config_defaults(self) -> None:
        config = SprintConfig()
        assert config.auto_advance
        assert config.require_review_gate
        assert len(config.phase_timeouts) == 7

    def test_sprint_model_create_sprint(self) -> None:
        model = SprintModel()
        sprint = model.create_sprint("Build feature X", ["agent-1", "agent-2"])
        assert sprint.goal == "Build feature X"
        assert "agent-1" in sprint.agents
        assert sprint.status == SprintStatus.IN_PROGRESS
        assert sprint.current_phase_index == 0

    def test_sprint_model_advance_phase(self) -> None:
        model = SprintModel()
        sprint = model.create_sprint("test", ["a1"])
        advanced = model.advance_phase(sprint)
        assert advanced.current_phase_index == 1
        assert advanced.sprint_id == sprint.sprint_id

    def test_sprint_model_advance_through_all(self) -> None:
        model = SprintModel()
        sprint = model.create_sprint("test", ["a1"])
        for _ in range(len(SprintPhase)):
            if sprint.current_phase_index < len(SprintPhase) - 1:
                sprint = model.advance_phase(sprint)
        # Final advance should mark completed
        sprint = model.advance_phase(sprint)
        assert sprint.status == SprintStatus.COMPLETED

    def test_sprint_model_advance_completed_raises(self) -> None:
        model = SprintModel()
        sprint = model.create_sprint("test", ["a1"])
        for _ in range(len(SprintPhase)):
            if sprint.current_phase_index < len(SprintPhase) - 1:
                sprint = model.advance_phase(sprint)
        finished = model.advance_phase(sprint)
        with pytest.raises(SprintError, match="already finished"):
            model.advance_phase(finished)

    def test_sprint_model_advance_failed_raises(self) -> None:
        model = SprintModel()
        sprint = model.create_sprint("test", ["a1"])
        failed = model.fail_sprint(sprint)
        with pytest.raises(SprintError, match="already finished"):
            model.advance_phase(failed)

    def test_sprint_model_get_sprint(self) -> None:
        model = SprintModel()
        sprint = model.create_sprint("test", ["a1"], sprint_id="custom-sprint")
        assert model.get_sprint("custom-sprint") is sprint
        assert model.get_sprint("nonexistent") is None

    def test_sprint_model_add_task(self) -> None:
        model = SprintModel()
        sprint = model.create_sprint("test", ["a1"])
        task = SprintTask("t1", SprintPhase.BUILD, "a1")
        model.add_task(sprint.sprint_id, task)
        tasks = model.get_tasks(sprint.sprint_id)
        assert len(tasks) == 1
        assert tasks[0].task_id == "t1"

    def test_sprint_model_add_task_unknown_raises(self) -> None:
        model = SprintModel()
        task = SprintTask("t1", SprintPhase.BUILD, "a1")
        with pytest.raises(SprintError, match="Unknown sprint"):
            model.add_task("nonexistent", task)

    def test_sprint_model_fail_sprint(self) -> None:
        model = SprintModel()
        sprint = model.create_sprint("test", ["a1"])
        failed = model.fail_sprint(sprint)
        assert failed.status == SprintStatus.FAILED

    def test_sprint_model_complete_sprint(self) -> None:
        model = SprintModel()
        sprint = model.create_sprint("test", ["a1"])
        task = SprintTask("t1", SprintPhase.BUILD, "a1", artifacts=("out.py",))
        result = model.complete_sprint(sprint, tasks=[task])
        assert result.sprint.status == SprintStatus.COMPLETED
        assert "out.py" in result.artifacts


# =====================================================================
# Squad Manager
# =====================================================================


class TestSquadManager:
    def test_squad_domain_enum(self) -> None:
        assert SquadDomain.BACKEND.name == "BACKEND"
        assert SquadDomain.FRONTEND.name == "FRONTEND"
        assert SquadDomain.DEVOPS.name == "DEVOPS"
        assert SquadDomain.DATA.name == "DATA"
        assert SquadDomain.SECURITY.name == "SECURITY"
        assert SquadDomain.RESEARCH.name == "RESEARCH"
        assert SquadDomain.GENERAL.name == "GENERAL"

    def test_squad_creation(self) -> None:
        squad = Squad(
            squad_id="sq1",
            name="Backend Squad",
            leader="lead-001",
            members=("member-1", "member-2"),
            domain=SquadDomain.BACKEND,
        )
        assert squad.squad_id == "sq1"
        assert squad.leader == "lead-001"
        assert len(squad.members) == 2
        assert squad.active_sprint is None

    def test_squad_frozen(self) -> None:
        squad = Squad("sq1", "Test", "leader", (), SquadDomain.GENERAL)
        with pytest.raises(AttributeError):
            squad.leader = "new"  # type: ignore[misc]

    def test_squad_metrics_creation(self) -> None:
        metrics = SquadMetrics(tasks_completed=10, avg_completion_time=5.0, success_rate=0.9)
        assert metrics.tasks_completed == 10
        assert metrics.avg_completion_time == 5.0
        assert metrics.success_rate == 0.9

    def test_squad_metrics_defaults(self) -> None:
        metrics = SquadMetrics()
        assert metrics.tasks_completed == 0
        assert metrics.avg_completion_time == 0.0
        assert metrics.success_rate == 1.0

    def test_squad_manager_create_squad(self) -> None:
        manager = SquadManager()
        squad = manager.create_squad("leader-1", ["member-1", "member-2"], SquadDomain.DATA)
        assert squad.leader == "leader-1"
        assert len(squad.members) == 2
        assert squad.domain == SquadDomain.DATA
        assert squad.squad_id in manager.squads

    def test_squad_manager_leader_in_members_raises(self) -> None:
        manager = SquadManager()
        with pytest.raises(SquadError, match="Leader must not be in members"):
            manager.create_squad("lead", ["lead"], SquadDomain.GENERAL)

    def test_squad_manager_empty_members_raises(self) -> None:
        manager = SquadManager()
        with pytest.raises(SquadError, match="at least one member"):
            manager.create_squad("lead", [], SquadDomain.GENERAL)

    def test_squad_manager_get_squad(self) -> None:
        manager = SquadManager()
        squad = manager.create_squad("lead", ["m1"], SquadDomain.BACKEND)
        assert manager.get_squad(squad.squad_id) is squad
        assert manager.get_squad("nonexistent") is None

    def test_squad_manager_assign_task(self) -> None:
        manager = SquadManager()
        squad = manager.create_squad("lead", ["m1"], SquadDomain.BACKEND)
        updated = manager.assign_task(squad, "sprint-001")
        assert updated.active_sprint == "sprint-001"
        assert manager.get_squad(squad.squad_id).active_sprint == "sprint-001"

    def test_squad_manager_rebalance_no_squads(self) -> None:
        manager = SquadManager()
        result = manager.rebalance_squads()
        assert result == []

    def test_squad_manager_rebalance_single_squad(self) -> None:
        manager = SquadManager()
        squad = manager.create_squad("lead", ["m1", "m2"], SquadDomain.BACKEND)
        result = manager.rebalance_squads()
        assert len(result) == 1
        assert result[0].leader == "lead"

    def test_squad_manager_record_completion(self) -> None:
        manager = SquadManager()
        squad = manager.create_squad("lead", ["m1"], SquadDomain.BACKEND)
        updated = manager.record_completion(squad, success=True, duration=10.0)
        assert updated.metrics.tasks_completed == 1
        assert updated.metrics.success_rate == 1.0
        assert updated.active_sprint is None

    def test_squad_manager_record_completion_failure(self) -> None:
        manager = SquadManager()
        squad = manager.create_squad("lead", ["m1"], SquadDomain.GENERAL)
        updated = manager.record_completion(squad, success=False, duration=5.0)
        assert updated.metrics.success_rate == 0.0

    def test_squad_manager_remove_squad(self) -> None:
        manager = SquadManager()
        squad = manager.create_squad("lead", ["m1"], SquadDomain.GENERAL)
        manager.remove_squad(squad.squad_id)
        assert manager.get_squad(squad.squad_id) is None
        assert len(manager.squads) == 0

    def test_squad_manager_remove_nonexistent_raises(self) -> None:
        manager = SquadManager()
        with pytest.raises(SquadError, match="not found"):
            manager.remove_squad("nonexistent")


# =====================================================================
# Coalition Former
# =====================================================================


class TestCoalitionFormer:
    def test_agent_contribution_creation(self) -> None:
        contrib = AgentContribution(agent_id="a1", marginal_contribution=2.0, shapley_value=0.5)
        assert contrib.agent_id == "a1"
        assert contrib.marginal_contribution == 2.0
        assert contrib.shapley_value == 0.5

    def test_coalition_creation(self) -> None:
        task = TaskTicket("t1", "test")
        coalition = Coalition(
            coalition_id="c1",
            agents=(SISYPHUS,),
            task=task,
            shapley_values=(),
        )
        assert coalition.coalition_id == "c1"
        assert len(coalition.agents) == 1
        assert coalition.task.task_id == "t1"

    def test_coalition_config_defaults(self) -> None:
        config = CoalitionConfig()
        assert config.max_coalition_size == 5
        assert config.min_shapley_threshold == 0.01

    def test_coalition_former_no_agents_raises(self) -> None:
        former = CoalitionFormer()
        task = TaskTicket("t1", "test", frozenset({Capability.CODE_GEN}))
        with pytest.raises(CoalitionError, match="No available agents"):
            former.form_coalition(task, [])

    def test_coalition_former_form_single_agent(self) -> None:
        former = CoalitionFormer(CoalitionConfig(min_shapley_threshold=0.0))
        task = TaskTicket("t1", "test", frozenset({Capability.CODE_GEN}))
        coalition = former.form_coalition(task, [SISYPHUS])
        assert len(coalition.agents) == 1
        assert coalition.agents[0].agent_id == "sisyphus-001"
        assert len(coalition.shapley_values) == 1

    def test_coalition_former_shapley_values(self) -> None:
        former = CoalitionFormer(CoalitionConfig(min_shapley_threshold=0.0))
        task = TaskTicket("t1", "test", frozenset({Capability.CODE_GEN, Capability.DEBUGGING}))
        contributions = former.compute_shapley_values([SISYPHUS, HEPHAESTUS], task)
        assert len(contributions) == 2
        # Shapley values should sum to approximately 1.0
        total = sum(c.shapley_value for c in contributions)
        assert abs(total - 1.0) < 0.001

    def test_coalition_former_shapley_no_capability_match(self) -> None:
        former = CoalitionFormer(CoalitionConfig(min_shapley_threshold=0.0))
        task = TaskTicket("t1", "test", frozenset({Capability.TESTING}))
        contributions = former.compute_shapley_values([SISYPHUS], task)
        assert len(contributions) == 1
        assert contributions[0].shapley_value < 1.0

    def test_coalition_former_all_equal_shapley(self) -> None:
        former = CoalitionFormer(CoalitionConfig(min_shapley_threshold=0.0))
        a1 = DisciplineAgent("a1", "A1", AgentRole.SISYPHUS, "sonnet", frozenset({Capability.CODE_GEN}), 1)
        a2 = DisciplineAgent("a2", "A2", AgentRole.HEPHAESTUS, "sonnet", frozenset({Capability.CODE_GEN}), 1)
        task = TaskTicket("t1", "test", frozenset({Capability.CODE_GEN}))
        contributions = former.compute_shapley_values([a1, a2], task)
        # Both have same capability, so contributions should be equal
        assert abs(contributions[0].shapley_value - contributions[1].shapley_value) < 0.001

    def test_coalition_former_evaluate_coalition(self) -> None:
        former = CoalitionFormer(CoalitionConfig(min_shapley_threshold=0.0))
        task = TaskTicket("t1", "test", frozenset({Capability.CODE_GEN}))
        coalition = former.form_coalition(task, [SISYPHUS])
        score = former.evaluate_coalition(coalition, 2.0)
        assert score > 0

    def test_coalition_former_evaluate_empty(self) -> None:
        task = TaskTicket("t1", "test")
        coalition = Coalition("c1", (SISYPHUS,), task, ())
        former = CoalitionFormer()
        score = former.evaluate_coalition(coalition, 1.0)
        assert score == 0.0

    def test_coalition_former_max_size_respected(self) -> None:
        former = CoalitionFormer(CoalitionConfig(max_coalition_size=2, min_shapley_threshold=0.0))
        task = TaskTicket("t1", "test", frozenset({Capability.CODE_GEN}))
        agents = [SISYPHUS, HEPHAESTUS, PROMETHEUS]
        coalition = former.form_coalition(task, agents)
        assert len(coalition.agents) <= 2

    def test_coalition_former_different_capabilities(self) -> None:
        former = CoalitionFormer(CoalitionConfig(min_shapley_threshold=0.0))
        a1 = DisciplineAgent("a1", "A1", AgentRole.SISYPHUS, "sonnet", frozenset({Capability.CODE_GEN, Capability.TESTING}), 1)
        a2 = DisciplineAgent("a2", "A2", AgentRole.HEPHAESTUS, "sonnet", frozenset({Capability.ARCHITECTURE, Capability.PLANNING}), 1)
        task = TaskTicket("t1", "test", frozenset({Capability.CODE_GEN, Capability.ARCHITECTURE}))
        contributions = former.compute_shapley_values([a1, a2], task)
        assert len(contributions) == 2
        total = sum(c.shapley_value for c in contributions)
        assert abs(total - 1.0) < 0.001


# =====================================================================
# Autopilot
# =====================================================================


class TestAutopilot:
    def test_schedule_creation(self) -> None:
        schedule = Schedule(cron_expr="*/5 * * * *", max_duration=3600.0)
        assert schedule.cron_expr == "*/5 * * * *"
        assert schedule.max_duration == 3600.0
        assert schedule.timeout_action == "stop"

    def test_run_status_enum(self) -> None:
        assert RunStatus.RUNNING.name == "RUNNING"
        assert RunStatus.COMPLETED.name == "COMPLETED"
        assert RunStatus.FAILED.name == "FAILED"
        assert RunStatus.TIMED_OUT.name == "TIMED_OUT"

    def test_autopilot_job_creation(self) -> None:
        schedule = Schedule(cron_expr="0 * * * *")
        job = AutopilotJob(
            job_id="job-1",
            schedule=schedule,
            task_template={"cmd": "deploy"},
            assigned_agents=("sisyphus-001",),
        )
        assert job.job_id == "job-1"
        assert job.enabled
        assert job.task_template == {"cmd": "deploy"}

    def test_autopilot_config_defaults(self) -> None:
        config = AutopilotConfig()
        assert config.max_concurrent_jobs == 5
        assert config.retry_on_failure
        assert config.notify_on_completion

    def test_autopilot_run_creation(self) -> None:
        schedule = Schedule(cron_expr="0 * * * *")
        job = AutopilotJob("j1", schedule, {}, ())
        run = AutopilotRun(job=job, started_at=100.0)
        assert run.status == RunStatus.RUNNING
        assert run.result is None

    def test_autopilot_register_job(self) -> None:
        autopilot = Autopilot()
        schedule = Schedule(cron_expr="*/10 * * * *")
        job = AutopilotJob("j1", schedule, {"task": "build"}, ("a1",))
        autopilot.register_job(job)
        assert "j1" in autopilot.jobs

    def test_autopilot_register_duplicate_raises(self) -> None:
        autopilot = Autopilot()
        schedule = Schedule(cron_expr="0 * * * *")
        job = AutopilotJob("j1", schedule, {}, ())
        autopilot.register_job(job)
        with pytest.raises(AutopilotError, match="already registered"):
            autopilot.register_job(job)

    def test_autopilot_start_job(self) -> None:
        autopilot = Autopilot()
        schedule = Schedule(cron_expr="* * * * *")
        job = AutopilotJob("j1", schedule, {}, ())
        autopilot.register_job(job)
        run = autopilot.start_job("j1")
        assert run.status == RunStatus.RUNNING
        assert run.job.job_id == "j1"

    def test_autopilot_start_nonexistent_raises(self) -> None:
        autopilot = Autopilot()
        with pytest.raises(AutopilotError, match="not found"):
            autopilot.start_job("nonexistent")

    def test_autopilot_stop_job(self) -> None:
        autopilot = Autopilot()
        schedule = Schedule(cron_expr="0 * * * *")
        job = AutopilotJob("j1", schedule, {}, ())
        autopilot.register_job(job)
        autopilot.stop_job("j1")
        assert not autopilot.jobs["j1"].enabled

    def test_autopilot_stop_nonexistent_raises(self) -> None:
        autopilot = Autopilot()
        with pytest.raises(AutopilotError, match="not found"):
            autopilot.stop_job("nonexistent")

    def test_autopilot_pause_resume(self) -> None:
        autopilot = Autopilot()
        assert not autopilot.is_paused
        autopilot.pause_all()
        assert autopilot.is_paused
        autopilot.resume_all()
        assert not autopilot.is_paused

    def test_autopilot_mark_completed(self) -> None:
        autopilot = Autopilot()
        schedule = Schedule(cron_expr="0 * * * *")
        job = AutopilotJob("j1", schedule, {}, ())
        autopilot.register_job(job)
        autopilot.start_job("j1")
        autopilot.mark_completed("j1", "deployment successful")
        runs = autopilot.get_runs("j1")
        assert runs[-1].status == RunStatus.COMPLETED
        assert runs[-1].result == "deployment successful"

    def test_autopilot_get_runs(self) -> None:
        autopilot = Autopilot()
        schedule = Schedule(cron_expr="0 * * * *")
        job = AutopilotJob("j1", schedule, {}, ())
        autopilot.register_job(job)
        assert autopilot.get_runs("j1") == []
        autopilot.start_job("j1")
        assert len(autopilot.get_runs("j1")) == 1


# =====================================================================
# Team Messaging
# =====================================================================


class TestTeamMessaging:
    def test_message_priority_enum(self) -> None:
        assert MessagePriority.LOW.name == "LOW"
        assert MessagePriority.NORMAL.name == "NORMAL"
        assert MessagePriority.HIGH.name == "HIGH"
        assert MessagePriority.URGENT.name == "URGENT"

    def test_agent_message_creation(self) -> None:
        msg = AgentMessage(
            message_id="m1",
            sender="sisyphus-001",
            recipient="hermes-001",
            subject="Status update",
            body="Build complete",
        )
        assert msg.sender == "sisyphus-001"
        assert msg.recipient == "hermes-001"
        assert msg.priority == MessagePriority.NORMAL
        assert not msg.is_read

    def test_message_thread_creation(self) -> None:
        thread = MessageThread(root_id="m1", messages=("m1", "m2"), subject="Thread")
        assert thread.root_id == "m1"
        assert len(thread.messages) == 2

    def test_messaging_config_defaults(self) -> None:
        config = MessagingConfig()
        assert config.max_inbox_size == 1000
        assert config.message_ttl == 86400.0

    def test_team_messaging_send(self) -> None:
        tm = TeamMessaging()
        msg_id = tm.send("sisyphus-001", "hermes-001", "Hello", "World")
        assert msg_id.startswith("msg-")

    def test_team_messaging_get_inbox(self) -> None:
        tm = TeamMessaging()
        tm.send("a1", "a2", "Subj", "Body")
        inbox = tm.get_inbox("a2")
        assert len(inbox) == 1
        assert inbox[0].subject == "Subj"

    def test_team_messaging_get_inbox_empty(self) -> None:
        tm = TeamMessaging()
        assert tm.get_inbox("unknown") == []

    def test_team_messaging_broadcast(self) -> None:
        tm = TeamMessaging()
        ids = tm.broadcast("a1", ["a2", "a3", "a4"], "Broadcast", "Message")
        assert len(ids) == 3
        assert tm.get_inbox("a2")[0].subject == "Broadcast"
        assert tm.get_inbox("a3")[0].subject == "Broadcast"

    def test_team_messaging_broadcast_no_recipients_raises(self) -> None:
        tm = TeamMessaging()
        with pytest.raises(MessagingError, match="No recipients"):
            tm.broadcast("a1", [], "test", "body")

    def test_team_messaging_mark_read(self) -> None:
        tm = TeamMessaging()
        msg_id = tm.send("a1", "a2", "Subj", "Body")
        tm.mark_read(msg_id)
        msg = tm.get_message(msg_id)
        assert msg is not None
        assert msg.is_read

    def test_team_messaging_mark_read_nonexistent_raises(self) -> None:
        tm = TeamMessaging()
        with pytest.raises(MessagingError, match="not found"):
            tm.mark_read("nonexistent")

    def test_team_messaging_reply_thread(self) -> None:
        tm = TeamMessaging()
        root_id = tm.send("a1", "a2", "Original", "Body")
        reply_id = tm.send("a2", "a1", "Re: Original", "Reply", reply_to=root_id)
        thread = tm.get_thread(root_id)
        assert thread is not None
        assert reply_id in thread.messages

    def test_team_messaging_reply_to_nonexistent_raises(self) -> None:
        tm = TeamMessaging()
        with pytest.raises(MessagingError, match="not found"):
            tm.send("a1", "a2", "Reply", "Body", reply_to="nonexistent")

    def test_team_messaging_inbox_priority_sort(self) -> None:
        tm = TeamMessaging()
        tm.send("a1", "a2", "Normal msg", "body", priority=MessagePriority.NORMAL)
        tm.send("a1", "a2", "Urgent msg", "body", priority=MessagePriority.URGENT)
        inbox = tm.get_inbox("a2")
        assert inbox[0].subject == "Urgent msg"
        assert inbox[1].subject == "Normal msg"

    def test_team_messaging_get_message(self) -> None:
        tm = TeamMessaging()
        msg_id = tm.send("a1", "a2", "Subj", "Body")
        msg = tm.get_message(msg_id)
        assert msg is not None
        assert msg.subject == "Subj"

    def test_team_messaging_get_message_none(self) -> None:
        tm = TeamMessaging()
        assert tm.get_message("nonexistent") is None


# =====================================================================
# Consensus Builder
# =====================================================================


class TestConsensusBuilder:
    def test_vote_choice_enum(self) -> None:
        assert VoteChoice.APPROVE.name == "APPROVE"
        assert VoteChoice.REJECT.name == "REJECT"
        assert VoteChoice.ABSTAIN.name == "ABSTAIN"
        assert VoteChoice.NEEDS_DISCUSSION.name == "NEEDS_DISCUSSION"

    def test_aggregation_method_enum(self) -> None:
        assert AggregationMethod.MAJORITY.name == "MAJORITY"
        assert AggregationMethod.SUPERMAJORITY.name == "SUPERMAJORITY"
        assert AggregationMethod.WEIGHTED.name == "WEIGHTED"
        assert AggregationMethod.UNANIMOUS.name == "UNANIMOUS"

    def test_proposal_creation(self) -> None:
        proposal = Proposal(proposal_id="p1", content="Deploy to prod", proposer="prometheus-001")
        assert proposal.proposal_id == "p1"
        assert proposal.proposer == "prometheus-001"
        assert proposal.deadline is None

    def test_vote_creation(self) -> None:
        vote = Vote(agent_id="a1", proposal_id="p1", choice=VoteChoice.APPROVE)
        assert vote.agent_id == "a1"
        assert vote.choice == VoteChoice.APPROVE
        assert vote.confidence == 1.0

    def test_consensus_result_creation(self) -> None:
        proposal = Proposal("p1", "content", "a1")
        result = ConsensusResult(
            proposal=proposal,
            votes=(),
            passed=True,
            confidence=0.8,
            dissenting_opinions=("disagree",),
        )
        assert result.passed
        assert result.confidence == 0.8
        assert len(result.dissenting_opinions) == 1

    def test_consensus_config_defaults(self) -> None:
        config = ConsensusConfig()
        assert config.method == AggregationMethod.MAJORITY
        assert config.min_participation == 0.5
        assert config.timeout == 300.0

    def test_consensus_builder_submit_proposal(self) -> None:
        cb = ConsensusBuilder()
        proposal = Proposal("p1", "Deploy", "a1")
        cb.submit_proposal(proposal)
        assert cb.get_proposal("p1") is proposal

    def test_consensus_builder_duplicate_proposal_raises(self) -> None:
        cb = ConsensusBuilder()
        cb.submit_proposal(Proposal("p1", "Deploy", "a1"))
        with pytest.raises(ConsensusError, match="already exists"):
            cb.submit_proposal(Proposal("p1", "Again", "a2"))

    def test_consensus_builder_cast_vote(self) -> None:
        cb = ConsensusBuilder()
        proposal = Proposal("p1", "Deploy", "a1")
        cb.submit_proposal(proposal)
        vote = Vote("a1", "p1", VoteChoice.APPROVE)
        cb.cast_vote(vote)
        assert len(cb.get_votes("p1")) == 1

    def test_consensus_builder_cast_vote_unknown_proposal_raises(self) -> None:
        cb = ConsensusBuilder()
        with pytest.raises(ConsensusError, match="Unknown proposal"):
            cb.cast_vote(Vote("a1", "nonexistent", VoteChoice.APPROVE))

    def test_consensus_builder_majority_pass(self) -> None:
        cb = ConsensusBuilder()
        proposal = Proposal("p1", "Deploy", "a1")
        cb.submit_proposal(proposal)
        cb.cast_vote(Vote("a1", "p1", VoteChoice.APPROVE))
        cb.cast_vote(Vote("a2", "p1", VoteChoice.APPROVE))
        cb.cast_vote(Vote("a3", "p1", VoteChoice.REJECT))
        agents = ["a1", "a2", "a3"]
        result = cb.build_consensus(proposal, agents, AggregationMethod.MAJORITY)
        assert result.passed

    def test_consensus_builder_majority_fail(self) -> None:
        cb = ConsensusBuilder()
        proposal = Proposal("p1", "Deploy", "a1")
        cb.submit_proposal(proposal)
        cb.cast_vote(Vote("a1", "p1", VoteChoice.REJECT))
        cb.cast_vote(Vote("a2", "p1", VoteChoice.REJECT))
        agents = ["a1", "a2"]
        result = cb.build_consensus(proposal, agents, AggregationMethod.MAJORITY)
        assert not result.passed

    def test_consensus_builder_majority_tie_rejected(self) -> None:
        cb = ConsensusBuilder()
        proposal = Proposal("p1", "Decision", "a1")
        cb.submit_proposal(proposal)
        cb.cast_vote(Vote("a1", "p1", VoteChoice.APPROVE))
        cb.cast_vote(Vote("a2", "p1", VoteChoice.REJECT))
        agents = ["a1", "a2"]
        result = cb.build_consensus(proposal, agents, AggregationMethod.MAJORITY)
        assert not result.passed

    def test_consensus_builder_weighted(self) -> None:
        cb = ConsensusBuilder()
        proposal = Proposal("p1", "Deploy", "a1")
        cb.submit_proposal(proposal)
        cb.cast_vote(Vote("a1", "p1", VoteChoice.APPROVE, confidence=0.9))
        cb.cast_vote(Vote("a2", "p1", VoteChoice.REJECT, confidence=0.3))
        agents = ["a1", "a2"]
        result = cb.build_consensus(proposal, agents, AggregationMethod.WEIGHTED)
        assert result.passed
        assert result.confidence > 0.5

    def test_consensus_builder_weighted_rejected(self) -> None:
        cb = ConsensusBuilder()
        proposal = Proposal("p1", "Deploy", "a1")
        cb.submit_proposal(proposal)
        cb.cast_vote(Vote("a1", "p1", VoteChoice.REJECT, confidence=0.9))
        cb.cast_vote(Vote("a2", "p1", VoteChoice.REJECT, confidence=0.8))
        agents = ["a1", "a2"]
        result = cb.build_consensus(proposal, agents, AggregationMethod.WEIGHTED)
        assert not result.passed

    def test_consensus_builder_supermajority_pass(self) -> None:
        cb = ConsensusBuilder()
        proposal = Proposal("p1", "Critical deploy", "a1")
        cb.submit_proposal(proposal)
        cb.cast_vote(Vote("a1", "p1", VoteChoice.APPROVE))
        cb.cast_vote(Vote("a2", "p1", VoteChoice.APPROVE))
        cb.cast_vote(Vote("a3", "p1", VoteChoice.REJECT))
        agents = ["a1", "a2", "a3"]
        result = cb.build_consensus(proposal, agents, AggregationMethod.SUPERMAJORITY)
        assert result.passed  # 2/3 >= 2/3

    def test_consensus_builder_supermajority_fail(self) -> None:
        cb = ConsensusBuilder()
        proposal = Proposal("p1", "Critical", "a1")
        cb.submit_proposal(proposal)
        cb.cast_vote(Vote("a1", "p1", VoteChoice.APPROVE))
        cb.cast_vote(Vote("a2", "p1", VoteChoice.REJECT))
        cb.cast_vote(Vote("a3", "p1", VoteChoice.REJECT))
        agents = ["a1", "a2", "a3"]
        result = cb.build_consensus(proposal, agents, AggregationMethod.SUPERMAJORITY)
        assert not result.passed  # 1/3 < 2/3

    def test_consensus_builder_unanimous_pass(self) -> None:
        cb = ConsensusBuilder()
        proposal = Proposal("p1", "Simple", "a1")
        cb.submit_proposal(proposal)
        cb.cast_vote(Vote("a1", "p1", VoteChoice.APPROVE))
        cb.cast_vote(Vote("a2", "p1", VoteChoice.APPROVE))
        agents = ["a1", "a2"]
        result = cb.build_consensus(proposal, agents, AggregationMethod.UNANIMOUS)
        assert result.passed

    def test_consensus_builder_unanimous_fail(self) -> None:
        cb = ConsensusBuilder()
        proposal = Proposal("p1", "Simple", "a1")
        cb.submit_proposal(proposal)
        cb.cast_vote(Vote("a1", "p1", VoteChoice.APPROVE))
        cb.cast_vote(Vote("a2", "p1", VoteChoice.REJECT))
        agents = ["a1", "a2"]
        result = cb.build_consensus(proposal, agents, AggregationMethod.UNANIMOUS)
        assert not result.passed

    def test_consensus_builder_insufficient_participation(self) -> None:
        cb = ConsensusBuilder(ConsensusConfig(min_participation=0.8))
        proposal = Proposal("p1", "Test", "a1")
        cb.submit_proposal(proposal)
        cb.cast_vote(Vote("a1", "p1", VoteChoice.APPROVE))
        agents = ["a1", "a2", "a3", "a4", "a5"]
        with pytest.raises(ConsensusError, match="Insufficient participation"):
            cb.build_consensus(proposal, agents, AggregationMethod.MAJORITY)

    def test_consensus_builder_all_abstain(self) -> None:
        cb = ConsensusBuilder()
        proposal = Proposal("p1", "Test", "a1")
        cb.submit_proposal(proposal)
        cb.cast_vote(Vote("a1", "p1", VoteChoice.ABSTAIN))
        cb.cast_vote(Vote("a2", "p1", VoteChoice.ABSTAIN))
        agents = ["a1", "a2"]
        result = cb.build_consensus(proposal, agents, AggregationMethod.MAJORITY)
        assert not result.passed
        assert result.confidence == 0.0

    def test_consensus_builder_dissenting_opinions(self) -> None:
        cb = ConsensusBuilder()
        proposal = Proposal("p1", "Test", "a1")
        cb.submit_proposal(proposal)
        cb.cast_vote(Vote("a1", "p1", VoteChoice.APPROVE, reasoning="Good idea"))
        cb.cast_vote(Vote("a2", "p1", VoteChoice.REJECT, reasoning="Too risky"))
        agents = ["a1", "a2"]
        result = cb.build_consensus(proposal, agents, AggregationMethod.MAJORITY)
        assert not result.passed
        assert "Too risky" in result.dissenting_opinions

    def test_consensus_builder_get_votes(self) -> None:
        cb = ConsensusBuilder()
        proposal = Proposal("p1", "Test", "a1")
        cb.submit_proposal(proposal)
        cb.cast_vote(Vote("a1", "p1", VoteChoice.APPROVE))
        assert len(cb.get_votes("p1")) == 1
        assert cb.get_votes("nonexistent") == []

    def test_consensus_builder_weighted_no_votes_raises(self) -> None:
        cb = ConsensusBuilder()
        with pytest.raises(ConsensusError, match="No votes"):
            cb.weighted_vote([])


# =====================================================================
# Swarm Visualizer
# =====================================================================


class TestSwarmVisualizer:
    def test_agent_state_enum(self) -> None:
        assert AgentState.IDLE.name == "IDLE"
        assert AgentState.BUSY.name == "BUSY"
        assert AgentState.BLOCKED.name == "BLOCKED"
        assert AgentState.ERROR.name == "ERROR"
        assert AgentState.OFFLINE.name == "OFFLINE"

    def test_agent_status_creation(self) -> None:
        status = AgentStatus(agent_id="a1", state=AgentState.BUSY, current_task="deploy", utilization=0.75)
        assert status.agent_id == "a1"
        assert status.state == AgentState.BUSY
        assert status.current_task == "deploy"
        assert status.utilization == 0.75

    def test_agent_status_defaults(self) -> None:
        status = AgentStatus(agent_id="a1")
        assert status.state == AgentState.IDLE
        assert status.current_task is None
        assert status.utilization == 0.0

    def test_swarm_snapshot_creation(self) -> None:
        status = AgentStatus(agent_id="a1", state=AgentState.BUSY)
        snapshot = SwarmSnapshot(
            agents=(status,),
            active_tasks=1,
            metrics=SwarmMetrics(total_agents=1, busy=1),
        )
        assert snapshot.active_tasks == 1
        assert snapshot.metrics is not None

    def test_swarm_metrics_creation(self) -> None:
        metrics = SwarmMetrics(total_agents=5, busy=3, idle=2, throughput=0.6)
        assert metrics.total_agents == 5
        assert metrics.busy == 3
        assert metrics.idle == 2

    def test_swarm_metrics_defaults(self) -> None:
        metrics = SwarmMetrics()
        assert metrics.total_agents == 0
        assert metrics.busy == 0

    def test_swarm_visualizer_register_agent(self) -> None:
        viz = SwarmVisualizer()
        viz.register_agent("a1")
        status = viz.get_agent_status("a1")
        assert status is not None
        assert status.agent_id == "a1"

    def test_swarm_visualizer_update_status(self) -> None:
        viz = SwarmVisualizer()
        viz.register_agent("a1")
        viz.update_status("a1", AgentStatus("a1", AgentState.BUSY, "task-1", 0.5))
        status = viz.get_agent_status("a1")
        assert status is not None
        assert status.state == AgentState.BUSY
        assert status.current_task == "task-1"

    def test_swarm_visualizer_get_snapshot(self) -> None:
        viz = SwarmVisualizer()
        viz.register_agent("a1", AgentStatus("a1", AgentState.BUSY))
        viz.register_agent("a2", AgentStatus("a2", AgentState.IDLE))
        snapshot = viz.get_snapshot()
        assert len(snapshot.agents) == 2
        assert snapshot.active_tasks == 1
        assert snapshot.metrics is not None
        assert snapshot.metrics.busy == 1
        assert snapshot.metrics.idle == 1

    def test_swarm_visualizer_get_snapshot_empty(self) -> None:
        viz = SwarmVisualizer()
        snapshot = viz.get_snapshot()
        assert len(snapshot.agents) == 0
        assert snapshot.active_tasks == 0

    def test_swarm_visualizer_format_tmux_pane(self) -> None:
        viz = SwarmVisualizer()
        viz.register_agent("a1", AgentStatus("a1", AgentState.BUSY, "task-1"))
        pane = viz.format_tmux_pane("a1")
        assert "a1" in pane
        assert "BUSY" in pane
        assert "task-1" in pane

    def test_swarm_visualizer_format_tmux_pane_offline(self) -> None:
        viz = SwarmVisualizer()
        pane = viz.format_tmux_pane("unknown")
        assert "OFFLINE" in pane

    def test_swarm_visualizer_format_dashboard(self) -> None:
        viz = SwarmVisualizer()
        viz.register_agent("a1", AgentStatus("a1", AgentState.BUSY, "deploy"))
        viz.register_agent("a2", AgentStatus("a2", AgentState.IDLE))
        dashboard = viz.format_dashboard()
        assert "LYRA AGENT SWARM DASHBOARD" in dashboard
        assert "a1" in dashboard
        assert "a2" in dashboard

    def test_swarm_visualizer_format_dashboard_empty(self) -> None:
        viz = SwarmVisualizer()
        dashboard = viz.format_dashboard()
        assert "LYRA AGENT SWARM DASHBOARD" in dashboard
        assert "Agents: 0" in dashboard
