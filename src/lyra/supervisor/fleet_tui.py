"""
FleetTUI — terminal-based fleet monitoring dashboard.

Renders live session cards with status, cost, and progress metrics.
Supports keyboard navigation, per-session peek panels, and auto-refresh.

Usage::

    tui = FleetTUI(fleet_orchestrator)
    tui.run()  # blocks until 'q' is pressed

Or render a one-shot snapshot::

    print(tui.render_fleet())
"""

from __future__ import annotations

import datetime
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import structlog

from lyra.supervisor.circuit_breaker import CircuitState, LoopHealth
from lyra.supervisor.fleet import FleetOrchestrator, SessionProgress

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# ANSI color codes
# ---------------------------------------------------------------------------

_RESET = "\033[0m"
_BOLD = "\033[1m"
_DIM = "\033[2m"

_GREEN = "\033[92m"
_YELLOW = "\033[93m"
_RED = "\033[91m"
_GRAY = "\033[90m"
_CYAN = "\033[96m"
_WHITE = "\033[97m"

_BG_GREEN = "\033[42m"
_BG_YELLOW = "\033[43m"
_BG_RED = "\033[41m"
_BG_GRAY = "\033[100m"
_BG_CYAN = "\033[46m"
_BG_BLUE = "\033[44m"

_CLEAR_LINE = "\033[K"
_CURSOR_UP = "\033[A"
_CURSOR_HIDE = "\033[?25l"
_CURSOR_SHOW = "\033[?25h"
_CLEAR_SCREEN = "\033[2J\033[H"


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TUISessionCard:
    """Rendered representation of a session card for the dashboard.

    Attributes:
        session_id: The session identifier.
        name: Human-readable session name.
        state_label: Colorized state string.
        state_color: ANSI color code for state.
        progress_bar: ASCII progress bar string.
        cost_str: Formatted cost string.
        uptime_str: Formatted uptime string.
        circuit_badge: Circuit breaker status badge, or empty string.
        is_selected: Whether this card is currently highlighted.
    """

    session_id: str
    name: str
    state_label: str
    state_color: str
    progress_bar: str
    cost_str: str
    uptime_str: str
    circuit_badge: str
    is_selected: bool = False


@dataclass
class FleetTUIConfig:
    """Configuration for the fleet TUI.

    Attributes:
        auto_refresh_seconds: Interval between auto-refreshes (0 to disable).
        max_visible_sessions: Maximum cards shown before scrolling.
        peek_lines: Number of lines shown in the peek panel.
        color_enabled: Whether to use ANSI color codes.
    """

    auto_refresh_seconds: float = 2.0
    max_visible_sessions: int = 20
    peek_lines: int = 10
    color_enabled: bool = True


# ---------------------------------------------------------------------------
# FleetTUI
# ---------------------------------------------------------------------------


class FleetTUI:
    """Terminal-based fleet monitoring dashboard.

    Provides keyboard-driven navigation, live session cards, peek-panels
    for expanded session views, and colour-coded health indicators.

    Keyboard shortcuts::

        j / down-arrow    - move selection down
        k / up-arrow      - move selection up
        Enter             - toggle peek panel for selected session
        q                 - quit dashboard
        r                 - manual refresh
        K                 - kill selected session (with confirmation)
    """

    def __init__(
        self,
        fleet: FleetOrchestrator,
        circuit_breaker: Any | None = None,
        config: FleetTUIConfig | None = None,
    ) -> None:
        """
        Args:
            fleet: The FleetOrchestrator to monitor.
            circuit_breaker: Optional ConfidenceCircuitBreaker for circuit status.
            config: TUI configuration. Uses defaults if not provided.
        """
        self._fleet = fleet
        self._circuit_breaker = circuit_breaker
        self._config = config or FleetTUIConfig()

        # UI state
        self._selected_index: int = 0
        self._scroll_offset: int = 0
        self._peek_sessions: set[str] = set()
        self._running = False
        self._render_lock = threading.Lock()
        self._last_render: str | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Run the interactive TUI. Blocks until 'q' is pressed."""
        self._running = True
        self._selected_index = 0
        self._peek_sessions.clear()

        try:
            self._enable_raw_mode()
            print(_CURSOR_HIDE, end="", flush=True)

            while self._running:
                self._render()
                key = self._read_key(timeout=self._config.auto_refresh_seconds)

                if key is None:
                    continue  # auto-refresh timeout

                self._handle_key(key)

        except KeyboardInterrupt:
            self._running = False
        finally:
            print(_CURSOR_SHOW, end="", flush=True)
            self._disable_raw_mode()

    def stop(self) -> None:
        """Signal the event loop to stop."""
        self._running = False

    def render_fleet(self) -> str:
        """Render a one-shot snapshot of the fleet as a string.

        Returns:
            A terminal-formatted string of the fleet dashboard.
        """
        cards = self._build_cards()
        return self._render_cards(cards, {})

    def peek_panel(self, session_id: str) -> str:
        """Render an expanded peek panel for a session.

        Args:
            session_id: The session to expand.

        Returns:
            A terminal-formatted string with session details.
        """
        info = self._fleet.get_session_info(session_id)
        if info is None:
            return f"Session '{session_id}' not found."

        lines: list[str] = []
        lines.append(f"{_BOLD}Session Details{_RESET}")
        lines.append(f"  ID:        {session_id}")
        lines.append(f"  Name:      {info.name}")
        lines.append(f"  State:     {self._color_for_state(info.state.value)}{info.state.value}{_RESET}")
        lines.append(f"  Working:   {info.working_dir}")
        lines.append(f"  Created:   {info.created_at.isoformat()}")
        lines.append(f"  Active:    {info.last_active.isoformat()}")

        # Circuit breaker info
        if self._circuit_breaker is not None:
            try:
                health = self._circuit_breaker.session_health(session_id)
                if health is not None:
                    lines.append(
                        f"  Circuit:   {self._color_for_circuit(health.circuit_state)}"
                        f"{health.circuit_state.value}{_RESET} "
                        f"(low: {health.consecutive_low})"
                    )
            except Exception:
                pass

        # Progress info
        try:
            status = self._fleet.fleet_status()
            for sp in status.sessions:
                if sp.session_id == session_id:
                    lines.append(
                        f"  Checkpts:  {sp.checkpoint_count}  "
                        f"Cost: {sp.cost_estimate:.2f}  "
                        f"Stagnation: L{sp.stagnation_level}"
                    )
                    break
        except Exception:
            pass

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _render(self) -> None:
        """Render the full dashboard to the terminal."""
        cards = self._build_cards()
        output = self._render_cards(cards, self._peek_sessions)
        terminal_width = self._terminal_width()

        # Build header
        now_str = datetime.datetime.now(tz=datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        header = (
            f"{_BOLD}LYRA FLEET DASHBOARD{_RESET}  "
            f"| {_DIM}{now_str}{_RESET}  "
            f"| {len(cards)} sessions  "
            f"| j/k nav | Enter peek | K kill | q quit"
        )
        header = header[:terminal_width]

        # Clear and redraw
        lines = output.split("\n")
        total_lines = len(lines) + 2  # header + status line
        print(_CLEAR_SCREEN, end="")
        print(header)
        for line in lines:
            print(line[:terminal_width])
        print(f"{_DIM}[{len(self._peek_sessions)} peek panels open]{_RESET}", end="", flush=True)

    def _build_cards(self) -> list[TUISessionCard]:
        """Build session cards from fleet state and circuit breaker info."""
        cards: list[TUISessionCard] = []
        try:
            status = self._fleet.fleet_status()
        except Exception:
            return cards

        sessions_list: list[SessionProgress] = list(status.sessions)

        for i, sp in enumerate(sessions_list):
            info = self._fleet.get_session_info(sp.session_id)
            name = info.name if info else sp.session_id[:8]

            # State label and color
            if sp.stagnation_level >= 3:
                state_label = "STUCK"
                state_color = _RED
            elif sp.stagnation_level >= 1:
                state_label = "SLOW"
                state_color = _YELLOW
            elif info and info.state.value == "WORKING":
                state_label = "RUN"
                state_color = _GREEN
            elif info and info.state.value == "STOPPED":
                state_label = "STOP"
                state_color = _GRAY
            elif info and info.state.value == "FAILED":
                state_label = "FAIL"
                state_color = _RED
            else:
                state_label = info.state.value[:4] if info else "?"
                state_color = _GRAY

            # Progress bar
            bar = self._progress_bar(sp.checkpoint_count, 20)

            # Cost
            cost_str = f"{sp.cost_estimate:.1f}"

            # Uptime
            if info:
                uptime = datetime.datetime.now(tz=datetime.timezone.utc) - info.created_at
                uptime_str = self._format_duration(uptime)
            else:
                uptime_str = "?"

            # Circuit badge
            circuit_badge = ""
            if self._circuit_breaker is not None:
                try:
                    health = self._circuit_breaker.session_health(sp.session_id)
                    if health is not None and health.circuit_state != CircuitState.CLOSED:
                        circuit_badge = (
                            f" [{_RED}CIRCUIT {health.circuit_state.value}{_RESET}]"
                        )
                except Exception:
                    pass

            is_selected = i == self._selected_index
            cards.append(TUISessionCard(
                session_id=sp.session_id,
                name=name,
                state_label=state_label,
                state_color=state_color,
                progress_bar=bar,
                cost_str=cost_str,
                uptime_str=uptime_str,
                circuit_badge=circuit_badge,
                is_selected=is_selected,
            ))

        return cards

    def _render_cards(
        self,
        cards: list[TUISessionCard],
        peek_sessions: set[str],
    ) -> str:
        """Render session cards into a formatted string."""
        lines: list[str] = []

        for i, card in enumerate(cards):
            sel_marker = ">" if card.is_selected else " "
            line = (
                f"{sel_marker} "
                f"{card.state_color}{card.state_label}{_RESET} "
                f"{card.uptime_str} "
                f"{card.progress_bar} "
                f"{_DIM}${card.cost_str}{_RESET} "
                f"{_BOLD}{card.name[:20]:20s}{_RESET}"
                f"{card.circuit_badge}"
            )
            lines.append(line)

            # Peek panel
            if card.session_id in peek_sessions:
                peek = self._peek_content(card.session_id)
                for peek_line in peek.split("\n"):
                    lines.append(f"  {_DIM}{peek_line}{_RESET}")
                lines.append("")

        return "\n".join(lines)

    def _peek_content(self, session_id: str) -> str:
        """Generate the expanded content for a peek panel."""
        return self.peek_panel(session_id)

    # ------------------------------------------------------------------
    # Keyboard input
    # ------------------------------------------------------------------

    def _enable_raw_mode(self) -> None:
        """Enable raw terminal input (no line buffering)."""
        try:
            import termios
            import tty
            import sys

            self._fd = sys.stdin.fileno()
            self._old_attr = termios.tcgetattr(self._fd)
            tty.setraw(self._fd)
        except (ImportError, AttributeError, OSError):
            self._fd = None

    def _disable_raw_mode(self) -> None:
        """Restore terminal to cooked mode."""
        if hasattr(self, "_fd") and self._fd is not None:
            try:
                import termios
                import sys

                termios.tcsetattr(self._fd, termios.TCSADRAIN, self._old_attr)
            except (ImportError, AttributeError, OSError):
                pass

    def _read_key(self, timeout: float = 0.5) -> str | None:
        """Read a single keypress with *timeout* seconds.

        Returns None on timeout.
        """
        try:
            import select
            import sys

            if self._fd is None:
                # Fallback: use input() (blocking)
                try:
                    return sys.stdin.read(1)
                except (OSError, EOFError):
                    return None

            readable, _, _ = select.select([self._fd], [], [], timeout)
            if not readable:
                return None

            ch = os.read(self._fd, 3)  # up to 3 bytes for escape sequences
            if len(ch) == 1:
                return ch.decode("utf-8", errors="replace")
            if len(ch) == 3 and ch[0] == 0x1b and ch[1] == 0x5b:
                # Escape sequence: arrow keys
                if ch[2] == 0x41:  # up
                    return "UP"
                if ch[2] == 0x42:  # down
                    return "DOWN"
                if ch[2] == 0x43:  # right
                    return "RIGHT"
                if ch[2] == 0x44:  # left
                    return "LEFT"
            return None
        except (OSError, EOFError, ImportError):
            return None

    def _handle_key(self, key: str) -> None:
        """Process a keypress."""
        status = self._fleet.fleet_status()
        session_count = status.total_sessions

        if key == "q":
            self._running = False
        elif key in ("j", "DOWN"):
            self._selected_index = min(self._selected_index + 1, max(0, session_count - 1))
        elif key in ("k", "UP"):
            self._selected_index = max(self._selected_index - 1, 0)
        elif key == "\r" or key == "\n":  # Enter
            self._toggle_peek()
        elif key == "r":
            pass  # trigger re-render
        elif key in ("K",):
            self._kill_selected()
        elif key == "h":
            self._selected_index = 0
        elif key == "l":
            self._selected_index = max(0, session_count - 1)

    def _toggle_peek(self) -> None:
        """Toggle the peek panel for the selected session."""
        status = self._fleet.fleet_status()
        sessions = list(status.sessions)
        if not sessions or self._selected_index >= len(sessions):
            return
        sid = sessions[self._selected_index].session_id
        if sid in self._peek_sessions:
            self._peek_sessions.remove(sid)
        else:
            self._peek_sessions.add(sid)

    def _kill_selected(self) -> None:
        """Kill the selected session (no confirmation in test mode)."""
        status = self._fleet.fleet_status()
        sessions = list(status.sessions)
        if not sessions or self._selected_index >= len(sessions):
            return
        sid = sessions[self._selected_index].session_id
        try:
            self._fleet.kill_session(sid)
            self._peek_sessions.discard(sid)
            logger.info("tui_killed_session", session_id=sid)
        except Exception as exc:
            logger.error("tui_kill_failed", session_id=sid, error=str(exc))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _terminal_width() -> int:
        """Return the current terminal width (default 80)."""
        try:
            import shutil

            return shutil.get_terminal_size().columns
        except (ImportError, ValueError):
            return 80

    @staticmethod
    def _color_for_state(state: str) -> str:
        """Return ANSI color code for a session state."""
        color_map: dict[str, str] = {
            "WORKING": _GREEN,
            "IDLE": _YELLOW,
            "STOPPED": _GRAY,
            "FAILED": _RED,
            "COMPLETED": _GRAY,
            "NEEDS_INPUT": _YELLOW,
        }
        return color_map.get(state, _RESET)

    @staticmethod
    def _color_for_circuit(state: CircuitState) -> str:
        """Return ANSI color code for a circuit state."""
        if state == CircuitState.CLOSED:
            return _GREEN
        if state == CircuitState.OPEN:
            return _RED
        return _YELLOW  # HALF_OPEN

    @staticmethod
    def _progress_bar(value: int, max_ticks: int = 20) -> str:
        """Render an ASCII progress bar."""
        filled = min(value, max_ticks)
        empty = max_ticks - filled
        return f"[{'#' * filled}{'.' * empty}]"

    @staticmethod
    def _format_duration(delta: datetime.timedelta) -> str:
        """Format a timedelta as a short duration string."""
        total_seconds = int(delta.total_seconds())
        if total_seconds < 60:
            return f"{total_seconds}s"
        minutes = total_seconds // 60
        if minutes < 60:
            return f"{minutes}m"
        hours = minutes // 60
        minutes = minutes % 60
        if hours < 24:
            return f"{hours}h{minutes:02d}m"
        days = hours // 24
        hours = hours % 24
        return f"{days}d{hours:02d}h"
