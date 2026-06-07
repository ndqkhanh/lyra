"""Tests for src/rmux/integration.py."""
from __future__ import annotations

import pytest

from lyra.rmux.integration import RmuxIntegration, TerminalSession, TerminalSessionStatus


class TestTerminalSession:
    """Tests for TerminalSession."""

    def test_default_status_created(self):
        """Default session status is CREATED."""
        session = TerminalSession(session_id="s1", name="test")
        assert session.status == TerminalSessionStatus.CREATED

    def test_default_command_empty(self):
        """Default command is empty string."""
        session = TerminalSession(session_id="s1", name="test")
        assert session.command == ""


class TestRmuxIntegration:
    """Tests for RmuxIntegration."""

    def test_create_session(self):
        """Create session returns a CREATED session."""
        rmux = RmuxIntegration()
        session = rmux.create_session("my-session")
        assert session.name == "my-session"
        assert session.status == TerminalSessionStatus.CREATED
        assert len(session.session_id) > 0

    def test_start_session(self):
        """Start changes status to RUNNING and adds a pane."""
        rmux = RmuxIntegration()
        session = rmux.create_session("test")
        assert rmux.start_session(session.session_id) is True
        updated = rmux.get_session(session.session_id)
        assert updated is not None
        assert updated.status == TerminalSessionStatus.RUNNING
        assert len(updated.panes) == 1

    def test_start_not_created_returns_false(self):
        """Starting a session that is already running returns False."""
        rmux = RmuxIntegration()
        session = rmux.create_session("test")
        rmux.start_session(session.session_id)
        assert rmux.start_session(session.session_id) is False

    def test_pause_and_resume(self):
        """Pause then resume transitions correctly."""
        rmux = RmuxIntegration()
        session = rmux.create_session("test")
        rmux.start_session(session.session_id)
        assert rmux.pause_session(session.session_id) is True
        assert rmux.get_session(session.session_id).status == TerminalSessionStatus.PAUSED
        assert rmux.resume_session(session.session_id) is True
        assert rmux.get_session(session.session_id).status == TerminalSessionStatus.RUNNING

    def test_terminate_session(self):
        """Terminate sets status to TERMINATED and clears panes."""
        rmux = RmuxIntegration()
        session = rmux.create_session("bye")
        rmux.start_session(session.session_id)
        assert rmux.terminate_session(session.session_id) is True
        terminated = rmux.get_session(session.session_id)
        assert terminated.status == TerminalSessionStatus.TERMINATED
        assert terminated.panes == []

    def test_send_command(self):
        """send_command records the command in metadata."""
        rmux = RmuxIntegration()
        session = rmux.create_session("cmd-test")
        rmux.start_session(session.session_id)
        assert rmux.send_command(session.session_id, "echo hello") is True
        updated = rmux.get_session(session.session_id)
        assert "echo hello" in updated.metadata["commands"]

    def test_send_command_not_running_returns_false(self):
        """send_command fails on non-running session."""
        rmux = RmuxIntegration()
        session = rmux.create_session("no-run")
        assert rmux.send_command(session.session_id, "ls") is False

    def test_split_and_kill_pane(self):
        """Split adds a pane, kill removes it."""
        rmux = RmuxIntegration()
        session = rmux.create_session("pane-test")
        rmux.start_session(session.session_id)
        new_pane = rmux.split_pane(session.session_id)
        assert new_pane is not None
        updated = rmux.get_session(session.session_id)
        assert len(updated.panes) == 2
        assert rmux.kill_pane(session.session_id, new_pane) is True
        assert len(rmux.get_session(session.session_id).panes) == 1

    def test_list_sessions_filtered(self):
        """list_sessions can filter by status."""
        rmux = RmuxIntegration()
        s1 = rmux.create_session("running-session")
        rmux.start_session(s1.session_id)
        s2 = rmux.create_session("created-session")
        running = rmux.list_sessions(TerminalSessionStatus.RUNNING)
        created = rmux.list_sessions(TerminalSessionStatus.CREATED)
        assert len(running) == 1
        assert len(created) == 1
