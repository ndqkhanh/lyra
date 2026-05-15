"""Status-bar v2 footer renderer.

Replaces the legacy ``StatusSource.render`` text output with a Rich
:class:`~rich.text.Text` that follows opencode's footer layout:

::

    cwd  ·  ◆ <model>  ·  <mode>  ·  △ <perms>  ·  ✦ <lsp>  ·  ⊙ <mcp>
                                          ·  t<turn>  ·  <tokens>  ·  $<cost>

Empty / zero fields collapse so a fresh session shows just
``cwd · ◆ deepseek-v4-pro · plan``. Non-TTY callers (log captures,
piped output) request ``plain=True`` to get a plain-text string with
no Rich markup or unicode symbols, but field labels preserved.
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Optional, Union

from rich.text import Text

from .task_list import render_checklist_text

if TYPE_CHECKING:
    from .status_source import StatusSource


def _humanise_tokens(n: int) -> str:
    if n < 1_000:
        return str(n)
    if n < 1_000_000:
        return f"{n / 1_000:.1f}k"
    return f"{n / 1_000_000:.1f}M"


def _fmt_elapsed(secs: float) -> str:
    m, s = divmod(int(secs), 60)
    return f"{m}m {s:02d}s" if m else f"{s}s"


def _truncate(text: str, width: int) -> str:
    return text if len(text) <= width else text[: width - 1] + "…"


# Symbol vocabulary, kept here so the welcome screen and command
# palette can reuse it without re-importing.
SYM_MODEL = "◆"
SYM_PERMS = "△"
SYM_LSP = "✦"
SYM_MCP = "⊙"
SEP = " · "

def render_checklist_section(source: "StatusSource") -> str:
    """Return the checklist block as a plain-text string (multi-line).

    Returns ``""`` when there are no tasks so callers can skip the newline.
    Reads the task list via :meth:`StatusSource.snapshot_tasks` to avoid
    holding the lock while rendering.
    """
    tasks = source.snapshot_tasks()
    return render_checklist_text(tasks)


def render_agents_text(processes: list, *, max_show: int = 3) -> str:
    """Render a compact agent list for the REPL bottom toolbar.

    Each line: ``  ◯ {type:<14} {desc:<38}  {elapsed} · ↓ {tokens} tokens``

    Args:
        processes: List of :class:`~lyra_core.transparency.models.AgentProcess`.
        max_show: Maximum number of agent lines to display.

    Returns:
        Multi-line string (empty string when no processes).
    """
    if not processes:
        return ""
    lines: list[str] = []
    for proc in processes[:max_show]:
        agent_type = _infer_agent_type(proc)
        desc = _truncate(proc.current_tool or "—", 38)
        elapsed = _fmt_elapsed(getattr(proc, "elapsed_s", 0.0))
        tokens = _humanise_tokens(getattr(proc, "tokens_out", 0))
        lines.append(f"  ◯ {agent_type:<14} {desc:<38}  {elapsed} · ↓ {tokens} tokens")
    return "\n".join(lines)


def _infer_agent_type(proc: object) -> str:
    """Guess a short agent type label from an AgentProcess."""
    session_id = getattr(proc, "session_id", "") or ""
    for keyword in ("executor", "researcher", "planner", "architect", "reviewer"):
        if keyword in session_id.lower():
            return keyword
    return "general-purpose"


__all__ = [
    "render_footer",
    "render_checklist_section",
    "render_agents_text",
    "SEP",
    "SYM_MODEL",
    "SYM_PERMS",
    "SYM_LSP",
    "SYM_MCP",
]


def _shorten_cwd(cwd: Path, max_width: int) -> str:
    """Compress ``cwd`` to fit within ``max_width`` chars.

    First tries ``~`` expansion. If still too long, drops middle
    segments and inserts ``…`` — this beats truncating the leaf
    (where users actually distinguish projects) or the head (where
    ``~/Downloads`` lives).
    """
    raw = str(cwd)
    home = str(Path.home())
    if raw.startswith(home):
        raw = "~" + raw[len(home):]
    if len(raw) <= max_width:
        return raw

    # Walk segments, keeping head + tail, replace middle with `…`.
    parts = raw.split("/")
    if len(parts) <= 2:
        return raw[: max_width - 1] + "…"
    head = parts[0]  # "" or "~" or "/"
    tail = parts[-1]
    middle = parts[1:-1]
    while middle and len(f"{head}/…/{tail}") > max_width and len(middle) > 1:
        middle.pop(len(middle) // 2)
    candidate = f"{head}/…/{tail}" if not middle else f"{head}/{'/'.join(middle)}/{tail}"
    if len(candidate) > max_width:
        candidate = f"{head}/…/{tail}"
    if len(candidate) > max_width:
        return candidate[: max_width - 1] + "…"
    return candidate


def _format_tokens(n: int) -> str:
    """Compact token display: 1234 → "1.2k", 1_234_567 → "1.2M"."""
    if n < 1_000:
        return str(n)
    if n < 1_000_000:
        return f"{n / 1000:.1f}k"
    return f"{n / 1_000_000:.1f}M"


def _format_cost(usd: float) -> str:
    """Cost display: $0.01 always shows two decimals (cents resolution)."""
    if usd < 0.01:
        return f"${usd:.4f}"
    return f"${usd:.2f}"


def render_footer(
    source: "StatusSource",
    *,
    term_cols: int = 80,
    plain: bool = False,
) -> Union[Text, str]:
    """Render the v2 footer for ``source``.

    Args:
        source: The :class:`StatusSource` to read fields from. Reads
            are atomic via :attr:`StatusSource._lock`.
        term_cols: Maximum width to fit. The footer truncates the cwd
            (middle segments) before any other field; if the right
            side is still too wide we drop low-priority fields
            (cost, tokens) before high-priority ones (model, mode).
        plain: When True, return a plain text string with no symbols
            or Rich markup. Used by the log-capture and non-TTY
            paths so output stays greppable.
    """
    with source._lock:
        cwd = source.cwd
        model = source.model
        mode = source.mode
        permissions = source.permissions
        lsp = source.lsp_count
        mcp = source.mcp_count
        tokens = source.tokens
        cost = source.cost_usd
        turn = source.turn
        extra = dict(source.extra)
        bg_tasks = source.bg_task_count
        shell_count = getattr(source, "shell_count", 0)
        is_inferring = getattr(source, "is_inferring", False)

    # Build a list of (priority, plain_segment, rich_segment) tuples.
    # Higher priority = drops first when terminal is narrow.
    segments: list[tuple[int, str, Text]] = []

    # cwd — left-most, never drops; we shrink instead.
    cwd_text = _shorten_cwd(cwd, max_width=max(20, term_cols // 3))
    segments.append((0, cwd_text, Text(cwd_text, style="dim")))

    if model:
        plain_seg = f"model:{model}"
        rich_seg = Text.assemble(
            (f"{SYM_MODEL} ", "bright_cyan"), (model, "bright_cyan bold")
        )
        segments.append((0, plain_seg, rich_seg))

    if mode:
        plain_seg = mode
        rich_seg = Text(mode, style="green")
        segments.append((1, plain_seg, rich_seg))

    if permissions:
        if permissions == "yolo":
            # Claude Code-style bypass badge: ⏵⏵ bypass permissions on
            plain_seg = "bypass permissions on"
            rich_seg = Text.assemble(("⏵⏵ ", "bold red"), ("bypass permissions on", "bold red"))
        else:
            plain_seg = f"permissions={permissions}"
            rich_seg = Text.assemble((f"{SYM_PERMS} ", "yellow"), (permissions, "yellow"))
        segments.append((2, plain_seg, rich_seg))

    if lsp:
        plain_seg = f"LSP:{lsp}"
        rich_seg = Text.assemble((f"{SYM_LSP} ", "magenta"), (str(lsp), "magenta"))
        segments.append((3, plain_seg, rich_seg))

    if mcp:
        plain_seg = f"MCP:{mcp}"
        rich_seg = Text.assemble((f"{SYM_MCP} ", "blue"), (str(mcp), "blue"))
        segments.append((3, plain_seg, rich_seg))

    if shell_count:
        shell_label = "shell" if shell_count == 1 else "shells"
        plain_seg = f"{shell_count} {shell_label}"
        rich_seg = Text(plain_seg, style="bold #00E5FF")
        segments.append((2, plain_seg, rich_seg))

    if bg_tasks:
        bg_label = "task" if bg_tasks == 1 else "tasks"
        bg_str = f"{bg_tasks} background {bg_label}"
        plain_seg = f"{bg_str} · ↓ to manage"
        rich_seg = Text.assemble(
            ("⏵⏵ ", "cyan"),
            (bg_str, "bold cyan"),
            (" · ↓ to manage", "dim cyan"),
        )
        segments.append((1, plain_seg, rich_seg))

    if is_inferring:
        plain_seg = "esc to interrupt"
        rich_seg = Text(plain_seg, style="dim italic")
        segments.append((1, plain_seg, rich_seg))

    if turn:
        plain_seg = f"t{turn}"
        rich_seg = Text(f"t{turn}", style="dim")
        segments.append((4, plain_seg, rich_seg))

    if tokens:
        formatted = _format_tokens(tokens)
        plain_seg = f"{formatted} tok"
        rich_seg = Text(f"{formatted} tok", style="dim")
        segments.append((5, plain_seg, rich_seg))

    if cost:
        cost_str = _format_cost(cost)
        plain_seg = cost_str
        rich_seg = Text(cost_str, style="bold yellow")
        segments.append((6, plain_seg, rich_seg))

    for k, v in extra.items():
        plain_seg = f"{k}:{v}"
        segments.append((7, plain_seg, Text(plain_seg, style="dim")))

    # Drop low-priority segments until we fit.
    def _join_plain(segs: list[tuple[int, str, Text]]) -> str:
        return SEP.join(s[1] for s in segs)

    while segments and len(_join_plain(segments)) > term_cols:
        # Drop the highest-numbered priority that's still present.
        max_pri = max(s[0] for s in segments)
        if max_pri == 0:
            break  # cwd + model + mode are non-droppable
        for i in range(len(segments) - 1, -1, -1):
            if segments[i][0] == max_pri:
                segments.pop(i)
                break

    if plain:
        return _join_plain(segments)

    # Render the Rich Text with the styled separators.
    out = Text()
    sep = Text(SEP, style="dim")
    for i, (_, _plain_seg, rich_seg) in enumerate(segments):
        if i:
            out.append_text(sep)
        out.append_text(rich_seg)
    return out
