"""Claude-Code-style welcome banner for the Lyra REPL.

Two-column layout: left column carries the wordmark, mark, model line and
working-directory; right column carries "Tips for getting started" and
"What's new" lists. Below the panel we print a model-source hint, a
horizontal rule, the input prompt area framed by rules, and a footer
that keeps ``? for shortcuts`` on the left and the active *mode* +
*effort* indicator pinned to the bottom-right corner.

This module is non-destructive: the existing :mod:`banner` module keeps
working. The driver can switch to this layout via a config flag (e.g.
``ui.banner_style = "claude"``) without losing the Lyra-flavoured
ANSI-shadow logo path for users who prefer it.

The renderer is pure (no I/O, no env reads) so tests render and grep
without spinning a real Console.
"""
from __future__ import annotations

import io
import os
import shutil
from pathlib import Path
from typing import Sequence

from rich.box import ROUNDED
from rich.console import Console
from rich.padding import Padding
from rich.table import Table
from rich.text import Text

from .. import __version__


# Compact 3-line brand mark — visual match for Claude Code's asterisk-block.
# Lyra-themed: slimmer pillars with a tilted base to read as "L Y" at a glance.
_MARK = (
    "▐▛███▜▌\n"
    "▝▜█████▛▘\n"
    " ▘▘ ▝▝"
)


def _term_cols(default: int = 80) -> int:
    try:
        return shutil.get_terminal_size(fallback=(default, 24)).columns
    except OSError:
        return default


def _truncate_right(s: str, width: int) -> str:
    """Right-truncate with ``…`` if needed; never widens."""
    if len(s) <= width:
        return s
    if width <= 1:
        return s[:width]
    return s[: width - 1] + "…"


def render_claude_style_banner(
    *,
    user_name: str,
    model: str,
    plan: str,
    organization: str,
    cwd: Path,
    tips: Sequence[str],
    whats_new: Sequence[str],
    title: str = f"Lyra v{__version__}",
    term_cols: int | None = None,
    plain: bool = False,
) -> str:
    """Return a ready-to-print welcome panel string.

    The panel is two columns inside one rounded box. Width auto-fits the
    terminal; right column gets ~25 cols, left column gets the rest with
    a 2-col separator and 1-col borders.
    """
    cols = term_cols if term_cols is not None else _term_cols()
    panel_width = max(60, min(cols - 2, 100))

    # Right column reserves a fixed ratio of the panel — matches the
    # claude reference where the right pane is comfortably narrow.
    right_w = max(22, panel_width // 3)
    left_w = panel_width - right_w - 5  # 2 borders + " │ " separator

    buf = io.StringIO()
    console = Console(
        file=buf,
        force_terminal=not plain,
        color_system=None if plain else "truecolor",
        soft_wrap=False,
        legacy_windows=False,
        width=panel_width,
    )

    # --- left column — assembled as a Rich Group of centered Text rows.
    left_rows: list[Text] = []
    left_rows.append(Text(""))
    left_rows.append(Text(f"Welcome back {user_name}!", style="bold", justify="center"))
    left_rows.append(Text(""))
    for line in _MARK.splitlines():
        left_rows.append(Text(line, style="bright_yellow", justify="center"))
    left_rows.append(Text(""))
    left_rows.append(Text(f"{model} · {plan} ·", justify="center"))
    left_rows.append(Text(organization, justify="center"))
    left_rows.append(Text(str(cwd), style="dim", justify="center"))

    # --- right column — single column with title + bullets, dim style.
    right_rows: list[Text] = []
    right_rows.append(Text("Tips for getting", style="bold"))
    right_rows.append(Text("started"))
    for tip in tips:
        right_rows.append(Text(_truncate_right(tip, right_w - 1), style="dim"))
    right_rows.append(Text("─" * (right_w - 2), style="dim"))
    right_rows.append(Text("What's new", style="bold"))
    for entry in whats_new:
        right_rows.append(Text(_truncate_right(entry, right_w - 1), style="dim"))

    # Pad the shorter column with empty rows so the table renders flush.
    n_rows = max(len(left_rows), len(right_rows))
    while len(left_rows) < n_rows:
        left_rows.append(Text(""))
    while len(right_rows) < n_rows:
        right_rows.append(Text(""))

    # Build a 2-column Rich Table with a ROUNDED box and a vertical
    # divider between the columns. Title hangs off the top border.
    table = Table(
        show_header=False,
        show_lines=False,
        show_edge=True,
        box=ROUNDED,
        padding=(0, 1),
        title=Text.assemble(
            ("─── ", "dim"),
            (title, "bold bright_cyan"),
            (" ", "dim"),
        ),
        title_justify="left",
        border_style="dim",
        expand=False,
        width=panel_width,
    )
    table.add_column(justify="center", width=left_w, no_wrap=True, overflow="ellipsis")
    table.add_column(justify="left", width=right_w, no_wrap=True, overflow="ellipsis")
    for l, r in zip(left_rows, right_rows):
        table.add_row(l, r)

    console.print(table)
    return buf.getvalue()


def render_using_line(
    *, model: str, settings_source: str, term_cols: int | None = None,
) -> str:
    """Print the small ``Using <model> (from <source>) · /model to change`` line."""
    cols = term_cols if term_cols is not None else _term_cols()
    buf = io.StringIO()
    console = Console(
        file=buf, force_terminal=True, color_system="truecolor",
        soft_wrap=False, legacy_windows=False, width=cols,
    )
    line = Text(no_wrap=True)
    line.append("  Using ", style="dim")
    line.append(model, style="bold")
    line.append(f" (from {settings_source})", style="dim")
    line.append(" · ", style="dim")
    line.append("/model", style="bold cyan")
    line.append(" to change", style="dim")
    console.print(line)
    return buf.getvalue()


def render_input_frame(
    *,
    mode: str,
    effort: str,
    placeholder: str = "",
    term_cols: int | None = None,
) -> str:
    """Render the prompt area: rule · ``❯ <placeholder>`` · rule · footer.

    The footer pins ``? for shortcuts`` to the left and ``◉ <effort> · <mode>``
    to the right corner — that's the user's explicit ask.
    """
    cols = term_cols if term_cols is not None else _term_cols()
    buf = io.StringIO()
    console = Console(
        file=buf, force_terminal=True, color_system="truecolor",
        soft_wrap=False, legacy_windows=False, width=cols,
    )

    rule = "─" * cols
    console.print(Text(rule, style="dim"))

    prompt = Text(no_wrap=True)
    prompt.append("❯ ", style="bold bright_cyan")
    if placeholder:
        prompt.append(placeholder, style="dim")
    console.print(prompt)

    console.print(Text(rule, style="dim"))

    # Footer: left side + right side with computed gap.
    left_text = "  ? for shortcuts"
    right_text = f"◉ {effort} · {mode}"
    visible_len = len(left_text) + len(right_text)
    gap = max(2, cols - visible_len)

    footer = Text(no_wrap=True)
    footer.append("  ", style="dim")
    footer.append("?", style="bold")
    footer.append(" for shortcuts", style="dim")
    footer.append(" " * (gap - 2))  # we already wrote 2-col leading pad
    footer.append("◉", style="bold bright_yellow")
    footer.append(f" {effort}", style="bold")
    footer.append(" · ", style="dim")
    footer.append(mode, style="bold cyan")
    console.print(footer)

    return buf.getvalue()


__all__ = [
    "render_claude_style_banner",
    "render_using_line",
    "render_input_frame",
]
