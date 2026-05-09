"""Phase 0 — RED for the claw-code-inspired tool call card.

Contract (plan Phase 6, cc-tool-card):

- ``render_tool_card(name, preview, *, is_error=False)`` lives at
  ``lyra_cli.interactive.tool_card``.
- Returns a ``str`` (already ANSI-colored) with at least 3 lines:
  1. top border:    ``╭─ <name> ─╮``
  2. body:          ``│ <preview>``
  3. bottom border: ``╰─...─╯``
- For ``name == "bash"`` and a preview like ``$ ls -la`` the body
  renders the command on an inverted background (ANSI ``48;5;236``).
- When ``is_error=True`` the top border uses a red color.
- The name appears in bold cyan; borders in dim grey.
"""
from __future__ import annotations

import re

import pytest


def _import_tool_card():
    try:
        from lyra_cli.interactive.tool_card import render_tool_card
    except ModuleNotFoundError as exc:
        pytest.fail(f"lyra_cli.interactive.tool_card.render_tool_card must exist ({exc})")
    return render_tool_card


_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _strip(s: str) -> str:
    return _ANSI_RE.sub("", s)


def test_tool_card_has_three_borders_with_name():
    render_tool_card = _import_tool_card()
    out = render_tool_card("bash", "$ ls -la")
    lines = _strip(out).splitlines()
    assert len(lines) >= 3
    assert lines[0].startswith("╭"), f"top border wrong: {lines[0]!r}"
    assert "bash" in lines[0]
    assert lines[-1].startswith("╰"), f"bottom border wrong: {lines[-1]!r}"
    # Body must contain the preview.
    assert any("ls -la" in line for line in lines[1:-1]), lines


def test_bash_preview_uses_inverted_background():
    render_tool_card = _import_tool_card()
    out = render_tool_card("bash", "$ ls -la")
    # ANSI code for 256-color background 236 is "\x1b[48;5;236m".
    assert "48;5;236" in out, (
        "bash preview must render on the inverted dim-grey background"
    )


def test_tool_card_name_in_bold_cyan_border_in_dim():
    render_tool_card = _import_tool_card()
    out = render_tool_card("read_file", "path=/tmp/x.txt")
    # Bold cyan = "\x1b[1;36m" (or similar close composition containing '1;' and '36').
    assert "36" in out, "tool name must use cyan"
    # Dim-grey borders (ANSI 38;5;245) are the claw-code signature.
    assert "38;5;245" in out, "borders must use 256-color dim 245"


def test_error_tool_card_uses_red_accent():
    render_tool_card = _import_tool_card()
    ok = render_tool_card("bash", "$ uname -a")
    err = render_tool_card("bash", "$ exit 1", is_error=True)
    assert ok != err, "error and success cards must differ visually"
    # A 256-color red (203) or classic 31 should appear somewhere in the error card.
    assert ("203" in err) or ("31" in err), "error card must carry red"


def test_long_name_does_not_break_border_alignment():
    render_tool_card = _import_tool_card()
    out = render_tool_card("very_long_tool_name_that_could_cause_issues", "doing")
    lines = _strip(out).splitlines()
    # The bottom border should be at least as wide as the top one.
    assert len(lines[-1]) >= len("╭─  ─╮") + len("very_long_tool_name_that_could_cause_issues")
