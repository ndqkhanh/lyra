"""Command loader - Loads commands from all sources into unified registry."""

from __future__ import annotations

from pathlib import Path

from .command_registry import Command, get_registry


def _load_lyra_commands_dict() -> dict[str, str]:
    """Load LYRA_COMMANDS from the cli commands module (shadowed by cli/commands/ package)."""
    from importlib.util import module_from_spec, spec_from_file_location

    cli_dir = Path(__file__).resolve().parents[1] / "cli"
    cmd_path = cli_dir / "commands.py"
    spec = spec_from_file_location("lyra_cli._slash_cmds", str(cmd_path))
    mod = module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.LYRA_COMMANDS


class CommandLoader:
    """Loads commands from Lyra core and ECC sources."""

    @staticmethod
    def load_lyra_commands() -> list[Command]:
        """Load commands from the core LYRA_COMMANDS registry."""
        commands: list[Command] = []
        lyra_cmds = _load_lyra_commands_dict()
        for name, description in lyra_cmds.items():
            cmd = Command(
                name=name.lstrip("/"),
                description=description,
                handler=lambda: None,
                category="general",
                source="lyra",
            )
            commands.append(cmd)
        return commands

    @staticmethod
    def register_all():
        """Register all commands from all sources into the global registry."""
        registry = get_registry()

        for cmd in CommandLoader.load_lyra_commands():
            registry.register(cmd)

        from .ecc_commands import register_ecc_commands

        register_ecc_commands(registry)

        return registry

    @staticmethod
    def total_count() -> int:
        """Return the total number of registered commands."""
        return len(get_registry().commands)

    @staticmethod
    def count_by_source() -> dict[str, int]:
        """Count commands by source (lyra vs ecc)."""
        registry = get_registry()
        counts: dict[str, int] = {}
        for cmd in registry.commands.values():
            counts[cmd.source] = counts.get(cmd.source, 0) + 1
        return counts
