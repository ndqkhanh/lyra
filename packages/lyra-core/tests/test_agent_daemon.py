"""Tests for AgentDaemon — per-user daemon managing agent sessions."""

import time

import pytest
import pytest_asyncio

from lyra_core.agent.daemon import AgentDaemon, DaemonConfig, DaemonStatus
from lyra_core.agent.session import SessionStatus
from lyra_core.protocol import (
    AgentHealth,
    AgentIdentity,
    AgentLifecycle,
    AgentState,
    Task,
)


class _MockAgent:
    """Minimal AgentProtocol stub for daemon testing."""

    def __init__(self, agent_id="daemon_test_agent"):
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
        yield f"output_from_{self.identity.agent_id}"
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
def daemon():
    """Fresh daemon for each test (not started)."""
    return AgentDaemon()


@pytest_asyncio.fixture
async def running_daemon():
    """Started daemon for lifecycle tests."""
    d = AgentDaemon()
    await d.start()
    yield d
    await d.stop()


@pytest_asyncio.fixture
async def daemon_with_session(running_daemon):
    """Running daemon with one spawned session."""
    agent = _MockAgent("agent_1")
    session = await running_daemon.spawn(agent)
    return running_daemon, session


class TestDaemonConfig:
    """Tests for DaemonConfig."""

    def test_default_config(self):
        cfg = DaemonConfig()
        assert cfg.max_sessions == 50
        assert cfg.max_tasks_per_session == 1000
        assert cfg.idle_timeout_s == 3600.0
        assert cfg.heartbeat_interval_s == 30.0
        assert cfg.auto_recovery is True

    def test_custom_config(self):
        cfg = DaemonConfig(max_sessions=10, idle_timeout_s=60.0)
        assert cfg.max_sessions == 10
        assert cfg.idle_timeout_s == 60.0


class TestDaemonStatus:
    """Tests for DaemonStatus dataclass."""

    def test_daemon_status_creation(self):
        s = DaemonStatus(
            session_count=0,
            active_sessions=0,
            paused_sessions=0,
            error_sessions=0,
            total_tasks_executed=0,
            total_tasks_completed=0,
            total_tasks_failed=0,
            uptime_s=0.0,
            socket_path="/tmp/test.sock",
        )
        assert s.session_count == 0


class TestAgentDaemonLifecycle:
    """Tests for daemon start/stop."""

    @pytest.mark.asyncio
    async def test_start_sets_running(self, daemon):
        await daemon.start()
        assert daemon._running is True
        assert daemon._started_at is not None

    @pytest.mark.asyncio
    async def test_stop_clears_sessions(self, running_daemon):
        await running_daemon.stop()
        assert running_daemon._running is False
        assert running_daemon.session_count == 0

    @pytest.mark.asyncio
    async def test_uptime_tracks_time(self, running_daemon):
        assert running_daemon.uptime_s >= 0

    @pytest.mark.asyncio
    async def test_status_after_start(self, running_daemon):
        s = running_daemon.status
        assert s.session_count == 0
        assert s.active_sessions == 0


class TestAgentDaemonSessions:
    """Tests for session spawning and management."""

    @pytest.mark.asyncio
    async def test_spawn_creates_session(self, running_daemon):
        agent = _MockAgent("agent_1")
        session = await running_daemon.spawn(agent)
        assert session.status == SessionStatus.RUNNING
        assert running_daemon.session_count == 1

    @pytest.mark.asyncio
    async def test_spawn_multiple_sessions(self, running_daemon):
        for i in range(3):
            agent = _MockAgent(f"agent_{i}")
            await running_daemon.spawn(agent)
        assert running_daemon.session_count == 3

    @pytest.mark.asyncio
    async def test_spawn_respects_max_sessions(self, running_daemon):
        running_daemon.config.max_sessions = 2
        await running_daemon.spawn(_MockAgent("a1"))
        await running_daemon.spawn(_MockAgent("a2"))
        with pytest.raises(RuntimeError, match="Max sessions"):
            await running_daemon.spawn(_MockAgent("a3"))

    @pytest.mark.asyncio
    async def test_run_task_on_session(self, daemon_with_session):
        daemon, session = daemon_with_session
        task = Task(task_id="t1", instruction="test")
        result = await daemon.run(session.session_id, task)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_run_unknown_session_raises(self, running_daemon):
        task = Task(task_id="t1", instruction="test")
        with pytest.raises(KeyError, match="Unknown session"):
            await running_daemon.run("nonexistent", task)

    @pytest.mark.asyncio
    async def test_pause_and_resume(self, daemon_with_session):
        daemon, session = daemon_with_session
        await daemon.pause(session.session_id)
        assert session.status == SessionStatus.PAUSED

        await daemon.resume(session.session_id)
        assert session.status == SessionStatus.RUNNING

    @pytest.mark.asyncio
    async def test_terminate_removes_session(self, daemon_with_session):
        daemon, session = daemon_with_session
        sid = session.session_id
        await daemon.terminate(sid)
        assert daemon.get_session(sid) is None
        assert daemon.session_count == 0

    @pytest.mark.asyncio
    async def test_list_sessions_filtered(self, running_daemon):
        a1 = _MockAgent("a1")
        a2 = _MockAgent("a2")
        s1 = await running_daemon.spawn(a1)
        s2 = await running_daemon.spawn(a2)
        await running_daemon.pause(s1.session_id)

        running = running_daemon.list_sessions(SessionStatus.RUNNING)
        paused = running_daemon.list_sessions(SessionStatus.PAUSED)
        assert len(running) == 1
        assert len(paused) == 1

    @pytest.mark.asyncio
    async def test_terminate_idle(self, running_daemon):
        # Set idle timeout to a small positive value and advance time
        running_daemon.config.idle_timeout_s = 0.01
        agent = _MockAgent("a1")
        session = await running_daemon.spawn(agent)
        await running_daemon.pause(session.session_id)
        # Let the idle timeout expire
        import asyncio
        await asyncio.sleep(0.02)

        removed = await running_daemon.terminate_idle()
        assert removed == 1
        assert running_daemon.session_count == 0


class TestAgentDaemonHealth:
    """Tests for health checks."""

    @pytest.mark.asyncio
    async def test_health_check_returns_status(self, running_daemon):
        health = await running_daemon.health_check()
        assert health["daemon_running"] is True
        assert "sessions" in health
        assert "errors" in health

    @pytest.mark.asyncio
    async def test_health_check_detects_errors(self, running_daemon):
        agent = _MockAgent("a1")
        session = await running_daemon.spawn(agent)
        # Force error state by directly manipulating internal state
        session._status = SessionStatus.ERROR

        health = await running_daemon.health_check()
        assert len(health["errors"]) == 1


class TestAgentDaemonSnapshots:
    """Tests for snapshot persistence."""

    @pytest.mark.asyncio
    async def test_snapshot_all(self, running_daemon):
        await running_daemon.spawn(_MockAgent("a1"))
        await running_daemon.spawn(_MockAgent("a2"))
        snaps = running_daemon.snapshot_all()
        assert len(snaps) == 2

    @pytest.mark.asyncio
    async def test_snapshot_dir_persistence(self, tmp_path):
        snap_dir = tmp_path / "snapshots"
        snap_dir.mkdir(parents=True, exist_ok=True)

        d = AgentDaemon(DaemonConfig(snapshot_dir=snap_dir))
        await d.start()
        await d.spawn(_MockAgent("a1"))
        await d.stop()

        snap_file = snap_dir / "sessions.json"
        assert snap_file.exists()
