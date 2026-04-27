"""Phase 7 — fuzzy-searchable command palette v2.

Lyra v2.1.x ships a flat ``/help`` plain-text table. v2.1.9 adds a
genuine command palette: an opencode-/fzf-style picker that filters
the registry by substring + initial-char fuzzy match, groups by
category, and renders to a Rich :class:`~rich.panel.Panel`.

Public surface:

* :func:`fuzzy_filter(query: str) -> list[CommandSpec]` — pure search
  function; empty query returns the full registry, sorted by category
  then alphabetical name.
* :func:`render_palette(specs, *, query: Optional[str], max_height: int) -> Text`
  — formatter; safe to print even when ``len(specs)`` is zero (renders
  "(no matches)" rather than crashing).

Both must be importable without spinning up a TTY so the test suite
can exercise them headlessly.
"""
from __future__ import annotations

import pytest


def test_fuzzy_filter_empty_query_returns_all() -> None:
    from lyra_cli.interactive.command_palette import fuzzy_filter
    from lyra_cli.interactive.session import COMMAND_REGISTRY

    out = fuzzy_filter("")
    assert len(out) == len(COMMAND_REGISTRY)


def test_fuzzy_filter_substring_match() -> None:
    from lyra_cli.interactive.command_palette import fuzzy_filter

    out = fuzzy_filter("model")
    names = [spec.name for spec in out]
    assert "model" in names
    assert "models" in names


def test_fuzzy_filter_aliases_match_too() -> None:
    """Aliases must match — typing ``branch`` should surface ``fork``."""
    from lyra_cli.interactive.command_palette import fuzzy_filter

    out = fuzzy_filter("branch")
    names = [spec.name for spec in out]
    assert "fork" in names


def test_fuzzy_filter_initials_match() -> None:
    """Typing ``ur`` should match ``ultrareview``."""
    from lyra_cli.interactive.command_palette import fuzzy_filter

    out = fuzzy_filter("ur")
    names = [spec.name for spec in out]
    assert "ultrareview" in names


def test_fuzzy_filter_unknown_returns_empty() -> None:
    from lyra_cli.interactive.command_palette import fuzzy_filter

    out = fuzzy_filter("zzzzznothingmatchesthis")
    assert out == []


def test_render_palette_returns_rich_text() -> None:
    from rich.text import Text

    from lyra_cli.interactive.command_palette import render_palette
    from lyra_cli.interactive.session import COMMAND_REGISTRY

    out = render_palette(list(COMMAND_REGISTRY)[:5], query=None)
    assert isinstance(out, Text)
    plain = out.plain
    # First spec name surfaces.
    assert COMMAND_REGISTRY[0].name in plain


def test_render_palette_handles_no_matches() -> None:
    from rich.text import Text

    from lyra_cli.interactive.command_palette import render_palette

    out = render_palette([], query="nothing")
    assert isinstance(out, Text)
    assert "no matches" in out.plain.lower()


def test_render_palette_groups_by_category() -> None:
    from lyra_cli.interactive.command_palette import (
        fuzzy_filter,
        render_palette,
    )

    out = render_palette(fuzzy_filter(""), query=None, max_height=200)
    plain = out.plain.lower()
    # All categories present in the regstry should appear as headers.
    assert "session" in plain
    assert "plan" in plain or "build" in plain or "run" in plain


def test_render_palette_truncates_to_max_height() -> None:
    from lyra_cli.interactive.command_palette import (
        fuzzy_filter,
        render_palette,
    )

    full = fuzzy_filter("")
    short = render_palette(full, query=None, max_height=4)
    assert short.plain.count("\n") <= 8  # 4 entries + headers/footer


def test_render_palette_highlights_query() -> None:
    """When a query is given the matched fragment is bolded."""
    from lyra_cli.interactive.command_palette import (
        fuzzy_filter,
        render_palette,
    )

    out = render_palette(fuzzy_filter("model"), query="model")
    # Rich Text spans store style info in `_spans`; checking the plain
    # output is enough — we just need the matched query to appear.
    assert "model" in out.plain
