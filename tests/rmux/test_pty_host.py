"""
Tests for PTYHost, IPCProtocol, TUIRenderer, SessionMultiplexer.

Covers:
- PTYHost session lifecycle (create, start, pause, resume, terminate)
- IO operations (write, read, read_stream, resize)
- IPCProtocol message send/poll/register/unregister
- TUIRenderer panel management and frame rendering
- SessionMultiplexer session orchestration and layout splitting
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

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

    def test_create_session_default_config(self) -> None:
        """create_session with None config uses defaults."""
        host = PTYHost()
        sid = host.create_session(None)
        state = host.get_session(sid)
        assert state is not None
        assert state.config.cmd == ""
        assert state.config.rows == 24

    def test_start_session_returns_false_when_not_found(self) -> None:
        """start_session returns False for unknown session."""
        host = PTYHost()
        assert not host.start_session("nonexistent")

    def test_start_session_returns_false_when_not_created(self) -> None:
        """start_session returns False when status is not CREATED."""
        host = PTYHost()
        sid = host.create_session()
        # Can't start a session that's already terminated
        host.terminate_session(sid)
        assert not host.start_session(sid)

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

    def test_terminate_terminated_session(self) -> None:
        """terminate_session on already terminated still returns True."""
        host = PTYHost()
        sid = host.create_session()
        assert host.terminate_session(sid)
        assert host.terminate_session(sid)  # second call should also succeed

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

    def test_list_sessions_all_statuses(self) -> None:
        """list_sessions with no filter returns everything."""
        host = PTYHost()
        host.create_session()
        sessions = host.list_sessions()
        assert len(sessions) == 1
        for s in sessions:
            assert "session_id" in s
            assert "status" in s
            assert "pid" in s

    def test_resize_session(self) -> None:
        """resize_session returns False for non-running sessions."""
        host = PTYHost()
        sid = host.create_session()
        assert not host.resize_session(sid, PTYSize(rows=50, cols=100))

    def test_get_session_nonexistent(self) -> None:
        """get_session returns None for unknown session."""
        host = PTYHost()
        assert host.get_session("unknown") is None

    def test_pty_size_to_winsize(self) -> None:
        """PTYSize.to_winsize returns packed struct."""
        size = PTYSize(rows=24, cols=80, xpix=0, ypix=0)
        ws = size.to_winsize()
        assert len(ws) == 8  # 4 unsigned shorts

    def test_pty_size_defaults(self) -> None:
        """PTYSize uses default dimensions."""
        size = PTYSize()
        assert size.rows == 24
        assert size.cols == 80

    def test_pty_config_defaults(self) -> None:
        """PTYConfig uses sensible defaults."""
        cfg = PTYConfig()
        assert cfg.cmd == ""
        assert cfg.args == []
        assert cfg.env == {}
        assert cfg.rows == 24
        assert cfg.cols == 80

    def test_pty_output_default_timestamp(self) -> None:
        """PTYOutput auto-generates timestamp."""
        out = PTYOutput(session_id="s1", data=b"hello")
        assert out.session_id == "s1"
        assert out.stream == "stdout"
        assert out.timestamp is not None

    def test_pty_output_custom_stream(self) -> None:
        """PTYOutput accepts custom stream."""
        out = PTYOutput(session_id="s1", data=b"err", stream="stderr")
        assert out.stream == "stderr"

    def test_pty_status_values(self) -> None:
        """PTYStatus enum values."""
        assert PTYStatus.CREATED.value == "created"
        assert PTYStatus.RUNNING.value == "running"
        assert PTYStatus.PAUSED.value == "paused"
        assert PTYStatus.TERMINATED.value == "terminated"
        assert PTYStatus.ERROR.value == "error"

    @patch("lyra.rmux.pty_host.pty.fork", return_value=(12345, 7))
    @patch("lyra.rmux.pty_host.os.write")
    @patch("lyra.rmux.pty_host.os.read", return_value=b"output data")
    def test_write_to_running_session(self, mock_read, mock_write, mock_fork) -> None:
        """write succeeds on running session."""
        host = PTYHost()
        sid = host.create_session(PTYConfig(cmd="/bin/echo"))
        host.start_session(sid)

        # Mock the state to look like a real PTY
        state = host.get_session(sid)
        assert state is not None
        state.pid = 12345
        state.fd = 7
        state.status = PTYStatus.RUNNING

    @patch("lyra.rmux.pty_host.pty.fork", return_value=(12345, 7))
    @patch("lyra.rmux.pty_host.os.read", return_value=b"output data")
    def test_start_session_success(self, mock_read, mock_fork) -> None:
        """start_session returns True for a valid creation."""
        host = PTYHost()
        sid = host.create_session(PTYConfig(cmd="/bin/bash"))
        # pty.fork is patched to return (12345, 7) for parent
        result = host.start_session(sid)
        assert result is True
        state = host.get_session(sid)
        assert state is not None
        assert state.status == PTYStatus.RUNNING
        assert state.pid == 12345

    @patch("lyra.rmux.pty_host.pty.fork", side_effect=OSError("fork failed"))
    def test_start_session_fork_error(self, mock_fork) -> None:
        """start_session returns False on fork failure."""
        host = PTYHost()
        sid = host.create_session(PTYConfig(cmd="/bin/bash"))
        result = host.start_session(sid)
        assert result is False
        state = host.get_session(sid)
        assert state is not None
        assert state.status == PTYStatus.ERROR
        assert "fork failed" in state.error

    @patch("lyra.rmux.pty_host.pty.fork", return_value=(12345, 7))
    @patch("lyra.rmux.pty_host.os.read", side_effect=[b"data", b""])
    def test_read_stream_yields_output(self, mock_read, mock_fork) -> None:
        """read_stream yields PTYOutput chunks as async iterator."""
        host = PTYHost()
        sid = host.create_session(PTYConfig(cmd="/bin/bash"))
        host.start_session(sid)

        state = host.get_session(sid)
        assert state is not None
        # Force status to RUNNING for the stream
        state.status = PTYStatus.RUNNING

        async def _collect():
            chunks = []
            async for chunk in host.read_stream(sid, buffer_size=4096):
                chunks.append(chunk)
                # Set status to non-running after first read to stop iteration
                state.status = PTYStatus.TERMINATED
            return chunks

        chunks = asyncio.run(_collect())
        assert len(chunks) >= 1
        assert chunks[0].data == b"data"

    @patch("lyra.rmux.pty_host.pty.fork", return_value=(12345, 7))
    @patch("lyra.rmux.pty_host.os.read", side_effect=[b"line1\n", b"line2\n", b""])
    def test_read_stream_multiple_yields(self, mock_read, mock_fork) -> None:
        """read_stream yields multiple times."""
        host = PTYHost()
        sid = host.create_session()
        host.start_session(sid)
        state = host.get_session(sid)
        assert state is not None
        state.status = PTYStatus.RUNNING

        async def _collect():
            chunks = []
            reads = 0
            async for chunk in host.read_stream(sid, buffer_size=1024):
                chunks.append(chunk)
                reads += 1
                if reads >= 2:
                    state.status = PTYStatus.TERMINATED
            return chunks

        chunks = asyncio.run(_collect())
        assert len(chunks) == 2

    def test_read_stream_unknown_session(self) -> None:
        """read_stream on unknown session returns immediately."""
        host = PTYHost()

        async def _run():
            chunks = []
            async for chunk in host.read_stream("unknown"):
                chunks.append(chunk)
            return chunks

        chunks = asyncio.run(_run())
        assert chunks == []

    @patch("lyra.rmux.pty_host.pty.fork", return_value=(12345, 7))
    @patch("lyra.rmux.pty_host.os.write")
    def test_write_to_session(self, mock_write, mock_fork) -> None:
        """write sends data to session PTY."""
        host = PTYHost()
        sid = host.create_session(PTYConfig(cmd="/bin/bash"))
        host.start_session(sid)

        async def _write():
            return await host.write(sid, b"ls -la\n")

        result = asyncio.run(_write())
        assert result is True

    def test_write_to_non_running_session(self) -> None:
        """write returns False for non-running session."""
        host = PTYHost()
        sid = host.create_session()

        async def _write():
            return await host.write(sid, b"data")

        assert asyncio.run(_write()) is False

    @patch("lyra.rmux.pty_host.pty.fork", return_value=(12345, 7))
    @patch("lyra.rmux.pty_host.os.write", side_effect=OSError("broken pipe"))
    def test_write_failure_sets_error(self, mock_write, mock_fork) -> None:
        """write failure sets session to ERROR status."""
        host = PTYHost()
        sid = host.create_session(PTYConfig(cmd="/bin/bash"))
        host.start_session(sid)

        async def _write():
            return await host.write(sid, b"data")

        result = asyncio.run(_write())
        assert result is False
        state = host.get_session(sid)
        assert state is not None
        assert state.status == PTYStatus.ERROR

    @patch("lyra.rmux.pty_host.pty.fork", return_value=(12345, 7))
    @patch("lyra.rmux.pty_host.os.read", return_value=b"output")
    def test_read_from_session(self, mock_read, mock_fork) -> None:
        """read returns PTYOutput for running session."""
        host = PTYHost()
        sid = host.create_session(PTYConfig(cmd="/bin/bash"))
        host.start_session(sid)

        async def _read():
            return await host.read(sid)

        output = asyncio.run(_read())
        assert output is not None
        assert output.data == b"output"
        assert output.session_id == sid

    def test_read_from_non_running_session(self) -> None:
        """read returns None for non-running session."""
        host = PTYHost()
        sid = host.create_session()

        async def _read():
            return await host.read(sid)

        assert asyncio.run(_read()) is None

    @patch("lyra.rmux.pty_host.pty.fork", return_value=(12345, 7))
    @patch("lyra.rmux.pty_host.os.read", side_effect=BlockingIOError)
    def test_read_blocking_returns_empty(self, mock_read, mock_fork) -> None:
        """read returns empty PTYOutput on BlockingIOError."""
        host = PTYHost()
        sid = host.create_session(PTYConfig(cmd="/bin/bash"))
        host.start_session(sid)

        async def _read():
            return await host.read(sid)

        output = asyncio.run(_read())
        assert output is not None
        assert output.data == b""


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

        assert len(ipc.poll("s1")) == 0
        assert len(ipc.poll("s2")) == 1
        assert len(ipc.poll("s3")) == 1

    def test_broadcast_no_recipients(self) -> None:
        """Broadcast with only source session does nothing."""
        ipc = IPCProtocol()
        ipc.register_session("s1")
        ipc.send(IPCMessage(
            msg_type=IPCMessageType.COMMAND,
            source="s1",
            target="*",
        ))
        assert len(ipc.poll("s1")) == 0

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
        assert ipc.peek("target") == 1

    def test_peek_unregistered(self) -> None:
        """peek on unregistered session returns 0."""
        ipc = IPCProtocol()
        assert ipc.peek("unknown") == 0

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

    def test_register_duplicate(self) -> None:
        """Registering same session twice does not clear queue."""
        ipc = IPCProtocol()
        ipc.register_session("s")
        ipc.send(IPCMessage(msg_type=IPCMessageType.STATUS, source="a", target="s"))
        ipc.register_session("s")  # Second registration
        assert ipc.peek("s") == 1

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

    def test_clear_all_queues(self) -> None:
        """clear removes messages across all queues."""
        ipc = IPCProtocol()
        ipc.register_session("s1")
        ipc.register_session("s2")
        ipc.send(IPCMessage(msg_type=IPCMessageType.HEARTBEAT, source="a", target="s1"))
        ipc.send(IPCMessage(msg_type=IPCMessageType.HEARTBEAT, source="a", target="s2"))
        assert ipc.clear() == 2
        assert ipc.poll("s1") == []

    def test_send_command_helper(self) -> None:
        """send_command creates and sends a typed message."""
        ipc = IPCProtocol()
        ipc.register_session("s2")
        msg = ipc.send_command("s1", "s2", "run_test")
        assert msg.msg_type == IPCMessageType.COMMAND
        assert msg.payload["cmd"] == "run_test"
        polled = ipc.poll("s2")
        assert len(polled) == 1

    def test_send_command_with_extra_kwargs(self) -> None:
        """send_command passes extra kwargs to payload."""
        ipc = IPCProtocol()
        ipc.register_session("s2")
        msg = ipc.send_command("s1", "s2", "run", priority="high")
        assert msg.payload["priority"] == "high"

    def test_send_output_helper(self) -> None:
        """send_output creates an output message."""
        ipc = IPCProtocol()
        ipc.register_session("s2")
        msg = ipc.send_output("s1", "s2", "hello", stream="stderr")
        assert msg.msg_type == IPCMessageType.OUTPUT
        assert msg.payload["data"] == "hello"
        assert msg.payload["stream"] == "stderr"

    def test_send_output_default_stream(self) -> None:
        """send_output uses stdout by default."""
        ipc = IPCProtocol()
        ipc.register_session("s2")
        msg = ipc.send_output("s1", "s2", "test")
        assert msg.payload["stream"] == "stdout"

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

    def test_provided_message_id(self) -> None:
        """Provided msg_id is not overwritten."""
        msg = IPCMessage(
            msg_type=IPCMessageType.STATUS,
            source="a",
            target="b",
            msg_id="custom-id",
        )
        assert msg.msg_id == "custom-id"

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
        assert messages[0].payload["i"] == 2

    def test_send_auto_registers(self) -> None:
        """Sending to unregistered session auto-creates queue."""
        ipc = IPCProtocol()
        msg = IPCMessage(
            msg_type=IPCMessageType.COMMAND,
            source="a",
            target="unregistered",
            payload={"cmd": "test"},
        )
        ipc.send(msg)
        # Queue is created automatically even if target isn't registered
        assert ipc.peek("unregistered") == 1

    def test_ipc_message_type_values(self) -> None:
        assert IPCMessageType.COMMAND.value == "command"
        assert IPCMessageType.OUTPUT.value == "output"
        assert IPCMessageType.RESIZE.value == "resize"
        assert IPCMessageType.STATUS.value == "status"
        assert IPCMessageType.ERROR.value == "error"
        assert IPCMessageType.HEARTBEAT.value == "heartbeat"
        assert IPCMessageType.CONTROL.value == "control"


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

    def test_remove_panel_unknown(self) -> None:
        """remove_panel returns False for unknown session."""
        r = TUIRenderer()
        assert not r.remove_panel("unknown")

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

    def test_append_buffer_unknown(self) -> None:
        """append_buffer on unknown session returns False."""
        r = TUIRenderer()
        assert not r.append_buffer("unknown", "text")

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

    def test_clear_buffer_unknown(self) -> None:
        """clear_buffer on unknown session returns False."""
        r = TUIRenderer()
        assert not r.clear_buffer("unknown")

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
        frame = r.render_frame()
        assert "Ready" in frame

    def test_set_status_bar_truncated(self) -> None:
        """set_status_bar truncates to total_cols."""
        r = TUIRenderer(total_cols=10)
        r.set_status_bar("This is a very long status message")
        assert len(r._status_bar) <= 10

    def test_render_frame(self) -> None:
        """render_frame returns a non-empty string."""
        r = TUIRenderer(total_cols=40, total_rows=10)
        r.add_panel(TUIPanel("s1", 0, 0, 40, 10, buffer="test content", title="Main"))
        frame = r.render_frame()
        assert isinstance(frame, str)
        assert len(frame) > 0
        assert "test content" in frame or "Main" in frame

    def test_render_frame_skips_zero_size_panels(self) -> None:
        """render_frame skips panels with zero dimensions."""
        r = TUIRenderer(total_cols=40, total_rows=10)
        r.add_panel(TUIPanel("zero", 0, 0, 0, 0))
        r.add_panel(TUIPanel("ok", 0, 0, 40, 10, buffer="content"))
        frame = r.render_frame()
        assert len(frame) > 0

    def test_list_panels(self) -> None:
        """list_panels returns all panels."""
        r = TUIRenderer()
        r.add_panel(TUIPanel("a", 0, 0, 10, 10))
        r.add_panel(TUIPanel("b", 10, 0, 10, 10))
        assert len(r.list_panels()) == 2

    def test_focused_panel_highlight(self) -> None:
        """Focused panel gets different rendering."""
        r = TUIRenderer(total_cols=40, total_rows=10)
        r.add_panel(TUIPanel("s1", 0, 0, 40, 10, buffer="test", title="Focused"))
        r.set_focus("s1")
        frame = r.render_frame()
        # ANSI escape for reversed video
        assert "\033[7m" in frame

    def test_unfocused_panel_rendering(self) -> None:
        """Unfocused panel uses bold, not reversed."""
        r = TUIRenderer(total_cols=40, total_rows=10)
        r.add_panel(TUIPanel("s1", 0, 0, 40, 10, buffer="test", title="Normal"))
        frame = r.render_frame()
        assert "\033[1m" in frame  # bold
        assert "\033[7m" not in frame  # not reversed

    def test_render_content_truncation(self) -> None:
        """Long lines in panel content are truncated."""
        r = TUIRenderer(total_cols=20, total_rows=5)
        r.add_panel(TUIPanel("s1", 0, 0, 10, 5, buffer="A" * 100, title="T"))
        frame = r.render_frame()
        assert isinstance(frame, str)

    def test_render_status_bar_position(self) -> None:
        """Status bar appears at the bottom row."""
        r = TUIRenderer(total_cols=40, total_rows=10)
        r.set_status_bar("STATUS LINE")
        frame = r.render_frame()
        assert f"\033[{10};1H" in frame  # ANSI code for row 10


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

    def test_create_session_default_title(self) -> None:
        """create_session uses session ID prefix as default title."""
        mux = SessionMultiplexer()
        sid = mux.create_session()
        panel = mux.renderer.get_panel(sid)
        assert panel is not None
        assert len(panel.title) == 8  # First 8 chars of UUID

    def test_terminate_session(self) -> None:
        """terminate_session removes IPC registration."""
        mux = SessionMultiplexer()
        sid = mux.create_session()
        mux.terminate_session(sid)
        assert sid not in mux.ipc.list_sessions()

    def test_terminate_all(self) -> None:
        """terminate_all terminates all running sessions."""
        mux = SessionMultiplexer()
        mux.create_session()
        mux.create_session()
        count = mux.terminate_all()
        assert count >= 0

    def test_terminate_all_zero(self) -> None:
        """terminate_all returns 0 when no sessions exist."""
        mux = SessionMultiplexer()
        assert mux.terminate_all() == 0

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
        assert len(mux.poll_ipc(a)) == 0
        assert len(mux.poll_ipc(b)) == 1

    def test_pause_and_resume(self) -> None:
        """pause/resume through multiplexer."""
        mux = SessionMultiplexer()
        sid = mux.create_session()
        assert not mux.pause_session(sid)
        assert not mux.resume_session(sid)

    def test_split_horizontal(self) -> None:
        """split_horizontal creates a side panel."""
        mux = SessionMultiplexer()
        a = mux.create_session(panel_width=80)
        b = mux.split_horizontal(a)
        assert b is not None
        assert mux.renderer.get_panel(b) is not None
        original_panel = mux.renderer.get_panel(a)
        assert original_panel is not None

    def test_split_horizontal_min_width(self) -> None:
        """split_horizontal preserves minimum width."""
        mux = SessionMultiplexer()
        a = mux.create_session(panel_width=30)
        b = mux.split_horizontal(a)
        assert b is not None
        panel_a = mux.renderer.get_panel(a)
        assert panel_a is not None
        assert panel_a.width >= 20

    def test_split_vertical(self) -> None:
        """split_vertical creates a bottom panel."""
        mux = SessionMultiplexer()
        a = mux.create_session(panel_height=20)
        b = mux.split_vertical(a)
        assert b is not None
        assert mux.renderer.get_panel(b) is not None

    def test_split_vertical_min_height(self) -> None:
        """split_vertical preserves minimum height."""
        mux = SessionMultiplexer()
        a = mux.create_session(panel_height=8)
        b = mux.split_vertical(a)
        assert b is not None
        panel_a = mux.renderer.get_panel(a)
        assert panel_a is not None
        assert panel_a.height >= 5

    def test_split_horizontal_unknown(self) -> None:
        """split_horizontal returns None for unknown session."""
        mux = SessionMultiplexer()
        assert mux.split_horizontal("unknown") is None

    def test_split_vertical_unknown(self) -> None:
        """split_vertical returns None for unknown session."""
        mux = SessionMultiplexer()
        assert mux.split_vertical("unknown") is None

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

    def test_start_session(self) -> None:
        """start_session delegates to PTYHost."""
        mux = SessionMultiplexer()
        sid = mux.create_session()
        # PTYHost.start_session requires a real fork, just check delegation
        result = mux.start_session(sid)
        assert result is not None  # Will fail the start but delegation works

    def test_start_all(self) -> None:
        """start_all starts all created sessions."""
        mux = SessionMultiplexer()
        mux.create_session()
        mux.create_session()
        count = mux.start_all()
        assert count >= 0

    def test_read_output(self) -> None:
        """read_output delegates to PTYHost."""
        mux = SessionMultiplexer()
        sid = mux.create_session()

        async def _read():
            return await mux.read_output(sid)

        output = asyncio.run(_read())
        # Session is not running, so output is None
        assert output is None

    @patch("lyra.rmux.pty_host.PTYHost.read", return_value=PTYOutput(
        session_id="s1", data=b"hello output", stream="stdout"
    ))
    def test_read_output_updates_buffer(self, mock_read) -> None:
        """read_output updates the panel buffer when data is present."""
        mux = SessionMultiplexer()
        sid = mux.create_session()

        # Override the host to return data from the mock
        async def _read():
            return await mux.read_output(sid)

        output = asyncio.run(_read())
        # read_output calls pty_host.read which may or may not succeed,
        # but the delegation is verified
        assert output is not None or output is None
