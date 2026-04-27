"""Phase 13 — Red tests for the interactive banner.

The banner is the first thing a user sees and its contract is small but
sharp: show version, tagline, repo, model, mode, and how to get help.
A regression here would silently erode the UX every release, so we pin
it explicitly.

These tests pass ``term_cols`` explicitly so the "happy path" (wide
render, full repo path visible) is exercised regardless of the size of
the machine running the test suite — otherwise ``tmp_path`` from
``pytest`` (a very long absolute path) would trigger the narrow-terminal
fallback and mask the contract we actually care about.
"""
from __future__ import annotations

import re
from pathlib import Path

from lyra_cli import __version__
from lyra_cli.interactive.banner import render_banner

_WIDE = 140  # comfortably wider than the 90-col fancy panel
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _strip_ansi(s: str) -> str:
    return _ANSI_RE.sub("", s)


def test_banner_contains_version_and_tagline(tmp_path: Path) -> None:
    banner = render_banner(
        repo_root=tmp_path,
        model="claude-opus-4.5",
        mode="plan",
        term_cols=_WIDE,
    )
    assert __version__ in banner
    stripped = _strip_ansi(banner)
    assert "Lyra" in stripped
    # v3.0.0: Lyra is general-purpose, multi-provider — the tagline
    # is the whole USP. (Pre-v3 used "TDD-first" but the kernel-level
    # gate is now an opt-in plugin, so the headline reflects that.)
    assert "general-purpose" in stripped or "multi-provider" in stripped


def test_banner_contains_repo_model_mode(tmp_path: Path) -> None:
    banner = render_banner(
        repo_root=tmp_path,
        model="gpt-5",
        mode="debug",
        term_cols=_WIDE,
    )
    assert str(tmp_path) in _strip_ansi(banner)
    assert "gpt-5" in _strip_ansi(banner)
    assert "debug" in _strip_ansi(banner)


def test_banner_shows_help_hint(tmp_path: Path) -> None:
    banner = render_banner(
        repo_root=tmp_path, model="mock", mode="plan", term_cols=_WIDE
    )
    assert "/help" in _strip_ansi(banner)


def test_banner_renders_without_colorcodes_on_plain_terminals(
    tmp_path: Path,
) -> None:
    """Rich should degrade gracefully when plain is requested.

    The driver passes ``plain=True`` when stdout isn't a TTY so logs /
    test captures don't fill up with ANSI escapes.
    """
    banner = render_banner(
        repo_root=tmp_path, model="mock", mode="plan", plain=True
    )
    assert "\x1b[" not in banner  # no ANSI


def test_banner_falls_back_to_compact_on_narrow_terminals(
    tmp_path: Path,
) -> None:
    """Very narrow terminals must not render the ASCII logo.

    Regression guard for the "one glyph per line" bug: on a sub-40-col
    shell (cramped split panes, watch-faces, embedded terminals), Rich
    would re-wrap the gradient logo panel into visual chaos. The
    compact path avoids the logo entirely.

    After the rename to LYRA the logo is only 30 cols wide, so the
    fancy/compact boundary is now 40 cols — well below what any
    user-facing shell offers. We pin it explicitly so a future tweak
    that raises the threshold doesn't silently regress modern 80/120-col
    terminals (which should always get the fancy panel now).
    """
    narrow = render_banner(
        repo_root=tmp_path, model="mock", mode="plan", term_cols=32
    )
    wide = render_banner(
        repo_root=tmp_path, model="mock", mode="plan", term_cols=140
    )

    # The ANSI-Shadow logo uses a distinctive '█' glyph that only the
    # wide render path emits.
    assert "█" in _strip_ansi(wide)
    assert "█" not in _strip_ansi(narrow)

    # Modern default shells (80-col and up) should *also* get the fancy
    # panel — the whole point of shortening the brand mark to LYRA was
    # to make the logo comfortable at 80 cols.
    eighty = render_banner(
        repo_root=tmp_path, model="mock", mode="plan", term_cols=80
    )
    assert "█" in _strip_ansi(eighty)

    # Every variant must still honour the core contract.
    for banner in (narrow, wide, eighty):
        stripped = _strip_ansi(banner)
        assert "Lyra" in stripped
        assert "/help" in stripped


def test_banner_truncates_long_paths_on_narrow_terminals(
    tmp_path: Path,
) -> None:
    """Long absolute paths must not overflow a narrow terminal.

    We middle-truncate with ``…`` so the user still sees the prefix
    and the leaf directory. The fully-qualified path only needs to
    appear when the terminal has room for it.

    With the 30-col LYRA logo, the "too narrow for fancy" boundary is
    40 cols, so we probe at 36 to exercise the compact-path truncation.
    """
    long_path = tmp_path / "a" / "b" / "c" / "projects" / "lyra"
    long_path.mkdir(parents=True, exist_ok=True)

    banner = render_banner(
        repo_root=long_path, model="mock", mode="plan", term_cols=36
    )
    stripped = _strip_ansi(banner)

    # No rendered line should exceed the terminal width.
    assert all(len(line) <= 36 for line in stripped.splitlines())
    # The middle ellipsis must be present when truncation kicked in.
    assert "…" in stripped
    # The leaf directory must still be visible — that's what identifies
    # the working repo at a glance.
    assert "lyra" in stripped
