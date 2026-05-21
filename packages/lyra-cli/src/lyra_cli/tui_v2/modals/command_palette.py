"""Command palette modal for TUI v2.

Ctrl+K fuzzy-searchable command palette that mirrors the REPL's /palette
functionality. Provides quick access to all slash commands with keyboard
navigation and real-time filtering.

Architecture:
- Extends LyraPickerModal for consistent modal behavior
- Uses COMMAND_REGISTRY as the single source of truth
- Fuzzy matching handled by base class
- Keyboard navigation: Up/Down/Enter/Escape

Usage:
    result = await app.push_screen(CommandPaletteModal())
    if result:
        # result is the command name (e.g., "model", "fork")
        composer.text = f"/{result} "
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .base import Entry, LyraPickerModal

if TYPE_CHECKING:
    from lyra_cli.commands.registry import CommandSpec


class CommandPaletteModal(LyraPickerModal):
    """Fuzzy-searchable command palette modal.
    
    Displays all available slash commands with descriptions, grouped by
    category. Supports fuzzy search and keyboard navigation.
    """

    picker_title = "Command Palette"

    def entries(self) -> list[Entry]:
        """Load all commands from the registry.
        
        Returns:
            List of Entry objects, one per command
        """
        # Import here to avoid circular dependency
        from lyra_cli.commands.registry import COMMAND_REGISTRY

        entries = []
        for cmd in COMMAND_REGISTRY:
            # Build label with aliases
            label = f"/{cmd.name}"
            if cmd.aliases:
                label += f" ({', '.join('/' + a for a in cmd.aliases)})"
            
            # Build description with category
            description = f"[{cmd.display_category}] {cmd.description}"
            
            # Add metadata for preview
            meta = {
                "Category": cmd.display_category,
                "Description": cmd.description,
            }
            if cmd.aliases:
                meta["Aliases"] = ", ".join(f"/{a}" for a in cmd.aliases)
            
            entries.append(
                Entry(
                    key=cmd.name,
                    label=label,
                    description=description,
                    meta=meta,
                )
            )
        
        # Sort by category, then name
        entries.sort(key=lambda e: (e.meta["Category"], e.label.lower()))
        return entries

    def _preview(self, key: str) -> str:
        """Render detailed preview for the selected command.
        
        Args:
            key: Command name
            
        Returns:
            Rich-formatted preview text
        """
        # Import here to avoid circular dependency
        from lyra_cli.commands.registry import COMMAND_REGISTRY

        # Find the command
        cmd = next((c for c in COMMAND_REGISTRY if c.name == key), None)
        if not cmd:
            return "[dim](command not found)[/]"
        
        lines = []
        
        # Command name
        lines.append(f"[bold cyan]/{cmd.name}[/]")
        
        # Aliases
        if cmd.aliases:
            aliases_str = ", ".join(f"/{a}" for a in cmd.aliases)
            lines.append(f"[dim]Aliases:[/] {aliases_str}")
        
        lines.append("")
        
        # Category
        lines.append(f"[dim]Category:[/] {cmd.display_category}")
        
        lines.append("")
        
        # Description
        lines.append(f"[bold]Description:[/]")
        lines.append(cmd.description)
        
        # Usage hint
        lines.append("")
        lines.append("[dim]Press Enter to insert this command[/]")
        
        return "\n".join(lines)
