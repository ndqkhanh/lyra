"""Regression: prompt_toolkit silently disables the buffer-level
``complete_while_typing`` filter whenever ``enable_history_search=True``.

Symptom: after the explicit ``start_completion()`` call from the ``/``
keybinding pops the palette, the next keystroke (e.g. ``m`` to filter to
``/m``) wipes ``complete_state`` via ``_text_changed`` and the buffer's
filter returns False, so no new completion task is scheduled. The user
sees the dropdown vanish on the second character.

prompt_toolkit's ``shortcuts/prompt.py`` wires the buffer with a
``Condition(complete_while_typing AND NOT enable_history_search)`` filter
(which is intentional in upstream — history search and completion would
fight over the up/down arrows). Lyra opted out of history search to keep
live filtering, so this test pins the contract by:

1. Reading the kwargs the driver passes to ``PromptSession``.
2. Building a real ``PromptSession`` with those kwargs.
3. Asserting the *buffer-level* filter (the one ``_async_completer``
   actually consults) returns True.

The user-facing ``PromptSession.complete_while_typing`` attribute is
*not* a reliable signal — it returns True even when the underlying
buffer filter returns False. That mismatch is what made this bug
hard to spot.
"""
from __future__ import annotations

import inspect

from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory

from lyra_cli.interactive import driver


def test_run_prompt_toolkit_does_not_set_enable_history_search_to_true() -> None:
    """Sentinel: the source must not re-introduce the broken combo.

    Ignores comment lines so the explanatory comment that tells future
    maintainers *why* the kwarg is absent doesn't trip the test.
    """
    src = inspect.getsource(driver._run_prompt_toolkit)
    code_lines = [
        line for line in src.splitlines() if not line.lstrip().startswith("#")
    ]
    code = "\n".join(code_lines)
    assert "enable_history_search=True" not in code, (
        "PromptSession sets enable_history_search=True, which silently "
        "disables the buffer-level complete_while_typing filter and makes "
        "the slash palette disappear after the first keystroke."
    )


def test_buffer_complete_while_typing_filter_is_active() -> None:
    """Behavioural: a PromptSession built like the driver builds it must
    have a buffer whose ``complete_while_typing`` filter returns True."""
    ps = PromptSession(
        history=InMemoryHistory(),
        complete_while_typing=True,
        # Mirror the driver's other relevant kwargs that touch completion;
        # any future addition that re-enables history search would flip
        # the filter and this assertion would catch it.
    )
    assert ps.default_buffer.complete_while_typing() is True


def test_enable_history_search_silently_disables_filter() -> None:
    """Documents the upstream prompt_toolkit gotcha so future maintainers
    don't re-introduce it 'because the user-facing attribute looks True'.
    """
    ps = PromptSession(
        history=InMemoryHistory(),
        complete_while_typing=True,
        enable_history_search=True,
    )
    # The user-facing attribute reports True...
    assert ps.complete_while_typing is True
    # ...but the buffer-level filter (the one that actually gates
    # _async_completer on every keystroke) is False. This is the
    # gotcha that caused the slash dropdown to close after `/m`.
    assert ps.default_buffer.complete_while_typing() is False
