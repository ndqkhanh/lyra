"""CommandPaletteModal — Ctrl-K fuzzy command search for TUI v2.

Ports the REPL's command palette experience to Textual. Uses the same
fuzzy_filter logic from interactive.command_palette but adapts it to
the LyraPickerModal pattern.

Usage:
    result = await self.app.push_screen(CommandPaletteModal())
    if result:
        # result is the command name (e.g., "model", "mode")
        await self.run_command(f"/{result}")
"""
from __future__ import annotations

from lyra_cli.interactive.command_palette import fuzzy_filter

from .base import Entry, LyraPickerModal


class CommandPaletteModal(LyraPickerModal):
    """Fuzzy-searchable command palette (Ctrl-K)."""

    picker_title = "Command Palette"

    # Larger modal for command descriptions
    DEFAULT_CSS = """
    CommandPaletteModal {
        align: center middle;
    }
    CommandPaletteModal > Vertical {
        width: 88;
        height: 28;
        background: $surface;
        border: tall $primary;
        padding: 1 2;
    }
    CommandPaletteModal #title {
        height: 1;
        color: $primary;
        text-style: bold;
    }
    CommandPaletteModal #filter {
        height: 3;
        margin-bottom: 1;
    }
    CommandPaletteModal #cols {
        height: 1fr;
    }
    CommandPaletteModal ListView {
        width: 35;
        background: $bg;
    }
    CommandPaletteModal #preview {
        width: 1fr;
        background: $bg;
        padding: 0 1;
    }
    CommandPaletteModal #hint {
        height: 1;
        color: $fg_muted;
    }
    """

    def entries(self) -> list[Entry]:
        """Load all commands from COMMAND_REGISTRY."""
        # Use fuzzy_filter with empty query to get all commands
        specs = fuzzy_filter("")

        entries = []
        for spec in specs:
            # Build label with category prefix
            label = f"/{spec.name}"
            if spec.args_hint:
                label = f"{label} {spec.args_hint}"

            # Build description with category
            description = f"[dim]{spec.category}[/]\n{spec.description}"

            # Add aliases to meta
            meta = {}
            if spec.aliases:
                meta["aliases"] = ", ".join(f"/{a}" for a in spec.aliases)

            entries.append(
                Entry(
                    key=spec.name,
                    label=label,
                    description=description,
                    meta=meta,
                )
            )

        return entries

    def _preview(self, key: str) -> str:
        """Enhanced preview with category and aliases."""
        for e in self._all:
            if e.key == key:
                lines = [f"[bold cyan]{e.label}[/]"]
                if e.description:
                    lines.append("")
                    lines.append(e.description)
                if e.meta:
                    lines.append("")
                    for k, v in e.meta.items():
                        lines.append(f"[dim]{k}:[/] {v}")
                return "\n".join(lines)
        return "[dim](no command selected)[/]"
