"""Session manager — create, attach, detach, split, send, kill sessions."""

from __future__ import annotations

import os
import signal
import time
from typing import Sequence

from lyra_rmux.models import (
    Pane,
    PaneState,
    PtyProcess,
    Session,
    SessionState,
    Snapshot,
    Window,
)
from lyra_rmux.pty_manager import PtyManager
from lyra_rmux.snapshot_engine import SnapshotEngine


class SessionManager:
    """High-level session management built on top of PtyManager.

    A session owns one or more windows; each window owns one or more panes.
    For now each session gets a single window with a single pane (the
    split_pane method is provided for future multi-pane support).
    """

    def __init__(self, pty_manager: PtyManager | None = None) -> None:
        self._pty = pty_manager or PtyManager()
        self._sessions: dict[str, Session] = {}
        self._pane_to_pid: dict[str, int] = {}  # pane_id -> child PID
        self._pid_to_pane: dict[int, str] = {}  # child PID -> pane_id
        self._snap_engine = SnapshotEngine()

    # ------------------------------------------------------------------
    # session lifecycle
    # ------------------------------------------------------------------

    def create_session(
        self,
        name: str = "",
        command: tuple[str, ...] = ("/bin/sh", "-i"),
        cwd: str | None = None,
        env: dict[str, str] | None = None,
        rows: int = 24,
        cols: int = 80,
    ) -> Session:
        """Create a new session with a single pane running *command*."""
        proc = self._pty.spawn(command=command, cwd=cwd, env=env, rows=rows, cols=cols)
        pane = Pane(
            pane_id=f"pane-{proc.pid:x}",
            state=PaneState.RUNNING,
            rows=rows,
            cols=cols,
            process=proc,
        )
        win = Window(window_id="win-1", name="main", panes=(pane,))
        sess = Session(name=name or f"sess-{proc.pid:x}", state=SessionState.RUNNING, windows=(win,))
        self._sessions[sess.session_id] = sess
        self._pane_to_pid[pane.pane_id] = proc.pid
        self._pid_to_pane[proc.pid] = pane.pane_id
        return sess

    def attach_session(self, session_id: str) -> Session | None:
        """Mark a session as attached (logical attach; does not redirect a TTY)."""
        sess = self._sessions.get(session_id)
        if sess is None:
            return None
        sess = _session_replace(sess, state=SessionState.ATTACHED)
        self._sessions[session_id] = sess
        return sess

    def detach_session(self, session_id: str) -> Session | None:
        """Mark a session as detached."""
        sess = self._sessions.get(session_id)
        if sess is None:
            return None
        sess = _session_replace(sess, state=SessionState.DETACHED)
        self._sessions[session_id] = sess
        return sess

    def kill_session(self, session_id: str) -> None:
        """Kill every pane in the session and remove it."""
        sess = self._sessions.pop(session_id, None)
        if sess is None:
            return
        for win in sess.windows:
            for pane in win.panes:
                pid = self._pane_to_pid.pop(pane.pane_id, None)
                self._pid_to_pane.pop(pid, None)
                if pid is not None:
                    self._pty.close(pid)

    def list_sessions(self) -> Sequence[Session]:
        """Return all tracked sessions."""
        return list(self._sessions.values())

    def get_session(self, session_id: str) -> Session | None:
        """Retrieve a session by ID."""
        return self._sessions.get(session_id)

    # ------------------------------------------------------------------
    # pane operations
    # ------------------------------------------------------------------

    def split_pane(
        self,
        session_id: str,
        window_id: str = "win-1",
        vertical: bool = True,
        command: tuple[str, ...] = ("/bin/sh", "-i"),
    ) -> Pane | None:
        """Split an existing pane, creating a new pane in the same window."""
        sess = self._sessions.get(session_id)
        if sess is None:
            return None

        new_windows: list[Window] = []
        found = False
        new_pane: Pane | None = None

        for win in sess.windows:
            if win.window_id != window_id:
                new_windows.append(win)
                continue
            found = True
            if not win.panes:
                return None
            first = win.panes[0]
            new_rows = first.rows
            new_cols = first.cols
            if vertical:
                new_cols = first.cols // 2
            else:
                new_rows = first.rows // 2

            proc = self._pty.spawn(command=command, rows=new_rows, cols=new_cols)
            new_pane = Pane(
                pane_id=f"pane-{proc.pid:x}",
                state=PaneState.RUNNING,
                rows=new_rows,
                cols=new_cols,
                x=first.cols // 2 if vertical else 0,
                y=first.rows // 2 if not vertical else 0,
                process=proc,
            )
            self._pane_to_pid[new_pane.pane_id] = proc.pid
            self._pid_to_pane[proc.pid] = new_pane.pane_id

            new_windows.append(Window(window_id=win.window_id, name=win.name, panes=(*win.panes, new_pane)))

        if not new_pane:
            return None

        sess = Session(
            session_id=sess.session_id,
            name=sess.name,
            state=sess.state,
            windows=tuple(new_windows),
        )
        self._sessions[session_id] = sess
        return new_pane

    def send_keys(self, session_id: str, data: str, pane_id: str | None = None) -> bool:
        """Send text to a pane.  If *pane_id* is None, send to the first pane."""
        pid = self._resolve_pid(session_id, pane_id)
        if pid is None:
            return False
        self._pty.write(pid, data.encode("utf-8", errors="replace"))
        return True

    def send_bytes(self, session_id: str, data: bytes, pane_id: str | None = None) -> bool:
        """Send raw bytes to a pane."""
        pid = self._resolve_pid(session_id, pane_id)
        if pid is None:
            return False
        self._pty.write(pid, data)
        return True

    def get_snapshot(self, session_id: str, pane_id: str | None = None) -> Snapshot | None:
        """Capture the current visible content of a pane.

        This drains buffered output from the PTY and stores the result.
        Since PTYs don't expose a framebuffer, we collect whatever output
        has accumulated and treat each line as "visible".
        """
        pid = self._resolve_pid(session_id, pane_id)
        if pid is None:
            return None
        if pane_id is None:
            pane_id = self._first_pane_id(session_id)
            if pane_id is None:
                return None

        raw = self._pty.read_all_buffered(pid, timeout=0.05)
        text = raw.decode("utf-8", errors="replace")
        lines = tuple(text.splitlines())
        snapshot = self._snap_engine.capture(pane_id, lines)
        return snapshot

    def resize_pane(
        self,
        session_id: str,
        rows: int,
        cols: int,
        pane_id: str | None = None,
    ) -> bool:
        """Resize a pane's PTY window."""
        pid = self._resolve_pid(session_id, pane_id)
        if pid is None:
            return False
        self._pty.resize(pid, rows, cols)
        return True

    def kill_pane(self, session_id: str, pane_id: str | None = None) -> bool:
        """Kill a pane and remove it from the session."""
        pid = self._resolve_pid(session_id, pane_id)
        if pid is None:
            return False
        if pane_id is None:
            pane_id = self._first_pane_id(session_id)
            if pane_id is None:
                return False

        self._pty.close(pid)
        self._pane_to_pid.pop(pane_id, None)
        self._pid_to_pane.pop(pid, None)

        sess = self._sessions.get(session_id)
        if sess is None:
            return True

        new_windows: list[Window] = []
        for win in sess.windows:
            kept = tuple(p for p in win.panes if p.pane_id != pane_id)
            if kept:
                new_windows.append(Window(window_id=win.window_id, name=win.name, panes=kept))

        if new_windows:
            self._sessions[session_id] = Session(
                session_id=sess.session_id,
                name=sess.name,
                state=sess.state,
                windows=tuple(new_windows),
            )
        else:
            self._sessions.pop(session_id, None)

        return True

    # ------------------------------------------------------------------
    # snapshot engine access
    # ------------------------------------------------------------------

    @property
    def snapshot_engine(self) -> SnapshotEngine:
        """Access the snapshot engine for diff/replay operations."""
        return self._snap_engine

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------

    def _resolve_pid(self, session_id: str, pane_id: str | None) -> int | None:
        if pane_id is not None:
            return self._pane_to_pid.get(pane_id)
        # fallback: first pane of the first window
        sess = self._sessions.get(session_id)
        if sess is None or not sess.windows:
            return None
        panes = sess.windows[0].panes
        if not panes:
            return None
        return self._pane_to_pid.get(panes[0].pane_id)

    def _first_pane_id(self, session_id: str) -> str | None:
        sess = self._sessions.get(session_id)
        if sess is None or not sess.windows:
            return None
        panes = sess.windows[0].panes
        if not panes:
            return None
        return panes[0].pane_id


def _session_replace(sess: Session, **kw: object) -> Session:
    """Return a new Session with the given fields replaced."""
    d = {
        "session_id": sess.session_id,
        "name": sess.name,
        "state": sess.state,
        "windows": sess.windows,
    }
    d.update(**kw)
    return Session(**d)  # type: ignore[arg-type]
