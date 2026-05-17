"""Lyra-specific status-segment formatting helpers.

The ``tokens`` segment matches Hermes-Agent's pattern — a horizontal
fill bar plus percentage, coloured by occupancy threshold:

    [██████░░░░░░░░░░░░░░]  6%

  * green   < 50%
  * yellow  50–80%
  * orange  80–95%
  * red     ≥ 95%

These pure helpers keep the format logic testable without mounting a
Textual app. The colour names map to Rich style strings (consumed by
the StatusLine widget's ``set_segment`` path).
"""
from __future__ import annotations

from typing import Final

# Lyra-default context window when the provider doesn't expose one.
# Claude Sonnet 4 + DeepSeek + GPT-4o all sit in the 128–200k range; 200k
# is a reasonable upper bound that keeps the fill bar usable.
DEFAULT_CONTEXT_WINDOW: Final[int] = 200_000

# Bar width in cells. 20 keeps the segment readable in the compact
# (52–75 col) width mode of the StatusLine.
_BAR_WIDTH: Final[int] = 20

# Sentinel glyphs — full block + light shade. Both single-width so the
# bar lines up across CJK / emoji terminal modes.
_FILL: Final[str] = "█"
_EMPTY: Final[str] = "░"


def threshold_colour(pct: float) -> str:
    """Return a Rich style name for the given fill percentage [0–100]."""
    if pct >= 95.0:
        return "bold red"
    if pct >= 80.0:
        return "bold orange1"
    if pct >= 50.0:
        return "bold yellow"
    return "bold green"


def format_token_bar(used: int, maximum: int = DEFAULT_CONTEXT_WINDOW) -> str:
    """Format the tokens segment as ``[██░░] N% (used/max)``.

    Returns a Rich-markup string suitable for ``StatusLine.set_segment``.
    ``maximum`` <= 0 falls back to ``DEFAULT_CONTEXT_WINDOW`` to avoid
    a zero-division — the caller is responsible for surfacing the real
    cap once we wire up provider introspection (Phase 5/6).
    """
    if used < 0:
        used = 0
    if maximum <= 0:
        maximum = DEFAULT_CONTEXT_WINDOW
    pct = min(100.0, used * 100.0 / maximum)
    filled = int(round(pct / 100.0 * _BAR_WIDTH))
    bar = _FILL * filled + _EMPTY * (_BAR_WIDTH - filled)
    style = threshold_colour(pct)
    used_label = _humanise(used)
    max_label = _humanise(maximum)
    # Embed Rich markup so the colour follows the threshold; the rest of
    # the segment stays muted.
    return f"[{style}]{bar}[/]  {pct:>4.1f}%  [dim]{used_label}/{max_label}[/]"


def format_repo_segment(working_dir: str) -> str:
    """Compact repo label — basename of the working directory.

    Resolves relative paths (e.g. ``"."``) to absolute so the segment
    always shows a meaningful name instead of ``"."``.
    """
    if not working_dir:
        return "—"
    from pathlib import Path
    try:
        name = Path(working_dir).resolve().name
    except Exception:
        name = working_dir.rstrip("/").rsplit("/", 1)[-1]
    return name or "/"


def format_turn_segment(turn_index: int) -> str:
    """Render the ``turn`` counter."""
    if turn_index < 0:
        turn_index = 0
    return f"#{turn_index}"


# ---------------------------------------------------------------------
# Observability segments (Phase 6)
# ---------------------------------------------------------------------

def format_health_segment(score: float) -> str:
    """Render the composite health score as a coloured badge.

    Score is 0–1 (from ``DisplayState.health_score()``):
      * green  ≥ 0.7
      * yellow ≥ 0.4
      * red    < 0.4
    """
    score = max(0.0, min(1.0, score))
    if score >= 0.7:
        return f"[bold green]● {score:.0%}[/]"
    if score >= 0.4:
        return f"[bold yellow]◐ {score:.0%}[/]"
    return f"[bold red]○ {score:.0%}[/]"


_PERMISSION_STYLES: dict[str, str] = {
    "plan": "bold cyan",
    "auto": "bold green",
    "ask": "bold yellow",
    "agent": "bold magenta",
}


def format_permission_badge(mode: str) -> str:
    """Render the permission mode as a coloured badge for the status bar.

    Modes: plan / auto / ask / agent (short labels from Lyra's taxonomy).
    Unknown modes fall back to dim white.
    """
    if not mode or mode == "—":
        return "[dim]mode=—[/]"
    style = _PERMISSION_STYLES.get(mode.lower(), "white")
    return f"[{style}]mode={mode}[/]"


def format_bg_tasks_segment(count: int) -> str:
    """Render the background task count as a coloured badge.

    Returns an empty string when ``count`` is zero so the caller can
    skip the segment entirely (field collapses in narrow terminals).

    Example output:
        [bold cyan]⏵⏵ 5 background tasks[/]
    """
    if count <= 0:
        return ""
    label = "task" if count == 1 else "tasks"
    return f"[bold cyan]⏵⏵ {count} background {label}[/]"


def format_daemon_segment(iteration: int, last_job: str = "—") -> str:
    """Render the daemon iteration counter and last cron job.

    Shows nothing (empty string) when iteration is 0 — the daemon hasn't
    ticked yet and the segment would just be noise.
    """
    if iteration <= 0:
        return ""
    job_label = f"  cron={last_job}" if last_job and last_job != "—" else ""
    return f"[dim]⊙ iter={iteration}{job_label}[/]"


_TOOL_STATUS_STYLES: dict[str, str] = {
    "running": "yellow",
    "done": "green",
    "error": "red",
    "blocked": "bold red",
}


def format_tool_card(name: str, status: str, duration_ms: float | None = None) -> str:
    """Format one live tool card line for the status bar or TUI overlay.

    Example output:
        [yellow]⚙ bash[/]  running
        [green]⚙ bash[/]  done  420ms
        [red]⚙ rm[/]  blocked
    """
    style = _TOOL_STATUS_STYLES.get(status, "white")
    dur = f"  {duration_ms:.0f}ms" if duration_ms is not None else ""
    return f"[{style}]⚙ {name}[/]  {status}{dur}"


# ---------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------


def _humanise(n: int) -> str:
    """Compact 4-character humanisation (1.2K / 9.9M)."""
    if n < 1_000:
        return str(n)
    if n < 1_000_000:
        return f"{n / 1_000:.1f}K"
    if n < 1_000_000_000:
        return f"{n / 1_000_000:.1f}M"
    return f"{n / 1_000_000_000:.1f}B"


def format_compaction_message(
    util_before: float,
    util_after: float,
    tokens_before: int,
    tokens_after: int,
    preserved: int,
    summarized: int,
) -> str:
    """Format context compaction notification message.

    Returns multi-line Rich markup matching Claude Code style:
        ✻ Conversation compacted (60% → 40%)
          ⎿  Preserved last 4 turns (12.5K tokens)
          ⎿  Summarized 8 older turns (45.2K → 8.1K tokens)

    Args:
        util_before: Context utilization before compaction (0.0-1.0)
        util_after: Context utilization after compaction (0.0-1.0)
        tokens_before: Token count before compaction
        tokens_after: Token count after compaction
        preserved: Number of turns preserved
        summarized: Number of turns summarized

    Returns:
        Multi-line Rich markup string
    """
    before_pct = f"{util_before:.0%}"
    after_pct = f"{util_after:.0%}"
    tokens_saved = tokens_before - tokens_after

    lines = [
        f"[bold cyan]✻[/] Conversation compacted ({before_pct} → {after_pct})",
        f"  [dim]⎿[/]  Preserved last {preserved} turns ({_humanise(tokens_after)} tokens)",
        f"  [dim]⎿[/]  Summarized {summarized} older turns ({_humanise(tokens_before)} → {_humanise(tokens_after)} tokens)",
    ]
    return "\n".join(lines)


def format_agents_segment(running: int, total: int, tokens: int) -> str:
    """Format live agent count badge for status bar.

    Example output:
        [bold cyan]⏺ Running 2/4 agents · 45.2K tokens[/]

    Args:
        running: Number of currently running agents
        total: Total number of agents
        tokens: Total token count across all agents

    Returns:
        Rich markup string for status bar, or empty string if no agents
    """
    if running <= 0:
        return ""

    tokens_label = _humanise(tokens)
    return f"[bold cyan]⏺ Running {running}/{total} agents · {tokens_label} tokens[/]"
