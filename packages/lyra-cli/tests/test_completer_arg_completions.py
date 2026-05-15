"""Argument completions for slash commands (regression for v3.5.x UX bug).

Before this fix, ``/model deepseek`` produced an empty completion menu
because the completer's first branch unconditionally returned after
attempting subcommand completion — and ``/model`` has no registered
subcommands, so zero items shipped to the user. The fix:

1. Stop the unconditional ``return`` when no subcommand matched.
2. Fall through to a per-command argument completer.
3. For ``/model`` and ``/llm``, surface the canonical slugs from the
   alias registry plus the ``fast=`` / ``smart=`` slot syntax.

These tests pin that contract.
"""
from __future__ import annotations

from prompt_toolkit.document import Document

from lyra_cli.interactive.completer import SlashCompleter


def _completions(text: str) -> list[str]:
    completer = SlashCompleter()
    doc = Document(text=text, cursor_position=len(text))
    return [c.text for c in completer.get_completions(doc, complete_event=None)]


def _displays(text: str) -> list[str]:
    completer = SlashCompleter()
    doc = Document(text=text, cursor_position=len(text))
    out: list[str] = []
    for c in completer.get_completions(doc, complete_event=None):
        display = c.display
        if hasattr(display, "_text"):
            out.append(display._text[0][1])
        else:
            out.append(str(display))
    return out


# ---------------------------------------------------------------------------
# /model — the headline regression
# ---------------------------------------------------------------------------


def test_model_with_no_arg_yields_at_least_one_completion() -> None:
    """``/model `` (trailing space, no stem) must show *something*.

    Regression guard: before the fix this branch silently returned
    zero completions because ``/model`` has no registered subcommands.
    """
    items = _completions("/model ")
    assert len(items) >= 1, (
        f"expected at least one completion for '/model ', got {items!r}"
    )


def test_model_with_partial_stem_yields_matching_slugs() -> None:
    """``/model dee`` must surface DeepSeek slugs."""
    items = _completions("/model dee")
    joined = " ".join(items).lower()
    assert "deepseek" in joined, (
        f"expected a deepseek slug in completions, got {items!r}"
    )


def test_model_yields_canonical_slugs() -> None:
    """The completion set must include real DeepSeek API slugs."""
    items = set(_completions("/model "))
    # Sample a few slugs we know are registered in DEFAULT_ALIASES.
    expected_subset = {"deepseek-chat", "deepseek-reasoner"}
    assert expected_subset.issubset(items), (
        f"missing canonical slugs; items={sorted(items)!r}"
    )


def test_model_yields_slot_syntax() -> None:
    """``/model `` should also offer the ``fast=`` / ``smart=`` slots."""
    items = _completions("/model ")
    assert "fast=" in items, f"missing fast= slot syntax; items={items!r}"
    assert "smart=" in items, f"missing smart= slot syntax; items={items!r}"


def test_llm_alias_works_too() -> None:
    """``/llm`` is the muscle-memory alias for ``/model``."""
    items = _completions("/llm ")
    assert len(items) >= 1


# ---------------------------------------------------------------------------
# Other commands stay unaffected
# ---------------------------------------------------------------------------


def test_unknown_command_with_arg_returns_empty_safely() -> None:
    """``/foo bar`` must not crash; just return zero completions."""
    items = _completions("/foo bar")
    assert items == []


def test_slash_palette_still_works_with_partial_command() -> None:
    """Typing ``/mod`` keeps showing the slash palette filtered by stem."""
    items = _completions("/mod")
    assert "model" in items or "mode" in items, (
        f"slash palette regression; items={items!r}"
    )


def test_empty_input_yields_nothing() -> None:
    items = _completions("")
    assert items == []
