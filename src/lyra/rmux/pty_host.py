"""
Pseudo-terminal (PTY) hosting for multiplexed sessions.

Provides ``PTYHost`` for creating and managing PTY subprocesses,
``IPCProtocol`` for message-passing between PTY sessions,
``TUIRenderer`` for terminal UI rendering of multiplexed views, and
``SessionMultiplexer`` for managing multiple concurrent PTY sessions.

Classes
-------
PTYConfig:
    Configuration for a PTY session.
PTYSize:
    Terminal dimensions (rows, cols).
PTYOutput:
    Captured output from a PTY session.
PTYHost:
    Pseudo-terminal hosting for multiplexed sessions.
IPCProtocol:
    Message-passing between PTY sessions.
IPCMessage:
    A single IPC message.
TUIRenderer:
    Terminal UI rendering for multiplexed view.
SessionMultiplexer:
    Manage multiple PTY sessions concurrently.
"""

from __future__ import annotations

import asyncio
import logging
import os
import pty
import signal
import struct
import termios
import time
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Enums and data classes
# ---------------------------------------------------------------------------


class PTYStatus(str, Enum):
    """Status of a PTY session."""

    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    TERMINATED = "terminated"
    ERROR = "error"


@dataclass
class PTYConfig:
    """Configuration for a PTY session.

    Attributes
    ----------
    cmd:
        Command to run (default: shell).
    args:
        Command arguments.
    cwd:
        Working directory for the PTY process.
    env:
        Additional environment variables.
    rows:
        Terminal height in rows (default 24).
    cols:
        Terminal width in columns (default 80).
    """

    cmd: str = ""
    args: list[str] = field(default_factory=list)
    cwd: str = ""
    env: dict[str, str] = field(default_factory=dict)
    rows: int = 24
    cols: int = 80


@dataclass
class PTYSize:
    """Terminal dimensions.

    Attributes
    ----------
    rows:
        Number of rows.
    cols:
        Number of columns.
    xpix:
        Pixel width (optional, default 0).
    ypix:
        Pixel height (optional, default 0).
    """

    rows: int = 24
    cols: int = 80
    xpix: int = 0
    ypix: int = 0

    def to_winsize(self) -> bytes:
        """Encode as ``termios`` winsize struct (4 unsigned shorts)."""
        return struct.pack("HHHH", self.rows, self.cols, self.xpix, self.ypix)


@dataclass
class PTYOutput:
    """Captured output from a PTY session.

    Attributes
    ----------
    session_id:
        Session identifier.
    data:
        Raw bytes output.
    timestamp:
        When the output was captured.
    stream:
        Stream name (``"stdout"`` or ``"stderr"``).
    """

    session_id: str
    data: bytes
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    stream: str = "stdout"


# ---------------------------------------------------------------------------
# PTYHost
# ---------------------------------------------------------------------------


class PTYHost:
    """Pseudo-terminal hosting for multiplexed sessions.

    Spawns subprocesses in PTYs, manages their lifecycle, and provides
    I/O channels for reading output and writing input.

    Usage::

        host = PTYHost()
        session_id = host.create_session(
            PTYConfig(cmd="/bin/bash", cols=120, rows=40)
        )
        host.start_session(session_id)

        await host.write(session_id, b"ls -la\\n")
        output = await host.read(session_id)
        print(output.data.decode())

        host.terminate_session(session_id)
    """

    def __init__(self) -> None:
        self._sessions: dict[str, _PTYSessionState] = {}

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    def create_session(self, config: PTYConfig | None = None) -> str:
        """Create a new PTY session (does not start it yet).

        Args:
            config: PTY configuration.  Uses defaults if not provided.

        Returns:
            New session ID.
        """
        cfg = config or PTYConfig()
        session_id = str(uuid.uuid4())
        self._sessions[session_id] = _PTYSessionState(
            session_id=session_id,
            config=cfg,
            status=PTYStatus.CREATED,
        )
        return session_id

    def start_session(
        self,
        session_id: str,
        size: PTYSize | None = None,
    ) -> bool:
        """Start a created session by spawning its PTY subprocess.

        Args:
            session_id: Session to start.
            size: Terminal dimensions (uses config dimensions if not
                provided).

        Returns:
            True if the session was started successfully.
        """
        state = self._sessions.get(session_id)
        if state is None or state.status != PTYStatus.CREATED:
            return False

        cfg = state.config
        sz = size or PTYSize(rows=cfg.rows, cols=cfg.cols)

        try:
            pid, fd = pty.fork()
        except OSError as e:
            state.status = PTYStatus.ERROR
            state.error = str(e)
            logger.error("PTY fork failed for session %s: %s", session_id, e)
            return False

        if pid == 0:
            # Child: execute the command
            try:
                # Set terminal size
                termios.tcsetwinsize(fd, sz.to_winsize())  # type: ignore[arg-type]

                # Build environment
                env = os.environ.copy()
                if cfg.env:
                    env.update(cfg.env)

                # Change directory if specified
                if cfg.cwd:
                    os.chdir(cfg.cwd)

                # Execute
                cmd = cfg.cmd or os.environ.get("SHELL", "/bin/bash")
                if cfg.args:
                    os.execve(cmd, [cmd] + cfg.args, env)
                else:
                    os.execve(cmd, [cmd], env)
            except Exception as e:
                os._exit(1)

        # Parent
        state.pid = pid
        state.fd = fd
        state.status = PTYStatus.RUNNING

        # Set non-blocking
        import fcntl

        fl = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)

        logger.info("PTY session %s started (pid=%d)", session_id, pid)
        return True

    def pause_session(self, session_id: str) -> bool:
        """Pause a running session (stop reading its output).

        Args:
            session_id: Session to pause.

        Returns:
            True if the session was paused.
        """
        state = self._sessions.get(session_id)
        if state is None or state.status != PTYStatus.RUNNING:
            return False
        state.status = PTYStatus.PAUSED
        return True

    def resume_session(self, session_id: str) -> bool:
        """Resume a paused session.

        Args:
            session_id: Session to resume.

        Returns:
            True if the session was resumed.
        """
        state = self._sessions.get(session_id)
        if state is None or state.status != PTYStatus.PAUSED:
            return False
        state.status = PTYStatus.RUNNING
        return True

    def terminate_session(self, session_id: str) -> bool:
        """Terminate a session and clean up its PTY.

        Args:
            session_id: Session to terminate.

        Returns:
            True if the session was terminated.
        """
        state = self._sessions.get(session_id)
        if state is None:
            return False
        if state.status in (PTYStatus.RUNNING, PTYStatus.PAUSED):
            try:
                os.kill(state.pid, signal.SIGTERM)
                os.waitpid(state.pid, 0)
            except (OSError, ChildProcessError):
                pass
            try:
                if state.fd >= 0:
                    os.close(state.fd)
            except OSError:
                pass
        state.status = PTYStatus.TERMINATED
        logger.info("PTY session %s terminated", session_id)
        return True

    # ------------------------------------------------------------------
    # I/O
    # ------------------------------------------------------------------

    async def write(self, session_id: str, data: bytes) -> bool:
        """Write data to a session's PTY.

        Args:
            session_id: Target session.
            data: Raw bytes to write (e.g., ``b"ls\\n"``).

        Returns:
            True if the data was written.
        """
        state = self._sessions.get(session_id)
        if state is None or state.status != PTYStatus.RUNNING:
            return False
        try:
            os.write(state.fd, data)
            return True
        except OSError as e:
            logger.error("PTY write failed for session %s: %s", session_id, e)
            state.status = PTYStatus.ERROR
            state.error = str(e)
            return False

    async def read(self, session_id: str, max_bytes: int = 4096) -> PTYOutput | None:
        """Read output from a session's PTY.

        Args:
            session_id: Target session.
            max_bytes: Maximum bytes to read.

        Returns:
            ``PTYOutput`` with the data, or ``None`` if the session is
            not running.
        """
        state = self._sessions.get(session_id)
        if state is None or state.status != PTYStatus.RUNNING:
            return None
        try:
            data = os.read(state.fd, max_bytes)
            return PTYOutput(
                session_id=session_id,
                data=data,
                stream="stdout",
            )
        except (OSError, BlockingIOError):
            return PTYOutput(
                session_id=session_id,
                data=b"",
                stream="stdout",
            )

    async def read_stream(
        self,
        session_id: str,
        buffer_size: int = 4096,
        poll_interval: float = 0.01,
    ) -> AsyncIterator[PTYOutput]:
        """Stream output from a session as an async iterator.

        Args:
            session_id: Target session.
            buffer_size: Buffer size per read.
            poll_interval: Seconds between polls.

        Yields:
            ``PTYOutput`` chunks as they become available.
        """
        state = self._sessions.get(session_id)
        if state is None:
            return

        while state.status == PTYStatus.RUNNING:
            try:
                data = os.read(state.fd, buffer_size)
                if data:
                    yield PTYOutput(
                        session_id=session_id,
                        data=data,
                        stream="stdout",
                    )
                else:
                    # EOF
                    break
            except (BlockingIOError, OSError):
                await asyncio.sleep(poll_interval)

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    def resize_session(self, session_id: str, size: PTYSize) -> bool:
        """Resize a session's terminal.

        Args:
            session_id: Session to resize.
            size: New terminal dimensions.

        Returns:
            True if the terminal was resized.
        """
        state = self._sessions.get(session_id)
        if state is None or state.status not in (PTYStatus.RUNNING, PTYStatus.PAUSED):
            return False
        try:
            termios.tcsetwinsize(state.fd, size.to_winsize())  # type: ignore[arg-type]
            return True
        except OSError:
            return False

    def get_session(self, session_id: str) -> _PTYSessionState | None:
        """Get session state.

        Args:
            session_id: Session identifier.

        Returns:
            Session state or None.
        """
        return self._sessions.get(session_id)

    def list_sessions(
        self,
        status: PTYStatus | None = None,
    ) -> list[dict[str, Any]]:
        """List all sessions, optionally filtered by status.

        Args:
            status: Filter by session status.

        Returns:
            List of session info dicts.
        """
        sessions = list(self._sessions.values())
        if status is not None:
            sessions = [s for s in sessions if s.status == status]

        return [
            {
                "session_id": s.session_id,
                "status": s.status.value,
                "pid": s.pid,
                "error": s.error,
            }
            for s in sessions
        ]


# ---------------------------------------------------------------------------
# Internal session state
# ---------------------------------------------------------------------------


@dataclass
class _PTYSessionState:
    """Internal state for a single PTY session."""

    session_id: str
    config: PTYConfig
    status: PTYStatus = PTYStatus.CREATED
    pid: int = -1
    fd: int = -1
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    error: str = ""


# ---------------------------------------------------------------------------
# IPCProtocol
# ---------------------------------------------------------------------------


class IPCMessageType(str, Enum):
    """Types of IPC messages."""

    COMMAND = "command"
    OUTPUT = "output"
    RESIZE = "resize"
    STATUS = "status"
    ERROR = "error"
    HEARTBEAT = "heartbeat"
    CONTROL = "control"


@dataclass
class IPCMessage:
    """A single IPC message.

    Attributes
    ----------
    msg_type:
        Message type.
    source:
        Source session ID.
    target:
        Target session ID (``"*"`` for broadcast).
    payload:
        Message payload (arbitrary).
    msg_id:
        Unique message ID (auto-generated).
    timestamp:
        Message creation time.
    """

    msg_type: IPCMessageType
    source: str
    target: str = "*"
    payload: dict[str, Any] = field(default_factory=dict)
    msg_id: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if not self.msg_id:
            self.msg_id = str(uuid.uuid4())


class IPCProtocol:
    """Message-passing between PTY sessions.

    Routes typed messages (command, output, resize, status, error,
    heartbeat, control) between sessions.  Supports broadcast (``"*"``)
    and direct addressing.

    Usage::

        ipc = IPCProtocol()
        ipc.send(IPCMessage(
            msg_type=IPCMessageType.COMMAND,
            source="session-a",
            target="session-b",
            payload={"cmd": "ls -la"},
        ))

        messages = ipc.poll("session-b")
        for msg in messages:
            print(msg.msg_type, msg.payload)
    """

    def __init__(self, max_queue_size: int = 1000) -> None:
        self._queues: dict[str, list[IPCMessage]] = {}
        self._max_queue_size = max_queue_size

    # ------------------------------------------------------------------
    # Send / poll
    # ------------------------------------------------------------------

    def send(self, message: IPCMessage) -> bool:
        """Send a message to its target session(s).

        Args:
            message: The message to send.

        Returns:
            True if the message was queued.
        """
        if message.target == "*":
            # Broadcast to all known sessions except source
            for session_id in self._queues:
                if session_id != message.source:
                    self._enqueue(session_id, message)
            return True

        self._enqueue(message.target, message)
        return True

    def poll(self, session_id: str) -> list[IPCMessage]:
        """Retrieve all pending messages for a session.

        Args:
            session_id: Session to poll.

        Returns:
            List of pending messages (clears the queue).
        """
        return self._queues.pop(session_id, [])

    def peek(self, session_id: str) -> int:
        """Check how many pending messages a session has.

        Args:
            session_id: Session to check.

        Returns:
            Number of pending messages.
        """
        return len(self._queues.get(session_id, []))

    # ------------------------------------------------------------------
    # Session registration
    # ------------------------------------------------------------------

    def register_session(self, session_id: str) -> None:
        """Register a session for message delivery.

        Args:
            session_id: Session ID to register.
        """
        if session_id not in self._queues:
            self._queues[session_id] = []

    def unregister_session(self, session_id: str) -> None:
        """Unregister a session and drop its pending messages.

        Args:
            session_id: Session ID to unregister.
        """
        self._queues.pop(session_id, None)

    def list_sessions(self) -> list[str]:
        """List all registered session IDs."""
        return list(self._queues.keys())

    def clear(self) -> int:
        """Clear all queues and return total messages cleared."""
        total = sum(len(q) for q in self._queues.values())
        self._queues.clear()
        return total

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def send_command(
        self,
        source: str,
        target: str,
        cmd: str,
        **kwargs: Any,
    ) -> IPCMessage:
        """Convenience: send a command message.

        Args:
            source: Source session.
            target: Target session.
            cmd: Command string.
            **kwargs: Extra payload fields.

        Returns:
            The sent message.
        """
        msg = IPCMessage(
            msg_type=IPCMessageType.COMMAND,
            source=source,
            target=target,
            payload={"cmd": cmd, **kwargs},
        )
        self.send(msg)
        return msg

    def send_output(
        self,
        source: str,
        target: str,
        data: str,
        stream: str = "stdout",
    ) -> IPCMessage:
        """Convenience: send an output message.

        Args:
            source: Source session.
            target: Target session.
            data: Output data (string).
            stream: Stream name.

        Returns:
            The sent message.
        """
        msg = IPCMessage(
            msg_type=IPCMessageType.OUTPUT,
            source=source,
            target=target,
            payload={"data": data, "stream": stream},
        )
        self.send(msg)
        return msg

    def send_error(
        self,
        source: str,
        target: str,
        error: str,
    ) -> IPCMessage:
        """Convenience: send an error message.

        Args:
            source: Source session.
            target: Target session.
            error: Error description.

        Returns:
            The sent message.
        """
        msg = IPCMessage(
            msg_type=IPCMessageType.ERROR,
            source=source,
            target=target,
            payload={"error": error},
        )
        self.send(msg)
        return msg

    def _enqueue(self, session_id: str, message: IPCMessage) -> None:
        """Add a message to a session's queue."""
        if session_id not in self._queues:
            self._queues[session_id] = []
        queue = self._queues[session_id]
        queue.append(message)
        if len(queue) > self._max_queue_size:
            queue.pop(0)


# ---------------------------------------------------------------------------
# TUIRenderer
# ---------------------------------------------------------------------------


@dataclass
class TUIPanel:
    """A panel region in the multiplexed TUI.

    Attributes
    ----------
    session_id:
        Session ID this panel displays.
    x:
        X position (column offset).
    y:
        Y position (row offset).
    width:
        Panel width in characters.
    height:
        Panel height in rows.
    buffer:
        Text buffer for the panel.
    title:
        Panel title.
    """

    session_id: str
    x: int
    y: int
    width: int
    height: int
    buffer: str = ""
    title: str = ""


class TUIRenderer:
    """Terminal UI rendering for multiplexed view.

    Renders multiple session panels into a single terminal frame using
    ANSI escape codes.  Supports split layouts, status bars, and focus
    highlighting.

    Usage::

        renderer = TUIRenderer(total_cols=160, total_rows=40)
        renderer.add_panel(TUIPanel(
            session_id="session-a",
            x=0, y=0, width=80, height=40,
            title="Session A",
        ))
        renderer.add_panel(TUIPanel(
            session_id="session-b",
            x=80, y=0, width=80, height=40,
            title="Session B",
        ))

        renderer.update_buffer("session-a", "Hello\\nWorld\\n")
        print(renderer.render_frame())
    """

    def __init__(self, total_cols: int = 80, total_rows: int = 24) -> None:
        self.total_cols = total_cols
        self.total_rows = total_rows
        self._panels: dict[str, TUIPanel] = {}
        self._focused_session: str | None = None
        self._status_bar: str = ""

    # ------------------------------------------------------------------
    # Panel management
    # ------------------------------------------------------------------

    def add_panel(self, panel: TUIPanel) -> None:
        """Add a panel to the layout.

        Args:
            panel: The panel to add.
        """
        self._panels[panel.session_id] = panel

    def remove_panel(self, session_id: str) -> bool:
        """Remove a panel by session ID.

        Args:
            session_id: Session to remove.

        Returns:
            True if the panel was removed.
        """
        return self._panels.pop(session_id, None) is not None

    def get_panel(self, session_id: str) -> TUIPanel | None:
        """Get a panel by session ID.

        Args:
            session_id: Session to find.

        Returns:
            The panel, or None.
        """
        return self._panels.get(session_id)

    def list_panels(self) -> list[TUIPanel]:
        """Return all registered panels."""
        return list(self._panels.values())

    # ------------------------------------------------------------------
    # Buffer management
    # ------------------------------------------------------------------

    def update_buffer(self, session_id: str, text: str) -> bool:
        """Update a panel's text buffer.

        Args:
            session_id: Session whose buffer to update.
            text: New text content.

        Returns:
            True if the buffer was updated.
        """
        panel = self._panels.get(session_id)
        if panel is None:
            return False
        panel.buffer = text
        return True

    def append_buffer(self, session_id: str, text: str) -> bool:
        """Append text to a panel's buffer.

        Args:
            session_id: Session whose buffer to append to.
            text: Text to append.

        Returns:
            True if the buffer was appended.
        """
        panel = self._panels.get(session_id)
        if panel is None:
            return False
        panel.buffer += text
        # Trim to fit panel height
        lines = panel.buffer.split("\n")
        if len(lines) > panel.height:
            panel.buffer = "\n".join(lines[-panel.height:])
        return True

    def clear_buffer(self, session_id: str) -> bool:
        """Clear a panel's text buffer.

        Args:
            session_id: Session to clear.

        Returns:
            True if the buffer was cleared.
        """
        panel = self._panels.get(session_id)
        if panel is None:
            return False
        panel.buffer = ""
        return True

    # ------------------------------------------------------------------
    # Focus
    # ------------------------------------------------------------------

    def set_focus(self, session_id: str | None) -> None:
        """Set the focused session (highlighted in the UI).

        Args:
            session_id: Session to focus, or None to clear focus.
        """
        self._focused_session = session_id

    def get_focus(self) -> str | None:
        """Get the currently focused session ID."""
        return self._focused_session

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def set_status_bar(self, text: str) -> None:
        """Set the status bar text.

        Args:
            text: Status bar content.
        """
        self._status_bar = text[: self.total_cols]

    def render_frame(self) -> str:
        """Render the full multiplexed frame as a string.

        Returns:
            A string with ANSI escape codes for cursor positioning and
            styling, suitable for printing to a terminal.
        """
        lines: list[str] = []

        # ANSI escape: clear screen, reset cursor
        lines.append("\033[2J\033[H")

        # Render each panel
        for panel in self._panels.values():
            if panel.height <= 0 or panel.width <= 0:
                continue

            panel_lines = self._render_panel(panel)
            for i, line in enumerate(panel_lines):
                row = panel.y + i
                if row >= self.total_rows:
                    break
                lines.append(f"\033[{row + 1};{panel.x + 1}H{line}")

        # Status bar
        if self._status_bar:
            lines.append(f"\033[{self.total_rows};1H")
            lines.append(self._status_bar)
            lines.append("\033[K")  # Clear to end of line

        return "".join(lines)

    def _render_panel(self, panel: TUIPanel) -> list[str]:
        """Render a single panel's content."""
        is_focused = panel.session_id == self._focused_session
        result: list[str] = []

        # Title bar
        title_text = f" {panel.title} "
        if is_focused:
            title_line = f"\033[7m{title_text:^{panel.width}}\033[0m"
        else:
            title_line = f"\033[1m{title_text:^{panel.width}}\033[0m"
        result.append(title_line)

        # Content
        content_lines = panel.buffer.split("\n")
        for i in range(panel.height - 1):
            if i < len(content_lines):
                line = content_lines[i]
                if len(line) > panel.width:
                    line = line[: panel.width - 1] + "…"
                else:
                    line = line.ljust(panel.width)
            else:
                line = " " * panel.width
            result.append(f"\033[{panel.y + 1 + i};{panel.x}H{line}")

        return result


# ---------------------------------------------------------------------------
# SessionMultiplexer
# ---------------------------------------------------------------------------


class SessionMultiplexer:
    """Manage multiple PTY sessions concurrently.

    Coordinates session lifecycle, IPC message routing, and TUI
    rendering across all active PTY sessions.

    Usage::

        mux = SessionMultiplexer()
        sid1 = mux.create_session(PTYConfig(cmd="htop"))
        sid2 = mux.create_session(PTYConfig(cmd="vim"))

        mux.start_all()
        mux.send_command(sid1, b"q")  # quit htop
        mux.terminate_session(sid1)
    """

    def __init__(
        self,
        pty_host: PTYHost | None = None,
        ipc: IPCProtocol | None = None,
        renderer: TUIRenderer | None = None,
    ) -> None:
        self.pty_host = pty_host or PTYHost()
        self.ipc = ipc or IPCProtocol()
        self.renderer = renderer or TUIRenderer()

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    def create_session(
        self,
        config: PTYConfig | None = None,
        panel_title: str = "",
        panel_x: int = 0,
        panel_y: int = 0,
        panel_width: int = 80,
        panel_height: int = 24,
    ) -> str:
        """Create a new session with an associated TUI panel.

        Args:
            config: PTY configuration.
            panel_title: Panel title (defaults to session ID prefix).
            panel_x: Panel X position.
            panel_y: Panel Y position.
            panel_width: Panel width.
            panel_height: Panel height.

        Returns:
            New session ID.
        """
        session_id = self.pty_host.create_session(config)
        self.ipc.register_session(session_id)

        title = panel_title or session_id[:8]
        self.renderer.add_panel(
            TUIPanel(
                session_id=session_id,
                x=panel_x,
                y=panel_y,
                width=panel_width,
                height=panel_height,
                title=title,
            )
        )

        return session_id

    def start_session(self, session_id: str) -> bool:
        """Start a session's PTY subprocess.

        Args:
            session_id: Session to start.

        Returns:
            True if started successfully.
        """
        return self.pty_host.start_session(session_id)

    def start_all(self) -> int:
        """Start all created sessions.

        Returns:
            Number of sessions started.
        """
        count = 0
        for s in self.pty_host.list_sessions(PTYStatus.CREATED):
            if self.start_session(s["session_id"]):
                count += 1
        return count

    def pause_session(self, session_id: str) -> bool:
        """Pause a session.

        Args:
            session_id: Session to pause.

        Returns:
            True if paused.
        """
        return self.pty_host.pause_session(session_id)

    def resume_session(self, session_id: str) -> bool:
        """Resume a session.

        Args:
            session_id: Session to resume.

        Returns:
            True if resumed.
        """
        return self.pty_host.resume_session(session_id)

    def terminate_session(self, session_id: str) -> bool:
        """Terminate a session and clean up.

        Args:
            session_id: Session to terminate.

        Returns:
            True if terminated.
        """
        ok = self.pty_host.terminate_session(session_id)
        self.ipc.unregister_session(session_id)
        return ok

    def terminate_all(self) -> int:
        """Terminate all running/paused sessions.

        Returns:
            Number of sessions terminated.
        """
        count = 0
        for s in self.pty_host.list_sessions():
            if s["status"] in (PTYStatus.RUNNING.value, PTYStatus.PAUSED.value):
                if self.terminate_session(s["session_id"]):
                    count += 1
        return count

    # ------------------------------------------------------------------
    # I/O
    # ------------------------------------------------------------------

    async def send_command(self, session_id: str, data: bytes) -> bool:
        """Write data to a session's PTY.

        Args:
            session_id: Target session.
            data: Raw bytes.

        Returns:
            True if written.
        """
        return await self.pty_host.write(session_id, data)

    async def read_output(self, session_id: str) -> PTYOutput | None:
        """Read output from a session and update its panel buffer.

        Args:
            session_id: Session to read from.

        Returns:
            The output, or None.
        """
        output = await self.pty_host.read(session_id)
        if output is not None and output.data:
            self.renderer.append_buffer(
                session_id,
                output.data.decode(errors="replace"),
            )
        return output

    # ------------------------------------------------------------------
    # IPC
    # ------------------------------------------------------------------

    def send_ipc(
        self,
        msg_type: IPCMessageType,
        source: str,
        target: str = "*",
        payload: dict[str, Any] | None = None,
    ) -> IPCMessage:
        """Send an IPC message between sessions.

        Args:
            msg_type: Message type.
            source: Source session.
            target: Target session (``"*"`` for broadcast).
            payload: Message payload.

        Returns:
            The sent message.
        """
        msg = IPCMessage(
            msg_type=msg_type,
            source=source,
            target=target,
            payload=payload or {},
        )
        self.ipc.send(msg)
        return msg

    def poll_ipc(self, session_id: str) -> list[IPCMessage]:
        """Poll pending IPC messages for a session.

        Args:
            session_id: Session to poll.

        Returns:
            List of pending messages.
        """
        return self.ipc.poll(session_id)

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def split_horizontal(self, session_id: str) -> str | None:
        """Split the current session's panel horizontally.

        Creates a new session whose panel occupies the right half of
        the current panel's space.

        Args:
            session_id: Session to split from.

        Returns:
            New session ID, or None.
        """
        panel = self.renderer.get_panel(session_id)
        if panel is None:
            return None

        half_width = max(20, panel.width // 2)
        panel.width = half_width

        new_id = self.create_session(
            panel_title=f"{session_id[:4]}-split",
            panel_x=panel.x + half_width,
            panel_y=panel.y,
            panel_width=half_width,
            panel_height=panel.height,
        )
        return new_id

    def split_vertical(self, session_id: str) -> str | None:
        """Split the current session's panel vertically.

        Creates a new session whose panel occupies the bottom half of
        the current panel's space.

        Args:
            session_id: Session to split from.

        Returns:
            New session ID, or None.
        """
        panel = self.renderer.get_panel(session_id)
        if panel is None:
            return None

        half_height = max(5, panel.height // 2)
        panel.height = half_height

        new_id = self.create_session(
            panel_title=f"{session_id[:4]}-vsplit",
            panel_x=panel.x,
            panel_y=panel.y + half_height,
            panel_width=panel.width,
            panel_height=half_height,
        )
        return new_id

    def focus_session(self, session_id: str | None) -> None:
        """Focus on a specific session in the TUI.

        Args:
            session_id: Session to focus, or None.
        """
        self.renderer.set_focus(session_id)

    def set_status(self, text: str) -> None:
        """Set the multiplexer status bar text.

        Args:
            text: Status text.
        """
        self.renderer.set_status_bar(text)

    def render(self) -> str:
        """Render the full multiplexed frame.

        Returns:
            Rendered frame string.
        """
        return self.renderer.render_frame()
