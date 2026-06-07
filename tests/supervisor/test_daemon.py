"""Tests for SupervisorDaemon."""

import datetime
import tempfile
from pathlib import Path

import pytest

from src.supervisor.daemon import SupervisorDaemon
from src.supervisor.state import ProcessState, SessionState


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
def daemon(db_path: str) -> SupervisorDaemon:
    """Return a SupervisorDaemon backed by a temp SQLite database."""
    return SupervisorDaemon(db_path=db_path, idle_timeout_minutes=60)


# ------------------------------------------------------------------
# Session lifecycle
# ------------------------------------------------------------------


class TestStartSession:
    def test_returns_session_id(self, daemon: SupervisorDaemon) -> None:
        sid = daemon.start_session("my-agent", "/tmp/workdir")
        assert isinstance(sid, str)
        assert len(sid) > 0

    def test_starts_as_working_alive(self, daemon: SupervisorDaemon) -> None:
        sid = daemon.start_session("my-agent", "/tmp/workdir")
        state = daemon.get_session(sid)
        assert state == SessionState.WORKING
        info = daemon.get_session_info(sid)
        assert info is not None
        assert info.process_state == ProcessState.ALIVE

    def test_multiple_sessions(self, daemon: SupervisorDaemon) -> None:
        s1 = daemon.start_session("agent-1", "/tmp/a")
        s2 = daemon.start_session("agent-2", "/tmp/b")
        assert s1 != s2
        assert len(daemon.list_sessions()) == 2


class TestGetSession:
    def test_returns_none_for_unknown(self, daemon: SupervisorDaemon) -> None:
        assert daemon.get_session("nonexistent") is None

    def test_returns_state(self, daemon: SupervisorDaemon) -> None:
        sid = daemon.start_session("test", "/tmp")
        assert daemon.get_session(sid) == SessionState.WORKING


class TestGetSessionInfo:
    def test_returns_none_for_unknown(self, daemon: SupervisorDaemon) -> None:
        assert daemon.get_session_info("nonexistent") is None

    def test_returns_full_info(self, daemon: SupervisorDaemon) -> None:
        sid = daemon.start_session("test", "/tmp")
        info = daemon.get_session_info(sid)
        assert info is not None
        assert info.session_id == sid
        assert info.name == "test"
        assert info.working_dir == "/tmp"


class TestListSessions:
    def test_empty_initially(self, daemon: SupervisorDaemon) -> None:
        assert daemon.list_sessions() == []

    def test_ordered_newest_first(self, daemon: SupervisorDaemon) -> None:
        s1 = daemon.start_session("first", "/tmp/a")
        s2 = daemon.start_session("second", "/tmp/b")
        sessions = daemon.list_sessions()
        assert sessions[0].session_id == s2
        assert sessions[1].session_id == s1


class TestStopSession:
    def test_stop_existing(self, daemon: SupervisorDaemon) -> None:
        sid = daemon.start_session("test", "/tmp")
        daemon.stop_session(sid)
        assert daemon.get_session(sid) == SessionState.STOPPED

    def test_stop_nonexistent_does_nothing(self, daemon: SupervisorDaemon) -> None:
        daemon.stop_session("nonexistent")  # should not raise

    def test_stop_sets_process_exited(self, daemon: SupervisorDaemon) -> None:
        sid = daemon.start_session("test", "/tmp")
        daemon.stop_session(sid)
        info = daemon.get_session_info(sid)
        assert info is not None
        assert info.process_state == ProcessState.EXITED


class TestUpdateSessionState:
    def test_update_state(self, daemon: SupervisorDaemon) -> None:
        sid = daemon.start_session("test", "/tmp")
        daemon.update_session_state(sid, SessionState.COMPLETED)
        assert daemon.get_session(sid) == SessionState.COMPLETED

    def test_update_process_state(self, daemon: SupervisorDaemon) -> None:
        sid = daemon.start_session("test", "/tmp")
        daemon.update_session_state(sid, SessionState.IDLE, process_state=ProcessState.LOOP_SLEEPING)
        info = daemon.get_session_info(sid)
        assert info is not None
        assert info.state == SessionState.IDLE
        assert info.process_state == ProcessState.LOOP_SLEEPING

    def test_update_nonexistent_does_nothing(self, daemon: SupervisorDaemon) -> None:
        daemon.update_session_state("nonexistent", SessionState.COMPLETED)  # should not raise


class TestUpdatePrUrl:
    def test_updates_pr_url(self, daemon: SupervisorDaemon) -> None:
        sid = daemon.start_session("test", "/tmp")
        daemon.update_pr_url(sid, "https://github.com/example/pull/1")
        info = daemon.get_session_info(sid)
        assert info is not None
        assert info.pr_url == "https://github.com/example/pull/1"

    def test_nonexistent_does_nothing(self, daemon: SupervisorDaemon) -> None:
        daemon.update_pr_url("nonexistent", "https://example.com")  # should not raise


# ------------------------------------------------------------------
# Idle timeout
# ------------------------------------------------------------------


class TestStopIdleSessions:
    def test_no_idle_when_working(self, daemon: SupervisorDaemon) -> None:
        daemon.start_session("busy", "/tmp")
        stopped = daemon.stop_idle_sessions()
        assert stopped == []

    def test_stops_idle_sessions(self, db_path: str) -> None:
        """Idle sessions beyond the short timeout should be stopped."""
        daemon = SupervisorDaemon(db_path=db_path, idle_timeout_minutes=0)
        sid = daemon.start_session("idle-agent", "/tmp")
        # Manually wind back last_active by 1 second past the timeout
        old = daemon.get_session_info(sid)
        assert old is not None
        past = old.last_active - datetime.timedelta(seconds=1)
        daemon._store.update_last_active(sid, now=past)
        # re-load into memory
        daemon._load_existing_sessions()
        stopped = daemon.stop_idle_sessions()
        assert sid in stopped
        assert daemon.get_session(sid) == SessionState.STOPPED

    def test_completed_not_stopped(self, daemon: SupervisorDaemon) -> None:
        sid = daemon.start_session("done", "/tmp")
        daemon.update_session_state(sid, SessionState.COMPLETED)
        stopped = daemon.stop_idle_sessions()
        assert sid not in stopped

    def test_failed_not_stopped(self, daemon: SupervisorDaemon) -> None:
        sid = daemon.start_session("broken", "/tmp")
        daemon.update_session_state(sid, SessionState.FAILED)
        stopped = daemon.stop_idle_sessions()
        assert sid not in stopped

    def test_stopped_not_stopped_again(self, daemon: SupervisorDaemon) -> None:
        sid = daemon.start_session("already-stopped", "/tmp")
        daemon.stop_session(sid)
        stopped = daemon.stop_idle_sessions()
        assert sid not in stopped


# ------------------------------------------------------------------
# Persistence
# ------------------------------------------------------------------


class TestPersistence:
    def test_survives_daemon_recreation(self, db_path: str) -> None:
        d1 = SupervisorDaemon(db_path=db_path)
        sid = d1.start_session("persistent", "/tmp/work")
        d1.update_pr_url(sid, "https://github.com/example/pull/99")

        d2 = SupervisorDaemon(db_path=db_path)
        info = d2.get_session_info(sid)
        assert info is not None
        assert info.name == "persistent"
        assert info.pr_url == "https://github.com/example/pull/99"

    def test_stop_persisted(self, db_path: str) -> None:
        d1 = SupervisorDaemon(db_path=db_path)
        sid = d1.start_session("will-stop", "/tmp")
        d1.stop_session(sid)

        d2 = SupervisorDaemon(db_path=db_path)
        assert d2.get_session(sid) == SessionState.STOPPED


# ------------------------------------------------------------------
# Idle timeout configuration
# ------------------------------------------------------------------


class TestIdleTimeoutConfig:
    def test_custom_timeout(self, daemon: SupervisorDaemon) -> None:
        assert daemon._idle_timeout == datetime.timedelta(minutes=60)

    def test_zero_timeout(self, db_path: str) -> None:
        d = SupervisorDaemon(db_path=db_path, idle_timeout_minutes=0)
        assert d._idle_timeout == datetime.timedelta()
