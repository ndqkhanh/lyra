"""Tests for supervisor daemon — session lifecycle and state management."""

import time
from lyra.supervisor.daemon import SupervisorDaemon
from lyra.supervisor.state import SessionState, ProcessState


class TestSupervisorDaemon:
    """Supervisor daemon lifecycle tests."""

    def test_start_session(self, tmp_path):
        db = tmp_path / "test.db"
        daemon = SupervisorDaemon(db_path=str(db))
        sid = daemon.start_session("test-session", "/tmp/test")
        assert len(sid) == 12
        info = daemon.get_session_info(sid)
        assert info is not None
        assert info.name == "test-session"
        assert info.state == SessionState.WORKING
        assert info.process_state == ProcessState.ALIVE

    def test_list_sessions(self, tmp_path):
        db = tmp_path / "test.db"
        daemon = SupervisorDaemon(db_path=str(db))
        daemon.start_session("session-a", "/tmp/a")
        daemon.start_session("session-b", "/tmp/b")
        sessions = daemon.list_sessions()
        assert len(sessions) == 2

    def test_stop_session(self, tmp_path):
        db = tmp_path / "test.db"
        daemon = SupervisorDaemon(db_path=str(db))
        sid = daemon.start_session("test", "/tmp")
        daemon.stop_session(sid)
        info = daemon.get_session_info(sid)
        assert info is not None
        assert info.state == SessionState.STOPPED

    def test_update_state(self, tmp_path):
        db = tmp_path / "test.db"
        daemon = SupervisorDaemon(db_path=str(db))
        sid = daemon.start_session("test", "/tmp")
        daemon.update_session_state(sid, SessionState.NEEDS_INPUT, ProcessState.LOOP_SLEEPING)
        info = daemon.get_session_info(sid)
        assert info is not None
        assert info.state == SessionState.NEEDS_INPUT
        assert info.process_state == ProcessState.LOOP_SLEEPING

    def test_get_nonexistent_session(self, tmp_path):
        db = tmp_path / "test.db"
        daemon = SupervisorDaemon(db_path=str(db))
        assert daemon.get_session_info("nonexistent") is None
        assert daemon.get_session("nonexistent") is None

    def test_stop_nonexistent_session_no_error(self, tmp_path):
        db = tmp_path / "test.db"
        daemon = SupervisorDaemon(db_path=str(db))
        daemon.stop_session("nonexistent")  # Should not raise

    def test_idle_timeout(self, tmp_path):
        db = tmp_path / "test.db"
        daemon = SupervisorDaemon(db_path=str(db), idle_timeout_minutes=0)
        sid = daemon.start_session("test", "/tmp")
        time.sleep(0.01)
        stopped = daemon.stop_idle_sessions()
        assert sid in stopped

    def test_pr_url(self, tmp_path):
        db = tmp_path / "test.db"
        daemon = SupervisorDaemon(db_path=str(db))
        sid = daemon.start_session("test", "/tmp")
        daemon.update_pr_url(sid, "https://github.com/user/repo/pull/1")
        info = daemon.get_session_info(sid)
        assert info is not None
        assert info.pr_url == "https://github.com/user/repo/pull/1"

    def test_persistence_across_restart(self, tmp_path):
        db = tmp_path / "test.db"
        daemon1 = SupervisorDaemon(db_path=str(db))
        sid = daemon1.start_session("persistent", "/tmp")

        daemon2 = SupervisorDaemon(db_path=str(db))
        info = daemon2.get_session_info(sid)
        assert info is not None
        assert info.name == "persistent"
