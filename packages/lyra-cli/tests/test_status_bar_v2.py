"""Phase 5 — opencode-style footer (status bar v2).

The legacy renderer in :class:`StatusSource.render` returned a flat
text line that worked but lacked iconography and made it hard to
distinguish "no MCP servers" from "MCP renderer hasn't initialized"
(both showed nothing). v2 delegates to :func:`render_footer` which
produces a Rich :class:`~rich.text.Text` with claw-code-aligned
symbols (◆ model · △ perms · ✦ LSP · ⊙ MCP) and a non-TTY plain
fallback.

Contract:

* Every populated field is rendered exactly once with its symbol.
* ``cost_usd=0`` and counts of zero collapse — the footer never
  shouts ``MCP:0`` at users who aren't using MCP.
* Plain mode (when stdout isn't a TTY) drops the symbols but keeps
  the field labels so log captures stay greppable.
* The full footer never exceeds ``term_cols`` characters; long cwd
  paths get truncated in the middle (``~/Downloads/…/lyra``).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from lyra_cli.interactive.status_bar import render_footer
from lyra_cli.interactive.status_source import StatusSource


def _basic_source(tmp_path: Path, **kw) -> StatusSource:
    s = StatusSource(cwd=tmp_path)
    s.update(**kw)
    return s


def _plain(text_obj) -> str:
    """Coerce the Rich Text returned by render_footer to plain string."""
    if hasattr(text_obj, "plain"):
        return text_obj.plain
    return str(text_obj)


def test_renders_cwd_and_model(tmp_path: Path) -> None:
    s = _basic_source(tmp_path, model="deepseek-chat", mode="plan")
    out = _plain(render_footer(s, term_cols=120))
    assert "deepseek-chat" in out
    assert "plan" in out
    assert str(tmp_path.name) in out


def test_zero_counts_collapse(tmp_path: Path) -> None:
    """Empty MCP / LSP / cost fields must not appear."""
    s = _basic_source(tmp_path, model="deepseek-chat", mode="plan")
    out = _plain(render_footer(s, term_cols=120))
    assert "MCP" not in out
    assert "LSP" not in out
    assert "$" not in out


def test_permissions_field_present_when_set(tmp_path: Path) -> None:
    s = _basic_source(tmp_path, model="m", mode="plan", permissions="strict")
    out = _plain(render_footer(s, term_cols=120))
    assert "strict" in out


def test_lsp_and_mcp_count_present_when_nonzero(tmp_path: Path) -> None:
    s = _basic_source(tmp_path, model="m", mode="plan", lsp_count=3, mcp_count=2)
    rich_out = _plain(render_footer(s, term_cols=120))
    plain_out = render_footer(s, term_cols=120, plain=True)

    # Rich mode: symbols + numbers
    assert "✦" in rich_out and "3" in rich_out
    assert "⊙" in rich_out and "2" in rich_out

    # Plain mode: labels + numbers (greppable)
    plain_str = plain_out if isinstance(plain_out, str) else _plain(plain_out)
    assert "LSP:3" in plain_str
    assert "MCP:2" in plain_str


def test_cost_renders_two_decimals_when_nonzero(tmp_path: Path) -> None:
    s = _basic_source(tmp_path, model="m", mode="plan", cost_usd=0.0123)
    out = _plain(render_footer(s, term_cols=120))
    assert "$" in out
    assert "0.01" in out


def test_token_count_present_when_nonzero(tmp_path: Path) -> None:
    s = _basic_source(tmp_path, model="m", mode="plan", tokens=1234)
    out = _plain(render_footer(s, term_cols=120))
    assert "1234" in out or "1,234" in out or "1.2k" in out


def test_plain_mode_drops_symbols_but_keeps_labels(tmp_path: Path) -> None:
    """plain=True is the non-TTY / log-capture format."""
    s = _basic_source(tmp_path, model="m", mode="plan", lsp_count=2)
    out = render_footer(s, term_cols=120, plain=True)
    # plain mode returns a str directly (no Rich Text)
    out_str = out if isinstance(out, str) else _plain(out)
    assert "model" in out_str.lower() or "m" in out_str
    assert "LSP" in out_str
    # Symbols shouldn't be in plain mode
    assert "◆" not in out_str
    assert "△" not in out_str


def test_cwd_truncated_when_path_exceeds_terminal_width() -> None:
    deep = Path("/very/very/long/nested/path/structure/with/many/segments/lyra")
    s = StatusSource(cwd=deep)
    s.update(model="m", mode="plan")
    out = _plain(render_footer(s, term_cols=60))
    assert len(out) <= 60
    assert "…" in out or "..." in out


def test_collapsed_initial_state_shows_only_cwd_model_mode(tmp_path: Path) -> None:
    """Spec §8.2: a fresh session shows just `cwd · ◆ <model> · <mode>`."""
    s = _basic_source(tmp_path, model="deepseek-v4-pro", mode="plan")
    out = _plain(render_footer(s, term_cols=120))
    forbidden = ("MCP", "LSP", "tokens", "$", "perms", "permissions=")
    for token in forbidden:
        assert token not in out, f"{token!r} should be collapsed but appeared in: {out}"
