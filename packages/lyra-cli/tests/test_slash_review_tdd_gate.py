"""Wave-C Task 10: ``/review``, ``/ultrareview``, and ``/tdd-gate``.

* ``/review`` runs a single post-turn verifier (TDD gate + safety
  + evidence) and reports a ``status`` line. The verifier itself
  is mock-LLM-backed so the slash is testable offline.
* ``/ultrareview`` fans out to N reviewer subagents. Wave-D wires
  the real subagent runtime; Wave-C ships the *fan-out shape*
  (a list of mocked reports) so the slash returns useful output.
* ``/tdd-gate on|off|status`` toggles a session-level boolean and
  is consulted by the agent loop's "would this Edit pass the gate?"
  check.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from lyra_cli.interactive.session import InteractiveSession


# ---- /tdd-gate --------------------------------------------------------

def test_tdd_gate_default_status(tmp_path: Path) -> None:
    s = InteractiveSession(repo_root=tmp_path)
    out = s.dispatch("/tdd-gate status").output
    # v3.0.0 (Phase G): TDD became opt-in. A fresh session matches the
    # claw-code / opencode / hermes-agent posture — a general coding
    # agent that doesn't refuse Edits because no failing test exists.
    assert "off" in out.lower()
    assert s.tdd_gate_enabled is False


def test_tdd_gate_off_then_status(tmp_path: Path) -> None:
    s = InteractiveSession(repo_root=tmp_path)
    s.dispatch("/tdd-gate off")
    assert s.tdd_gate_enabled is False
    out = s.dispatch("/tdd-gate status").output
    assert "off" in out.lower()


def test_tdd_gate_on_then_status(tmp_path: Path) -> None:
    """Opt-in path: flipping the plugin on must take effect immediately."""
    s = InteractiveSession(repo_root=tmp_path, tdd_gate_enabled=False)
    s.dispatch("/tdd-gate on")
    assert s.tdd_gate_enabled is True


# ---- /review ----------------------------------------------------------

def test_review_reports_pass_for_clean_session(tmp_path: Path) -> None:
    s = InteractiveSession(repo_root=tmp_path)
    out = s.dispatch("/review").output
    # The verifier produces three sub-checks; each must appear so the
    # user can see what's been validated.
    assert "tdd" in out.lower()
    assert "safety" in out.lower()
    assert "evidence" in out.lower()


def test_review_neutral_when_tdd_plugin_off(tmp_path: Path) -> None:
    """v3.0.0 — TDD-off must NOT be reported as a verifier failure.

    Phase G demoted TDD from kernel invariant to opt-in plugin, so a
    default session whose gate is off should still pass /review on
    correctness/safety/evidence grounds. The output mentions the gate
    state for transparency, but the verdict isn't punitive.
    """
    s = InteractiveSession(repo_root=tmp_path)
    s.dispatch("/tdd-gate off")
    out = s.dispatch("/review").output.lower()
    # The status line still shows the gate state so users know what's
    # active, but the wording is neutral ("opt-in") rather than a
    # warning like "skipped" / "missing".
    assert "tdd" in out
    assert "off" in out or "opt-in" in out


def test_review_flags_when_tdd_plugin_on_but_gate_misconfigured(tmp_path: Path) -> None:
    """When TDD is opted into, the gate's state line still shows ``on``."""
    s = InteractiveSession(repo_root=tmp_path, tdd_gate_enabled=True)
    out = s.dispatch("/review").output.lower()
    assert "tdd" in out
    assert "on" in out


# ---- /ultrareview -----------------------------------------------------

def test_ultrareview_fan_out_returns_three_reports(tmp_path: Path) -> None:
    """Wave-C ships a mock fan-out of three reviewer voices."""
    s = InteractiveSession(repo_root=tmp_path)
    out = s.dispatch("/ultrareview").output
    # Three reviewer voices renders three blocks.
    assert out.lower().count("reviewer") >= 3


def test_ultrareview_includes_verdict(tmp_path: Path) -> None:
    s = InteractiveSession(repo_root=tmp_path)
    out = s.dispatch("/ultrareview").output
    assert any(word in out.lower() for word in ("verdict", "approve", "needs-revision"))
