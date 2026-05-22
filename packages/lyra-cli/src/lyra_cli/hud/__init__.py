"""Lyra HUD — live status pane (claude-hud-inspired).

Provides the rendering substrate for ``lyra hud preview`` and future
``lyra hud watch``. A HUD is a configurable grid of status widgets
(panels) that render live session state: token usage, agents, tasks,
model info, timing, and key bindings.

Inspired by claude-hud's layout + ECC's enterprise-controls.md
observability requirements.

Public API:
    - ``render(state, config, max_width)`` → Rich renderable
    - ``load_preset(name)`` → HudConfig
    - ``available_presets()`` → list[str]
    - ``HudState`` dataclass (the shape the app pushes into the renderer)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


# ── Presets ─────────────────────────────────────────────────────────────

_PRESETS: dict[str, dict[str, Any]] = {
    "minimal": {
        "sections": ["model", "tokens"],
        "width_ratio": [1, 1],
    },
    "compact": {
        "sections": ["model", "tokens", "agents"],
        "width_ratio": [1, 1, 1],
    },
    "full": {
        "sections": ["model", "tokens", "agents", "tasks", "resources", "keys"],
        "width_ratio": [1, 1, 1, 1, 1, 1],
    },
    "wide": {
        "sections": ["model", "tokens", "agents", "tasks"],
        "width_ratio": [1, 1, 2, 2],
    },
}


@dataclass
class HudConfig:
    """Configuration for one HUD layout."""
    sections: list[str] = field(default_factory=lambda: list(_PRESETS["compact"]["sections"]))
    width_ratio: list[int] = field(default_factory=lambda: list(_PRESETS["compact"]["width_ratio"]))
    title: str = "Lyra HUD"


@dataclass
class HudState:
    """Point-in-time state snapshot for the HUD renderer."""
    model: str = ""
    provider: str = ""
    mode: str = ""
    tokens_used: int = 0
    tokens_max: int = 200_000
    turn: int = 0
    agent_count: int = 0
    agent_running: int = 0
    duration_s: float = 0.0
    cost_usd: float = 0.0
    tasks: list[dict] = field(default_factory=list)
    memory_mb: float = 0.0
    compaction_count: int = 0
    bg_tasks: int = 0


# ── Public API ──────────────────────────────────────────────────────────

def available_presets() -> list[str]:
    return list(_PRESETS.keys())


def load_preset(name: str) -> HudConfig:
    if name not in _PRESETS:
        raise ValueError(f"Unknown preset '{name}'. Available: {', '.join(available_presets())}")
    data = _PRESETS[name]
    return HudConfig(
        sections=list(data["sections"]),
        width_ratio=list(data["width_ratio"]),
        title=f"Lyra HUD ({name})",
    )


def render(
    state: HudState,
    config: Optional[HudConfig] = None,
    max_width: int = 120,
) -> str:
    """Render the HUD as a Rich-markup string.

    Args:
        state: Current session state snapshot.
        config: Layout configuration. Defaults to "compact".
        max_width: Column cap for each panel.

    Returns:
        Rich-markup string suitable for ``/hud`` or ``console.print``.
    """
    if config is None:
        config = load_preset("compact")

    panels: list[Panel] = []
    builders = {
        "model": _build_model_panel,
        "tokens": _build_tokens_panel,
        "agents": _build_agents_panel,
        "tasks": _build_tasks_panel,
        "resources": _build_resources_panel,
        "keys": _build_keys_panel,
    }

    for section in config.sections:
        builder = builders.get(section)
        if builder:
            panel = builder(state, max_width)
            panels.append(panel)

    if not panels:
        return "[dim](no HUD sections configured)[/]"

    # Render into a single group
    rendered = Group(*panels)
    # Use Console to capture to string
    console = Console(width=max_width, force_terminal=True)
    with console.capture() as capture:
        console.print(rendered)
    return capture.get()


def render_inline(state: HudState, max_width: int = 80) -> str:
    """Render a single-line HUD for the REPL status bar.

    Compact format::
        ◆ deepseek-chat · ☰ 45% (12K/200K) · ⏺ 2 agents · T#5
    """
    tok_pct = (state.tokens_used / state.tokens_max * 100) if state.tokens_max > 0 else 0
    tok_color = "green" if tok_pct < 50 else ("yellow" if tok_pct < 80 else "red")
    dur = _fmt_dur(state.duration_s)
    cost = f" ${state.cost_usd:.4f}" if state.cost_usd > 0 else ""

    parts = [
        f"◆ {state.model}",
        f"[{tok_color}]☰ {tok_pct:.0f}% ({_human_tok(state.tokens_used)}/{_human_tok(state.tokens_max)})[/]",
    ]
    if state.agent_running > 0:
        parts.append(f"⏺ {state.agent_running} agents")
    parts.append(f"T#{state.turn}")
    if state.duration_s > 60:
        parts.append(dur)
    if cost:
        parts.append(cost)

    return " · ".join(parts)


# ── Panel builders ──────────────────────────────────────────────────────

def _build_model_panel(state: HudState, max_width: int) -> Panel:
    t = Table.grid(padding=(0, 1))
    t.add_row("[bold]Model[/]", state.model or "—")
    t.add_row("[dim]Provider[/]", state.provider or "—")
    t.add_row("[dim]Mode[/]", state.mode or "—")
    t.add_row("[dim]Turn[/]", f"#{state.turn}")
    return Panel(t, title="◆ Model", border_style="cyan", width=min(30, max_width))


def _build_tokens_panel(state: HudState, max_width: int) -> Panel:
    pct = (state.tokens_used / state.tokens_max * 100) if state.tokens_max > 0 else 0
    bar_w = 14
    f = int(pct / 100 * bar_w)
    bar = "█" * f + "░" * (bar_w - f)

    color = "green" if pct < 50 else ("yellow" if pct < 80 else ("orange1" if pct < 95 else "red"))
    tok_pct_str = f"[{color}]{bar}[/]  [{color}]{pct:.1f}%[/]"

    t = Table.grid(padding=(0, 1))
    t.add_row(tok_pct_str)
    t.add_row(f"[dim]Used:[/] {_human_tok(state.tokens_used)}")
    t.add_row(f"[dim]Max:[/]  {_human_tok(state.tokens_max)}")
    if state.compaction_count:
        t.add_row(f"[dim]Compactions:[/] {state.compaction_count}")
    return Panel(t, title="☰ Tokens", border_style="green", width=min(28, max_width))


def _build_agents_panel(state: HudState, max_width: int) -> Panel:
    t = Table.grid(padding=(0, 1))
    t.add_row("[bold]Active[/]", f"[cyan]{state.agent_running}[/] / {state.agent_count}")
    t.add_row("[dim]Background[/]", str(state.bg_tasks))
    return Panel(t, title="⏺ Agents", border_style="yellow", width=min(24, max_width))


def _build_tasks_panel(state: HudState, max_width: int) -> Panel:
    t = Table.grid(padding=(0, 1))
    if state.tasks:
        for task in state.tasks[:5]:
            label = task.get("label", "?")[:30]
            status = task.get("status", "pending")
            glyph = {"pending": "◻", "running": "◼", "done": "✓"}.get(status, "◻")
            color = {"pending": "dim", "running": "yellow", "done": "green"}.get(status, "dim")
            t.add_row(f"[{color}]{glyph}[/] {label}")
        if len(state.tasks) > 5:
            t.add_row(f"[dim]… +{len(state.tasks) - 5} more[/]")
    else:
        t.add_row("[dim](no tasks)[/]")
    return Panel(t, title="📋 Tasks", border_style="blue", width=min(36, max_width))


def _build_resources_panel(state: HudState, max_width: int) -> Panel:
    t = Table.grid(padding=(0, 1))
    t.add_row("[dim]Memory[/]", f"{state.memory_mb:.0f} MB" if state.memory_mb else "—")
    t.add_row("[dim]Duration[/]", _fmt_dur(state.duration_s))
    if state.cost_usd:
        t.add_row("[dim]Cost[/]", f"${state.cost_usd:.4f}")
    return Panel(t, title="⚙ Resources", border_style="magenta", width=min(24, max_width))


def _build_keys_panel(state: HudState, max_width: int) -> Panel:
    keys = [
        ("Ctrl+K", "Palette"),
        ("Ctrl+R", "Sessions"),
        ("Ctrl+N", "Notifications"),
        ("Ctrl+D", "Dashboard"),
        ("Ctrl+V", "Context"),
        ("/workflow", "Tasks"),
    ]
    t = Table.grid(padding=(0, 1))
    for key, action in keys:
        t.add_row(f"[accent]{key:<9}[/]", f"[dim]{action}[/]")
    return Panel(t, title="⌨ Keys", border_style="dim", width=min(26, max_width))


# ── Helpers ─────────────────────────────────────────────────────────────

def _human_tok(n: int) -> str:
    if n < 1_000:
        return str(n)
    if n < 1_000_000:
        return f"{n / 1_000:.1f}K"
    return f"{n / 1_000_000:.1f}M"


def _fmt_dur(secs: float) -> str:
    if secs < 60:
        return f"{secs:.0f}s"
    m, s = divmod(int(secs), 60)
    if m < 60:
        return f"{m}m {s:02d}s"
    h, m = divmod(m, 60)
    return f"{h}h {m:02d}m"


__all__ = [
    "HudConfig", "HudState", "render", "render_inline",
    "load_preset", "available_presets",
]
