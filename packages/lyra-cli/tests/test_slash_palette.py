"""Slash-command palette contract (Claude-Code / opencode parity).

When the user types a single ``/`` in the REPL, three things must be
true for the UX to feel like a proper command palette rather than bare
prompt_toolkit autocomplete:

1. The completer yields all canonical slash commands immediately.
2. Each completion carries a non-empty ``display_meta`` so the palette
   shows one-line descriptions next to the command.
3. The driver configures prompt_toolkit with enough reserved space to
   actually *display* the menu (``reserve_space_for_menu`` set) and a
   keybind on ``/`` that opens the palette the instant it's typed on
   an empty buffer.

These tests are the RED-first lock on the behaviour so future
refactors can't regress "dropdown on /" silently.
"""
from __future__ import annotations

import inspect
from pathlib import Path

from prompt_toolkit.document import Document

from lyra_cli.interactive.completer import SlashCompleter
from lyra_cli.interactive import driver as _driver


def _display_text(completion: object) -> str:
    """Extract the rendered display string from a prompt_toolkit Completion.

    ``completion.display`` is a list of ``(style, text)`` fragments; we
    only care about the concatenated text for assertions.
    """
    disp = getattr(completion, "display", None)
    if disp is None:
        return ""
    if isinstance(disp, str):
        return disp
    return "".join(text for _, text, *_ in disp)


def _meta_text(completion: object) -> str:
    disp = getattr(completion, "display_meta", None)
    if disp is None:
        return ""
    if isinstance(disp, str):
        return disp
    return "".join(text for _, text, *_ in disp)


def test_typing_slash_yields_full_palette() -> None:
    completer = SlashCompleter(repo_root=None)
    doc = Document(text="/", cursor_position=1)
    items = list(completer.get_completions(doc, object()))
    assert len(items) >= 10, (
        f"Typing `/` should open the full palette; got {len(items)} items."
    )


def test_every_palette_item_has_a_description() -> None:
    """The palette is only useful when each row has a one-line meta.

    This is the single biggest visual difference between Claude-Code's
    slash palette and bare autocomplete: the meta column tells the user
    what each command does without having to memorise 40+ names.
    """
    completer = SlashCompleter(repo_root=None)
    doc = Document(text="/", cursor_position=1)
    items = list(completer.get_completions(doc, object()))
    missing = [
        _display_text(c)
        for c in items
        if not _meta_text(c).strip()
    ]
    assert not missing, (
        "Every slash palette row must carry a description in its meta "
        f"column; missing for: {missing[:5]}"
    )


def test_palette_entries_display_as_slash_prefixed() -> None:
    """``display`` should render as ``/<name>`` so the palette looks like a palette.

    If the display is just the bare name the user can't tell it's a slash
    command at a glance — the ``/`` prefix is the palette's identity.
    """
    completer = SlashCompleter(repo_root=None)
    doc = Document(text="/", cursor_position=1)
    items = list(completer.get_completions(doc, object()))
    assert items, "completer produced no items"
    bad = [_display_text(c) for c in items if not _display_text(c).startswith("/")]
    assert not bad, (
        "Palette rows must render with a leading `/` in their display; "
        f"offenders: {bad[:5]}"
    )


# ----------------------------------------------------------------------
# Driver-level contract: menu reserved space + key binding on `/`.
# ----------------------------------------------------------------------


def test_driver_reserves_space_for_completion_menu() -> None:
    """The PromptSession must pin ``reserve_space_for_menu`` >= 6 rows.

    prompt_toolkit's default is 8, but any number of render paths
    (bottom toolbar, low terminal, skin overrides) can squeeze the menu
    to zero. We read the source to verify the kwarg is set explicitly
    so it survives future defaults changes in upstream.
    """
    src = inspect.getsource(_driver._run_prompt_toolkit)
    assert "reserve_space_for_menu" in src, (
        "driver._run_prompt_toolkit must set reserve_space_for_menu on "
        "the PromptSession so the slash palette actually renders."
    )


def test_driver_binds_slash_to_open_palette() -> None:
    """Pressing `/` on an empty buffer must open the completion menu.

    We look for a KeyBindings binding on ``"/"`` inside
    ``_build_key_bindings`` that calls ``start_completion``. The source-
    level check is deliberate — importing the driver to inspect its
    KeyBindings requires a running Application, which pytest can't give
    us headlessly.
    """
    src = inspect.getsource(_driver._build_key_bindings)
    assert 'kb.add("/")' in src or "kb.add('/')" in src, (
        "driver._build_key_bindings must bind `/` so the palette opens "
        "on first keystroke — Claude-Code/opencode-style."
    )
    assert "start_completion" in src, (
        "the `/` binding must call buffer.start_completion(...) so the "
        "menu pops immediately, not just on the next complete_while_typing tick."
    )
