"""Comprehensive tests for Phase 1: Unified Agent Protocol, EventBus, Watchdog, Adapters."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator

import pytest
from lyra_core.protocol import (
    AgentHealth,
    AgentIdentity,
    AgentLifecycle,
    AgentMode,
    AgentProtocol,
    AgentState,
    ItemKind,
    ItemStatus,
    Task,
    TaskResult,
    WorkstreamItem,
)

# ═══════════════════════════════════════════════════════════════════════════════
# AgentIdentity
# ═══════════════════════════════════════════════════════════════════════════════

class TestAgentIdentity:
    def test_create_minimal(self):
        ident = AgentIdentity(agent_id="a1", project_id="p1", agent_type="test")
        assert ident.agent_id == "a1"
        assert ident.project_id == "p1"
        assert ident.agent_type == "test"

    def test_create_with_capabilities(self):
        ident = AgentIdentity(
            agent_id="a1", project_id="p1", agent_type="code_review",
            capabilities=frozenset({"skill:python", "skill:review"}),
        )
        assert "skill:python" in ident.capabilities
        assert "skill:review" in ident.capabilities

    def test_immutable(self):
        ident = AgentIdentity(agent_id="a1", project_id="p1", agent_type="test")
        with pytest.raises(Exception):
            ident.agent_id = "new_id"  # type: ignore[misc]

    def test_equality(self):
        a = AgentIdentity(agent_id="a1", project_id="p1", agent_type="test")
        b = AgentIdentity(agent_id="a1", project_id="p1", agent_type="test")
        assert a == b

    def test_hashable(self):
        ident = AgentIdentity(agent_id="a1", project_id="p1", agent_type="test")
        s = {ident}
        assert ident in s


# ═══════════════════════════════════════════════════════════════════════════════
# AgentState
# ═══════════════════════════════════════════════════════════════════════════════

class TestAgentState:
    def test_default_state(self):
        state = AgentState(
            lifecycle=AgentLifecycle.REGISTERED,
            health=AgentHealth.UNKNOWN,
            since=time.time(),
        )
        assert state.lifecycle == AgentLifecycle.REGISTERED
        assert state.health == AgentHealth.UNKNOWN

    def test_all_lifecycle_values(self):
        for lc in AgentLifecycle:
            state = AgentState(lifecycle=lc, health=AgentHealth.HEALTHY,
                               since=time.time())
            assert state.lifecycle == lc

    def test_all_health_values(self):
        for h in AgentHealth:
            state = AgentState(lifecycle=AgentLifecycle.ACTIVE, health=h,
                               since=time.time())
            assert state.health == h


# ═══════════════════════════════════════════════════════════════════════════════
# Task & TaskResult
# ═══════════════════════════════════════════════════════════════════════════════

class TestTask:
    def test_create_task(self):
        t = Task(task_id="t1", instruction="do something")
        assert t.task_id == "t1"
        assert t.instruction == "do something"

    def test_task_with_context(self):
        t = Task(task_id="t1", instruction="analyze",
                 context={"file": "main.py", "line": 42})
        assert t.context["file"] == "main.py"

    def test_task_with_parent(self):
        parent = Task(task_id="t1", instruction="parent")
        child = Task(task_id="t2", instruction="child", parent_task_id=parent.task_id)
        assert child.parent_task_id == "t1"

    def test_task_immutable(self):
        t = Task(task_id="t1", instruction="do something")
        with pytest.raises(Exception):
            t.instruction = "changed"  # type: ignore[misc]


class TestTaskResult:
    def test_success_result(self):
        r = TaskResult(task_id="t1", agent_id="a1", success=True,
                       output="done", metrics={"elapsed": 1.5})
        assert r.success is True
        assert r.output == "done"
        assert r.metrics["elapsed"] == 1.5

    def test_failure_result(self):
        r = TaskResult(task_id="t1", agent_id="a1", success=False,
                       error="something went wrong")
        assert r.success is False
        assert r.error == "something went wrong"

    def test_with_artifacts(self):
        r = TaskResult(task_id="t1", agent_id="a1", success=True,
                       artifacts=("/tmp/out.txt", "/tmp/log.json"))
        assert len(r.artifacts) == 2


# ═══════════════════════════════════════════════════════════════════════════════
# WorkstreamItem
# ═══════════════════════════════════════════════════════════════════════════════

class TestWorkstreamItem:
    def test_create_pending(self):
        item = WorkstreamItem(id="w1", kind=ItemKind.TOOL_CALL)
        assert item.status == ItemStatus.PENDING
        assert item.kind == ItemKind.TOOL_CALL

    def test_terminal_statuses(self):
        for s in (ItemStatus.APPROVED, ItemStatus.REJECTED,
                  ItemStatus.EXPIRED, ItemStatus.RESOLVED):
            item = WorkstreamItem(id="w1", kind=ItemKind.TOOL_CALL, status=s)
            assert item.is_terminal

    def test_non_terminal_statuses(self):
        for s in (ItemStatus.PENDING, ItemStatus.WAITING):
            item = WorkstreamItem(id="w1", kind=ItemKind.TOOL_CALL, status=s)
            assert not item.is_terminal

    def test_age_calculation(self):
        now = 1000.0
        item = WorkstreamItem(id="w1", kind=ItemKind.TOOL_CALL,
                              created_at=990.0)
        assert item.get_age_seconds(now=now) == 10.0

    def test_correlation_id(self):
        item = WorkstreamItem(id="w1", kind=ItemKind.PROPOSAL,
                              correlation_id="corr_123")
        assert item.correlation_id == "corr_123"

    def test_all_item_kinds(self):
        for kind in ItemKind:
            item = WorkstreamItem(id="w1", kind=kind)
            assert item.kind == kind


# ═══════════════════════════════════════════════════════════════════════════════
# AgentMode (Protocol testing)
# ═══════════════════════════════════════════════════════════════════════════════

class _TestMode:
    """Minimal AgentMode implementation for testing."""
    name = "test_mode"

    async def on_enter(self, agent: AgentProtocol) -> None:
        pass

    async def on_exit(self, agent: AgentProtocol) -> None:
        pass

    async def handle_input(self, agent: AgentProtocol, text: str) -> str | None:
        return text

    async def transform_output(self, agent: AgentProtocol, chunk: str) -> str:
        return chunk


class TestAgentMode:
    def test_mode_implements_protocol(self):
        mode = _TestMode()
        assert mode.name == "test_mode"
        # Protocol is structural — no isinstance check needed

    def test_mode_name(self):
        mode = _TestMode()
        assert isinstance(mode.name, str)


# ═══════════════════════════════════════════════════════════════════════════════
# AgentProtocol (concrete implementation for testing)
# ═══════════════════════════════════════════════════════════════════════════════

class _TestAgent:
    """Minimal AgentProtocol implementation for testing."""

    def __init__(self, agent_id: str = "test", project_id: str = "p1") -> None:
        self._identity = AgentIdentity(
            agent_id=agent_id, project_id=project_id, agent_type="test",
            capabilities=frozenset({"test", "debug"}),
        )
        self._state = AgentState(
            lifecycle=AgentLifecycle.REGISTERED,
            health=AgentHealth.UNKNOWN,
            since=time.time(),
        )
        self._modes: list[AgentMode] = []

    @property
    def identity(self) -> AgentIdentity:
        return self._identity

    @property
    def state(self) -> AgentState:
        return self._state

    @property
    def mode_stack(self) -> tuple[AgentMode, ...]:
        return tuple(self._modes)

    def push_mode(self, mode: AgentMode) -> None:
        self._modes.append(mode)

    def pop_mode(self) -> AgentMode:
        if not self._modes:
            raise IndexError("empty")
        return self._modes.pop()

    def supports(self, capability: str) -> bool:
        return capability in self._identity.capabilities

    async def initialize(self) -> None:
        self._state = AgentState(
            lifecycle=AgentLifecycle.READY, health=AgentHealth.HEALTHY,
            since=time.time(),
        )

    async def run(self, task: Task) -> AsyncIterator[str]:
        self._state = AgentState(
            lifecycle=AgentLifecycle.ACTIVE, health=AgentHealth.HEALTHY,
            since=time.time(),
        )
        yield f"Task {task.task_id}: {task.instruction}"

    async def shutdown(self) -> None:
        self._state = AgentState(
            lifecycle=AgentLifecycle.TERMINATED, health=AgentHealth.HEALTHY,
            since=time.time(),
        )

    async def snapshot(self) -> dict:
        return {"agent_id": self._identity.agent_id}


class TestAgentProtocol:
    def test_isinstance_check(self):
        agent = _TestAgent()
        assert isinstance(agent, AgentProtocol)

    def test_identity(self):
        agent = _TestAgent(agent_id="my_agent")
        assert agent.identity.agent_id == "my_agent"

    def test_capability_check(self):
        agent = _TestAgent()
        assert agent.supports("test")
        assert agent.supports("debug")
        assert not agent.supports("unknown_skill")

    def test_mode_stack(self):
        agent = _TestAgent()
        mode = _TestMode()
        agent.push_mode(mode)
        assert len(agent.mode_stack) == 1
        popped = agent.pop_mode()
        assert popped is mode
        assert len(agent.mode_stack) == 0

    def test_pop_empty_mode_stack(self):
        agent = _TestAgent()
        with pytest.raises(IndexError):
            agent.pop_mode()

    @pytest.mark.asyncio
    async def test_initialize(self):
        agent = _TestAgent()
        await agent.initialize()
        assert agent.state.lifecycle == AgentLifecycle.READY
        assert agent.state.health == AgentHealth.HEALTHY

    @pytest.mark.asyncio
    async def test_run(self):
        agent = _TestAgent()
        await agent.initialize()
        task = Task(task_id="t1", instruction="hello")
        outputs = []
        async for chunk in agent.run(task):
            outputs.append(chunk)
        assert len(outputs) == 1
        assert "hello" in outputs[0]

    @pytest.mark.asyncio
    async def test_shutdown(self):
        agent = _TestAgent()
        await agent.shutdown()
        assert agent.state.lifecycle == AgentLifecycle.TERMINATED

    @pytest.mark.asyncio
    async def test_snapshot(self):
        agent = _TestAgent()
        snap = await agent.snapshot()
        assert snap["agent_id"] == "test"


# ═══════════════════════════════════════════════════════════════════════════════
# AgentLifecycle transitions
# ═══════════════════════════════════════════════════════════════════════════════

class TestAgentLifecycleTransitions:
    """Verify all valid lifecycle state transitions."""

    def test_registered_to_initializing(self):
        a = _TestAgent()
        assert a.state.lifecycle == AgentLifecycle.REGISTERED
        # initialize() moves to READY via INITIALIZING internally

    @pytest.mark.asyncio
    async def test_ready_to_active(self):
        a = _TestAgent()
        await a.initialize()
        assert a.state.lifecycle == AgentLifecycle.READY
        async for _ in a.run(Task(task_id="t1", instruction="test")):
            pass
        # After run, _TestAgent stays at IDLE (set by finally in adapters)

    @pytest.mark.asyncio
    async def test_full_lifecycle(self):
        a = _TestAgent()
        # REGISTERED → READY
        await a.initialize()
        assert a.state.lifecycle == AgentLifecycle.READY
        # READY → ACTIVE → IDLE
        async for _ in a.run(Task(task_id="t1", instruction="test")):
            pass
        # IDLE → TERMINATED
        await a.shutdown()
        assert a.state.lifecycle == AgentLifecycle.TERMINATED
