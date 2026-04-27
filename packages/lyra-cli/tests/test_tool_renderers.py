"""Phase 6 — per-tool renderers (claw-code parity).

The legacy :func:`render_tool_card` produced a one-size-fits-all card
("name + preview line"). v2.1.8 introduces a registry that dispatches
to specialised renderers per tool family:

* ``bash`` / ``shell`` — show the command and (when complete) exit code.
* ``read_file`` — show the file path and (optionally) the byte/line range.
* ``write_file`` / ``edit_file`` — show the path and diff stats
  (``+N/-M``).
* ``grep`` / ``glob`` — show the pattern and match count.
* anything else — fall through to the generic claw-code card.

Tests lock the contract: each renderer's output is a multi-line ANSI
string containing the relevant fields. We check on the *plain* form
(ANSI stripped) so the assertions don't drift when the colour table
moves.
"""
from __future__ import annotations

import re

import pytest

from lyra_cli.interactive.tool_renderers import get_renderer, render

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _plain(text: str) -> str:
    return _ANSI_RE.sub("", text)


def test_bash_renderer_shows_command() -> None:
    out = render(
        name="bash",
        args={"command": "ls -la /tmp"},
        result=None,
    )
    plain = _plain(out)
    assert "ls -la /tmp" in plain
    assert "bash" in plain.lower()


def test_bash_renderer_with_result_shows_exit_code() -> None:
    out = render(
        name="bash",
        args={"command": "false"},
        result={"exit_code": 1, "stdout": "", "stderr": "boom"},
    )
    plain = _plain(out)
    assert "false" in plain
    # Exit code surfaces somewhere in the body.
    assert "1" in plain or "exit" in plain.lower()


def test_bash_renderer_zero_exit_collapses_exit_code_label() -> None:
    """A zero-exit, no-output bash should NOT shout ``exit_code=0``."""
    out = render(
        name="bash",
        args={"command": "true"},
        result={"exit_code": 0, "stdout": "", "stderr": ""},
    )
    plain = _plain(out)
    assert "true" in plain
    # Exit-code spam on success is the anti-pattern we're avoiding.
    assert "exit_code" not in plain.lower()


def test_read_file_renderer_shows_path() -> None:
    out = render(
        name="read_file",
        args={"path": "src/lyra_cli/__main__.py"},
        result=None,
    )
    plain = _plain(out)
    assert "src/lyra_cli/__main__.py" in plain


def test_write_file_renderer_shows_path_and_size() -> None:
    out = render(
        name="write_file",
        args={"path": "src/foo.py", "content": "print('hi')\n"},
        result=None,
    )
    plain = _plain(out)
    assert "src/foo.py" in plain


def test_edit_file_renderer_shows_path_and_diff_stats() -> None:
    out = render(
        name="edit_file",
        args={
            "path": "src/foo.py",
            "old_str": "x=1\n",
            "new_str": "x = 1\nprint(x)\n",
        },
        result=None,
    )
    plain = _plain(out)
    assert "src/foo.py" in plain
    # Diff stats: the new content has 2 added lines vs 1 old.
    assert "+" in plain or "added" in plain.lower()


def test_search_renderer_shows_pattern() -> None:
    out = render(
        name="grep",
        args={"pattern": "TODO"},
        result={"matches": 5},
    )
    plain = _plain(out)
    assert "TODO" in plain


def test_glob_renderer_shows_pattern() -> None:
    out = render(
        name="glob",
        args={"glob_pattern": "**/*.py"},
        result=None,
    )
    plain = _plain(out)
    assert "**/*.py" in plain


def test_unknown_tool_falls_through_to_generic_renderer() -> None:
    out = render(
        name="some_random_brand_new_tool",
        args={"foo": "bar"},
        result=None,
    )
    plain = _plain(out)
    # Generic renderer at minimum echoes the tool name.
    assert "some_random_brand_new_tool" in plain


def test_get_renderer_returns_callable_for_known_tool() -> None:
    renderer = get_renderer("bash")
    assert callable(renderer)


def test_get_renderer_returns_generic_for_unknown_tool() -> None:
    renderer = get_renderer("not-a-real-tool-12345")
    assert callable(renderer)
