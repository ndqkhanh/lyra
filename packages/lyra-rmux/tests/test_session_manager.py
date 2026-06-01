"""Tests for lyra_rmux.session_manager."""

from types import SimpleNamespace

import pytest
from unittest.mock import MagicMock, patch, call

from lyra_rmux.session_manager import SessionManager
from lyra_rmux.models import SessionState, PaneState


@pytest.fixture
def mock_pty() -> MagicMock:
    pty = MagicMock()
    proc = SimpleNamespace(
        pid=42, fd=7, command=("/bin/sh", "-i"), cwd="/tmp", exit_code=None
    )
    pty.spawn.return_value = proc
    return pty


@pytest.fixture
def sm(mock_pty: MagicMock) -> SessionManager:
    return SessionManager(pty_manager=mock_pty)


# ------------------------------------------------------------------
# create_session
# ------------------------------------------------------------------


def test_create_session(sm: SessionManager) -> None:
    sess = sm.create_session(name="test-session")
    assert sess.name == "test-session"
    assert sess.state == SessionState.RUNNING
    assert len(sess.windows) == 1
    assert len(sess.windows[0].panes) == 1
    pane = sess.windows[0].panes[0]
    assert pane.state == PaneState.RUNNING
    assert pane.process is not None
    assert pane.process.pid == 42


def test_create_session_default_name(sm: SessionManager) -> None:
    sess = sm.create_session()
    assert sess.name.startswith("sess-")


def test_create_session_custom_geometry(sm: SessionManager) -> None:
    sess = sm.create_session(rows=50, cols=120)
    pane = sess.windows[0].panes[0]
    assert pane.rows == 50
    assert pane.cols == 120


# ------------------------------------------------------------------
# attach / detach
# ------------------------------------------------------------------


def test_attach_session(sm: SessionManager) -> None:
    sess = sm.create_session(name="att")
    attached = sm.attach_session(sess.session_id)
    assert attached is not None
    assert attached.state == SessionState.ATTACHED


def test_attach_unknown(sm: SessionManager) -> None:
    assert sm.attach_session("nonexistent") is None


def test_detach_session(sm: SessionManager) -> None:
    sess = sm.create_session(name="det")
    sm.attach_session(sess.session_id)
    detached = sm.detach_session(sess.session_id)
    assert detached is not None
    assert detached.state == SessionState.DETACHED


# ------------------------------------------------------------------
# kill_session
# ------------------------------------------------------------------


def test_kill_session(sm: SessionManager) -> None:
    sess = sm.create_session()
    sm.kill_session(sess.session_id)
    assert sm.get_session(sess.session_id) is None


def test_kill_session_unknown(sm: SessionManager) -> None:
    sm.kill_session("nonexistent")  # should not raise


# ------------------------------------------------------------------
# list_sessions
# ------------------------------------------------------------------


def test_list_sessions_empty(sm: SessionManager) -> None:
    assert sm.list_sessions() == []


def test_list_sessions(sm: SessionManager) -> None:
    sm.create_session(name="a")
    sm.create_session(name="b")
    assert len(sm.list_sessions()) == 2


# ------------------------------------------------------------------
# get_session
# ------------------------------------------------------------------


def test_get_session_unknown(sm: SessionManager) -> None:
    assert sm.get_session("x") is None


def test_get_session(sm: SessionManager) -> None:
    sess = sm.create_session(name="getme")
    assert sm.get_session(sess.session_id) is not None


# ------------------------------------------------------------------
# split_pane
# ------------------------------------------------------------------


def test_split_pane(sm: SessionManager) -> None:
    sess = sm.create_session()
    new_pane = sm.split_pane(sess.session_id)
    assert new_pane is not None
    assert new_pane.state == PaneState.RUNNING
    # session should now have 2 panes in the window
    updated = sm.get_session(sess.session_id)
    assert updated is not None
    assert len(updated.windows[0].panes) == 2


def test_split_pane_unknown_session(sm: SessionManager) -> None:
    assert sm.split_pane("unknown") is None


def test_split_pane_unknown_window(sm: SessionManager) -> None:
    sess = sm.create_session()
    assert sm.split_pane(sess.session_id, window_id="unknown") is None


# ------------------------------------------------------------------
# send_keys
# ------------------------------------------------------------------


def test_send_keys(sm: SessionManager, mock_pty: MagicMock) -> None:
    sess = sm.create_session()
    ok = sm.send_keys(sess.session_id, "echo hello")
    assert ok is True
    # pty.write should have been called
    assert mock_pty.write.called


def test_send_keys_unknown(sm: SessionManager) -> None:
    assert sm.send_keys("unknown", "data") is False


# ------------------------------------------------------------------
# send_bytes
# ------------------------------------------------------------------


def test_send_bytes(sm: SessionManager, mock_pty: MagicMock) -> None:
    sess = sm.create_session()
    ok = sm.send_bytes(sess.session_id, b"echo hello\n")
    assert ok is True


# ------------------------------------------------------------------
# get_snapshot
# ------------------------------------------------------------------


def test_get_snapshot(sm: SessionManager, mock_pty: MagicMock) -> None:
    mock_pty.read_all_buffered.return_value = b"line1\nline2\n"
    sess = sm.create_session()
    snap = sm.get_snapshot(sess.session_id)
    assert snap is not None
    assert len(snap.lines) >= 2


def test_get_snapshot_unknown(sm: SessionManager) -> None:
    assert sm.get_snapshot("unknown") is None


# ------------------------------------------------------------------
# resize_pane
# ------------------------------------------------------------------


def test_resize_pane(sm: SessionManager, mock_pty: MagicMock) -> None:
    sess = sm.create_session()
    ok = sm.resize_pane(sess.session_id, 50, 120)
    assert ok is True
    mock_pty.resize.assert_called()


def test_resize_pane_unknown(sm: SessionManager) -> None:
    assert sm.resize_pane("unknown", 50, 120) is False


# ------------------------------------------------------------------
# kill_pane
# ------------------------------------------------------------------


def test_kill_pane(sm: SessionManager, mock_pty: MagicMock) -> None:
    sess = sm.create_session()
    pane_id = sess.windows[0].panes[0].pane_id
    ok = sm.kill_pane(sess.session_id, pane_id=pane_id)
    assert ok is True
    # session should be removed since it had only one pane
    assert sm.get_session(sess.session_id) is None


def test_kill_pane_unknown(sm: SessionManager) -> None:
    assert sm.kill_pane("unknown") is False
