"""Rich renderers for interactive command results.

Every slash handler in :mod:`.session` returns a plain-text ``output``
(so tests stay string-based) *and* optionally a Rich renderable that
the driver prefers when a real TTY is attached. This module is the
renderable factory.

Design rules:

- Never import this module from :mod:`.session` eagerly; it's imported
  at the top of session so handlers can reference it, but tests that
  only touch plain-text paths don't have to care because we never
  actually render here during tests.
- Every builder takes only primitives (strings, dicts, paths), never
  the :class:`InteractiveSession` instance. This keeps the renderers
  reusable for ``/export`` and future static dumps.
- Colour vocabulary mirrors the banner's gradient:
    * cyan   ``#00E5FF``  — headings, keys, neutral emphasis
    * indigo ``#7C4DFF``  — dividers, secondary info
    * pink   ``#FF2D95``  — mode labels, "danger" accents
    * green  ``#7CFFB2``  — models, success checks
    * amber  ``#FFC857``  — warnings / needs-attention
    * red    ``#FF5370``  — errors, missing files, rejections
  Keep this vocabulary; deviating makes the UI feel noisy.
"""
from __future__ import annotations

from pathlib import Path

from rich.box import ROUNDED, SIMPLE
from rich.console import Group
from rich.padding import Padding
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


# Colour tokens — keep in sync with banner.py.
C_CYAN = "#00E5FF"
C_INDIGO = "#7C4DFF"
C_PINK = "#FF2D95"
C_GREEN = "#7CFFB2"
C_AMBER = "#FFC857"
C_RED = "#FF5370"
C_DIM = "#6B7280"


# ---------------------------------------------------------------------------
# /help — grouped command table
# ---------------------------------------------------------------------------


def help_renderable(
    groups: list[tuple[str, list[tuple[str, str]]]],
    footer: str,
) -> Group:
    """Render ``/help`` as a set of category-grouped tables.

    ``groups`` is a list of ``(heading, [(name, description), ...])``
    pairs. Command names are shown as ``/<name>`` in cyan-bold; the
    description column dims. A single footer line (how plain text
    routes) hangs below all groups.
    """
    tables: list[Table] = []
    for heading, rows in groups:
        if not rows:
            continue
        t = Table(
            box=SIMPLE,
            show_header=False,
            show_edge=False,
            pad_edge=False,
            padding=(0, 2),
            title=Text(heading, style=f"bold {C_INDIGO}"),
            title_justify="left",
            title_style="",
        )
        t.add_column(style=f"bold {C_CYAN}", no_wrap=True, width=14)
        t.add_column(style=C_DIM)
        for name, desc in rows:
            t.add_row(f"/{name}", desc)
        tables.append(t)

    total = sum(len(rows) for _, rows in groups)
    body = Panel(
        Group(*tables),
        box=ROUNDED,
        border_style=C_INDIGO,
        padding=(1, 2),
        title=f"[bold {C_CYAN}]Commands[/]",
        title_align="left",
        subtitle=f"[dim]{total} available[/]",
        subtitle_align="right",
    )

    foot = Padding(Text(footer, style=f"italic {C_DIM}"), (0, 2))
    return Group(body, foot)


# ---------------------------------------------------------------------------
# /status — two-column metadata panel
# ---------------------------------------------------------------------------


def status_renderable(
    *,
    mode: str,
    model: str,
    repo: Path,
    turn: int,
    cost_usd: float,
    tokens: int,
    pending: str | None,
    version: str,
    deep_think: bool = False,
    verbose: bool = False,
    vim_mode: bool = False,
    theme: str = "aurora",
    budget_cap_usd: float | None = None,
) -> Panel:
    """Session status shown as a rounded key/value panel."""
    t = Table(
        box=None,
        show_header=False,
        pad_edge=False,
        padding=(0, 2),
        expand=False,
    )
    t.add_column(style=C_DIM, no_wrap=True, width=11, justify="right")
    t.add_column()

    t.add_row("mode", _mode_badge(mode))
    t.add_row("model", Text(model, style=f"bold {C_GREEN}"))
    t.add_row("repo", Text(str(repo), style="bright_white"))
    t.add_row("turn", Text(str(turn), style=f"bold {C_CYAN}"))
    t.add_row("cost", Text(f"${cost_usd:.4f}", style="bright_white"))
    t.add_row("tokens", Text(f"{tokens:,}", style="bright_white"))
    pending_txt = (
        Text(pending, style=f"italic {C_AMBER}")
        if pending
        else Text("(none)", style=f"{C_DIM}")
    )
    t.add_row("pending", pending_txt)
    t.add_row("version", Text(f"v{version}", style=C_DIM))
    t.add_row(
        "deep-think",
        _on_off(deep_think, on_colour=C_PINK),
    )
    t.add_row("verbose", _on_off(verbose))
    t.add_row("vim", _on_off(vim_mode))
    t.add_row("theme", Text(theme, style=f"bold {C_INDIGO}"))
    t.add_row(
        "budget",
        Text(
            f"${budget_cap_usd:.2f}" if budget_cap_usd is not None else "(none)",
            style=C_AMBER if budget_cap_usd is not None else C_DIM,
        ),
    )

    return Panel(
        t,
        box=ROUNDED,
        border_style=C_CYAN,
        padding=(1, 2),
        title=f"[bold {C_CYAN}]session status[/]",
        title_align="left",
    )


# ---------------------------------------------------------------------------
# /doctor — health checks with ✓ / ✗
# ---------------------------------------------------------------------------


def doctor_renderable(checks: list[tuple[str, bool, str]]) -> Panel:
    """Render a list of ``(label, ok, hint)`` tuples as a health panel.

    ``ok=True`` → green check; ``ok=False`` → red cross + amber hint.
    """
    t = Table(
        box=None,
        show_header=False,
        pad_edge=False,
        padding=(0, 2),
        expand=False,
    )
    t.add_column(width=2)
    t.add_column(no_wrap=True, width=16)
    t.add_column(style=C_DIM)

    for label, ok, hint in checks:
        glyph = Text("✓", style=f"bold {C_GREEN}") if ok else Text(
            "✗", style=f"bold {C_RED}"
        )
        label_style = C_GREEN if ok else C_RED
        t.add_row(glyph, Text(label, style=f"bold {label_style}"), hint)

    return Panel(
        t,
        box=ROUNDED,
        border_style=C_INDIGO,
        padding=(1, 2),
        title=f"[bold {C_CYAN}]doctor[/]",
        title_align="left",
        subtitle=f"[dim]{sum(ok for _, ok, _ in checks)}/{len(checks)} ok[/]",
        subtitle_align="right",
    )


# ---------------------------------------------------------------------------
# /history — numbered recent inputs
# ---------------------------------------------------------------------------


def history_renderable(entries: list[str]) -> Panel:
    """Numbered history table; dim when empty."""
    if not entries:
        body: Text | Table = Text("(no history yet)", style=f"italic {C_DIM}")
    else:
        body = Table(
            box=None,
            show_header=False,
            pad_edge=False,
            padding=(0, 2),
        )
        body.add_column(style=f"{C_DIM}", no_wrap=True, width=4, justify="right")
        body.add_column()
        for i, entry in enumerate(entries, 1):
            body.add_row(str(i), Text(entry, style="bright_white"))

    return Panel(
        body,
        box=ROUNDED,
        border_style=C_INDIGO,
        padding=(1, 2),
        title=f"[bold {C_CYAN}]history[/]",
        title_align="left",
        subtitle=f"[dim]{len(entries)} turn{'s' if len(entries) != 1 else ''}[/]",
        subtitle_align="right",
    )


def verbose_history_renderable(turns: list[dict]) -> Panel:
    """Per-turn history table for ``/history --verbose`` (Phase L).

    ``turns`` is a list of dicts (one per recorded ``_TurnSnapshot``):

        {
          "n": int,                 # 1-indexed turn counter
          "kind": "turn" | "chat",  # source row
          "mode": str | None,
          "model": str | None,
          "tokens_in": int | None,
          "tokens_out": int | None,
          "cost_delta_usd": float | None,
          "latency_ms": float | None,
          "ts": str | None,         # already-formatted ``HH:MM:SS``
          "preview": str,           # short input/line preview
        }

    All fields except ``n`` and ``preview`` are optional and render as
    ``"—"`` when missing — sessions written by older builds keep
    rendering cleanly even after the schema growth in v3.2.
    """
    if not turns:
        body: Text | Table = Text("(no history yet)", style=f"italic {C_DIM}")
    else:
        body = Table(
            box=None,
            show_header=True,
            header_style=f"{C_DIM}",
            pad_edge=False,
            padding=(0, 1),
        )
        body.add_column("#", style=C_DIM, no_wrap=True, justify="right", width=4)
        body.add_column("kind", style=C_AMBER, no_wrap=True)
        body.add_column("mode", style=C_PINK, no_wrap=True)
        body.add_column("model", style=C_GREEN, no_wrap=True)
        body.add_column("tok in", style=C_DIM, no_wrap=True, justify="right")
        body.add_column("tok out", style=C_DIM, no_wrap=True, justify="right")
        body.add_column("cost Δ", style=C_DIM, no_wrap=True, justify="right")
        body.add_column("ms", style=C_DIM, no_wrap=True, justify="right")
        body.add_column("ts", style=C_DIM, no_wrap=True)
        body.add_column("preview")
        for t in turns:
            tin = t.get("tokens_in")
            tout = t.get("tokens_out")
            cdelta = t.get("cost_delta_usd")
            ms = t.get("latency_ms")
            preview = (t.get("preview") or "").splitlines()[0][:80]
            body.add_row(
                str(t.get("n", "")),
                str(t.get("kind") or "turn"),
                str(t.get("mode") or "—"),
                str(t.get("model") or "—"),
                f"{tin:,}" if isinstance(tin, (int, float)) else "—",
                f"{tout:,}" if isinstance(tout, (int, float)) else "—",
                f"${cdelta:.6f}" if isinstance(cdelta, (int, float)) else "—",
                f"{ms:.0f}" if isinstance(ms, (int, float)) else "—",
                str(t.get("ts") or "—"),
                Text(preview, style="bright_white"),
            )

    return Panel(
        body,
        box=ROUNDED,
        border_style=C_INDIGO,
        padding=(1, 2),
        title=f"[bold {C_CYAN}]history[/] [dim]· verbose[/]",
        title_align="left",
        subtitle=f"[dim]{len(turns)} turn{'s' if len(turns) != 1 else ''}[/]",
        subtitle_align="right",
    )


# ---------------------------------------------------------------------------
# /skills — packs list with short description
# ---------------------------------------------------------------------------


def skills_renderable(
    packs: list[tuple[str, str]], footer: str
) -> Group:
    """``packs`` is ``[(pack_name, one_line_desc), ...]``."""
    t = Table(
        box=None,
        show_header=False,
        pad_edge=False,
        padding=(0, 2),
    )
    t.add_column(style=f"bold {C_PINK}", no_wrap=True, width=16)
    t.add_column(style=C_DIM)
    for name, desc in packs:
        t.add_row(name, desc)

    panel = Panel(
        t,
        box=ROUNDED,
        border_style=C_INDIGO,
        padding=(1, 2),
        title=f"[bold {C_CYAN}]skills[/]",
        title_align="left",
        subtitle=f"[dim]{len(packs)} packs installed[/]",
        subtitle_align="right",
    )
    return Group(panel, Padding(Text(footer, style=f"italic {C_DIM}"), (0, 2)))


# ---------------------------------------------------------------------------
# Plain-text mode responses (plan / build / run / explore / retro / approve / reject)
# ---------------------------------------------------------------------------


def plan_renderable(task: str) -> Panel:
    body = Group(
        Text.assemble(
            (" ▸ recorded task  ", f"bold {C_CYAN}"),
            (task, "bright_white"),
        ),
        Text.assemble(
            (" ▸ next  ", f"bold {C_CYAN}"),
            ("review with ", C_DIM),
            ("/status", f"bold {C_CYAN}"),
            (", then ", C_DIM),
            ("/approve", f"bold {C_GREEN}"),
            (" or ", C_DIM),
            ("/reject", f"bold {C_RED}"),
            (".", C_DIM),
        ),
    )
    return Panel(
        body,
        box=ROUNDED,
        border_style=C_CYAN,
        padding=(1, 2),
        title=f"[bold {C_CYAN}]plan[/]",
        title_align="left",
    )


def build_renderable(task: str) -> Panel:
    body = Group(
        Text.assemble(
            (" ▸ would implement  ", f"bold {C_AMBER}"),
            (task, "bright_white"),
        ),
        Text(
            " ▸ build mode allows writes + shell under policy; "
            "real dispatch lands with Phase 14 CodeAct.",
            style=f"italic {C_DIM}",
        ),
    )
    return Panel(
        body,
        box=ROUNDED,
        border_style=C_AMBER,
        padding=(1, 2),
        title=f"[bold {C_AMBER}]build[/]",
        title_align="left",
    )


def run_renderable(task: str) -> Panel:
    body = Group(
        Text.assemble(
            (" ▸ would execute  ", f"bold {C_PINK}"),
            (task, "bright_white"),
        ),
        Text(
            " ▸ real LLM dispatch lands with the Phase 14 CodeAct plugin",
            style=f"italic {C_DIM}",
        ),
    )
    return Panel(
        body,
        box=ROUNDED,
        border_style=C_PINK,
        padding=(1, 2),
        title=f"[bold {C_PINK}]run[/]",
        title_align="left",
    )


def explore_renderable(task: str) -> Panel:
    body = Group(
        Text.assemble(
            (" ▸ would search  ", f"bold {C_CYAN}"),
            (task, "bright_white"),
        ),
        Text(
            " ▸ read-only explorer subagent; lands with Phase 7 worktrees.",
            style=f"italic {C_DIM}",
        ),
    )
    return Panel(
        body,
        box=ROUNDED,
        border_style=C_CYAN,
        padding=(1, 2),
        title=f"[bold {C_CYAN}]explore[/]",
        title_align="left",
    )


def chat_renderable(reply: str, *, mode: str = "agent") -> Panel:
    """Panel for an actual LLM reply in agent/plan/debug/ask modes.

    Coloured by mode so the user knows which side-effect surface they're
    on while still seeing real model output. ``reply`` is rendered as
    plain-text via Rich's :class:`~rich.text.Text` to defang any Rich
    markup the model might accidentally emit.

    v3.2.0 mode → colour:
      * ``agent``  — amber (the working / execution mode)
      * ``plan``   — cyan  (read-only design)
      * ``debug``  — pink  (troubleshooting; eye-catching)
      * ``ask``    — cyan  (read-only Q&A; same family as plan)

    Legacy v1.x / v2.x mode names (``build``, ``run``, ``explore``,
    ``retro``) still resolve to their pre-v3.2 colours so embedders
    that pass them through don't suddenly render in the fallback hue.
    """
    color = {
        "agent": C_AMBER,
        "plan": C_CYAN,
        "debug": C_PINK,
        "ask": C_CYAN,
        # Legacy fall-throughs — keep until v4 in case third-party
        # embedders or saved transcripts still refer to the old
        # taxonomy. The session itself has already been remapped.
        "build": C_AMBER,
        "run": C_PINK,
        "explore": C_CYAN,
        "retro": C_PINK,
    }.get(mode, C_AMBER)

    return Panel(
        Text(reply, style="bright_white"),
        box=ROUNDED,
        border_style=color,
        padding=(1, 2),
        title=f"[bold {color}]{mode}[/]",
        title_align="left",
    )


def chat_error_renderable(detail: str, *, mode: str = "agent") -> Panel:
    """Panel for an LLM call that failed (network, missing key, etc.)."""
    body = Group(
        Text.assemble((" ✗ ", f"bold {C_RED}"), (detail, "bright_white")),
        Text(
            " ▸ run [cyan]lyra connect <provider> --key ...[/cyan] "
            "to (re)configure, or set the provider's env var.",
            style=f"italic {C_DIM}",
        ),
    )
    return Panel(
        body,
        box=ROUNDED,
        border_style=C_RED,
        padding=(1, 2),
        title=f"[bold {C_RED}]{mode} · llm error[/]",
        title_align="left",
    )


def retro_renderable(note: str) -> Panel:
    body = Text.assemble(
        (" ▸ note logged  ", f"bold {C_INDIGO}"),
        (note, "bright_white"),
    )
    return Panel(
        body,
        box=ROUNDED,
        border_style=C_INDIGO,
        padding=(1, 2),
        title=f"[bold {C_INDIGO}]retro[/]",
        title_align="left",
    )


def approve_renderable(task: str) -> Panel:
    body = Group(
        Text.assemble(
            (" ✓ approved  ", f"bold {C_GREEN}"),
            (task, "bright_white"),
        ),
        Text(" ▸ switching to run mode.", style=f"italic {C_DIM}"),
    )
    return Panel(
        body,
        box=ROUNDED,
        border_style=C_GREEN,
        padding=(1, 2),
        title=f"[bold {C_GREEN}]approved[/]",
        title_align="left",
    )


def reject_renderable(task: str | None) -> Panel:
    if task is None:
        body = Text(" nothing to reject.", style=f"italic {C_DIM}")
    else:
        body = Text.assemble(
            (" ✗ dropped pending plan  ", f"bold {C_RED}"),
            (task, "bright_white"),
        )
    return Panel(
        body,
        box=ROUNDED,
        border_style=C_RED,
        padding=(1, 2),
        title=f"[bold {C_RED}]reject[/]",
        title_align="left",
    )


def bad_command_renderable(name: str) -> Panel:
    body = Text.assemble(
        (" unknown command  ", f"bold {C_RED}"),
        (f"/{name}", f"bold {C_CYAN}"),
        ("   ·   type ", C_DIM),
        ("/help", f"bold {C_CYAN}"),
        (" for the full list.", C_DIM),
    )
    return Panel(
        body,
        box=ROUNDED,
        border_style=C_RED,
        padding=(0, 2),
    )


def bad_mode_renderable(target: str, valid: tuple[str, ...]) -> Panel:
    body = Text.assemble(
        (" unknown mode  ", f"bold {C_RED}"),
        (target, f"bold {C_AMBER}"),
        ("   ·   valid: ", C_DIM),
        (", ".join(valid), f"bold {C_CYAN}"),
    )
    return Panel(body, box=ROUNDED, border_style=C_RED, padding=(0, 2))


def missing_file_renderable(kind: str, path: Path, hint: str) -> Panel:
    body = Group(
        Text.assemble(
            (" ✗ missing  ", f"bold {C_RED}"),
            (kind, f"bold {C_CYAN}"),
        ),
        Text.assemble(
            (" ▸ path  ", C_DIM),
            (str(path), "bright_white"),
        ),
        Text.assemble((" ▸ hint  ", C_DIM), (hint, C_AMBER)),
    )
    return Panel(
        body,
        box=ROUNDED,
        border_style=C_RED,
        padding=(1, 2),
        title=f"[bold {C_RED}]missing[/]",
        title_align="left",
    )


def file_contents_renderable(kind: str, path: Path, text: str) -> Panel:
    return Panel(
        Text(text, style="bright_white"),
        box=ROUNDED,
        border_style=C_INDIGO,
        padding=(1, 2),
        title=f"[bold {C_CYAN}]{kind}[/]  [dim]{path}[/]",
        title_align="left",
    )


# ---------------------------------------------------------------------------
# New command renderables (Claude Code / opencode / hermes parity)
# ---------------------------------------------------------------------------


def models_renderable(
    catalog: list[tuple[str, list[tuple[str, str]]]],
) -> Panel:
    t = Table(
        box=SIMPLE,
        show_header=False,
        pad_edge=False,
        padding=(0, 2),
    )
    t.add_column(style=f"bold {C_INDIGO}", no_wrap=True, width=11)
    t.add_column(style=f"bold {C_CYAN}", no_wrap=True, width=24)
    t.add_column(style=C_DIM)
    total = 0
    for provider, rows in catalog:
        for name, desc in rows:
            total += 1
            t.add_row(provider, name, desc)
    return Panel(
        t,
        box=ROUNDED,
        border_style=C_INDIGO,
        padding=(1, 2),
        title=f"[bold {C_CYAN}]models[/]",
        title_align="left",
        subtitle=f"[dim]{total} entries · /model <name> to switch[/]",
        subtitle_align="right",
    )


def compact_renderable(*, before: int, after: int) -> Panel:
    saved = max(before - after, 0)
    pct = (saved / before * 100) if before else 0
    body = Group(
        Text.assemble(
            (" ▸ tokens  ", f"bold {C_CYAN}"),
            (f"{before:,}", "bright_white"),
            ("  →  ", C_DIM),
            (f"{after:,}", f"bold {C_GREEN}"),
            (f"   ({pct:.0f}% saved)", C_DIM),
        ),
        Text(
            " ▸ real NGC-style compactor lands in v1.7 Phase 23.",
            style=f"italic {C_DIM}",
        ),
    )
    return Panel(
        body,
        box=ROUNDED,
        border_style=C_GREEN,
        padding=(1, 2),
        title=f"[bold {C_GREEN}]compact[/]",
        title_align="left",
    )


def context_renderable(
    *, buckets: list[tuple[str, int]], budget: int
) -> Panel:
    t = Table(
        box=None,
        show_header=False,
        pad_edge=False,
        padding=(0, 2),
    )
    t.add_column(style=C_DIM, no_wrap=True, width=14)
    t.add_column(style="bright_white", no_wrap=True, width=8, justify="right")
    t.add_column(style=f"{C_INDIGO}")
    for label, tok in buckets:
        width = max(int(tok * 24 / budget), 1 if tok else 0)
        bar = "█" * width
        t.add_row(label, f"{tok:,}", bar)
    t.add_row(
        Text("budget", style=f"bold {C_AMBER}"),
        Text(f"{budget:,}", style=f"bold {C_AMBER}"),
        "",
    )
    return Panel(
        t,
        box=ROUNDED,
        border_style=C_INDIGO,
        padding=(1, 2),
        title=f"[bold {C_CYAN}]context[/]",
        title_align="left",
        subtitle=f"[dim]usage vs {budget:,}-token window[/]",
        subtitle_align="right",
    )


def cost_renderable(
    *,
    cost_usd: float,
    tokens: int,
    turns: int,
    budget_cap_usd: float | None,
) -> Panel:
    t = Table(
        box=None,
        show_header=False,
        pad_edge=False,
        padding=(0, 2),
    )
    t.add_column(style=C_DIM, no_wrap=True, width=10, justify="right")
    t.add_column()
    t.add_row("cost", Text(f"${cost_usd:.4f}", style=f"bold {C_GREEN}"))
    t.add_row("tokens", Text(f"{tokens:,}", style="bright_white"))
    t.add_row("turns", Text(str(turns), style=f"bold {C_CYAN}"))
    if budget_cap_usd is not None:
        pct = cost_usd / budget_cap_usd * 100 if budget_cap_usd else 0
        colour = (
            C_GREEN if pct < 60 else C_AMBER if pct < 90 else C_RED
        )
        t.add_row(
            "budget",
            Text(f"${budget_cap_usd:.2f}", style=f"bold {C_AMBER}"),
        )
        t.add_row(
            "used",
            Text(f"{pct:.1f}%", style=f"bold {colour}"),
        )
    return Panel(
        t,
        box=ROUNDED,
        border_style=C_GREEN,
        padding=(1, 2),
        title=f"[bold {C_GREEN}]cost[/]",
        title_align="left",
    )


def stats_renderable(
    *,
    turns: int,
    slash: int,
    bash: int,
    files: int,
    cost_usd: float,
    tokens: int,
    mode: str,
    deep_think: bool,
) -> Panel:
    t = Table(
        box=None,
        show_header=False,
        pad_edge=False,
        padding=(0, 2),
    )
    t.add_column(style=C_DIM, no_wrap=True, width=14, justify="right")
    t.add_column()
    t.add_row("turns", Text(str(turns), style=f"bold {C_CYAN}"))
    t.add_row("/slash", Text(str(slash), style=f"bold {C_INDIGO}"))
    t.add_row("!bash", Text(str(bash), style=f"bold {C_PINK}"))
    t.add_row("@files", Text(str(files), style=f"bold {C_GREEN}"))
    t.add_row("cost", Text(f"${cost_usd:.4f}", style="bright_white"))
    t.add_row("tokens", Text(f"{tokens:,}", style="bright_white"))
    t.add_row("mode", _mode_badge(mode))
    t.add_row("deep-think", _on_off(deep_think, on_colour=C_PINK))
    return Panel(
        t,
        box=ROUNDED,
        border_style=C_CYAN,
        padding=(1, 2),
        title=f"[bold {C_CYAN}]stats[/]",
        title_align="left",
    )


def diff_renderable() -> Panel:
    body = Group(
        Text.assemble(
            (" ▸ tip  ", f"bold {C_CYAN}"),
            ("run ", C_DIM),
            ("!git diff --stat", f"bold {C_PINK}"),
            (" or ", C_DIM),
            ("!git diff", f"bold {C_PINK}"),
            (".", C_DIM),
        ),
        Text(
            " ▸ v1.5 upgrade: hunk-level annotations + inline TDD coverage.",
            style=f"italic {C_DIM}",
        ),
    )
    return Panel(
        body,
        box=ROUNDED,
        border_style=C_INDIGO,
        padding=(1, 2),
        title=f"[bold {C_INDIGO}]diff[/]",
        title_align="left",
    )


def rewind_renderable(snapshot: object | None) -> Panel:
    if snapshot is None:
        body = Text(" nothing to rewind.", style=f"italic {C_DIM}")
        return Panel(
            body,
            box=ROUNDED,
            border_style=C_DIM,
            padding=(0, 2),
            title=f"[bold {C_DIM}]rewind[/]",
            title_align="left",
        )
    # snapshot is a _TurnSnapshot but typed loosely here to avoid a
    # circular import at type-check time.
    line = getattr(snapshot, "line", "")
    mode = getattr(snapshot, "mode", "")
    turn = getattr(snapshot, "turn", 0)
    body = Group(
        Text.assemble(
            (" ↶ rewound turn  ", f"bold {C_AMBER}"),
            (str(turn + 1), "bright_white"),
            ("   restored mode  ", C_DIM),
            (mode, f"bold {C_CYAN}"),
        ),
        Text.assemble(
            (" ▸ line  ", C_DIM),
            (line, "bright_white"),
        ),
    )
    return Panel(
        body,
        box=ROUNDED,
        border_style=C_AMBER,
        padding=(1, 2),
        title=f"[bold {C_AMBER}]rewind[/]",
        title_align="left",
    )


def resume_renderable(repo_root: Path) -> Panel:
    folder = repo_root / ".lyra" / "sessions"
    body = Group(
        Text.assemble(
            (" ▸ resume queued  ", f"bold {C_CYAN}"),
        ),
        Text.assemble(
            (" ▸ sessions dir  ", C_DIM),
            (str(folder), "bright_white"),
        ),
        Text(
            " ▸ run /sessions to pick a different snapshot.",
            style=f"italic {C_DIM}",
        ),
    )
    return Panel(
        body,
        box=ROUNDED,
        border_style=C_CYAN,
        padding=(1, 2),
        title=f"[bold {C_CYAN}]resume[/]",
        title_align="left",
    )


def fork_renderable(*, name: str, turn: int) -> Panel:
    body = Group(
        Text.assemble(
            (" ⑂ fork saved  ", f"bold {C_GREEN}"),
            (name, "bright_white"),
        ),
        Text.assemble(
            (" ▸ branched at turn  ", C_DIM),
            (str(turn), f"bold {C_CYAN}"),
        ),
        Text.assemble(
            (" ▸ switch with  ", C_DIM),
            (f"/resume {name}", f"bold {C_PINK}"),
        ),
    )
    return Panel(
        body,
        box=ROUNDED,
        border_style=C_GREEN,
        padding=(1, 2),
        title=f"[bold {C_GREEN}]fork[/]",
        title_align="left",
    )


def sessions_renderable(folder: Path) -> Panel:
    body = Group(
        Text.assemble(
            (" ▸ sessions dir  ", C_DIM),
            (str(folder), "bright_white"),
        ),
        Text(
            " ▸ the driver lists snapshots; use /resume <id> to restore.",
            style=f"italic {C_DIM}",
        ),
    )
    return Panel(
        body,
        box=ROUNDED,
        border_style=C_INDIGO,
        padding=(1, 2),
        title=f"[bold {C_CYAN}]sessions[/]",
        title_align="left",
    )


def rename_renderable(name: str) -> Panel:
    body = Text.assemble(
        (" ✎ renamed to  ", f"bold {C_CYAN}"),
        (name, "bright_white"),
    )
    return Panel(body, box=ROUNDED, border_style=C_CYAN, padding=(0, 2))


def export_renderable(*, path: Path, turns: int) -> Panel:
    body = Group(
        Text.assemble(
            (" ▸ transcript  ", f"bold {C_CYAN}"),
            (str(path), "bright_white"),
        ),
        Text.assemble(
            (" ▸ turns  ", C_DIM),
            (str(turns), f"bold {C_CYAN}"),
        ),
    )
    return Panel(
        body,
        box=ROUNDED,
        border_style=C_CYAN,
        padding=(1, 2),
        title=f"[bold {C_CYAN}]export[/]",
        title_align="left",
    )


def theme_list_renderable(
    *, current: str, themes: tuple[str, ...]
) -> Panel:
    t = Table(
        box=None,
        show_header=False,
        pad_edge=False,
        padding=(0, 2),
    )
    t.add_column(width=2)
    t.add_column(no_wrap=True, width=12)
    t.add_column(style=C_DIM)
    for theme in themes:
        glyph = Text("●" if theme == current else "○",
                     style=f"bold {C_CYAN}" if theme == current else C_DIM)
        t.add_row(glyph, Text(theme, style=f"bold {C_CYAN}"), "active" if theme == current else "")
    return Panel(
        t,
        box=ROUNDED,
        border_style=C_INDIGO,
        padding=(1, 2),
        title=f"[bold {C_CYAN}]themes[/]",
        title_align="left",
        subtitle=f"[dim]active: {current}[/]",
        subtitle_align="right",
    )


def theme_set_renderable(name: str) -> Panel:
    """Live skin-preview panel.

    Pulls the actual :class:`~lyra_cli.interactive.themes.Skin`
    that just became active and paints a five-dot swatch in its real
    accent / secondary / danger / success / warning tokens so the user
    immediately *sees* what they're wearing, not just the name. Falls
    back to the legacy single-line panel if the skin is missing or the
    themes module can't be imported (defensive — the import happens
    locally to avoid a cyclic dep).
    """
    try:
        from . import themes as _themes  # local — avoid cyclic dep on import
        skin = _themes.skin(name)
    except Exception:  # pragma: no cover - defensive
        body = Text.assemble(
            (" ▸ skin  ", f"bold {C_CYAN}"),
            (name, "bright_white"),
            ("   applied.", C_DIM),
        )
        return Panel(body, box=ROUNDED, border_style=C_CYAN, padding=(0, 2))

    accent = skin.color("accent", C_CYAN)
    secondary = skin.color("secondary", C_INDIGO)
    danger = skin.color("danger", C_PINK)
    success = skin.color("success", C_GREEN)
    warning = skin.color("warning", C_AMBER)
    border = skin.color("banner_border", accent)
    welcome = skin.brand("welcome", "ready.")
    title = skin.brand("agent_name", "Lyra")

    swatch = Text.assemble(
        (" ● ", f"bold {accent}"),
        ("● ", f"bold {secondary}"),
        ("● ", f"bold {danger}"),
        ("● ", f"bold {success}"),
        ("● ", f"bold {warning}"),
        ("  ", ""),
        (f"now wearing: ", C_DIM),
        (name, f"bold {accent}"),
    )
    welcome_line = Text(welcome, style=f"italic {C_DIM}")
    body = Group(swatch, welcome_line)
    return Panel(
        body,
        box=ROUNDED,
        border_style=border,
        padding=(1, 2),
        title=f"[bold {accent}]{title} · {name}[/]",
        title_align="left",
        subtitle=(
            f"[dim]{skin.description}[/]" if skin.description else None
        ),
        subtitle_align="right",
    )


def bad_theme_renderable(target: str, valid: tuple[str, ...]) -> Panel:
    body = Text.assemble(
        (" unknown theme  ", f"bold {C_RED}"),
        (target, f"bold {C_AMBER}"),
        ("   ·   valid: ", C_DIM),
        (", ".join(valid), f"bold {C_CYAN}"),
    )
    return Panel(body, box=ROUNDED, border_style=C_RED, padding=(0, 2))


def toggle_renderable(name: str, state: bool) -> Panel:
    body = Text.assemble(
        (f" ▸ {name}  ", f"bold {C_CYAN}"),
        _on_off(state, on_colour=C_GREEN),
    )
    return Panel(body, box=ROUNDED, border_style=C_INDIGO, padding=(0, 2))


def keybindings_renderable(rows: list[tuple[str, str]]) -> Panel:
    t = Table(
        box=SIMPLE,
        show_header=False,
        pad_edge=False,
        padding=(0, 2),
    )
    t.add_column(style=f"bold {C_PINK}", no_wrap=True, width=12)
    t.add_column(style=C_DIM)
    for key, desc in rows:
        t.add_row(key, desc)
    return Panel(
        t,
        box=ROUNDED,
        border_style=C_INDIGO,
        padding=(1, 2),
        title=f"[bold {C_CYAN}]key bindings[/]",
        title_align="left",
    )


def tools_renderable(tools: list[dict[str, str]]) -> Panel:
    t = Table(
        box=SIMPLE,
        show_header=True,
        header_style=f"bold {C_INDIGO}",
        pad_edge=False,
        padding=(0, 2),
    )
    t.add_column("tool", style=f"bold {C_CYAN}", no_wrap=True, width=14)
    t.add_column("risk", no_wrap=True, width=8)
    t.add_column("ships", no_wrap=True, width=16, style=C_DIM)
    t.add_column("summary", style=C_DIM)
    for spec in tools:
        risk_colour = {
            "low": C_GREEN,
            "medium": C_AMBER,
            "high": C_RED,
        }.get(spec.get("risk", ""), C_DIM)
        t.add_row(
            spec.get("name", ""),
            Text(spec.get("risk", ""), style=f"bold {risk_colour}"),
            spec.get("planned", ""),
            spec.get("summary", ""),
        )
    return Panel(
        t,
        box=ROUNDED,
        border_style=C_INDIGO,
        padding=(1, 2),
        title=f"[bold {C_CYAN}]tools[/]",
        title_align="left",
        subtitle=f"[dim]{len(tools)} registered[/]",
        subtitle_align="right",
    )


def agents_renderable(
    agents: list[tuple[str, str, str]],
) -> Panel:
    t = Table(
        box=SIMPLE,
        show_header=True,
        header_style=f"bold {C_INDIGO}",
        pad_edge=False,
        padding=(0, 2),
    )
    t.add_column("agent", style=f"bold {C_PINK}", no_wrap=True, width=10)
    t.add_column("model", no_wrap=True, width=10)
    t.add_column("purpose", style=C_DIM)
    for name, model, desc in agents:
        t.add_row(name, Text(model, style=f"bold {C_GREEN}"), desc)
    return Panel(
        t,
        box=ROUNDED,
        border_style=C_PINK,
        padding=(1, 2),
        title=f"[bold {C_PINK}]subagents[/]",
        title_align="left",
        subtitle=f"[dim]{len(agents)} planned · v1.7[/]",
        subtitle_align="right",
    )


def spawn_renderable(task: str) -> Panel:
    body = Group(
        Text.assemble(
            (" ▸ queued  ", f"bold {C_PINK}"),
            (task, "bright_white"),
        ),
        Text(
            " ▸ worktree-isolated subagent orchestrator lands in v1 Phase 7.",
            style=f"italic {C_DIM}",
        ),
    )
    return Panel(
        body,
        box=ROUNDED,
        border_style=C_PINK,
        padding=(1, 2),
        title=f"[bold {C_PINK}]spawn[/]",
        title_align="left",
    )


def mcp_placeholder_renderable() -> Panel:
    body = Group(
        Text(
            " ▸ MCP bridge lands in v1 Phase 10 (block 14).",
            style=f"bold {C_CYAN}",
        ),
        Text(
            "   Planned: connected servers, tool listings, trust status, "
            "injection guard.",
            style=f"italic {C_DIM}",
        ),
    )
    return Panel(
        body,
        box=ROUNDED,
        border_style=C_INDIGO,
        padding=(1, 2),
        title=f"[bold {C_INDIGO}]mcp[/]",
        title_align="left",
    )


def map_renderable(repo: Path) -> Panel:
    body = Group(
        Text.assemble(
            (" ▸ repo  ", f"bold {C_CYAN}"),
            (str(repo), "bright_white"),
        ),
        Text(
            " ▸ v1.5 wires tree-sitter + import analysis for a live graph.",
            style=f"italic {C_DIM}",
        ),
    )
    return Panel(
        body,
        box=ROUNDED,
        border_style=C_INDIGO,
        padding=(1, 2),
        title=f"[bold {C_INDIGO}]map[/]",
        title_align="left",
    )


def blame_renderable(target: str) -> Panel:
    body = Group(
        Text.assemble(
            (" ▸ target  ", f"bold {C_CYAN}"),
            (target, "bright_white"),
        ),
        Text.assemble(
            (" ▸ tip  ", C_DIM),
            ("!git blame <path>", f"bold {C_PINK}"),
            (" for now — v1.5 adds inline author + age.", C_DIM),
        ),
    )
    return Panel(
        body,
        box=ROUNDED,
        border_style=C_INDIGO,
        padding=(1, 2),
        title=f"[bold {C_INDIGO}]blame[/]",
        title_align="left",
    )


def trace_renderable(*, path: Path, verbose: bool) -> Panel:
    body = Group(
        Text.assemble(
            (" ▸ events  ", f"bold {C_CYAN}"),
            (str(path), "bright_white"),
        ),
        Text.assemble(
            (" ▸ live-echo  ", C_DIM),
            _on_off(verbose, on_colour=C_GREEN),
        ),
        Text.assemble(
            (" ▸ tail with  ", C_DIM),
            (f"!tail -f {path}", f"bold {C_PINK}"),
        ),
    )
    return Panel(
        body,
        box=ROUNDED,
        border_style=C_INDIGO,
        padding=(1, 2),
        title=f"[bold {C_INDIGO}]trace[/]",
        title_align="left",
    )


def self_renderable(rows: list[tuple[str, str]]) -> Panel:
    t = Table(
        box=None,
        show_header=False,
        pad_edge=False,
        padding=(0, 2),
    )
    t.add_column(style=C_DIM, no_wrap=True, width=14, justify="right")
    t.add_column()
    for k, v in rows:
        t.add_row(k, Text(v, style=f"bold {C_CYAN}"))
    return Panel(
        t,
        box=ROUNDED,
        border_style=C_CYAN,
        padding=(1, 2),
        title=f"[bold {C_CYAN}]self[/]",
        title_align="left",
    )


def badges_renderable(rows: list[tuple[str, int]]) -> Panel:
    if not rows:
        body: Text | Table = Text(
            "(no slash commands run yet)", style=f"italic {C_DIM}"
        )
    else:
        body = Table(
            box=None,
            show_header=False,
            pad_edge=False,
            padding=(0, 2),
        )
        body.add_column(style=f"bold {C_CYAN}", no_wrap=True, width=14)
        body.add_column(style="bright_white", no_wrap=True, width=6, justify="right")
        body.add_column(style=f"{C_INDIGO}")
        top = max((count for _, count in rows), default=1) or 1
        for name, count in rows:
            bar = "█" * max(int(count * 18 / top), 1)
            body.add_row(f"/{name}", str(count), bar)
    return Panel(
        body,
        box=ROUNDED,
        border_style=C_INDIGO,
        padding=(1, 2),
        title=f"[bold {C_CYAN}]badges[/]",
        title_align="left",
        subtitle=f"[dim]{len(rows)} commands used[/]",
        subtitle_align="right",
    )


def budget_renderable(cap: float | None) -> Panel:
    if cap is None:
        body = Text(" ▸ no budget cap.", style=f"italic {C_DIM}")
    else:
        body = Text.assemble(
            (" ▸ cap  ", f"bold {C_AMBER}"),
            (f"${cap:.2f}", "bright_white"),
        )
    return Panel(body, box=ROUNDED, border_style=C_AMBER, padding=(0, 2))


def btw_renderable(topic: str) -> Panel:
    body = Group(
        Text.assemble(
            (" ▸ btw  ", f"bold {C_PINK}"),
            (topic, "bright_white"),
        ),
        Text(
            " ▸ handled out-of-band; does NOT pollute plan context.",
            style=f"italic {C_DIM}",
        ),
    )
    return Panel(
        body,
        box=ROUNDED,
        border_style=C_PINK,
        padding=(1, 2),
        title=f"[bold {C_PINK}]btw[/]",
        title_align="left",
    )


def handoff_renderable(
    *,
    repo: Path,
    turns: int,
    model: str,
    mode: str,
    pending: str | None,
) -> Panel:
    lines = Group(
        Text.assemble(
            (" ▸ repo  ", C_DIM),
            (str(repo), "bright_white"),
        ),
        Text.assemble(
            (" ▸ turns  ", C_DIM),
            (str(turns), f"bold {C_CYAN}"),
            ("   mode  ", C_DIM),
            _mode_badge(mode),
            ("   model  ", C_DIM),
            (model, f"bold {C_GREEN}"),
        ),
        Text.assemble(
            (" ▸ pending  ", C_DIM),
            (pending or "(none)", "bright_white" if pending else C_DIM),
        ),
        Text(
            " ▸ paste into a GitHub PR — markdown file staged at "
            ".lyra/handoff.md.",
            style=f"italic {C_DIM}",
        ),
    )
    return Panel(
        lines,
        box=ROUNDED,
        border_style=C_GREEN,
        padding=(1, 2),
        title=f"[bold {C_GREEN}]handoff[/]",
        title_align="left",
    )


def pair_renderable(mode: str) -> Panel:
    body = Group(
        Text.assemble(
            (" ▸ pair mode queued  ", f"bold {C_PINK}"),
            (f"({mode})", C_DIM),
        ),
        Text(
            " ▸ live streaming collaboration lands with the Phase 10 HTTP server.",
            style=f"italic {C_DIM}",
        ),
    )
    return Panel(
        body,
        box=ROUNDED,
        border_style=C_PINK,
        padding=(1, 2),
        title=f"[bold {C_PINK}]pair[/]",
        title_align="left",
    )


def wiki_renderable(path: Path) -> Panel:
    body = Group(
        Text.assemble(
            (" ▸ target  ", f"bold {C_CYAN}"),
            (str(path), "bright_white"),
        ),
        Text(
            " ▸ Devin-Wiki-style auto-indexed repo docs arrive in v1.5 Phase 18.",
            style=f"italic {C_DIM}",
        ),
    )
    return Panel(
        body,
        box=ROUNDED,
        border_style=C_INDIGO,
        padding=(1, 2),
        title=f"[bold {C_INDIGO}]wiki[/]",
        title_align="left",
    )


def effort_renderable(choice: str, levels: dict[str, str]) -> Panel:
    t = Table(
        box=None,
        show_header=False,
        pad_edge=False,
        padding=(0, 2),
    )
    t.add_column(width=2)
    t.add_column(style=f"bold {C_CYAN}", no_wrap=True, width=10)
    t.add_column(style=C_DIM)
    for name, desc in levels.items():
        glyph = Text("●" if name == choice else "○",
                     style=f"bold {C_CYAN}" if name == choice else C_DIM)
        t.add_row(glyph, name, desc)
    return Panel(
        t,
        box=ROUNDED,
        border_style=C_CYAN,
        padding=(1, 2),
        title=f"[bold {C_CYAN}]effort[/]",
        title_align="left",
        subtitle=f"[dim]active: {choice}[/]",
        subtitle_align="right",
    )


def bad_effort_renderable(target: str, valid: tuple[str, ...]) -> Panel:
    body = Text.assemble(
        (" unknown effort  ", f"bold {C_RED}"),
        (target, f"bold {C_AMBER}"),
        ("   ·   valid: ", C_DIM),
        (", ".join(valid), f"bold {C_CYAN}"),
    )
    return Panel(body, box=ROUNDED, border_style=C_RED, padding=(0, 2))


def ultrareview_renderable(mode: str) -> Panel:
    body = Group(
        Text.assemble(
            (" ▸ ultrareview queued  ", f"bold {C_PINK}"),
            (f"({mode})", C_DIM),
        ),
        Text(
            " ▸ 4-agent Executor/Grader/Comparator/Analyzer loop — v1.7 Phase 19.",
            style=f"italic {C_DIM}",
        ),
    )
    return Panel(
        body,
        box=ROUNDED,
        border_style=C_PINK,
        padding=(1, 2),
        title=f"[bold {C_PINK}]ultrareview[/]",
        title_align="left",
    )


def review_renderable(mode: str) -> Panel:
    body = Group(
        Text.assemble(
            (" ▸ post-turn verifier  ", f"bold {C_CYAN}"),
            (f"({mode})", C_DIM),
        ),
        Text(
            " ▸ TDD gate + safety monitor + cross-channel evidence — v1 Phase 5.",
            style=f"italic {C_DIM}",
        ),
    )
    return Panel(
        body,
        box=ROUNDED,
        border_style=C_CYAN,
        padding=(1, 2),
        title=f"[bold {C_CYAN}]review[/]",
        title_align="left",
    )


def tdd_gate_renderable(state: str) -> Panel:
    colour = C_GREEN if state == "on" else C_AMBER
    body = Group(
        Text.assemble(
            (" ▸ tdd-gate  ", f"bold {colour}"),
            (state, f"bold {colour}"),
        ),
        Text(
            " ▸ Edit without a preceding failing test is blocked "
            "(full enforcement lands in v1 Phase 4).",
            style=f"italic {C_DIM}",
        ),
    )
    return Panel(
        body,
        box=ROUNDED,
        border_style=colour,
        padding=(1, 2),
        title=f"[bold {colour}]tdd-gate[/]",
        title_align="left",
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mode_badge(mode: str) -> Text:
    """Coloured mode label, matching the bottom-toolbar palette."""
    colour = {
        "plan": C_CYAN,
        "build": C_AMBER,
        "run": C_PINK,
        "explore": C_CYAN,
        "retro": C_INDIGO,
    }.get(mode, C_AMBER)
    return Text(mode, style=f"bold {colour}")


def _on_off(state: bool, *, on_colour: str = C_GREEN) -> Text:
    return (
        Text("on", style=f"bold {on_colour}")
        if state
        else Text("off", style=f"{C_DIM}")
    )


def goodbye_renderable(*, turns: int, tokens: int, cost_usd: float) -> Panel:
    """Final session summary printed on clean exit.

    Pulls the active skin's branding so a kawaii skin can say
    ``"see you, partner~"`` and the panel border / accent follow the
    palette. Aurora's defaults still produce the historical
    ``"see you in the next session."`` line, so the existing tests
    that assert on that exact substring keep passing.
    """
    try:
        from . import themes as _themes  # local — avoid cyclic dep
        skin = _themes.get_active_skin()
        accent = skin.color("accent", C_CYAN)
        border = skin.color("banner_border", skin.color("secondary", C_INDIGO))
        farewell = skin.brand("goodbye", "see you in the next session.")
    except Exception:  # pragma: no cover - defensive
        accent = C_CYAN
        border = C_INDIGO
        farewell = "see you in the next session."

    t = Table(
        box=None,
        show_header=False,
        pad_edge=False,
        padding=(0, 2),
    )
    t.add_column(style=C_DIM, no_wrap=True, width=10, justify="right")
    t.add_column()
    t.add_row("turns", Text(str(turns), style=f"bold {accent}"))
    t.add_row("tokens", Text(f"{tokens:,}", style="bright_white"))
    t.add_row("cost", Text(f"${cost_usd:.4f}", style="bright_white"))
    footer = Text(farewell, style=f"italic {C_DIM}")
    return Panel(
        Group(t, Text(""), footer),
        box=ROUNDED,
        border_style=border,
        padding=(1, 2),
        title=f"[bold {accent}]bye[/]",
        title_align="left",
    )


def bash_output_renderable(
    *,
    command: str,
    exit_code: int,
    stdout: str,
    stderr: str,
    duration_sec: float | None = None,
) -> Panel:
    """Render a ``!cmd`` bash invocation's output inside a compact panel.

    *duration_sec* is optional; when provided we show ``exit 0 · 1.4s``
    in the panel subtitle so the user sees how long the run took
    (mirrors the trailing ``(2.3s)`` hermes adds to its tool lines).
    Streams are byte-counted in the subtitle when both are present so
    you can see at a glance whether a tool wrote to stderr without
    scrolling.
    """
    ok = exit_code == 0
    colour = C_GREEN if ok else C_RED
    glyph = "✓" if ok else "✗"

    parts: list[Text] = []
    if stdout:
        parts.append(Text(stdout.rstrip("\n"), style="bright_white"))
    if stderr:
        if parts:
            parts.append(Text(""))
        parts.append(Text(stderr.rstrip("\n"), style=f"{C_RED}"))
    if not parts:
        parts.append(Text("(no output)", style=f"italic {C_DIM}"))

    body = Group(*parts)
    subtitle_parts: list[str] = [f"exit {exit_code}"]
    if duration_sec is not None:
        subtitle_parts.append(f"{duration_sec:.1f}s")
    if stdout and stderr:
        subtitle_parts.append(
            f"out {len(stdout)}b · err {len(stderr)}b"
        )
    return Panel(
        body,
        box=ROUNDED,
        border_style=colour,
        padding=(1, 2),
        title=(
            f"[bold {colour}]{glyph} $[/] "
            f"[bold {C_CYAN}]{command}[/]"
        ),
        title_align="left",
        subtitle=f"[dim]{' · '.join(subtitle_parts)}[/]",
        subtitle_align="right",
    )


# ---------------------------------------------------------------------------
# Tool preview / completion lines (hermes-agent inspired)
# ---------------------------------------------------------------------------
#
# These small helpers exist so anywhere the agent loop touches an external
# tool we get a consistent two-line UI:
#
#     ┊ ⚡ <command>                   ← tool_preview_renderable (before run)
#     ▏ ✓ <command> (1.4s)             ← tool_completion_renderable (after run)
#
# Today only ``!bash`` uses them; once the LLM tool-call path lands
# (Phase 14), every tool invocation routes through the same helpers so
# the UX stays consistent across bash / read / write / search / ...
#
# Failure detection follows hermes' heuristic: terminal tools annotate
# with ``[exit N]``, others get ``[error]`` if the result body contains
# ``"error"``, ``"failed"``, or starts with ``Error``.


def tool_preview_renderable(
    tool_name: str,
    args: str,
    *,
    prefix: str = "┊",
    accent: str = C_CYAN,
    emoji: str | None = None,
) -> Text:
    """Single-line "about to run" preview, e.g. ``┊ ⚡ ls -la``.

    *args* is rendered as-is — callers should already truncate long
    arguments. We fall back to the tool name if *args* is empty.
    """
    glyph = emoji or _default_emoji(tool_name)
    body = args if args else f"({tool_name})"
    return Text.assemble(
        (f" {prefix} ", C_DIM),
        (f"{glyph} ", accent),
        (body, "bright_white"),
    )


def tool_completion_renderable(
    tool_name: str,
    args: str,
    *,
    duration_sec: float,
    success: bool,
    suffix: str = "",
    prefix: str = "▏",
) -> Text:
    """Single-line completion summary, e.g. ``▏ ✓ ls -la (0.4s)``.

    On failure renders red with ``✗`` and an optional ``[exit 1]`` /
    ``[error]`` suffix supplied by the caller (use
    :func:`detect_tool_failure` to compute it).
    """
    colour = C_GREEN if success else C_RED
    glyph = "✓" if success else "✗"
    body = args if args else f"({tool_name})"
    fragments: list[tuple[str, str]] = [
        (f" {prefix} ", C_DIM),
        (f"{glyph} ", colour),
        (body, "bright_white"),
        (f" ({duration_sec:.1f}s)", C_DIM),
    ]
    if suffix:
        fragments.append((f" {suffix}", colour))
    return Text.assemble(*fragments)


def detect_tool_failure(
    tool_name: str,
    *,
    exit_code: int | None = None,
    output: str | None = None,
) -> tuple[bool, str]:
    """Heuristic-detect tool failure, return ``(is_failure, suffix)``.

    Mirrors hermes' ``_detect_tool_failure``:

    - For shell-style tools an ``exit_code != 0`` is the strongest
      signal; we render ``[exit <code>]`` so the user sees the code.
    - Otherwise we sniff the first 500 chars of the output for the
      ``"error"`` / ``"failed"`` keywords. False positives are tolerable
      because the worst case is "user sees an [error] tag on a noisy
      tool" — they can /trace to see the raw event.
    """
    if exit_code is not None and exit_code != 0:
        return True, f"[exit {exit_code}]"
    if output:
        head = output[:500].lower()
        if (
            '"error"' in head
            or '"failed"' in head
            or head.lstrip().startswith("error")
            or head.lstrip().startswith("traceback")
        ):
            return True, "[error]"
    return False, ""


def _default_emoji(tool_name: str) -> str:
    """Per-tool emoji fallback. Skins can override via ``tool_emojis``."""
    return _DEFAULT_TOOL_EMOJIS.get(tool_name, "⚡")


_DEFAULT_TOOL_EMOJIS: dict[str, str] = {
    "bash": "⚡",
    "shell": "⚡",
    "read": "📖",
    "write": "✎",
    "edit": "✎",
    "patch": "✎",
    "search": "🔍",
    "grep": "🔍",
    "glob": "📂",
    "ls": "📂",
    "fetch": "🌐",
    "browser": "🌐",
    "test": "🧪",
    "git": "⎇",
    "spawn": "🚀",
    "skill": "✨",
}
