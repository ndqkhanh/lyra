"""Single source of truth for Lyra's REPL key bindings.

The driver wires ``Alt-?`` directly; the ``/keybindings`` slash handler
imports the same helper so the cheatsheet stays in sync regardless of
which surface the user reaches for.

Adding a new binding is two edits: add a row in :data:`_KEYBINDINGS_HELP`
*and* register the chord in :func:`driver._build_key_bindings`. The
table here is the thing users see — keep its descriptions current.
"""
from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table


# (group, chord, description)
_KEYBINDINGS_HELP: tuple[tuple[str, str, str], ...] = (
    ("Completion", "/",            "open slash-command palette"),
    ("Completion", "@",            "open in-repo file picker"),
    ("Completion", "#",            "open skill-pack picker"),
    ("Mode",       "Tab",          "cycle modes forward (empty buffer) / autocomplete"),
    ("Mode",       "Shift-Tab",    "cycle modes reverse"),
    ("Mode",       "Alt-T",        "toggle deep-think"),
    ("Mode",       "Alt-M",        "cycle permission mode"),
    ("Mode",       "Alt-P",        "open /models catalog"),
    ("Mode",       "Alt-I",        "open /skills picker"),
    ("Mode",       "Alt-G",        "open /agents picker"),
    ("Edit",       "Ctrl-J",       "insert newline (multi-line)"),
    ("Edit",       "Alt-Enter",    "insert newline"),
    ("Edit",       "Ctrl-G",       "open $EDITOR for the buffer"),
    ("Edit",       "Ctrl-X Ctrl-E","open $EDITOR (bash/zsh canonical)"),
    ("Edit",       "Ctrl-E",       "accept ghost-text suggestion (full)"),
    ("Edit",       "→ at EOL",     "accept ghost-text suggestion"),
    ("Edit",       "Alt-F",        "accept next word of suggestion"),
    ("Edit",       "Esc-K",        "wipe the input buffer"),
    ("Session",    "Ctrl-N",       "new chat (clear messages, keep mode/model)"),
    ("History",    "Ctrl-R",       "reverse history search"),
    ("History",    "Esc Esc",      "rewind one turn (truncates JSONL)"),
    ("History",    "Ctrl-F",       "refocus foreground subagent"),
    ("Display",    "Ctrl-L",       "clear screen + reprint banner"),
    ("Display",    "Ctrl-T",       "toggle task panel"),
    ("Display",    "Ctrl-O",       "toggle verbose tool output"),
    ("Display",    "Alt-?",        "show this cheatsheet"),
    ("Display",    "/keybindings", "show this cheatsheet (slash form)"),
    ("Session",    "Ctrl-C",       "cancel input / stop in-flight LLM turn"),
    ("Session",    "Ctrl-D",       "exit session (on empty buffer)"),
)


def show_keybindings_help(console: Console) -> None:
    """Render the keybindings cheatsheet as a Rich panel."""
    table = Table(
        show_header=True,
        header_style="bold #00E5FF",
        show_edge=False,
        pad_edge=False,
        padding=(0, 2),
    )
    table.add_column("Group", style="dim")
    table.add_column("Key", style="bold #7C4DFF")
    table.add_column("Action")
    last_group = ""
    for group, chord, desc in _KEYBINDINGS_HELP:
        shown_group = group if group != last_group else ""
        table.add_row(shown_group, chord, desc)
        last_group = group
    console.print(
        Panel(
            table,
            title="[bold #00E5FF]Lyra keybindings[/]",
            subtitle="[dim italic]Alt-? or /keybindings to dismiss/re-show[/]",
            border_style="#7C4DFF",
            padding=(1, 2),
        )
    )


__all__ = ["_KEYBINDINGS_HELP", "show_keybindings_help"]
