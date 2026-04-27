"""Phase 13 — Red tests for the interactive session dispatcher.

Claude-Code-style shell: ``lyra`` with no args drops into a prompt
loop. Plain-text input in the current mode calls the mode's handler;
``/`` prefixes are slash commands (meta).

The dispatcher is a pure function of its state, so tests exercise it
without any TTY, subprocess, or prompt_toolkit. The heavy driver is
covered by CLI smoke tests separately.

Contract pinned here (Phase 13 DoD):
- default mode is ``plan``;
- ``/help`` enumerates every registered slash command;
- ``/status`` surfaces mode, model, turn, cost;
- ``/mode <plan|run|retro>`` switches; unknown mode stays put with a hint;
- ``/exit``, ``/quit`` terminate; ``/clear`` asks the driver to clear;
- unknown ``/<name>`` returns a help hint and does not increment turn;
- ``/history`` returns the user-typed lines in order;
- ``/model <name>`` replaces the model;
- plain text is routed by mode; empty lines are no-ops.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from lyra_cli.interactive.session import (
    SLASH_COMMANDS,
    CommandResult,
    InteractiveSession,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def session(tmp_path: Path) -> InteractiveSession:
    return InteractiveSession(
        repo_root=tmp_path,
        model="claude-opus-4.5",
    )


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------


def test_default_mode_is_agent(session: InteractiveSession) -> None:
    """v3.2.0: REPL boots in ``agent`` (full-access execution) to match
    Claude Code's 4-mode taxonomy. Pre-v3.2 booted in ``build`` which
    was the same idea under a different label; pre-v2.2 booted in
    ``plan`` which confused users (typing "hello" recorded a "task"
    instead of replying)."""
    assert session.mode == "agent"
    assert session.turn == 0
    assert session.cost_usd == 0.0
    assert session.history == []


# ---------------------------------------------------------------------------
# /help
# ---------------------------------------------------------------------------


def test_slash_help_enumerates_every_registered_command(
    session: InteractiveSession,
) -> None:
    """/help must list every command in SLASH_COMMANDS — no silent gaps."""
    result = session.dispatch("/help")
    for name in SLASH_COMMANDS:
        assert f"/{name}" in result.output, f"{name!r} missing from /help"
    assert not result.should_exit
    assert not result.clear_screen


def test_slash_help_does_not_count_as_a_turn(
    session: InteractiveSession,
) -> None:
    """Meta commands don't bill a turn; only agent-facing actions do."""
    session.dispatch("/help")
    assert session.turn == 0


# ---------------------------------------------------------------------------
# /status
# ---------------------------------------------------------------------------


def test_slash_status_reports_mode_model_turn_cost(
    session: InteractiveSession,
) -> None:
    result = session.dispatch("/status")
    out = result.output
    assert "agent" in out  # mode (v3.2.0: default is now agent)
    assert "claude-opus-4.5" in out  # model
    assert "turn" in out.lower()
    assert "cost" in out.lower()


# ---------------------------------------------------------------------------
# /mode
# ---------------------------------------------------------------------------


def test_slash_mode_switches_mode(session: InteractiveSession) -> None:
    result = session.dispatch("/mode debug")
    assert session.mode == "debug"
    assert result.new_mode == "debug"
    assert "debug" in result.output.lower()


def test_slash_mode_rejects_unknown_mode(session: InteractiveSession) -> None:
    result = session.dispatch("/mode banana")
    assert session.mode == "agent"  # unchanged (v3.2.0 default)
    assert result.new_mode is None
    assert "unknown mode" in result.output.lower()


def test_slash_mode_without_argument_shows_current(
    session: InteractiveSession,
) -> None:
    result = session.dispatch("/mode")
    assert "agent" in result.output.lower()
    assert session.mode == "agent"


# ---------------------------------------------------------------------------
# /exit, /quit, /clear
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("cmd", ["/exit", "/quit"])
def test_slash_exit_and_quit_terminate(
    cmd: str, session: InteractiveSession
) -> None:
    result = session.dispatch(cmd)
    assert result.should_exit is True


def test_slash_clear_asks_driver_to_clear(
    session: InteractiveSession,
) -> None:
    result = session.dispatch("/clear")
    assert result.clear_screen is True
    assert not result.should_exit


# ---------------------------------------------------------------------------
# Unknown commands
# ---------------------------------------------------------------------------


def test_unknown_slash_command_returns_hint(
    session: InteractiveSession,
) -> None:
    result = session.dispatch("/banana")
    out = result.output.lower()
    assert "unknown" in out or "/help" in out
    assert session.turn == 0


# ---------------------------------------------------------------------------
# /history
# ---------------------------------------------------------------------------


def test_slash_history_lists_recent_user_inputs_in_order(
    session: InteractiveSession,
) -> None:
    session.dispatch("add CSV export")
    session.dispatch("/status")
    session.dispatch("fix pagination off-by-one")
    result = session.dispatch("/history")

    assert "add CSV export" in result.output
    assert "fix pagination off-by-one" in result.output
    assert result.output.index("add CSV export") < result.output.index(
        "fix pagination off-by-one"
    )


# ---------------------------------------------------------------------------
# /model
# ---------------------------------------------------------------------------


def test_slash_model_replaces_active_model(
    session: InteractiveSession,
) -> None:
    session.dispatch("/model gpt-5")
    assert session.model == "gpt-5"


def test_slash_model_without_argument_shows_current(
    session: InteractiveSession,
) -> None:
    result = session.dispatch("/model")
    assert "claude-opus-4.5" in result.output


# ---------------------------------------------------------------------------
# Plain input
# ---------------------------------------------------------------------------


def test_plain_input_in_plan_mode_queues_a_plan(
    session: InteractiveSession,
) -> None:
    """Plain text in plan mode still records the task for /approve.

    v2.2.1: plan mode now also calls the LLM (so the user gets a real
    reply), but the ``pending_task`` side-effect that backs ``/approve``
    is preserved unchanged. In the test environment no provider is
    configured, so the LLM call falls back to the friendly error path —
    which is fine for this test because we only care that the task got
    queued and the response mentions plan mode.
    """
    session.dispatch("/mode plan")
    result = session.dispatch("add a small feature that exports CSV")
    assert session.turn == 1
    assert session.pending_task == "add a small feature that exports CSV"
    assert "plan" in result.output.lower()


def test_empty_input_is_a_no_op(session: InteractiveSession) -> None:
    result = session.dispatch("")
    assert session.turn == 0
    assert result.output == ""
    assert session.pending_task is None


def test_whitespace_only_input_is_a_no_op(
    session: InteractiveSession,
) -> None:
    result = session.dispatch("   \t  ")
    assert session.turn == 0
    assert result.output == ""


# ---------------------------------------------------------------------------
# /approve and /reject
# ---------------------------------------------------------------------------


def test_slash_approve_after_plan_switches_to_agent_mode(
    session: InteractiveSession,
) -> None:
    """v3.2.0: ``run`` collapsed into ``agent``; approving a plan now
    hands off to ``agent`` (the single full-access execution mode)."""
    session.dispatch("/mode plan")
    session.dispatch("add CSV export")
    result = session.dispatch("/approve")
    assert session.mode == "agent"
    assert result.new_mode == "agent"


def test_slash_approve_without_pending_plan_explains(
    session: InteractiveSession,
) -> None:
    session.dispatch("/mode plan")
    result = session.dispatch("/approve")
    assert session.mode == "plan"
    assert "no plan" in result.output.lower()


def test_slash_reject_clears_pending_plan(
    session: InteractiveSession,
) -> None:
    session.dispatch("/mode plan")
    session.dispatch("add CSV export")
    assert session.pending_task is not None
    result = session.dispatch("/reject")
    assert session.pending_task is None
    assert session.mode == "plan"
    assert "reject" in result.output.lower() or "drop" in result.output.lower()


# ---------------------------------------------------------------------------
# /skills — lives alongside slash registry; enumerates shipped packs
# ---------------------------------------------------------------------------


def test_slash_skills_lists_installed_packs(
    session: InteractiveSession,
) -> None:
    """The four v0.1.0 packs must be listed — dogfooding the skill router.

    If a future phase adds a pack, this test reads it from the registry,
    not a hardcoded set — we just assert the four v0.1.0 ones show up.
    """
    result = session.dispatch("/skills")
    out = result.output
    for pack in ["atomic-skills", "tdd-sprint", "karpathy", "safety"]:
        assert pack in out, f"pack {pack!r} missing from /skills output"


# ---------------------------------------------------------------------------
# CommandResult defaults are safe
# ---------------------------------------------------------------------------


def test_command_result_defaults_are_safe() -> None:
    r = CommandResult()
    assert r.output == ""
    assert r.renderable is None
    assert r.should_exit is False
    assert r.clear_screen is False
    assert r.new_mode is None


# ---------------------------------------------------------------------------
# Renderables — every user-facing result ships a Rich-aware renderable
# alongside the plain text, so the driver can pretty-print in TTY mode
# without blowing up the plain / non-TTY path. We don't assert on the
# visual layout (that would be brittle) — we only assert that the slot
# is populated for the commands users look at.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "line",
    [
        "/help",
        "/status",
        "/history",
        "/skills",
        "/doctor",
        "/banana",  # unknown command
        "add CSV export",  # plan-mode plain text
    ],
)
def test_user_facing_commands_ship_a_renderable(
    session: InteractiveSession, line: str
) -> None:
    result = session.dispatch(line)
    assert result.renderable is not None, (
        f"{line!r} should ship a Rich renderable so the TTY path can "
        f"pretty-print instead of falling back to the plain string."
    )


def test_approve_renderable_is_produced_after_plan(
    session: InteractiveSession,
) -> None:
    session.dispatch("/mode plan")
    session.dispatch("add CSV export")
    result = session.dispatch("/approve")
    assert result.renderable is not None


def test_reject_renderable_even_when_nothing_to_drop(
    session: InteractiveSession,
) -> None:
    result = session.dispatch("/reject")
    assert result.renderable is not None


def test_bad_mode_renderable_preserves_plain_hint(
    session: InteractiveSession,
) -> None:
    """/mode with a bogus target must give the user both channels:
    a plain-text hint (for tests and non-TTY) AND a Rich renderable."""
    result = session.dispatch("/mode banana")
    assert "unknown mode" in result.output.lower()
    assert result.renderable is not None
