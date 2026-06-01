"""Tests for lyra_rmux.models."""

import json
import pytest
from lyra_rmux.models import (
    SessionState,
    PaneState,
    PtyProcess,
    Pane,
    Window,
    Session,
    Snapshot,
    IpcMessage,
    IpcResponse,
)


class TestEnums:
    def test_session_state_values(self) -> None:
        assert SessionState.CREATED.value == "created"
        assert SessionState.RUNNING.value == "running"
        assert SessionState.ATTACHED.value == "attached"
        assert SessionState.DETACHED.value == "detached"
        assert SessionState.CLOSED.value == "closed"

    def test_pane_state_values(self) -> None:
        assert PaneState.CREATED.value == "created"
        assert PaneState.RUNNING.value == "running"
        assert PaneState.CLOSED.value == "closed"


class TestPtyProcess:
    def test_create_frozen(self) -> None:
        p = PtyProcess(pid=100, fd=3, command=("/bin/sh", "-i"), cwd="/tmp")
        assert p.pid == 100
        assert p.fd == 3
        assert p.command == ("/bin/sh", "-i")
        assert p.cwd == "/tmp"
        assert p.exit_code is None

    def test_with_exit_code(self) -> None:
        p = PtyProcess(pid=101, fd=4, command=("/bin/ls",), cwd="/", exit_code=0)
        assert p.exit_code == 0

    def test_immutable(self) -> None:
        p = PtyProcess(pid=1, fd=5, command=("cat",), cwd="/tmp")
        with pytest.raises((AttributeError, TypeError)):
            p.pid = 99  # type: ignore[misc]


class TestPane:
    def test_defaults(self) -> None:
        pane = Pane()
        assert pane.pane_id.startswith("pane-")
        assert pane.state == PaneState.CREATED
        assert pane.rows == 24
        assert pane.cols == 80
        assert pane.x == 0
        assert pane.y == 0
        assert pane.process is None

    def test_with_process(self) -> None:
        proc = PtyProcess(pid=200, fd=6, command=("/bin/zsh",), cwd="/home")
        pane = Pane(pane_id="pane-abc", state=PaneState.RUNNING, process=proc)
        assert pane.pane_id == "pane-abc"
        assert pane.state == PaneState.RUNNING
        assert pane.process is not None
        assert pane.process.pid == 200

    def test_custom_geometry(self) -> None:
        pane = Pane(rows=50, cols=120, x=10, y=5)
        assert pane.rows == 50
        assert pane.cols == 120
        assert pane.x == 10
        assert pane.y == 5


class TestWindow:
    def test_defaults(self) -> None:
        win = Window()
        assert win.window_id.startswith("win-")
        assert win.name == "default"
        assert win.panes == ()

    def test_with_panes(self) -> None:
        p1 = Pane(pane_id="p1")
        p2 = Pane(pane_id="p2")
        win = Window(window_id="win-1", name="editor", panes=(p1, p2))
        assert len(win.panes) == 2
        assert win.panes[0].pane_id == "p1"
        assert win.panes[1].pane_id == "p2"

    def test_immutable_tuple(self) -> None:
        win = Window(panes=(Pane(),))
        with pytest.raises((AttributeError, TypeError)):
            win.panes = ()  # type: ignore[misc]


class TestSession:
    def test_defaults(self) -> None:
        sess = Session()
        assert sess.session_id.startswith("sess-")
        assert sess.name == ""
        assert sess.state == SessionState.CREATED
        assert sess.windows == ()

    def test_with_windows(self) -> None:
        win = Window(window_id="w1", name="main")
        sess = Session(session_id="sess-1", name="test", state=SessionState.RUNNING, windows=(win,))
        assert sess.session_id == "sess-1"
        assert sess.name == "test"
        assert sess.state == SessionState.RUNNING
        assert len(sess.windows) == 1

    def test_state_transition(self) -> None:
        sess = Session(state=SessionState.CREATED)
        assert sess.state == SessionState.CREATED


class TestSnapshot:
    def test_defaults(self) -> None:
        snap = Snapshot(pane_id="pane-1")
        assert snap.pane_id == "pane-1"
        assert snap.lines == ()
        assert snap.cursor_row == 0
        assert snap.cursor_col == 0

    def test_with_lines(self) -> None:
        lines = ("line1", "line2", "line3")
        snap = Snapshot(pane_id="pane-2", lines=lines, cursor_row=2, cursor_col=5)
        assert len(snap.lines) == 3
        assert snap.cursor_row == 2
        assert snap.cursor_col == 5

    def test_immutable_lines(self) -> None:
        snap = Snapshot(pane_id="p", lines=("a", "b"))
        with pytest.raises((AttributeError, TypeError)):
            snap.lines = ()  # type: ignore[misc]


class TestIpcMessage:
    def test_defaults(self) -> None:
        msg = IpcMessage(method="ping")
        assert msg.method == "ping"
        assert msg.params == {}
        assert len(msg.msg_id) == 32  # uuid hex

    def test_with_params(self) -> None:
        msg = IpcMessage(method="create_session", params={"name": "test", "rows": 24})
        assert msg.params["name"] == "test"
        assert msg.params["rows"] == 24


class TestIpcResponse:
    def test_success_default(self) -> None:
        resp = IpcResponse(msg_id="abc")
        assert resp.msg_id == "abc"
        assert resp.success is True
        assert resp.result is None
        assert resp.error is None

    def test_error(self) -> None:
        resp = IpcResponse(msg_id="def", success=False, error="Something broke")
        assert resp.success is False
        assert resp.error == "Something broke"

    def test_with_result(self) -> None:
        resp = IpcResponse(msg_id="ghi", result={"key": "value"})
        assert resp.result == {"key": "value"}
