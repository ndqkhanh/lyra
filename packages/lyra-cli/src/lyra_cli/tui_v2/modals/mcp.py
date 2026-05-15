"""McpPicker — browse configured MCP servers.

Read-only for Phase 5: shows servers from ``.lyra/mcp.json``,
``.claude/settings.json``, and ``~/.lyra/mcp.json``. Picking returns
the server name so the caller can echo it or wire it into a future
``/mcp enable`` mutation.
"""
from __future__ import annotations

from pathlib import Path

from ..commands.skills_mcp import _list_mcp
from .base import Entry, LyraPickerModal


def mcp_entries(working_dir: Path) -> list[Entry]:
    """Return the picker rows. Pure — testable without Textual."""
    rows = _list_mcp(working_dir)
    return [
        Entry(
            key=name,
            label=name,
            description=f"transport: {transport}",
            meta={"name": name, "transport": transport},
        )
        for name, transport in rows
    ]


class McpPicker(LyraPickerModal):
    picker_title = "MCP servers · browse configured"

    def __init__(self, working_dir: Path) -> None:
        self._working_dir = Path(working_dir)
        super().__init__()

    def entries(self) -> list[Entry]:
        return mcp_entries(self._working_dir)
