"""Rich-aware prompter for the ``AskUserQuestion`` tool.

The lyra-core tool defines an injectable ``Prompter`` callback so the
core package stays free of Rich. This module is the lyra-cli side: a
Rich-rendered question panel + arrow-key picker that the agent loop
wires in via ``build_chat_tool_registry(ask_user_prompter=…)``.

Design choice — IntPrompt over a Live-driven arrow picker: the agent
loop is *already inside* the streaming chat panel's render path when
the tool is invoked, and nesting a second ``rich.live.Live`` region
(which is what an arrow picker needs) reliably fights with the parent
for cursor positioning. A numbered prompt (``1, 2, 3…``) renders
correctly in every terminal Lyra ships into and survives SSH /
``patch_stdout`` / piped runs without contortion.
"""
from __future__ import annotations

from typing import Sequence

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from lyra_core.tools.ask_user import AskUserPrompt


def _build_panel(prompt: AskUserPrompt) -> Panel:
    """Render the question + numbered options as a single Rich panel.

    Mode-coloured purple/indigo to match Lyra's other inline tool
    cards. The instruction line at the bottom changes based on
    ``multi_select`` so the user knows the input contract for the
    line they're about to type.
    """
    body = Text()
    body.append(prompt.question.strip() + "\n", style="bright_white")
    body.append("\n")
    for i, option in enumerate(prompt.options, 1):
        body.append(f"  {i}. ", style="bold #8B5CF6")
        body.append(option + "\n", style="bright_white")
    body.append("\n")
    if prompt.multi_select:
        body.append(
            "  → enter indices comma-separated (e.g. 1,3) or blank to cancel",
            style="italic #6B7280",
        )
    else:
        body.append(
            "  → enter index 1–"
            f"{len(prompt.options)} or blank to cancel",
            style="italic #6B7280",
        )
    return Panel(
        body,
        border_style="#8B5CF6",
        title="[bold #8B5CF6]ask user[/]",
        title_align="left",
        padding=(1, 2),
    )


def _parse_picks(raw: str, n_options: int, multi: bool) -> list[int]:
    """Convert ``"1,3"`` or ``"2"`` into validated 1-based indices.

    Bad tokens are silently dropped so a typo (``"1, , 3"``) doesn't
    cancel the whole picker — only an empty result cancels. Caps at
    one pick when ``multi=False`` to mirror the contract documented
    on :class:`AskUserPrompt`.
    """
    out: list[int] = []
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk.isdigit():
            continue
        n = int(chunk)
        if 1 <= n <= n_options:
            out.append(n)
    if not multi:
        out = out[:1]
    return out


def make_prompter(console: Console):
    """Return a :data:`lyra_core.tools.ask_user.Prompter` bound to ``console``.

    Closes over the console so the agent loop can hand the same Rich
    output surface to every dispatch — Live regions stack predictably
    when they share a console, and the question panel inherits the
    REPL's theme overrides without re-resolving the active skin.
    """

    def _prompter(prompt: AskUserPrompt) -> Sequence[int]:
        console.print(_build_panel(prompt))
        try:
            raw = input("→ ").strip()
        except (EOFError, KeyboardInterrupt):
            # Ctrl-D / Ctrl-C cancels — same end-state as an empty
            # answer, so the caller treats it as a deliberate skip.
            return ()
        if not raw:
            return ()
        return _parse_picks(raw, len(prompt.options), prompt.multi_select)

    return _prompter


__all__ = ["make_prompter"]
