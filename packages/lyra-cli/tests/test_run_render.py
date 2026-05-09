"""Render helpers for ``lyra run`` output (header / panel / footer / fmt).

Pre-2.1.2 output for ``lyra run --no-plan "say hello"`` was three
bare lines:

    plan bypassed via --no-plan
    hello world
    agent stopped: StopReason.END_TURN · 1 step(s) · 0 tool call(s)

Two complaints landed:

1. ``StopReason.END_TURN`` is the Python repr of the enum, not its
   value — pointlessly noisy.
2. The answer is unframed and there's no "Lyra · deepseek ·
   deepseek-v4-pro" header so users don't see *which backend
   actually answered*.

This test pins the formatting helpers that fix both. The helpers
live in :mod:`lyra_cli.commands.run` and are pure (no I/O), so a
single-file test exercises every shape.
"""
from __future__ import annotations

from harness_core.loop import LoopResult
from harness_core.messages import StopReason

from lyra_cli.commands.run import (
    _format_elapsed,
    _format_run_footer,
    _format_run_header,
    _format_stop_reason,
)


# ---------------------------------------------------------------------------
# _format_stop_reason — strip the ``StopReason.`` prefix
# ---------------------------------------------------------------------------


def test_format_stop_reason_strips_enum_prefix() -> None:
    """``StopReason.END_TURN`` → ``end_turn`` (lower-cased value).

    Without the strip the footer reads ``agent stopped:
    StopReason.END_TURN`` which exposes the Python repr to users.
    """
    assert _format_stop_reason("StopReason.END_TURN") == "end_turn"
    assert _format_stop_reason("StopReason.MAX_TOKENS") == "max_tokens"
    assert _format_stop_reason("StopReason.TOOL_USE") == "tool_use"


def test_format_stop_reason_passes_already_clean_strings_through() -> None:
    """Already-friendly strings stay friendly — idempotent."""
    assert _format_stop_reason("end_turn") == "end_turn"
    assert _format_stop_reason("max_steps") == "max_steps"


def test_format_stop_reason_handles_enum_directly() -> None:
    """Passing the enum value (not its str) also works."""
    assert _format_stop_reason(StopReason.END_TURN) == "end_turn"


def test_format_stop_reason_handles_none() -> None:
    """Defensive: missing stop reason → ``end_turn`` (the success default)."""
    assert _format_stop_reason(None) == "end_turn"
    assert _format_stop_reason("") == "end_turn"


# ---------------------------------------------------------------------------
# _format_elapsed — "1.4s" / "12s" / "1m23s"
# ---------------------------------------------------------------------------


def test_format_elapsed_subsecond_shows_one_decimal() -> None:
    """Sub-second elapsed rounds to one decimal so users can tell
    ``0.3s`` apart from ``0.9s`` (matters for "did the model warm up
    or cache hit?" debugging)."""
    assert _format_elapsed(0.0) == "0.0s"
    assert _format_elapsed(0.34) == "0.3s"
    assert _format_elapsed(0.9) == "0.9s"


def test_format_elapsed_under_a_minute_shows_one_decimal() -> None:
    """Single-digit and double-digit second values both keep one
    decimal — ``9.4s`` reads better than ``9s`` in a status line."""
    assert _format_elapsed(1.4) == "1.4s"
    assert _format_elapsed(9.4) == "9.4s"
    assert _format_elapsed(45.7) == "45.7s"


def test_format_elapsed_over_a_minute_uses_compact_notation() -> None:
    """Past 60 seconds, switch to ``1m23s`` so the column doesn't
    grow ``120.0s``-wide and break alignment in the footer."""
    assert _format_elapsed(60.0) == "1m00s"
    assert _format_elapsed(83.4) == "1m23s"
    assert _format_elapsed(125.0) == "2m05s"


# ---------------------------------------------------------------------------
# _format_run_header — provider / model / mode line
# ---------------------------------------------------------------------------


def test_format_run_header_includes_provider_and_model() -> None:
    """The header must surface *which backend answered* — that's the
    whole point of the change. The user complained "wtf??" because
    the bare output never named the model."""
    rendered = _format_run_header(
        provider_label="deepseek · deepseek-v4-pro",
        mode="no-plan",
    )
    text = _strip_markup(rendered)
    assert "deepseek" in text
    assert "deepseek-v4-pro" in text


def test_format_run_header_includes_mode() -> None:
    """Mode (``plan`` / ``no-plan`` / ``auto-approve``) must be visible
    so the user can tell at a glance whether the safety gate fired."""
    rendered = _format_run_header(
        provider_label="anthropic · claude-3-5-sonnet-latest",
        mode="plan",
    )
    text = _strip_markup(rendered)
    assert "plan" in text


def test_format_run_header_carries_the_lyra_brand() -> None:
    """A header without "Lyra" looks like a generic tool — keep the
    brand visible. Matches the REPL banner's word-mark."""
    rendered = _format_run_header(
        provider_label="mock · canned outputs",
        mode="no-plan",
    )
    text = _strip_markup(rendered)
    assert "Lyra" in text


# ---------------------------------------------------------------------------
# _format_run_footer — stats line replacing the old bare string
# ---------------------------------------------------------------------------


def _make_result(
    stop_reason: str = "StopReason.END_TURN",
    steps: int = 1,
    tool_calls_count: int = 0,
    blocked_calls_count: int = 0,
    final_text: str = "hi",
) -> LoopResult:
    return LoopResult(
        final_text=final_text,
        transcript=[],
        steps=steps,
        stop_reason=stop_reason,
        tool_calls_count=tool_calls_count,
        blocked_calls_count=blocked_calls_count,
    )


def test_format_run_footer_uses_clean_stop_reason() -> None:
    """The footer must NOT show ``StopReason.END_TURN``.

    For the clean ``end_turn`` case we substitute the friendlier
    leader ``done`` (see :func:`test_format_run_footer_says_done_for_clean_end_turn`),
    so the only thing this test guards is the non-leak of the
    Python-repr prefix.
    """
    rendered = _format_run_footer(_make_result(), elapsed_s=1.4)
    text = _strip_markup(rendered)
    assert "StopReason." not in text
    # Non-end_turn cases must surface the cleaned reason verbatim.
    rendered_max = _format_run_footer(
        _make_result(stop_reason="StopReason.MAX_TOKENS"),
        elapsed_s=1.4,
    )
    text_max = _strip_markup(rendered_max)
    assert "StopReason." not in text_max
    assert "max_tokens" in text_max


def test_format_run_footer_includes_step_count_and_elapsed() -> None:
    """Steps + elapsed time are the two numbers users actually look at."""
    rendered = _format_run_footer(
        _make_result(steps=3, tool_calls_count=2),
        elapsed_s=12.7,
    )
    text = _strip_markup(rendered)
    assert "3" in text and "step" in text
    assert "12.7s" in text


def test_format_run_footer_omits_blocked_when_zero() -> None:
    """``0 blocked`` is noise — drop it. Show it only when nonzero so
    a non-zero count visually pops."""
    rendered = _format_run_footer(_make_result(), elapsed_s=1.0)
    text = _strip_markup(rendered)
    assert "blocked" not in text


def test_format_run_footer_includes_blocked_when_nonzero() -> None:
    """If a tool was blocked by the permission policy, the user MUST
    see it — silently dropping a blocked call is a security smell."""
    rendered = _format_run_footer(
        _make_result(blocked_calls_count=2),
        elapsed_s=1.0,
    )
    text = _strip_markup(rendered)
    assert "2" in text and "blocked" in text


def test_format_run_footer_says_done_for_clean_end_turn() -> None:
    """Successful runs lead with ``done`` so green-flag completion is
    a single keyword the eye finds in the wall of stats."""
    rendered = _format_run_footer(_make_result(), elapsed_s=1.0)
    text = _strip_markup(rendered)
    assert "done" in text


def test_format_run_footer_says_max_steps_for_step_budget_exhaustion() -> None:
    """Budget exhaustion is a soft-failure — call it out so users
    don't think the agent finished cleanly."""
    rendered = _format_run_footer(
        _make_result(stop_reason="max_steps"),
        elapsed_s=180.0,
    )
    text = _strip_markup(rendered)
    assert "max_steps" in text or "budget" in text


# ---------------------------------------------------------------------------
# Token-usage proof-of-life
# ---------------------------------------------------------------------------


def test_format_run_footer_shows_token_usage_when_provided() -> None:
    """The "I don't see real call to deepseek yet??" complaint:
    surface API-returned token counts so a non-zero in/out is hard
    proof the API actually answered. Mocks return zero — the
    presence of nonzero counts is proof-of-life by construction.
    """
    rendered = _format_run_footer(
        _make_result(),
        elapsed_s=1.5,
        usage={"prompt_tokens": 7, "completion_tokens": 4, "total_tokens": 11},
    )
    text = _strip_markup(rendered)
    # Expect "7 in / 4 out" or similar — exact format pinned but
    # tolerant of either separator.
    assert "7" in text
    assert "4" in text
    assert "in" in text
    assert "out" in text


def test_format_run_footer_omits_token_usage_when_zero_or_none() -> None:
    """No usage data → no usage column. Keeps the line uncluttered
    for local providers that don't report tokens."""
    no_usage = _format_run_footer(_make_result(), elapsed_s=1.5)
    no_usage_text = _strip_markup(no_usage)
    assert "in" not in no_usage_text or "tokens" not in no_usage_text

    zero_usage = _format_run_footer(
        _make_result(),
        elapsed_s=1.5,
        usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    )
    zero_text = _strip_markup(zero_usage)
    assert "0 in" not in zero_text  # don't show "0 in / 0 out" noise


def test_format_run_footer_handles_total_tokens_only() -> None:
    """Some providers report only ``total_tokens``. Show it as a
    single ``11 tokens`` segment rather than ``0 in / 0 out``."""
    rendered = _format_run_footer(
        _make_result(),
        elapsed_s=1.0,
        usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 11},
    )
    text = _strip_markup(rendered)
    assert "11" in text
    assert "tokens" in text or "tok" in text


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _strip_markup(rendered: object) -> str:
    """Crude Rich-markup stripper for assertions.

    The helpers return Rich ``Text`` / ``Renderable`` objects; for
    string-content tests we just stringify and walk character-by-
    character past any ``[…]`` markup tags. Good enough for asserting
    on substrings without spinning up a Rich console.
    """
    s = str(rendered)
    out = []
    in_tag = False
    for ch in s:
        if ch == "[":
            in_tag = True
            continue
        if ch == "]" and in_tag:
            in_tag = False
            continue
        if not in_tag:
            out.append(ch)
    return "".join(out)
