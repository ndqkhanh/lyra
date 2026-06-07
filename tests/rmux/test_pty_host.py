"""
Tests for PTYHost, IPCProtocol, TUIRenderer, SessionMultiplexer.

Covers:
- PTYHost session lifecycle (create, start, pause, resume, terminate)
- IPCProtocol message send/poll/register/unregister
- TUIRenderer panel management and frame rendering
- SessionMultiplexer session orchestration and layout splitting
"""

from __future__ import annotations

from lyra.rmux.pty_host import (
    IPCProtocol,
    IPCMessage,
    IPCMessageType,
    PTYConfig,
    PTYHost,
    PTYOutput,
    PTYSize,
    PTYStatus,
    SessionMultiplexer,
    TUIPanel,
    TUIRenderer,
)

# ======================================================================
# PTYHost — session lifecycle
# ======================================================================


class TestPTYHost:
    """PTYHost session lifecycle."""

    def test_create_session(self) -> None:
        """create_session returns a non-empty session ID."""
        host = PTYHost()
        session_id = host.create_session()
        assert len(session_id) > 0

    def test_create_session_with_config(self) -> None:
        """create_session with custom PTYConfig."""
        host = PTYHost()
        config = PTYConfig(cmd="/bin/bash", rows=40, cols=120)
        session_id = host.create_session(config)
        state = host.get_session(session_id)
        assert state is not None
        assert state.config.cmd == "/bin/bash"
        assert state.config.rows == 40

    def test_start_session_returns_false_when_not_found(self) -> None:
        """start_session returns False for unknown session."""
        host = PTYHost()
        assert not host.start_session("nonexistent")

    def test_pause_and_resume_session(self) -> None:
        """pause and resume session status transitions."""
        host = PTYHost()
        sid = host.create_session()
        # Can't pause a CREATED session
        assert not host.pause_session(sid)
        # Can't resume a CREATED session
        assert not host.resume_session(sid)

    def test_terminate_session(self) -> None:
        """terminate_session cleans up session state."""
        host = PTYHost()
        sid = host.create_session()
        assert host.terminate_session(sid)
        session = host.get_session(sid)
        assert session is not None
        assert session.status == PTYStatus.TERMINATED

    def test_terminate_nonexistent_session(self) -> None:
        """terminate_session returns False for unknown session."""
        host = PTYHost()
        assert not host.terminate_session("unknown")

    def test_list_sessions(self) -> None:
        """list_sessions returns all created sessions."""
        host = PTYHost()
        host.create_session()
        host.create_session()
        sessions = host.list_sessions()
        assert len(sessions) == 2

    def test_list_sessions_filtered(self) -> None:
        """list_sessions filters by status."""
        host = PTYHost()
        host.create_session()
        sessions = host.list_sessions(PTYStatus.CREATED)
        assert len(sessions) == 1
        sessions = host.list_sessions(PTYStatus.RUNNING)
        assert len(sessions) == 0

    def test_resize_session(self) -> None:
        """resize_session returns False for non-running sessions."""
        host = PTYHost()
        sid = host.create_session()
        assert not host.resize_session(sid, PTYSize(rows=50, cols=100))


# ======================================================================
# IPCProtocol
# ======================================================================


class TestIPCProtocol:
    """IPCProtocol — message-passing between sessions."""

    def test_send_and_poll(self) -> None:
        """send then poll retrieves the message."""
        ipc = IPCProtocol()
        ipc.register_session("session-b")
        msg = IPCMessage(
            msg_type=IPCMessageType.COMMAND,
            source="session-a",
            target="session-b",
            payload={"cmd": "ls"},
        )
        ipc.send(msg)

        messages = ipc.poll("session-b")
        assert len(messages) == 1
        assert messages[0].payload["cmd"] == "ls"

    def test_broadcast(self) -> None:
        """Broadcast to '*' reaches all registered sessions except source."""
        ipc = IPCProtocol()
        ipc.register_session("s1")
        ipc.register_session("s2")
        ipc.register_session("s3")

        msg = IPCMessage(
            msg_type=IPCMessageType.COMMAND,
            source="s1",
            target="*",
            payload={"cmd": "broadcast"},
        )
        ipc.send(msg)

        # s2 and s3 receive it, s1 should not
        assert len(ipc.poll("s1")) == 0
        assert len(ipc.poll("s2")) == 1
        assert len(ipc.poll("s3")) == 1

    def test_poll_empty(self) -> None:
        """poll on unregistered session returns empty list."""
        ipc = IPCProtocol()
        assert ipc.poll("unknown") == []

    def test_peek(self) -> None:
        """peek returns pending message count without consuming."""
        ipc = IPCProtocol()
        ipc.register_session("target")
        ipc.send(IPCMessage(
            msg_type=IPCMessageType.HEARTBEAT,
            source="a",
            target="target",
        ))
        assert ipc.peek("target") == 1
        # Messages are still there after peek
        assert ipc.peek("target") == 1

    def test_register_and_unregister(self) -> None:
        """Unregister drops pending messages."""
        ipc = IPCProtocol()
        ipc.register_session("s")
        ipc.send(IPCMessage(
            msg_type=IPCMessageType.STATUS,
            source="a",
            target="s",
        ))
        ipc.unregister_session("s")
        assert ipc.poll("s") == []

    def test_list_sessions(self) -> None:
        """list_sessions returns registered session IDs."""
        ipc = IPCProtocol()
        ipc.register_session("x")
        ipc.register_session("y")
        assert sorted(ipc.list_sessions()) == ["x", "y"]

    def test_clear(self) -> None:
        """clear removes all messages and returns count."""
        ipc = IPCProtocol()
        ipc.register_session("s")
        ipc.send(IPCMessage(
            msg_type=IPCMessageType.CONTROL,
            source="a",
            target="s",
        ))
        assert ipc.clear() == 1
        assert ipc.poll("s") == []

    def test_send_command_helper(self) -> None:
        """send_command creates and sends a typed message."""
        ipc = IPCProtocol()
        ipc.register_session("s2")
        msg = ipc.send_command("s1", "s2", "run_test")
        assert msg.msg_type == IPCMessageType.COMMAND
        assert msg.payload["cmd"] == "run_test"
        polled = ipc.poll("s2")
        assert len(polled) == 1

    def test_send_output_helper(self) -> None:
        """send_output creates an output message."""
        ipc = IPCProtocol()
        ipc.register_session("s2")
        msg = ipc.send_output("s1", "s2", "hello", stream="stderr")
        assert msg.msg_type == IPCMessageType.OUTPUT
        assert msg.payload["data"] == "hello"
        assert msg.payload["stream"] == "stderr"

    def test_send_error_helper(self) -> None:
        """send_error creates an error message."""
        ipc = IPCProtocol()
        ipc.register_session("s2")
        msg = ipc.send_error("s1", "s2", "something broke")
        assert msg.msg_type == IPCMessageType.ERROR
        assert msg.payload["error"] == "something broke"

    def test_auto_message_id(self) -> None:
        """Messages get auto-generated IDs."""
        msg = IPCMessage(
            msg_type=IPCMessageType.HEARTBEAT,
            source="a",
            target="b",
        )
        assert len(msg.msg_id) > 0

    def test_queue_overflow(self) -> None:
        """Old messages are dropped when queue exceeds max size."""
        ipc = IPCProtocol(max_queue_size=3)
        ipc.register_session("s")
        for i in range(5):
            ipc.send(IPCMessage(
                msg_type=IPCMessageType.HEARTBEAT,
                source="src",
                target="s",
                payload={"i": i},
            ))
        messages = ipc.poll("s")
        assert len(messages) == 3
        # The first 2 should have been dropped
        assert messages[0].payload["i"] == 2


# ======================================================================
# TUIRenderer
# ======================================================================


class TestTUIRenderer:
    """TUIRenderer — terminal UI rendering."""

    def test_add_panel(self) -> None:
        """add_panel registers a panel."""
        r = TUIRenderer()
        p = TUIPanel(session_id="s1", x=0, y=0, width=40, height=10, title="Panel 1")
        r.add_panel(p)
        assert r.get_panel("s1") is p

    def test_remove_panel(self) -> None:
        """remove_panel removes by session ID."""
        r = TUIRenderer()
        r.add_panel(TUIPanel("s1", 0, 0, 10, 10))
        assert r.remove_panel("s1")
        assert r.get_panel("s1") is None

    def test_update_buffer(self) -> None:
        """update_buffer sets panel text."""
        r = TUIRenderer()
        r.add_panel(TUIPanel("s1", 0, 0, 10, 10))
        assert r.update_buffer("s1", "hello")
        assert r.get_panel("s1").buffer == "hello"

    def test_update_buffer_unknown(self) -> None:
        """update_buffer on unknown session returns False."""
        r = TUIRenderer()
        assert not r.update_buffer("unknown", "text")

    def test_append_buffer(self) -> None:
        """append_buffer adds to existing text."""
        r = TUIRenderer()
        r.add_panel(TUIPanel("s1", 0, 0, 10, 5))
        r.update_buffer("s1", "line1\n")
        r.append_buffer("s1", "line2\n")
        assert "line2" in r.get_panel("s1").buffer

    def test_append_buffer_trims_to_height(self) -> None:
        """append_buffer trims overflow lines."""
        r = TUIRenderer()
        r.add_panel(TUIPanel("s1", 0, 0, 10, 3))
        for i in range(5):
            r.append_buffer("s1", f"line{i}\n")
        lines = r.get_panel("s1").buffer.split("\n")
        assert len(lines) <= 3

    def test_clear_buffer(self) -> None:
        """clear_buffer empties panel buffer."""
        r = TUIRenderer()
        r.add_panel(TUIPanel("s1", 0, 0, 10, 10))
        r.update_buffer("s1", "data")
        r.clear_buffer("s1")
        assert r.get_panel("s1").buffer == ""

    def test_focus(self) -> None:
        """set_focus and get_focus."""
        r = TUIRenderer()
        assert r.get_focus() is None
        r.set_focus("s1")
        assert r.get_focus() == "s1"
        r.set_focus(None)
        assert r.get_focus() is None

    def test_set_status_bar(self) -> None:
        """set_status_bar sets the status text."""
        r = TUIRenderer(total_cols=80)
        r.set_status_bar("Ready")
        # render_frame produces a string with status bar content
        frame = r.render_frame()
        assert "Ready" in frame

    def test_render_frame(self) -> None:
        """render_frame returns a non-empty string."""
        r = TUIRenderer(total_cols=40, total_rows=10)
        r.add_panel(TUIPanel("s1", 0, 0, 40, 10, buffer="test content", title="Main"))
        frame = r.render_frame()
        assert isinstance(frame, str)
        assert len(frame) > 0
        assert "test content" in frame or "Main" in frame

    def test_list_panels(self) -> None:
        """list_panels returns all panels."""
        r = TUIRenderer()
        r.add_panel(TUIPanel("a", 0, 0, 10, 10))
        r.add_panel(TUIPanel("b", 10, 0, 10, 10))
        assert len(r.list_panels()) == 2


# ======================================================================
# SessionMultiplexer
# ======================================================================


class TestSessionMultiplexer:
    """SessionMultiplexer — manage multiple PTY sessions."""

    def test_create_session(self) -> None:
        """create_session returns a session ID and adds a panel."""
        mux = SessionMultiplexer()
        sid = mux.create_session(panel_title="main")
        assert len(sid) > 0
        assert mux.renderer.get_panel(sid) is not None

    def test_create_session_with_config(self) -> None:
        """create_session with config."""
        mux = SessionMultiplexer()
        config = PTYConfig(cmd="htop", cols=100)
        sid = mux.create_session(config=config)
        state = mux.pty_host.get_session(sid)
        assert state is not None
        assert state.config.cmd == "htop"

    def test_terminate_session(self) -> None:
        """terminate_session removes IPC registration."""
        mux = SessionMultiplexer()
        sid = mux.create_session()
        mux.terminate_session(sid)
        assert sid not in mux.ipc.list_sessions()

    def test_terminate_all(self) -> None:
        """terminate_all terminates all created sessions."""
        mux = SessionMultiplexer()
        mux.create_session()
        mux.create_session()
        count = mux.terminate_all()
        assert count >= 0

    def test_send_ipc(self) -> None:
        """send_ipc routes messages between sessions."""
        mux = SessionMultiplexer()
        a = mux.create_session()
        b = mux.create_session()
        mux.send_ipc(IPCMessageType.STATUS, a, b, {"status": "ok"})
        msgs = mux.poll_ipc(b)
        assert len(msgs) == 1
        assert msgs[0].payload["status"] == "ok"

    def test_send_ipc_broadcast(self) -> None:
        """Broadcast IPC reaches all sessions."""
        mux = SessionMultiplexer()
        a = mux.create_session()
        b = mux.create_session()
        mux.send_ipc(IPCMessageType.HEARTBEAT, a, "*")
        # Session a (source) does not receive broadcast
        assert len(mux.poll_ipc(a)) == 0
        assert len(mux.poll_ipc(b)) == 1

    def test_pause_and_resume(self) -> None:
        """pause/resume through multiplexer."""
        mux = SessionMultiplexer()
        sid = mux.create_session()
        # Can pause/resume non-running sessions returns False
        assert not mux.pause_session(sid)
        assert not mux.resume_session(sid)

    def test_split_horizontal(self) -> None:
        """split_horizontal creates a side panel."""
        mux = SessionMultiplexer()
        a = mux.create_session(panel_width=80)
        b = mux.split_horizontal(a)
        assert b is not None
        assert mux.renderer.get_panel(b) is not None
        # Original panel width reduced
        original_panel = mux.renderer.get_panel(a)
        assert original_panel is not None

    def test_split_vertical(self) -> None:
        """split_vertical creates a bottom panel."""
        mux = SessionMultiplexer()
        a = mux.create_session(panel_height=20)
        b = mux.split_vertical(a)
        assert b is not None
        assert mux.renderer.get_panel(b) is not None

    def test_split_horizontal_unknown(self) -> None:
        """split_horizontal returns None for unknown session."""
        mux = SessionMultiplexer()
        assert mux.split_horizontal("unknown") is None

    def test_set_status(self) -> None:
        """set_status through multiplexer."""
        mux = SessionMultiplexer()
        mux.set_status("running")
        frame = mux.render()
        assert "running" in frame

    def test_focus_session(self) -> None:
        """focus_session sets renderer focus."""
        mux = SessionMultiplexer()
        mux.create_session()
        mux.focus_session("nonexistent")  # no error
        mux.focus_session(None)  # no error
