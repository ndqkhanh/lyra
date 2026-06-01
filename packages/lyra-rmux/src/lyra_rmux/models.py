"""Data models for lyra-rmux PTY multiplexer."""

from __future__ import annotations

import enum
import uuid
from dataclasses import dataclass, field
from typing import Any


class SessionState(str, enum.Enum):
    """Lifecycle states for a session."""

    CREATED = "created"
    RUNNING = "running"
    ATTACHED = "attached"
    DETACHED = "detached"
    CLOSED = "closed"


class PaneState(str, enum.Enum):
    """Lifecycle states for a pane."""

    CREATED = "created"
    RUNNING = "running"
    CLOSED = "closed"


@dataclass(frozen=True)
class PtyProcess:
    """Represents a spawned PTY child process (immutable snapshot of state)."""

    pid: int
    fd: int
    command: tuple[str, ...]
    cwd: str
    exit_code: int | None = None


@dataclass(frozen=True)
class Pane:
    """A single pane within a window."""

    pane_id: str = field(default_factory=lambda: f"pane-{uuid.uuid4().hex[:12]}")
    state: PaneState = PaneState.CREATED
    rows: int = 24
    cols: int = 80
    x: int = 0
    y: int = 0
    process: PtyProcess | None = None


@dataclass(frozen=True)
class Window:
    """A window containing one or more panes."""

    window_id: str = field(default_factory=lambda: f"win-{uuid.uuid4().hex[:12]}")
    name: str = "default"
    panes: tuple[Pane, ...] = ()


@dataclass(frozen=True)
class Session:
    """A top-level session containing windows."""

    session_id: str = field(default_factory=lambda: f"sess-{uuid.uuid4().hex[:12]}")
    name: str = ""
    state: SessionState = SessionState.CREATED
    windows: tuple[Window, ...] = ()


@dataclass(frozen=True)
class Snapshot:
    """Point-in-time capture of display content for a pane."""

    pane_id: str
    lines: tuple[str, ...] = ()
    cursor_row: int = 0
    cursor_col: int = 0
    scrollback_rows: int = 0


@dataclass(frozen=True)
class IpcMessage:
    """A JSON-RPC style request message sent over IPC."""

    method: str
    params: dict[str, Any] = field(default_factory=dict)
    msg_id: str = field(default_factory=lambda: uuid.uuid4().hex)


@dataclass(frozen=True)
class IpcResponse:
    """A JSON-RPC style response message over IPC."""

    msg_id: str
    success: bool = True
    result: Any = None
    error: str | None = None
