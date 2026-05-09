"""Claw-code-inspired tool-call card renderer.

Renders a compact three-line card around a tool invocation:

.. code-block:: text

    ╭─ bash ─╮
    │  $ ls -la
    ╰────────╯

Design tokens follow claw-code's signature style
(``rust/crates/rusty-claude-cli/src/main.rs::format_tool_call_start``):

- Borders in dim 256-color ``38;5;245``.
- Tool name bold cyan (``1;36``).
- For the ``bash`` tool, the preview is rendered on an inverted dim
  background (``48;5;236;38;5;255``) so the shell command pops.
- On error, the top border switches to a red accent (``38;5;203``)
  so the user can eyeball failed calls at a glance.

The output is raw ANSI and intended for ``sys.stdout.write`` /
``Console.file.write``. Width is sized to the longer of the border
framing the name and the widest body line so long names can't snap
the bottom border shorter than the top.
"""

from __future__ import annotations

from dataclasses import dataclass

_ANSI_RESET = "\x1b[0m"

# 256-color palette codes (match claw-code).
_DIM_BORDER = "\x1b[38;5;245m"
_NAME_BOLD_CYAN = "\x1b[1;36m"
_BASH_CHIP = "\x1b[48;5;236;38;5;255m"
_ERR_ACCENT = "\x1b[38;5;203m"


@dataclass(frozen=True)
class ToolCardStyle:
    border: str = _DIM_BORDER
    name: str = _NAME_BOLD_CYAN
    error_border: str = _ERR_ACCENT
    bash_chip: str = _BASH_CHIP


DEFAULT_STYLE = ToolCardStyle()


def render_tool_card(
    name: str,
    preview: str,
    *,
    is_error: bool = False,
    style: ToolCardStyle = DEFAULT_STYLE,
) -> str:
    r"""Return an ANSI-colored three-line tool card.

    Args:
        name: Tool name rendered in the top-border badge.
        preview: Body line (e.g. ``"$ ls -la"``).
        is_error: When ``True``, uses a red accent on the top border.
        style: Override :class:`ToolCardStyle`.

    Returns:
        A ``str`` containing exactly three lines separated by ``\n`` —
        top border, body, bottom border. Includes ANSI color escapes
        already; strip with ``re.sub(r"\x1b\[[0-9;]*m", "", s)`` for
        plain-text rendering.
    """
    safe_name = name or "tool"
    safe_preview = preview if preview is not None else ""

    # Visible widths (ignore ANSI escapes when sizing).
    name_plain_width = len(safe_name)
    body_plain_width = len(safe_preview)

    # Top border framing: "╭─ <name> ─╮" — compute minimum inner width
    # based on the name, then pad out to the widest body line so the
    # bottom border stays at least as wide.
    top_inner = f" {safe_name} "
    min_inner_width = len(top_inner) + 2  # for the two ─ sentinels
    inner_width = max(min_inner_width, body_plain_width + 2)
    dashes_top = inner_width - len(top_inner) - 2
    left_dash = "─"
    right_dashes = "─" * max(dashes_top, 0)

    border_top_color = style.error_border if is_error else style.border

    # --- top border ------------------------------------------------ #
    top = (
        f"{border_top_color}╭{left_dash} {style.name}{safe_name}{_ANSI_RESET}"
        f"{border_top_color} {right_dashes}╮{_ANSI_RESET}"
    )

    # --- body line ------------------------------------------------- #
    body_inner = safe_preview
    if safe_name == "bash":
        body_inner = f"{style.bash_chip}{body_inner}{_ANSI_RESET}"
    else:
        body_inner = f"{body_inner}"

    pad_right = max(inner_width - body_plain_width - 2, 0)
    body_line = (
        f"{style.border}│{_ANSI_RESET} {body_inner}"
        f"{' ' * pad_right}"
    )

    # --- bottom border --------------------------------------------- #
    # Always draw the bottom border as full width (at least as wide as
    # the top), so ``test_long_name_does_not_break_border_alignment``
    # holds even when the name is wider than any reasonable preview.
    full_inner_dashes = "─" * inner_width
    bottom = f"{style.border}╰{full_inner_dashes}╯{_ANSI_RESET}"

    return "\n".join([top, body_line, bottom])


__all__ = ["render_tool_card", "ToolCardStyle", "DEFAULT_STYLE"]
