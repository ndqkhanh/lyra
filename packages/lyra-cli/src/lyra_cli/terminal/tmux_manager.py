"""Tmux session manager — tmux pane splitting, session management, and multiplexing.

Manages tmux sessions for parallel agent work, splitting terminal panes
for concurrent agent execution and monitoring.
"""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from enum import StrEnum


class PaneDirection(StrEnum):
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"


class SessionState(StrEnum):
    ACTIVE = "active"
    DETACHED = "detached"
    DEAD = "dead"


@dataclass(frozen=True)
class TmuxPane:
    pane_id: str
    session_name: str
    window_index: int
    pane_index: int
    title: str
    current_command: str


@dataclass(frozen=True)
class TmuxSession:
    session_name: str
    state: SessionState
    pane_count: int
    window_count: int
    created_at: float
    attached: bool


class TmuxManager:
    """Manages tmux sessions and panes for parallel agent execution.

    Provides session creation, pane splitting, command sending,
    and session cleanup. Falls back gracefully when tmux is
    not available.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, TmuxSession] = {}
        self._panes: dict[str, list[TmuxPane]] = {}
        self._available = self._check_tmux()

    @staticmethod
    def _check_tmux() -> bool:
        try:
            result = subprocess.run(
                ["tmux", "-V"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    @property
    def is_available(self) -> bool:
        return self._available

    def new_session(
        self, session_name: str, window_name: str = "lyra", detach: bool = True
    ) -> TmuxSession | None:
        if not self._available:
            return None

        cmd = ["tmux", "new-session", "-d", "-s", session_name, "-n", window_name]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

        if result.returncode != 0:
            return None

        session = TmuxSession(
            session_name=session_name,
            state=SessionState.ACTIVE,
            pane_count=1,
            window_count=1,
            created_at=time.time(),
            attached=not detach,
        )
        self._sessions[session_name] = session
        self._panes[session_name] = []
        return session

    def split_pane(
        self,
        session_name: str,
        direction: PaneDirection = PaneDirection.VERTICAL,
        command: str | None = None,
    ) -> TmuxPane | None:
        if not self._available:
            return None

        direction_flag = "-h" if direction == PaneDirection.HORIZONTAL else "-v"
        cmd = ["tmux", "split-window", direction_flag, "-t", session_name]
        if command:
            cmd.extend([command])

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            return None

        pane = self._capture_pane_info(session_name)
        if pane:
            self._panes.setdefault(session_name, []).append(pane)
        return pane

    def send_keys(self, session_name: str, keys: str) -> bool:
        if not self._available:
            return False

        result = subprocess.run(
            ["tmux", "send-keys", "-t", session_name, keys],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0

    def capture_pane(self, session_name: str, pane_index: int = 0) -> str:
        if not self._available:
            return ""

        result = subprocess.run(
            [
                "tmux", "capture-pane", "-t",
                f"{session_name}:0.{pane_index}", "-p",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout if result.returncode == 0 else ""

    def kill_session(self, session_name: str) -> bool:
        if not self._available:
            return False

        result = subprocess.run(
            ["tmux", "kill-session", "-t", session_name],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            self._sessions.pop(session_name, None)
            self._panes.pop(session_name, None)
            return True
        return False

    def list_sessions(self) -> list[str]:
        if not self._available:
            return []

        result = subprocess.run(
            ["tmux", "list-sessions", "-F", "#{session_name}"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return []
        return [s for s in result.stdout.strip().split("\n") if s]

    def _capture_pane_info(self, session_name: str) -> TmuxPane | None:
        try:
            result = subprocess.run(
                [
                    "tmux", "display-message", "-t", session_name,
                    "-p", "#{pane_id}|#{session_name}|#{window_index}|#{pane_index}|#{pane_title}|#{pane_current_command}",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                return None
            parts = result.stdout.strip().split("|")
            if len(parts) < 6:
                return None
            return TmuxPane(
                pane_id=parts[0],
                session_name=parts[1],
                window_index=int(parts[2]),
                pane_index=int(parts[3]),
                title=parts[4],
                current_command=parts[5],
            )
        except (subprocess.TimeoutExpired, ValueError):
            return None

    def stats(self) -> dict:
        return {
            "tmux_available": self._available,
            "active_sessions": len(self._sessions),
            "total_panes": sum(len(p) for p in self._panes.values()),
        }
