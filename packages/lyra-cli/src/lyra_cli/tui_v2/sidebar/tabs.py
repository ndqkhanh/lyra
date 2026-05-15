"""Lyra sidebar tab widgets — Plans / Skills / MCP / Memory.

Each widget is a thin Textual ``Static`` that calls a pure helper from
:mod:`lyra_cli.tui_v2.sidebar.data` and renders the result. The data
layer is exhaustively tested in isolation; these widgets only test
the contract that ``refresh_content`` re-reads state on each tick.
"""
from __future__ import annotations

from pathlib import Path

from textual.widgets import Static

from . import REFRESH_SECONDS
from .data import (
    list_mcp_servers,
    list_memory_files,
    list_plans,
    list_sidebar_skills,
)


class _LyraSidebarTab(Static):
    """Base for the four Lyra sidebar tabs.

    Subclasses override ``_render_body(root)`` returning a single
    string (Rich markup permitted). The base handles mount-time
    initial paint and periodic refresh.
    """

    DEFAULT_CSS = """
    _LyraSidebarTab {
        height: auto;
    }
    """

    def __init__(self, root: Path) -> None:
        super().__init__("")
        self._root = Path(root)

    def on_mount(self) -> None:
        self.refresh_content()
        self.set_interval(REFRESH_SECONDS, self.refresh_content)

    def refresh_content(self) -> None:
        self.update(self._render_body(self._root))

    def _render_body(self, _root: Path) -> str:  # pragma: no cover — abstract
        raise NotImplementedError


# ---------------------------------------------------------------------
# Tab implementations
# ---------------------------------------------------------------------


class PlansTab(_LyraSidebarTab):
    """Plans saved under ``<repo>/.lyra/plans/`` and ``<repo>/.lyra/plan/``."""

    def _render_body(self, root: Path) -> str:
        return _format_list(
            "plans",
            list_plans(root),
            empty_hint="(no plans yet — try '/lyra plan')",
            render=lambda entry: f"  {entry['name']}  [dim]· {entry['updated']}[/]",
        )


class SkillsTab(_LyraSidebarTab):
    """Project + global skills as discovered by the slash-command helper."""

    def _render_body(self, root: Path) -> str:
        return _format_list(
            "skills",
            list_sidebar_skills(root),
            empty_hint="(no skills installed)",
            render=lambda s: f"  [dim][{s['source']}][/] {s['name']}",
        )


class McpTab(_LyraSidebarTab):
    """Configured MCP servers from ``.lyra/mcp.json`` and ``.claude/settings.json``."""

    def _render_body(self, root: Path) -> str:
        return _format_list(
            "mcp servers",
            list_mcp_servers(root),
            empty_hint="(no MCP servers configured)",
            render=lambda s: f"  {s['name']}  [dim]· {s['transport']}[/]",
        )


class MemoryTab(_LyraSidebarTab):
    """Memory notes under ``<repo>/.lyra/memory/`` and ``~/.claude/memory/``."""

    def _render_body(self, root: Path) -> str:
        return _format_list(
            "memory",
            list_memory_files(root),
            empty_hint="(no memory entries yet)",
            render=lambda m: f"  [dim][{m['source']}][/] {m['name']}",
        )


# ---------------------------------------------------------------------
# Pure helper — testable without Textual
# ---------------------------------------------------------------------


def _format_list(
    title: str,
    entries: list[dict],
    *,
    empty_hint: str,
    render,
) -> str:
    """Compose a sidebar block: bold title + list of entries (or empty hint)."""
    header = f"[bold]{title}[/] [dim]({len(entries)})[/]"
    if not entries:
        return f"{header}\n[dim]{empty_hint}[/]"
    lines = [header]
    for entry in entries:
        lines.append(render(entry))
    return "\n".join(lines)
