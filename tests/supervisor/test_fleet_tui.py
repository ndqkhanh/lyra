"""Tests for src/lyra/supervisor/fleet_tui.py — 85%+ coverage target.

FleetTUI is heavily terminal-interactive.  We test public methods,
rendering logic, and keyboard handling by mocking the FleetOrchestrator
and circuit breaker dependencies.
"""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from lyra.supervisor.circuit_breaker import CircuitState, LoopHealth
from lyra.supervisor.fleet import FleetOrchestrator, FleetStatus, SessionProgress
from lyra.supervisor.fleet_tui import (
    TUISessionCard,
    FleetTUI,
    FleetTUIConfig,
    _RESET,
    _BOLD,
    _DIM,
    _GREEN,
    _YELLOW,
    _RED,
    _GRAY,
    _CYAN,
)
from lyra.supervisor.state import ProcessState, SessionInfo, SessionState


# =========================================================================
# TUISessionCard
# =========================================================================


class TestTUISessionCard:
    def test_defaults(self):
        card = TUISessionCard(
            session_id="s1", name="test", state_label="RUN",
            state_color=_GREEN, progress_bar="[###.............]", cost_str="1.5",
            uptime_str="5m", circuit_badge="",
        )
        assert not card.is_selected

    def test_frozen(self):
        card = TUISessionCard(
            session_id="s1", name="test", state_label="RUN",
            state_color=_GREEN, progress_bar="[]", cost_str="0",
            uptime_str="0s", circuit_badge="",
        )
        with pytest.raises(AttributeError):
            card.is_selected = True  # frozen=True prevents mutation


# =========================================================================
# FleetTUIConfig
# =========================================================================


class TestFleetTUIConfig:
    def test_defaults(self):
        cfg = FleetTUIConfig()
        assert cfg.auto_refresh_seconds == 2.0
        assert cfg.max_visible_sessions == 20
        assert cfg.peek_lines == 10
        assert cfg.color_enabled is True


# =========================================================================
# FleetTUI — static helpers
# =========================================================================


class TestFleetTUIStatics:
    def test_terminal_width(self):
        with patch("shutil.get_terminal_size") as mock:
            mock.return_value.columns = 120
            assert FleetTUI._terminal_width() == 120

    def test_terminal_width_fallback(self):
        with patch("shutil.get_terminal_size", side_effect=ImportError("no shutil")):
            assert FleetTUI._terminal_width() == 80

    def test_terminal_width_value_error(self):
        with patch("shutil.get_terminal_size", side_effect=ValueError("bad")):
            assert FleetTUI._terminal_width() == 80

    def test_color_for_state(self):
        assert FleetTUI._color_for_state("WORKING") == _GREEN
        assert FleetTUI._color_for_state("IDLE") == _YELLOW
        assert FleetTUI._color_for_state("STOPPED") == _GRAY
        assert FleetTUI._color_for_state("FAILED") == _RED
        assert FleetTUI._color_for_state("COMPLETED") == _GRAY
        assert FleetTUI._color_for_state("NEEDS_INPUT") == _YELLOW
        assert FleetTUI._color_for_state("UNKNOWN") == _RESET

    def test_color_for_circuit(self):
        assert FleetTUI._color_for_circuit(CircuitState.CLOSED) == _GREEN
        assert FleetTUI._color_for_circuit(CircuitState.OPEN) == _RED
        assert FleetTUI._color_for_circuit(CircuitState.HALF_OPEN) == _YELLOW

    def test_progress_bar(self):
        assert FleetTUI._progress_bar(5, 10) == "[#####.....]"
        assert FleetTUI._progress_bar(0, 5) == "[.....]"
        assert FleetTUI._progress_bar(20, 10) == "[##########]"  # clamped to max_ticks

    def test_format_duration(self):
        td = datetime.timedelta
        assert FleetTUI._format_duration(td(seconds=30)) == "30s"
        assert FleetTUI._format_duration(td(minutes=5)) == "5m"
        assert FleetTUI._format_duration(td(hours=2, minutes=30)) == "2h30m"
        assert FleetTUI._format_duration(td(days=3, hours=4)) == "3d04h"


# =========================================================================
# FleetTUI — _build_cards
# =========================================================================


def _make_fleet_status(
    sessions: list[tuple[str, int, int, float]] = None,
) -> FleetStatus:
    """Helper: build a FleetStatus with sensible defaults."""
    if sessions is None:
        sessions = [("s1", 0, 5, 1.0)]
    progress = tuple(
        SessionProgress(
            session_id=sid,
            checkpoint_count=ck,
            stagnation_level=stg,
            cost_estimate=cost,
        )
        for sid, ck, stg, cost in sessions
    )
    return FleetStatus(
        total_sessions=len(progress),
        active_count=sum(1 for p in progress if p.stagnation_level == 0),
        stagnant_count=sum(1 for p in progress if p.stagnation_level > 0),
        gpu_allocated_count=0,
        sessions=progress,
    )


def _make_session_info(
    session_id: str = "s1",
    name: str = "test-agent",
    state: SessionState = SessionState.WORKING,
    process: ProcessState = ProcessState.ALIVE,
) -> SessionInfo:
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    return SessionInfo(
        session_id=session_id,
        name=name,
        state=state,
        process_state=process,
        working_dir="/tmp/work",
        created_at=now,
        last_active=now,
    )


class TestBuildCards:
    def test_empty_fleet(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.fleet_status.return_value = _make_fleet_status([])
        tui = FleetTUI(fleet)
        cards = tui._build_cards()
        assert cards == []

    def test_fleet_status_raises(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.fleet_status.side_effect = RuntimeError("boom")
        tui = FleetTUI(fleet)
        cards = tui._build_cards()
        assert cards == []

    def test_single_session_working(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.fleet_status.return_value = _make_fleet_status([("s1", 5, 0, 2.5)])
        fleet.get_session_info.return_value = _make_session_info("s1", "agent-1")
        tui = FleetTUI(fleet)
        cards = tui._build_cards()
        assert len(cards) == 1
        assert cards[0].state_label == "RUN"
        assert cards[0].state_color == _GREEN

    def test_session_stuck(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.fleet_status.return_value = _make_fleet_status([("s1", 0, 3, 0.0)])
        fleet.get_session_info.return_value = _make_session_info("s1", "stuck")
        tui = FleetTUI(fleet)
        cards = tui._build_cards()
        assert cards[0].state_label == "STUCK"
        assert cards[0].state_color == _RED

    def test_session_slow(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.fleet_status.return_value = _make_fleet_status([("s1", 1, 1, 0.5)])
        fleet.get_session_info.return_value = _make_session_info("s1", "slow")
        tui = FleetTUI(fleet)
        cards = tui._build_cards()
        assert cards[0].state_label == "SLOW"
        assert cards[0].state_color == _YELLOW

    def test_session_stopped(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.fleet_status.return_value = _make_fleet_status([("s1", 0, 0, 0.0)])
        fleet.get_session_info.return_value = _make_session_info("s1", "stopped", state=SessionState.STOPPED)
        tui = FleetTUI(fleet)
        cards = tui._build_cards()
        assert cards[0].state_label == "STOP"
        assert cards[0].state_color == _GRAY

    def test_session_failed(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.fleet_status.return_value = _make_fleet_status([("s1", 0, 0, 0.0)])
        fleet.get_session_info.return_value = _make_session_info("s1", "failed", state=SessionState.FAILED)
        tui = FleetTUI(fleet)
        cards = tui._build_cards()
        assert cards[0].state_label == "FAIL"
        assert cards[0].state_color == _RED

    def test_session_unknown_state(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.fleet_status.return_value = _make_fleet_status([("s1", 0, 0, 0.0)])
        fleet.get_session_info.return_value = _make_session_info("s1", "unknown", state=SessionState.IDLE)
        tui = FleetTUI(fleet)
        cards = tui._build_cards()
        # IDLE state -> falls into the else branch, shows first 4 chars
        assert cards[0].state_label == "IDLE"

    def test_session_info_not_found(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.fleet_status.return_value = _make_fleet_status([("s1", 3, 0, 1.0)])
        fleet.get_session_info.return_value = None
        tui = FleetTUI(fleet)
        cards = tui._build_cards()
        assert cards[0].name == "s1"  # fallback to session_id[:8]
        assert cards[0].state_label == "?"

    def test_selected_index_marks_card(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.fleet_status.return_value = _make_fleet_status([("s1", 0, 0, 0.0), ("s2", 0, 0, 0.0)])
        fleet.get_session_info.return_value = _make_session_info("s1", "a")
        tui = FleetTUI(fleet)
        tui._selected_index = 1
        cards = tui._build_cards()
        assert cards[0].is_selected is False
        assert cards[1].is_selected is True

    def test_circuit_badge_not_closed(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.fleet_status.return_value = _make_fleet_status([("s1", 0, 0, 0.0)])
        fleet.get_session_info.return_value = _make_session_info("s1")

        cb = MagicMock()
        health = LoopHealth(
            session_id="s1", circuit_state=CircuitState.OPEN,
            consecutive_low=3, last_confidence=0.2, trip_count=1,
        )
        cb.session_health.return_value = health

        tui = FleetTUI(fleet, circuit_breaker=cb)
        cards = tui._build_cards()
        assert "CIRCUIT" in cards[0].circuit_badge

    def test_circuit_badge_closed_omits(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.fleet_status.return_value = _make_fleet_status([("s1", 0, 0, 0.0)])
        fleet.get_session_info.return_value = _make_session_info("s1")
        cb = MagicMock()
        health = LoopHealth(
            session_id="s1", circuit_state=CircuitState.CLOSED,
            consecutive_low=0, last_confidence=1.0, trip_count=0,
        )
        cb.session_health.return_value = health
        tui = FleetTUI(fleet, circuit_breaker=cb)
        cards = tui._build_cards()
        assert cards[0].circuit_badge == ""

    def test_circuit_breaker_health_raises(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.fleet_status.return_value = _make_fleet_status([("s1", 0, 0, 0.0)])
        fleet.get_session_info.return_value = _make_session_info("s1")
        cb = MagicMock()
        cb.session_health.side_effect = RuntimeError("cb error")
        tui = FleetTUI(fleet, circuit_breaker=cb)
        cards = tui._build_cards()
        assert cards[0].circuit_badge == ""


# =========================================================================
# FleetTUI — _render_cards
# =========================================================================


class TestRenderCards:
    def test_render_cards_no_peek(self):
        card = TUISessionCard(
            session_id="s1", name="test", state_label="RUN", state_color=_GREEN,
            progress_bar="[###]", cost_str="1.0", uptime_str="5m",
            circuit_badge="", is_selected=True,
        )
        tui = FleetTUI(MagicMock(spec=FleetOrchestrator))
        output = tui._render_cards([card], set())
        assert "RUN" in output
        assert ">" in output  # selected marker

    def test_render_cards_with_peek(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.get_session_info.return_value = _make_session_info("s1", "peeked")
        fleet.fleet_status.return_value = _make_fleet_status([("s1", 3, 0, 1.0)])

        card = TUISessionCard(
            session_id="s1", name="peeked", state_label="RUN", state_color=_GREEN,
            progress_bar="[###]", cost_str="1.0", uptime_str="5m",
            circuit_badge="", is_selected=False,
        )
        tui = FleetTUI(fleet)
        output = tui._render_cards([card], {"s1"})
        assert "peeked" in output
        assert "Session Details" in output

    def test_render_cards_circuit_badge_appended(self):
        card = TUISessionCard(
            session_id="s1", name="test", state_label="RUN", state_color=_GREEN,
            progress_bar="[]", cost_str="0", uptime_str="0s",
            circuit_badge=" [OPEN]", is_selected=False,
        )
        tui = FleetTUI(MagicMock(spec=FleetOrchestrator))
        output = tui._render_cards([card], set())
        assert "OPEN" in output


# =========================================================================
# FleetTUI — peek_panel
# =========================================================================


class TestPeekPanel:
    def test_session_not_found(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.get_session_info.return_value = None
        tui = FleetTUI(fleet)
        result = tui.peek_panel("nonexistent")
        assert "not found" in result

    def test_with_circuit_breaker(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.get_session_info.return_value = _make_session_info("s1", "testy")
        fleet.fleet_status.return_value = _make_fleet_status([("s1", 3, 0, 1.5)])

        cb = MagicMock()
        health = LoopHealth(
            session_id="s1", circuit_state=CircuitState.HALF_OPEN,
            consecutive_low=1, last_confidence=0.5, trip_count=1,
        )
        cb.session_health.return_value = health

        tui = FleetTUI(fleet, circuit_breaker=cb)
        result = tui.peek_panel("s1")
        assert "testy" in result
        assert "HALF_OPEN" in result

    def test_circuit_breaker_session_health_none(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.get_session_info.return_value = _make_session_info("s1")
        fleet.fleet_status.return_value = _make_fleet_status([("s1", 0, 0, 0.0)])

        cb = MagicMock()
        cb.session_health.return_value = None

        tui = FleetTUI(fleet, circuit_breaker=cb)
        result = tui.peek_panel("s1")
        # Should still work but with no circuit info
        assert "s1" in result

    def test_circuit_breaker_health_raises_in_peek(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.get_session_info.return_value = _make_session_info("s1")
        fleet.fleet_status.return_value = _make_fleet_status([("s1", 0, 0, 0.0)])

        cb = MagicMock()
        cb.session_health.side_effect = RuntimeError("cb fail")

        tui = FleetTUI(fleet, circuit_breaker=cb)
        result = tui.peek_panel("s1")
        assert "s1" in result  # still renders without circuit info

    def test_fleet_status_raises_in_peek(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.get_session_info.return_value = _make_session_info("s1")
        fleet.fleet_status.side_effect = RuntimeError("fleet fail")

        tui = FleetTUI(fleet)
        result = tui.peek_panel("s1")
        assert "s1" in result


# =========================================================================
# FleetTUI — keyboard handling
# =========================================================================


class TestKeyHandling:
    def test_key_q_stops(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.fleet_status.return_value = _make_fleet_status([("s1", 0, 0, 0.0)])
        tui = FleetTUI(fleet)
        assert tui._running is False
        tui._running = True
        tui._handle_key("q")
        assert tui._running is False

    def test_key_down(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.fleet_status.return_value = _make_fleet_status([("s1", 0, 0, 0.0), ("s2", 0, 0, 0.0)])
        tui = FleetTUI(fleet)
        tui._selected_index = 0
        tui._handle_key("j")
        assert tui._selected_index == 1
        tui._handle_key("DOWN")
        assert tui._selected_index == 1  # clamped at max

    def test_key_up(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.fleet_status.return_value = _make_fleet_status([("s1", 0, 0, 0.0)])
        tui = FleetTUI(fleet)
        tui._selected_index = 0
        tui._handle_key("k")
        assert tui._selected_index == 0  # clamped at 0

    def test_key_up_from_positive(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.fleet_status.return_value = _make_fleet_status([("s1", 0, 0, 0.0), ("s2", 0, 0, 0.0)])
        tui = FleetTUI(fleet)
        tui._selected_index = 1
        tui._handle_key("UP")
        assert tui._selected_index == 0

    def test_key_home(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.fleet_status.return_value = _make_fleet_status([("s1", 0, 0, 0.0), ("s2", 0, 0, 0.0)])
        tui = FleetTUI(fleet)
        tui._selected_index = 1
        tui._handle_key("h")
        assert tui._selected_index == 0

    def test_key_end(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.fleet_status.return_value = _make_fleet_status([("s1", 0, 0, 0.0), ("s2", 0, 0, 0.0)])
        tui = FleetTUI(fleet)
        tui._selected_index = 0
        tui._handle_key("l")
        assert tui._selected_index == 1

    def test_key_enter_toggle_peek(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.fleet_status.return_value = _make_fleet_status([("s1", 0, 0, 0.0)])
        tui = FleetTUI(fleet)
        tui._handle_key("\r")
        assert "s1" in tui._peek_sessions
        tui._handle_key("\r")
        assert "s1" not in tui._peek_sessions

    def test_key_enter_no_sessions(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.fleet_status.return_value = _make_fleet_status([])
        tui = FleetTUI(fleet)
        tui._handle_key("\r")  # should not crash
        assert tui._peek_sessions == set()

    def test_key_k_kill_selected(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.fleet_status.return_value = _make_fleet_status([("s1", 0, 0, 0.0)])
        fleet.get_session_info.return_value = _make_session_info("s1")
        tui = FleetTUI(fleet)
        tui._handle_key("K")
        fleet.kill_session.assert_called_once_with("s1")

    def test_key_k_kill_nonexistent_session(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.fleet_status.return_value = _make_fleet_status([("s1", 0, 0, 0.0)])
        tui = FleetTUI(fleet)
        tui._selected_index = 99  # out of range
        tui._handle_key("K")  # should not crash

    def test_key_k_kill_raises(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.fleet_status.return_value = _make_fleet_status([("s1", 0, 0, 0.0)])
        fleet.kill_session.side_effect = RuntimeError("kill failed")
        tui = FleetTUI(fleet)
        tui._handle_key("K")  # should not crash

    def test_key_r_does_not_crash(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.fleet_status.return_value = _make_fleet_status([("s1", 0, 0, 0.0)])
        tui = FleetTUI(fleet)
        tui._handle_key("r")  # no-op, just re-render
        assert tui._running is False


# =========================================================================
# FleetTUI — raw mode and _read_key
# =========================================================================


class TestRawModeAndReadKey:
    def test_enable_raw_mode_fallback(self):
        """When termios is unavailable, _fd stays None."""
        fleet = MagicMock(spec=FleetOrchestrator)
        tui = FleetTUI(fleet)
        with patch.dict("sys.modules", {"termios": None, "tty": None}):
            import builtins
            real_import = builtins.__import__

            def mock_import(name, *args, **kwargs):
                if name in ("termios", "tty"):
                    raise ImportError("no termios")
                return real_import(name, *args, **kwargs)

            with patch("builtins.__import__", side_effect=mock_import):
                tui._enable_raw_mode()
                assert tui._fd is None

    def test_enable_raw_mode_os_error(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        tui = FleetTUI(fleet)
        with patch("tty.setraw", side_effect=OSError("no tty")):
            with patch("termios.tcgetattr", return_value=[]):
                with patch("termios.tcsetattr"):
                    tui._enable_raw_mode()
                    assert tui._fd is None

    def test_disable_raw_mode_no_op_when_fd_none(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        tui = FleetTUI(fleet)
        tui._fd = None
        tui._disable_raw_mode()  # should not raise

    def test_disable_raw_mode_fallback(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        tui = FleetTUI(fleet)
        tui._fd = 999
        tui._old_attr = []
        with patch("termios.tcsetattr", side_effect=OSError("no tty")):
            tui._disable_raw_mode()  # should not raise

    def test_read_key_fd_none_fallback(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        tui = FleetTUI(fleet)
        tui._fd = None
        with patch("sys.stdin.read", return_value="q"):
            key = tui._read_key(timeout=0.0)
            assert key == "q"

    def test_read_key_fd_none_eof_error(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        tui = FleetTUI(fleet)
        tui._fd = None
        with patch("sys.stdin.read", side_effect=EOFError()):
            key = tui._read_key(timeout=0.0)
            assert key is None

    def test_read_key_timeout(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        tui = FleetTUI(fleet)
        tui._fd = 0
        with patch("select.select", return_value=([], [], [])):
            key = tui._read_key(timeout=0.01)
            assert key is None

    def test_read_key_single_byte(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        tui = FleetTUI(fleet)
        tui._fd = 0
        with patch("select.select", return_value=([0], [], [])):
            with patch("os.read", return_value=b"q"):
                key = tui._read_key(timeout=0.01)
                assert key == "q"

    def test_read_key_escape_up(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        tui = FleetTUI(fleet)
        tui._fd = 0
        with patch("select.select", return_value=([0], [], [])):
            with patch("os.read", return_value=b"\x1b[A"):
                key = tui._read_key(timeout=0.01)
                assert key == "UP"

    def test_read_key_escape_down(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        tui = FleetTUI(fleet)
        tui._fd = 0
        with patch("select.select", return_value=([0], [], [])):
            with patch("os.read", return_value=b"\x1b[B"):
                key = tui._read_key(timeout=0.01)
                assert key == "DOWN"

    def test_read_key_escape_right(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        tui = FleetTUI(fleet)
        tui._fd = 0
        with patch("select.select", return_value=([0], [], [])):
            with patch("os.read", return_value=b"\x1b[C"):
                key = tui._read_key(timeout=0.01)
                assert key == "RIGHT"

    def test_read_key_escape_left(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        tui = FleetTUI(fleet)
        tui._fd = 0
        with patch("select.select", return_value=([0], [], [])):
            with patch("os.read", return_value=b"\x1b[D"):
                key = tui._read_key(timeout=0.01)
                assert key == "LEFT"

    def test_read_key_escape_non_arrow(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        tui = FleetTUI(fleet)
        tui._fd = 0
        with patch("select.select", return_value=([0], [], [])):
            with patch("os.read", return_value=b"\x1b[Z"):  # tab
                key = tui._read_key(timeout=0.01)
                assert key is None

    def test_read_key_os_error(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        tui = FleetTUI(fleet)
        tui._fd = 0
        with patch("select.select", side_effect=OSError("io")):
            key = tui._read_key(timeout=0.01)
            assert key is None

    def test_run_keyboard_interrupt(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        tui = FleetTUI(fleet)
        tui._running = True
        tui._selected_index = 0
        tui._peek_sessions.add("test")
        with patch.object(tui, "_render"):
            with patch.object(tui, "_read_key", side_effect=KeyboardInterrupt()):
                with patch.object(tui, "_enable_raw_mode"):
                    with patch.object(tui, "_disable_raw_mode"):
                        tui.run()
                        assert tui._running is False

    def test_stop(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        tui = FleetTUI(fleet)
        tui._running = True
        tui.stop()
        assert tui._running is False


# =========================================================================
# FleetTUI — render_fleet (one-shot)
# =========================================================================


class TestRenderFleet:
    def test_render_fleet_empty(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.fleet_status.return_value = _make_fleet_status([])
        tui = FleetTUI(fleet)
        output = tui.render_fleet()
        assert isinstance(output, str)

    def test_render_fleet_with_sessions(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.fleet_status.return_value = _make_fleet_status([("s1", 3, 0, 1.5)])
        fleet.get_session_info.return_value = _make_session_info("s1", "render-test")
        tui = FleetTUI(fleet)
        output = tui.render_fleet()
        assert "render-test" in output


# =========================================================================
# FleetTUI — _toggle_peek edge cases
# =========================================================================


class TestTogglePeek:
    def test_toggle_empty_fleet(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.fleet_status.return_value = _make_fleet_status([])
        tui = FleetTUI(fleet)
        tui._toggle_peek()  # should not crash

    def test_toggle_out_of_range(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.fleet_status.return_value = _make_fleet_status([("s1", 0, 0, 0.0)])
        tui = FleetTUI(fleet)
        tui._selected_index = 10  # out of range
        tui._toggle_peek()  # should not crash


# =========================================================================
# FleetTUI — render output truncation
# =========================================================================


class TestRender:
    def test_render_peek_status_line(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.fleet_status.return_value = _make_fleet_status([("s1", 1, 0, 0.5)])
        fleet.get_session_info.return_value = _make_session_info("s1")
        cb = MagicMock()
        tui = FleetTUI(fleet, circuit_breaker=cb)
        tui._peek_sessions.add("s1")
        with patch.object(tui, "_terminal_width", return_value=120):
            with patch("builtins.print") as mock_print:
                tui._render()
                # Should have printed at least 3 lines (header, content, status)
                assert mock_print.call_count >= 3
