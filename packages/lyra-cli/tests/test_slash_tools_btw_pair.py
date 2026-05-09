"""Tests for ``/tools`` + ``/btw`` + ``/pair`` (Wave-C Task 14).

Contract:

``/tools``
    - No arg → lists every registered tool with name, risk, summary.
    - ``/tools <name>`` → detailed view for one tool, including
      ``origin`` and the milestone tag from ``planned``.
    - ``/tools risk=<level>`` → filtered list (low | medium | high).
    - Unknown name → friendly "no such tool" message.

``/btw <topic>``
    - Records the question in a separate side-channel
      (``session._btw_log``), NOT in ``session.history``.
    - Echoes back with a "btw:" prefix so the user sees confirmation.
    - Empty input → usage line.
    - Survives across multiple invocations (FIFO order preserved).

``/pair``
    - First invocation flips ``session.pair_mode`` ON and emits a
      "pair mode: on" toast.
    - Second invocation flips it OFF.
    - ``/pair on`` / ``/pair off`` set explicitly.
    - When pair mode is on, the status line includes ``pair: on``.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from lyra_cli.interactive.session import InteractiveSession


def _session(tmp_path: Path) -> InteractiveSession:
    return InteractiveSession(repo_root=tmp_path)


# ---------------------------------------------------------------------------
# /tools
# ---------------------------------------------------------------------------


def test_tools_lists_every_registered_tool(tmp_path: Path) -> None:
    out = _session(tmp_path).dispatch("/tools").output or ""
    # Every shipped tool name must show up — Read/Write/Bash are the
    # canonical "v1 Phase 1" trio, while Skill/Delegate appear at
    # later milestones.
    for name in ("Read", "Glob", "Grep", "Edit", "Write", "Bash", "Skill"):
        assert name in out, f"/tools should mention {name}; got:\n{out}"


def test_tools_detail_view(tmp_path: Path) -> None:
    out = _session(tmp_path).dispatch("/tools Read").output or ""
    # Detail must include the milestone tag and origin so users know
    # whether the tool ships today vs. lands in a future wave.
    assert "Read" in out
    assert "low" in out  # risk
    assert "v1 Phase 1" in out  # planned


def test_tools_filter_by_risk(tmp_path: Path) -> None:
    out = _session(tmp_path).dispatch("/tools risk=high").output or ""
    assert "Bash" in out
    assert "ExecuteCode" in out
    # Low-risk tools must NOT show up in a high-risk filter
    assert "Read" not in out


def test_tools_unknown_name(tmp_path: Path) -> None:
    out = _session(tmp_path).dispatch("/tools NoSuchTool").output or ""
    assert "no such tool" in out.lower() or "unknown" in out.lower()


# ---------------------------------------------------------------------------
# /btw
# ---------------------------------------------------------------------------


def test_btw_records_side_channel(tmp_path: Path) -> None:
    session = _session(tmp_path)
    session.dispatch("/btw what does this script do?")
    log = getattr(session, "_btw_log", [])
    assert log, "/btw should append to session._btw_log"
    assert log[-1] == "what does this script do?"


def test_btw_does_not_pollute_main_history(tmp_path: Path) -> None:
    session = _session(tmp_path)
    session.dispatch("/btw quick aside")
    # The main session.history captures the slash itself (so /history
    # works), but the *plain question* must NOT enter the agent's
    # main context (that's the whole point of /btw).
    assert all("quick aside" not in line or line.startswith("/btw") for line in session.history)


def test_btw_preserves_fifo_order(tmp_path: Path) -> None:
    session = _session(tmp_path)
    session.dispatch("/btw first")
    session.dispatch("/btw second")
    log = getattr(session, "_btw_log", [])
    assert log == ["first", "second"]


def test_btw_empty_input(tmp_path: Path) -> None:
    out = _session(tmp_path).dispatch("/btw").output or ""
    assert "usage" in out.lower() or "topic" in out.lower()


# ---------------------------------------------------------------------------
# /pair
# ---------------------------------------------------------------------------


def test_pair_toggles_state(tmp_path: Path) -> None:
    session = _session(tmp_path)
    assert getattr(session, "pair_mode", False) is False
    session.dispatch("/pair")
    assert session.pair_mode is True
    session.dispatch("/pair")
    assert session.pair_mode is False


def test_pair_explicit_on_off(tmp_path: Path) -> None:
    session = _session(tmp_path)
    session.dispatch("/pair on")
    assert session.pair_mode is True
    session.dispatch("/pair off")
    assert session.pair_mode is False


def test_pair_status_line_reflects_mode(tmp_path: Path) -> None:
    session = _session(tmp_path)
    session.dispatch("/pair on")
    line = session.status_line()
    assert "pair" in line.lower()
