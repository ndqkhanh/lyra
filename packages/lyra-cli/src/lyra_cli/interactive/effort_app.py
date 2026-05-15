"""Interactive horizontal-slider picker for ``/effort``.

A tiny prompt_toolkit ``Application`` that runs in-place above the
REPL, lets the user adjust the cursor with ←/→ (or h/l, Tab/Shift-Tab),
confirm with Enter, or bail with Esc / Ctrl-C / q. Returns the picked
level on confirm or ``None`` on cancel.

Kept separate from :mod:`.effort` so the pure model stays
prompt_toolkit-free (cheap import for tests + non-TTY paths).
"""
from __future__ import annotations

from typing import Optional

from prompt_toolkit.application import Application
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import HSplit, Layout, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.styles import Style

from .effort import EffortPicker


_STYLE = Style.from_dict(
    {
        "header":   "bold #00E5FF",
        "axis":     "#6B7280",
        "track":    "#7C4DFF",
        "marker":   "bold #FFC857",
        "level":    "#A0AEC0",
        "level.active": "bold #00E5FF",
        "hint":     "italic #6B7280",
    }
)


def _build_fragments(picker: EffortPicker, *, width: int) -> FormattedText:
    """Compose the four-line slider into a single FormattedText so the
    Application can render it as one ``FormattedTextControl``."""
    axis, track, level_row, hint = picker.render_slider_lines(width=width)

    # Highlight the cursor on the track and the matching level name.
    cursor_col = picker.cursor
    n = len(picker.levels)
    target_col = 0 if n <= 1 else round(cursor_col * (width - 1) / (n - 1))

    fragments: list[tuple[str, str]] = []
    fragments.append(("class:header", "  Effort\n\n"))
    fragments.append(("class:axis", "  " + axis + "\n"))

    # Track: dim by default, marker bright at cursor position.
    fragments.append(("class:track", "  "))
    for i, ch in enumerate(track):
        if ch == "▲":
            fragments.append(("class:marker", ch))
        else:
            fragments.append(("class:track", ch))
    fragments.append(("", "\n"))

    # Level row: highlight the level whose centred column matches target_col.
    # Re-derive per-level columns to know which name is the active one.
    fragments.append(("class:level", "  "))
    active = picker.value
    # Walk the level_row once, tagging characters that fall inside the
    # active level's name span.
    active_start = level_row.find(active)
    active_end = active_start + len(active) if active_start != -1 else -1
    for i, ch in enumerate(level_row):
        if active_start != -1 and active_start <= i < active_end:
            fragments.append(("class:level.active", ch))
        else:
            fragments.append(("class:level", ch))
    fragments.append(("", "\n\n"))

    fragments.append(("class:hint", "  " + hint))
    return FormattedText(fragments)


def run_effort_picker(*, initial: str = "medium", width: int = 50) -> Optional[str]:
    """Run the interactive picker. Returns the chosen level or ``None``
    on cancel. Requires a TTY — callers should fall back to the static
    render when ``run_in_terminal`` would fail.
    """
    picker = EffortPicker(initial=initial)
    cancelled = False

    kb = KeyBindings()

    @kb.add("left")
    @kb.add("h")
    @kb.add("s-tab")
    def _(_event: object) -> None:
        picker.left()

    @kb.add("right")
    @kb.add("l")
    @kb.add("tab")
    def _(_event: object) -> None:
        picker.right()

    @kb.add("home")
    def _(_event: object) -> None:
        # Jump to the leftmost level.
        while picker.cursor != 0:
            picker.left()

    @kb.add("end")
    def _(_event: object) -> None:
        # Jump to the rightmost level.
        last = len(picker.levels) - 1
        while picker.cursor != last:
            picker.right()

    @kb.add("enter")
    def _(event: object) -> None:
        nonlocal cancelled
        cancelled = False
        app.exit(result=picker.value)  # type: ignore[has-type]

    @kb.add("escape")
    @kb.add("c-c")
    @kb.add("q")
    def _(event: object) -> None:
        nonlocal cancelled
        cancelled = True
        app.exit(result=None)  # type: ignore[has-type]

    body = Window(
        content=FormattedTextControl(
            text=lambda: _build_fragments(picker, width=width),
            focusable=True,
            show_cursor=False,
        ),
        always_hide_cursor=True,
        height=6,
    )

    layout = Layout(HSplit([body]))

    app = Application(
        layout=layout,
        key_bindings=kb,
        style=_STYLE,
        full_screen=False,
        mouse_support=False,
    )

    try:
        result = app.run()
    except (KeyboardInterrupt, EOFError):
        return None

    if cancelled:
        return None
    return result if isinstance(result, str) else None


__all__ = ["run_effort_picker"]
