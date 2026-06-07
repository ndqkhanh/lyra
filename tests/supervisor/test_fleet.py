"""Tests for FleetOrchestrator (multi-agent fleet lifecycle)."""

import datetime
import tempfile
from pathlib import Path

import pytest

from lyra.supervisor.fleet import (
    AgentConfig,
    FleetConfig,
    FleetEvent,
    FleetEventType,
    FleetOrchestrator,
    FleetStatus,
    GpuAllocationPolicy,
    SessionProgress,
)
from lyra.supervisor.state import SessionState


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


@pytest.fixture
def db_path() -> str:
    """Return a temporary file path for the SQLite database."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    yield path
    Path(path).unlink(missing_ok=True)


@pytest.fixture
def fleet(db_path: str) -> FleetOrchestrator:
    """Return a FleetOrchestrator backed by a temp SQLite database."""
    config = FleetConfig(
        max_concurrent=10,
        stagnation_threshold_seconds=60,
        stagnation_velocity_window=3,
        stagnation_improvement_ratio=0.3,
    )
    return FleetOrchestrator(
        db_path=db_path,
        idle_timeout_minutes=60,
        config=config,
    )


@pytest.fixture
def agent_config() -> AgentConfig:
    """Return a basic AgentConfig for testing."""
    return AgentConfig(
        name="test-agent",
        working_dir="/tmp/worktrees/test-agent",
        capabilities=["research", "reasoning"],
        model="sonnet",
    )


# ------------------------------------------------------------------
# FleetConfig & AgentConfig
# ------------------------------------------------------------------


class TestFleetConfig:
    """Verify FleetConfig defaults and construction."""

    def test_defaults(self) -> None:
        cfg = FleetConfig()
        assert cfg.max_concurrent == 10
        assert cfg.gpu_allocation_policy == GpuAllocationPolicy.MOST_PROMISING
        assert cfg.stagnation_threshold_seconds == 300
        assert cfg.stagnation_velocity_window == 5
        assert cfg.stagnation_improvement_ratio == 0.3

    def test_custom_values(self) -> None:
        cfg = FleetConfig(
            max_concurrent=5,
            gpu_allocation_policy=GpuAllocationPolicy.STAGNATION_PRIORITY,
            stagnation_threshold_seconds=120,
        )
        assert cfg.max_concurrent == 5
        assert cfg.gpu_allocation_policy == GpuAllocationPolicy.STAGNATION_PRIORITY
        assert cfg.stagnation_threshold_seconds == 120


class TestAgentConfig:
    """Verify AgentConfig defaults and construction."""

    def test_defaults(self) -> None:
        cfg = AgentConfig(name="a", working_dir="/tmp")
        assert cfg.name == "a"
        assert cfg.capabilities == []
        assert cfg.model == "sonnet"
        assert cfg.gpu_required is False
        assert cfg.initial_state == {}

    def test_custom_values(self) -> None:
        cfg = AgentConfig(
            name="researcher",
            working_dir="/tmp/wt",
            capabilities=["research", "vision"],
            model="opus",
            gpu_required=True,
            initial_state={"task": "analyze"},
        )
        assert cfg.name == "researcher"
        assert cfg.model == "opus"
        assert cfg.gpu_required is True
        assert cfg.initial_state == {"task": "analyze"}


# ------------------------------------------------------------------
# Spawning
# ------------------------------------------------------------------


class TestSpawning:
    """Test spawning multiple concurrent agents."""

    def test_spawn_returns_session_id(self, fleet: FleetOrchestrator, agent_config: AgentConfig) -> None:
        sid = fleet.spawn_agent(agent_config)
        assert isinstance(sid, str)
        assert len(sid) > 0

    def test_spawn_registers_session(self, fleet: FleetOrchestrator, agent_config: AgentConfig) -> None:
        sid = fleet.spawn_agent(agent_config)
        info = fleet.get_session_info(sid)
        assert info is not None
        assert info.name == "test-agent"
        assert info.state == SessionState.WORKING

    def test_spawn_max_concurrent(self, db_path: str, agent_config: AgentConfig) -> None:
        cfg = FleetConfig(max_concurrent=2)
        fleet = FleetOrchestrator(db_path=db_path, config=cfg)
        fleet.spawn_agent(agent_config)
        fleet.spawn_agent(agent_config)
        with pytest.raises(RuntimeError, match="capacity"):
            fleet.spawn_agent(agent_config)

    def test_spawn_multiple_sessions(self, fleet: FleetOrchestrator, agent_config: AgentConfig) -> None:
        """Fleet correctly tracks multiple concurrent agents."""
        s1 = fleet.spawn_agent(agent_config)
        s2 = fleet.spawn_agent(agent_config)
        s3 = fleet.spawn_agent(agent_config)

        assert len(s1) > 0
        assert len(s2) > 0
        assert len(s3) > 0
        assert s1 != s2 != s3

        status = fleet.fleet_status()
        assert status.total_sessions >= 3
        assert status.active_count >= 3

    def test_spawn_with_different_configs(self, fleet: FleetOrchestrator) -> None:
        """Fleet handles agents with varying configurations."""
        a1 = fleet.spawn_agent(AgentConfig(name="researcher", working_dir="/tmp/r"))
        a2 = fleet.spawn_agent(AgentConfig(name="coder", working_dir="/tmp/c", capabilities=["coding"], gpu_required=True))
        a3 = fleet.spawn_agent(AgentConfig(name="reviewer", working_dir="/tmp/v", model="haiku"))

        assert a1 != a2 != a3
        status = fleet.fleet_status()
        assert status.total_sessions == 3


# ------------------------------------------------------------------
# Fleet status
# ------------------------------------------------------------------


class TestFleetStatus:
    """Verify fleet_status() returns accurate snapshots."""

    def test_empty_fleet(self, db_path: str) -> None:
        fleet = FleetOrchestrator(db_path=db_path)
        status = fleet.fleet_status()
        assert status.total_sessions == 0
        assert status.active_count == 0
        assert status.stagnant_count == 0

    def test_fleet_status_after_spawn(self, fleet: FleetOrchestrator, agent_config: AgentConfig) -> None:
        fleet.spawn_agent(agent_config)
        status = fleet.fleet_status()
        assert status.total_sessions == 1
        assert status.active_count == 1
        assert status.stagnant_count == 0

    def test_fleet_status_after_kill(self, fleet: FleetOrchestrator, agent_config: AgentConfig) -> None:
        sid = fleet.spawn_agent(agent_config)
        fleet.kill_session(sid)
        status = fleet.fleet_status()
        assert status.total_sessions >= 1
        assert status.active_count == 0
        # session still tracked in _sessions but no longer active

    def test_fleet_status_contains_progress(self, fleet: FleetOrchestrator, agent_config: AgentConfig) -> None:
        fleet.spawn_agent(agent_config)
        status = fleet.fleet_status()
        assert len(status.sessions) >= 1
        progress = status.sessions[0]
        assert isinstance(progress, SessionProgress)
        assert progress.checkpoint_count >= 0
        assert progress.stagnation_level == 0
        assert progress.gpu_allocated is False


# ------------------------------------------------------------------
# GPU allocation
# ------------------------------------------------------------------


class TestGpuAllocation:
    """Test GPU resource management."""

    def test_register_gpus(self, fleet: FleetOrchestrator) -> None:
        fleet.register_gpus(["cuda:0", "cuda:1"])
        pool = fleet.gpu_pool
        assert "cuda:0" in pool
        assert "cuda:1" in pool
        assert pool["cuda:0"] is None

    def test_allocate_gpu_round_robin(self, db_path: str, agent_config: AgentConfig) -> None:
        cfg = FleetConfig(gpu_allocation_policy=GpuAllocationPolicy.ROUND_ROBIN)
        fleet = FleetOrchestrator(db_path=db_path, config=cfg)
        fleet.register_gpus(["cuda:0", "cuda:1"])
        fleet.spawn_agent(agent_config)
        fleet.spawn_agent(agent_config)

        allocated = fleet.allocate_gpus(2)
        assert len(allocated) == 2
        assert fleet.gpu_assignments[allocated[0]] == "cuda:0"
        assert fleet.gpu_assignments[allocated[1]] == "cuda:1"

    def test_allocate_gpu_most_promising(self, db_path: str, agent_config: AgentConfig) -> None:
        cfg = FleetConfig(gpu_allocation_policy=GpuAllocationPolicy.MOST_PROMISING)
        fleet = FleetOrchestrator(db_path=db_path, config=cfg)
        fleet.register_gpus(["cuda:0"])

        sid = fleet.spawn_agent(agent_config)
        fleet.record_progress(sid, 1.0)

        allocated = fleet.allocate_gpus(1)
        assert sid in allocated

    def test_allocate_gpu_stagnation_priority(self, db_path: str, agent_config: AgentConfig) -> None:
        cfg = FleetConfig(gpu_allocation_policy=GpuAllocationPolicy.STAGNATION_PRIORITY)
        fleet = FleetOrchestrator(db_path=db_path, config=cfg)
        fleet.register_gpus(["cuda:0"])

        sid = fleet.spawn_agent(agent_config)
        # Simulate stagnation by aging last_active
        fleet.detect_stagnation(sid)

        allocated = fleet.allocate_gpus(1)
        assert sid in allocated

    def test_allocate_gpu_insufficient(self, fleet: FleetOrchestrator, agent_config: AgentConfig) -> None:
        fleet.register_gpus(["cuda:0"])
        fleet.spawn_agent(agent_config)

        with pytest.raises(RuntimeError, match="Insufficient GPUs"):
            fleet.allocate_gpus(5)

    def test_deallocate_gpu(self, fleet: FleetOrchestrator, agent_config: AgentConfig) -> None:
        fleet.register_gpus(["cuda:0"])
        sid = fleet.spawn_agent(agent_config)
        fleet.allocate_gpus(1)

        freed = fleet.deallocate_gpu(sid)
        assert freed == "cuda:0"
        assert sid not in fleet.gpu_assignments
        # GPU should be free again
        assert fleet.gpu_pool["cuda:0"] is None

    def test_deallocate_gpu_none_allocated(self, fleet: FleetOrchestrator) -> None:
        freed = fleet.deallocate_gpu("nonexistent")
        assert freed is None


# ------------------------------------------------------------------
# Stagnation detection
# ------------------------------------------------------------------


class TestStagnationDetection:
    """Multi-level stagnation detection tests."""

    def test_no_stagnation_on_fresh_session(self, fleet: FleetOrchestrator, agent_config: AgentConfig) -> None:
        sid = fleet.spawn_agent(agent_config)
        stagnant = fleet.detect_stagnation(sid)
        assert stagnant is False

    def test_level_1_idle_stagnation(self, db_path: str, agent_config: AgentConfig) -> None:
        cfg = FleetConfig(stagnation_threshold_seconds=0)
        fleet = FleetOrchestrator(db_path=db_path, config=cfg)
        sid = fleet.spawn_agent(agent_config)

        # Wind back last_active
        info = fleet.get_session_info(sid)
        assert info is not None
        past = info.last_active - datetime.timedelta(seconds=10)
        fleet._store.update_last_active(sid, now=past)

        stagnant = fleet.detect_stagnation(sid)
        assert stagnant is True

    def test_level_2_velocity_stagnation(self, fleet: FleetOrchestrator, agent_config: AgentConfig) -> None:
        sid = fleet.spawn_agent(agent_config)
        # Record decreasing progress (velocity near zero)
        fleet.record_progress(sid, 1.0)
        fleet.record_progress(sid, 1.0)
        fleet.record_progress(sid, 1.0)

        stagnant = fleet.detect_stagnation(sid)
        assert stagnant is True  # velocity is zero

    def test_no_velocity_stagnation_with_improvement(self, fleet: FleetOrchestrator, agent_config: AgentConfig) -> None:
        sid = fleet.spawn_agent(agent_config)
        # Record increasing progress
        fleet.record_progress(sid, 0.2)
        fleet.record_progress(sid, 0.5)
        fleet.record_progress(sid, 0.9)

        stagnant = fleet.detect_stagnation(sid)
        # Should not stagnate since velocity is positive
        assert stagnant is False

    def test_level_3_improvement_stagnation(self, db_path: str, agent_config: AgentConfig) -> None:
        cfg = FleetConfig(stagnation_improvement_ratio=0.5)
        fleet = FleetOrchestrator(db_path=db_path, config=cfg)
        sid = fleet.spawn_agent(agent_config)

        # Record mostly flat progress (only 1 out of 4 improves)
        fleet.record_progress(sid, 0.5)
        fleet.record_progress(sid, 0.5)
        fleet.record_progress(sid, 0.6)  # one improvement
        fleet.record_progress(sid, 0.6)

        stagnant = fleet.detect_stagnation(sid)
        assert stagnant is True

    def test_detect_all_stagnation(self, db_path: str, agent_config: AgentConfig) -> None:
        cfg = FleetConfig(stagnation_threshold_seconds=0)
        fleet = FleetOrchestrator(db_path=db_path, config=cfg)

        s1 = fleet.spawn_agent(agent_config)
        s2 = fleet.spawn_agent(agent_config)

        # Age both sessions
        for sid in [s1, s2]:
            info = fleet.get_session_info(sid)
            assert info is not None
            past = info.last_active - datetime.timedelta(seconds=10)
            fleet._store.update_last_active(sid, now=past)

        stagnant = fleet.detect_all_stagnation()
        assert len(stagnant) == 2
        assert s1 in stagnant
        assert s2 in stagnant


# ------------------------------------------------------------------
# Kill / graceful shutdown
# ------------------------------------------------------------------


class TestKillSession:
    """Test graceful session shutdown."""

    def test_kill_active_session(self, fleet: FleetOrchestrator, agent_config: AgentConfig) -> None:
        sid = fleet.spawn_agent(agent_config)
        fleet.kill_session(sid)
        info = fleet.get_session_info(sid)
        assert info is not None
        assert info.state == SessionState.STOPPED

    def test_kill_cleans_gpu(self, fleet: FleetOrchestrator, agent_config: AgentConfig) -> None:
        fleet.register_gpus(["cuda:0"])
        sid = fleet.spawn_agent(agent_config)
        fleet.allocate_gpus(1)
        assert sid in fleet.gpu_assignments

        fleet.kill_session(sid)
        assert sid not in fleet.gpu_assignments

    def test_kill_nonexistent_does_nothing(self, fleet: FleetOrchestrator) -> None:
        # Should not raise
        fleet.kill_session("nonexistent")


# ------------------------------------------------------------------
# Event bus
# ------------------------------------------------------------------


class TestFleetEventBus:
    """Test the fleet event bus (WebSocket IPC integration point)."""

    def test_subscribe_and_publish(self, fleet: FleetOrchestrator, agent_config: AgentConfig) -> None:
        events: list[FleetEvent] = []

        def collector(event: FleetEvent) -> None:
            events.append(event)

        fleet.subscribe(collector)
        fleet.spawn_agent(agent_config)

        assert len(events) >= 1
        assert events[0].event_type == FleetEventType.SESSION_SPAWNED

    def test_unsubscribe(self, fleet: FleetOrchestrator, agent_config: AgentConfig) -> None:
        events: list[FleetEvent] = []

        def collector(event: FleetEvent) -> None:
            events.append(event)

        fleet.subscribe(collector)
        fleet.unsubscribe(collector)
        fleet.spawn_agent(agent_config)

        assert len(events) == 0

    def test_gpu_events_published(self, fleet: FleetOrchestrator, agent_config: AgentConfig) -> None:
        events: list[FleetEvent] = []

        def collector(event: FleetEvent) -> None:
            events.append(event)

        fleet.subscribe(collector)
        fleet.register_gpus(["cuda:0"])
        sid = fleet.spawn_agent(agent_config)
        fleet.allocate_gpus(1)
        fleet.deallocate_gpu(sid)

        event_types = [e.event_type for e in events]
        assert FleetEventType.GPU_ALLOCATED in event_types
        assert FleetEventType.GPU_DEALLOCATED in event_types


# ------------------------------------------------------------------
# Crash recovery (integration with checkpoint manager)
# ------------------------------------------------------------------


class TestCrashRecovery:
    """Test fleet recovery from interrupted sessions."""

    def test_recover_without_checkpoint_manager(self, db_path: str) -> None:
        """Fleet should initialize normally without checkpoint manager."""
        fleet = FleetOrchestrator(db_path=db_path)
        assert fleet is not None
        status = fleet.fleet_status()
        assert status.total_sessions == 0


# ------------------------------------------------------------------
# Fleet event dataclass
# ------------------------------------------------------------------


class TestFleetEvent:
    """Verify FleetEvent dataclass."""

    def test_create_event(self) -> None:
        event = FleetEvent(
            event_type=FleetEventType.SESSION_SPAWNED,
            session_id="abc123",
            payload={"name": "test"},
        )
        assert event.event_type == FleetEventType.SESSION_SPAWNED
        assert event.session_id == "abc123"
        assert event.payload["name"] == "test"
        assert event.timestamp is not None

    def test_default_timestamp(self) -> None:
        event = FleetEvent(
            event_type=FleetEventType.SESSION_STOPPED,
            session_id="xyz",
        )
        assert event.timestamp is not None
        assert isinstance(event.timestamp, datetime.datetime)


# ------------------------------------------------------------------
# FleetStatus dataclass
# ------------------------------------------------------------------


class TestFleetStatusData:
    """Verify FleetStatus dataclass."""

    def test_create_status(self) -> None:
        progress = SessionProgress(session_id="abc")
        status = FleetStatus(
            total_sessions=1,
            active_count=1,
            stagnant_count=0,
            gpu_allocated_count=0,
            sessions=(progress,),
        )
        assert status.total_sessions == 1
        assert status.active_count == 1
        assert len(status.sessions) == 1

    def test_empty_status(self) -> None:
        status = FleetStatus(
            total_sessions=0,
            active_count=0,
            stagnant_count=0,
            gpu_allocated_count=0,
            sessions=(),
        )
        assert status.sessions == ()


# ------------------------------------------------------------------
# Fleet event type enum
# ------------------------------------------------------------------


class TestFleetEventType:
    """Verify FleetEventType enum."""

    def test_all_members_present(self) -> None:
        expected = {
            "session_spawned",
            "session_stopped",
            "session_stagnated",
            "session_recovered",
            "gpu_allocated",
            "gpu_deallocated",
            "fleet_status_change",
        }
        assert {m.value for m in FleetEventType} == expected


# ------------------------------------------------------------------
# SessionProgress
# ------------------------------------------------------------------


class TestSessionProgress:
    """Verify SessionProgress dataclass."""

    def test_defaults(self) -> None:
        p = SessionProgress(session_id="abc")
        assert p.session_id == "abc"
        assert p.checkpoint_count == 0
        assert p.last_checkpoint_at is None
        assert p.stagnation_level == 0
        assert p.gpu_allocated is False
        assert p.cost_estimate == 0.0

    def test_custom_values(self) -> None:
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        p = SessionProgress(
            session_id="xyz",
            checkpoint_count=5,
            last_checkpoint_at=now,
            stagnation_level=2,
            gpu_allocated=True,
            cost_estimate=42.5,
        )
        assert p.checkpoint_count == 5
        assert p.last_checkpoint_at == now
        assert p.stagnation_level == 2
        assert p.cost_estimate == 42.5
