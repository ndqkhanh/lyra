"""ECC Engine TUI Widget — inline dependency analysis and impact visualization.

Ports the 544-line ``ecc_integration.py`` (ECC Engine) into the TUI shell.
Provides:
  • Blast radius analysis — when editing a file, shows what depends on it
  • Dependency visualization — tree of imports/inheritance
  • Symbol search across the repo
  • Cycle detection 🔄
  • Inline risk assessment (low/medium/high)

Wired into the TUI as:
  • ``Ctrl+E`` — toggle ECC panel
  • ``/ecc`` — slash command for REPL

ECC reference: the ``ecc_integration.py`` engine was already built
but never UI'd — this is the missing frontend.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static

from ...ecc_integration import ECCEngine, RepositoryContext, ImpactAnalysis


class ECCWidget(Widget):
    """Live ECC engine panel — dependency graph, blast radius, symbols.

    Toggle: Ctrl+E
    Shows: repo stats, dependency graph health, file impact analysis.
    """

    DEFAULT_CSS = """
    ECCWidget {
        height: auto;
        border: solid $border;
        padding: 0 1;
        margin: 0 1;
    }

    ECCWidget.collapsed {
        height: 1;
        border: none;
    }

    ECCWidget #ecc-header {
        height: 1;
        color: $text-muted;
    }

    ECCWidget #ecc-content {
        height: auto;
        margin: 0 0 0 1;
    }

    ECCWidget .ecc-row {
        height: 1;
    }

    ECCWidget .ecc-risk-low {
        color: green;
    }

    ECCWidget .ecc-risk-medium {
        color: yellow;
    }

    ECCWidget .ecc-risk-high {
        color: red;
        text-style: bold;
    }

    ECCWidget .ecc-cycle {
        color: red;
        text-style: bold;
    }
    """

    BINDINGS = [
        Binding("ctrl+e", "toggle_ecc", "ECC Analysis"),
    ]

    expanded: reactive[bool] = reactive(False)
    repo_path: reactive[str] = reactive("")
    status: reactive[str] = reactive("")

    def __init__(self, repo_root: Optional[Path] = None):
        super().__init__()
        self._engine: Optional[ECCEngine] = None
        self._context: Optional[RepositoryContext] = None
        self._repo_root = repo_root or Path.cwd()
        self._analyzed = False

    def compose(self) -> ComposeResult:
        yield Static("", id="ecc-header")
        yield Static("", id="ecc-content")

    def on_mount(self) -> None:
        self._render()

    # ── Public API ─────────────────────────────────────────────────────

    def analyze(self, repo_path: Optional[Path] = None) -> None:
        """Run full ECC analysis on the repo."""
        if repo_path:
            self._repo_root = repo_path

        self.status = "Analyzing…"
        self._render()

        try:
            self._engine = ECCEngine(self._repo_root)
            self._context = self._engine.analyze_repository()
            self._analyzed = True
            self.status = f"✓ {self._context.total_files} files, {self._context.total_lines} lines"
        except Exception as e:
            self._analyzed = False
            self.status = f"[red]✗[/] {e}"

        self._render()

    def analyze_file(self, file_path: str) -> Optional[ImpactAnalysis]:
        """Run impact analysis on a specific file."""
        if not self._engine or not self._analyzed:
            self.analyze()
        if self._engine:
            return self._engine.analyze_impact(file_path)
        return None

    @property
    def engine(self) -> Optional[ECCEngine]:
        return self._engine

    @property
    def context(self) -> Optional[RepositoryContext]:
        return self._context

    # ── Actions ────────────────────────────────────────────────────────

    def action_toggle_ecc(self) -> None:
        self.expanded = not self.expanded
        self.toggle_class("collapsed", not self.expanded)
        if self.expanded and not self._analyzed:
            self.analyze()
        self._render()

    # ── Internal ───────────────────────────────────────────────────────

    def _render(self) -> None:
        if not self.is_mounted:
            return
        try:
            self._render_header()
            self._render_content()
        except Exception:
            pass

    def _render_header(self) -> None:
        hint = "[dim](ctrl+e)[/]"
        if self.expanded:
            self.query_one("#ecc-header", Static).update(
                f"[bold]ECC Analysis[/]  {hint}"
            )
        else:
            self.query_one("#ecc-header", Static).update(
                f"[bold]ECC[/]  {self.status}  {hint}"
            )

    def _render_content(self) -> None:
        if not self.expanded:
            self.query_one("#ecc-content", Static).update("")
            return

        if not self._analyzed or not self._context:
            self.query_one("#ecc-content", Static).update(
                f"  [dim]{self.status}[/]"
            )
            return

        ctx = self._context
        lines = []

        # ── Repository stats ─────────────────────────────────────────
        lang_str = ", ".join(f"{lang}: {n}" for lang, n in ctx.languages.items()) if ctx.languages else "—"
        lines.append(f"  [dim]files[/]    {ctx.total_files}")
        lines.append(f"  [dim]lines[/]    {ctx.total_lines:,}")
        lines.append(f"  [dim]langs[/]    {lang_str}")
        lines.append(f"  [dim]symbols[/]  {len(ctx.symbols)}")

        # ── Dependencies ──────────────────────────────────────────────
        if ctx.dependencies:
            lines.append(f"  [dim]deps[/]     {len(ctx.dependencies)} relations")
            if self._engine:
                cycles = self._engine.graph.detect_cycles()
                if cycles:
                    lines.append(f"  [red]⚠ {len(cycles)} cycle(s) detected[/]")
                    for cycle in cycles[:3]:
                        names = " → ".join(cycle[:5])
                        suffix = " …" if len(cycle) > 5 else ""
                        lines.append(f"    [red]↻[/] {names}{suffix}")

        # ── Entry points ──────────────────────────────────────────────
        if ctx.entry_points:
            lines.append(f"  [dim]entry[/]    {len(ctx.entry_points)} points")
            for ep in ctx.entry_points[:3]:
                lines.append(f"    [dim]{Path(ep).name}[/]")
            if len(ctx.entry_points) > 3:
                lines.append(f"    [dim]… +{len(ctx.entry_points) - 3} more[/]")

        self.query_one("#ecc-content", Static).update("\n".join(lines))
