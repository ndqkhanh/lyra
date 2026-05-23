"""Command loader - Loads commands from various sources"""

from pathlib import Path
from typing import List
from .command_registry import Command, get_registry


class CommandLoader:
    """Loads commands from files and modules"""

    @staticmethod
    def load_lyra_commands() -> List[Command]:
        """Load existing Lyra commands (placeholder)"""
        # This would load from existing Lyra command definitions
        # For now, return sample commands
        commands = [
            Command(
                name="help",
                description="Show help information",
                handler=lambda: print("Help"),
                category="general",
                source="lyra"
            ),
            Command(
                name="version",
                description="Show version",
                handler=lambda: print("Lyra v0.1.0"),
                aliases=["v"],
                category="general",
                source="lyra"
            ),
        ]
        return commands

    @staticmethod
    def register_all():
        """Register all commands"""
        registry = get_registry()

        # Load Lyra commands
        lyra_commands = CommandLoader.load_lyra_commands()
        for cmd in lyra_commands:
            registry.register(cmd)

        # Load ECC commands
        from .ecc_commands import register_ecc_commands
        register_ecc_commands(registry)

        return registry
