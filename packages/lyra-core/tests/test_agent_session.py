"""Tests for AgentSession — persistent lifecycle wrapper with snapshots."""

import time

import pytest
import pytest_asyncio

from lyra_core.agent.session import (
    AgentSession,
    SessionSnapshot,
    SessionStatus,
)
from lyra_core.protocol import (
    AgentHealth,
    AgentIdentity,
    AgentLifecycle,
    AgentState,
    Task,
)


class _MockAgent:
    """Minimal AgentProtocol stub for testing."""

    def __init__(self, agent_id="test_agent"):
        self.identity = AgentIdentity(
            agent_id=agent_id,
            project_id="test_project",
            agent_type="mock",
        )
        self._lifecycle = AgentLifecycle.READY
        self._health = AgentHealth.HEALTHY
        self.mode_stack: list = []
        self._init_called = False
        self._shutdown_called = False
        self._run_outputs: list[str] = ["mock output"]

    @property
    def state(self):
        return AgentState(
            lifecycle=self._lifecycle,
            health=self._health,
            since=time.time(),
        )

    async def initialize(self):
        self._init_called = True
        self._lifecycle = AgentLifecycle.ACTIVE

    async def run(self, task):
        for chunk in self._run_outputs:
            yield chunk
        self._lifecycle = AgentLifecycle.IDLE

    async def shutdown(self):
        self._shutdown_called = True
        self._lifecycle = AgentLifecycle.TERMINATED

    def supports(self, capability: str) -> bool:
        return True

    def snapshot(self):
        return {}

    def push_mode(self, mode):
        self.mode_stack.append(mode)

    def pop_mode(self):
        if self.mode_stack:
            return self.mode_stack.pop()
        return None


@pytest.fixture
def agent():
    return _MockAgent()


@pytest.fixture
def session(agent):
    return AgentSession(agent)


@pytest_asyncio.fixture
async def started_session(agent):
    s = AgentSession(agent)
    await s.start()
    return s


class TestSessionStatus:
    """Tests for SessionStatus enum and colored rings."""

    def test_color_mapping(self):
        assert SessionStatus.SPAWNING.color() == "blue"
        assert SessionStatus.RUNNING.color() == "green"
        assert SessionStatus.PAUSED.color() == "yellow"
        assert SessionStatus.ERROR.color() == "red"
        assert SessionStatus.COMPLETED.color() == "bright_black"
        assert SessionStatus.TERMINATED.color() == "grey"


class TestSessionSnapshot:
    """Tests for SessionSnapshot dataclass."""

    def test_snapshot_creation(self):
        snap = SessionSnapshot(
            session_id="s1",
            agent_id="a1",
            status=SessionStatus.RUNNING,
            lifecycle=AgentLifecycle.ACTIVE,
            health=AgentHealth.HEALTHY,
            created_at=time.time(),
            updated_at=time.time(),
        )
        assert snap.session_id == "s1"
        assert snap.status == SessionStatus.RUNNING
        assert snap.task_count == 0


class TestAgentSessionInit:
    """Tests for AgentSession initialization."""

    def test_session_starts_in_spawning(self, session):
        assert session.status == SessionStatus.SPAWNING
        assert session.session_id.startswith("session_")

    def test_session_custom_id(self, agent):
        s = AgentSession(agent, session_id="my_session")
        assert s.session_id == "my_session"

    def test_session_exposes_agent_identity(self, session):
        assert session.identity.agent_id == "test_agent"

    def test_initial_task_count_zero(self, session):
        assert session.task_count == 0
        assert session.success_rate == 1.0

    def test_refcount_starts_at_zero(self, session):
        assert session.refcount == 0


class TestAgentSessionLifecycle:
    """Tests for session lifecycle transitions."""

    @pytest.mark.asyncio
    async def test_start_transitions_to_running(self, agent):
        s = AgentSession(agent)
        await s.start()
        assert s.status == SessionStatus.RUNNING
        assert agent._init_called is True

    @pytest.mark.asyncio
    async def test_run_executes_task(self, started_session):
        task = Task(task_id="t1", instruction="test")
        result = await started_session.run(task)
        assert result.success is True
        assert started_session.task_count == 1
        assert started_session.success_rate == 1.0

    @pytest.mark.asyncio
    async def test_run_tracks_failure(self, agent):
        agent._run_outputs = []  # Will cause error during iteration
        async def _failing_run(task):
            raise RuntimeError("simulated failure")
            yield  # unreachable
        agent.run = _failing_run

        s = AgentSession(agent)
        await s.start()
        task = Task(task_id="t1", instruction="test")
        result = await s.run(task)
        assert result.success is False
        assert s._failed_tasks == 1

    @pytest.mark.asyncio
    async def test_pause_resume_cycle(self, started_session):
        await started_session.pause()
        assert started_session.status == SessionStatus.PAUSED

        await started_session.resume()
        assert started_session.status == SessionStatus.RUNNING

    @pytest.mark.asyncio
    async def test_shutdown_transitions_to_terminated(self, started_session):
        await started_session.shutdown()
        assert started_session.status == SessionStatus.TERMINATED

    @pytest.mark.asyncio
    async def test_history_accumulates_results(self, started_session):
        t1 = Task(task_id="t1", instruction="first")
        t2 = Task(task_id="t2", instruction="second")
        await started_session.run(t1)
        await started_session.run(t2)
        assert len(started_session.history) == 2
        assert started_session.history[0].task_id == "t1"
        assert started_session.history[1].task_id == "t2"


class TestAgentSessionRefcount:
    """Tests for winlink-style reference counting."""

    def test_acquire_increments_refcount(self, session):
        session.acquire()
        assert session.refcount == 1
        session.acquire()
        assert session.refcount == 2

    def test_release_decrements_refcount(self, session):
        session.acquire()
        session.acquire()
        session.release()
        assert session.refcount == 1

    def test_release_does_not_go_below_zero(self, session):
        session.release()
        assert session.refcount == 0


class TestAgentSessionSnapshot:
    """Tests for session snapshot and restore."""

    @pytest.mark.asyncio
    async def test_snapshot_captures_state(self, started_session):
        snap = started_session.snapshot()
        assert snap.session_id == started_session.session_id
        assert snap.status == SessionStatus.RUNNING
        assert snap.lifecycle is not None
        assert snap.health is not None
        assert snap.task_count == 0

    @pytest.mark.asyncio
    async def test_snapshot_after_tasks(self, started_session):
        await started_session.run(Task(task_id="t1", instruction="test"))
        snap = started_session.snapshot()
        assert snap.task_count == 1
        assert snap.completed_tasks == 1

    def test_restore_updates_metadata(self, session):
        snap = SessionSnapshot(
            session_id=session.session_id,
            agent_id="test_agent",
            status=SessionStatus.RUNNING,
            lifecycle=AgentLifecycle.ACTIVE,
            health=AgentHealth.HEALTHY,
            created_at=time.time(),
            updated_at=time.time(),
            task_count=5,
            completed_tasks=4,
            failed_tasks=1,
            metadata={"key": "value"},
        )
        session.restore(snap)
        assert session.task_count == 5
        assert session._completed_tasks == 4
        assert session._failed_tasks == 1


class TestAgentSessionSummary:
    """Tests for session summary."""

    def test_summary_includes_key_fields(self, session):
        s = session.summary()
        assert s["session_id"] == session.session_id
        assert s["status"] == "spawning"
        assert "color" in s
        assert s["task_count"] == 0
        assert s["refcount"] == 0

    @pytest.mark.asyncio
    async def test_summary_after_work(self, started_session):
        await started_session.run(Task(task_id="t1", instruction="test"))
        s = started_session.summary()
        assert s["task_count"] == 1
        assert s["completed"] == 1
        assert s["success_rate"] == 1.0
