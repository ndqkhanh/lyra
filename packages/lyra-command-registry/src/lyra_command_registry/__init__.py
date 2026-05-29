"""Command Registry — Quick action commands evolved from raw instincts.

Part of the Beliefs→Instincts→Skills hierarchy (Plan 6).
Commands are the lightest-weight agent action — between instincts (raw patterns)
and skills (formal definitions).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

__all__ = [
    "Command",
    "CommandRegistry",
]


@dataclass
class Command:
    name: str
    description: str
    pattern: str
    source_instinct_id: str | None = None
    hit_count: int = 0


class CommandRegistry:
    """Lightweight command registry — commands are evolved from instincts."""

    def __init__(self):
        self._commands: dict[str, Command] = {}
        self._handlers: dict[str, Callable] = {}

    def register(self, command: Command, handler: Callable | None = None) -> None:
        self._commands[command.name] = command
        if handler:
            self._handlers[command.name] = handler
        logger.info(f"Registered command: {command.name}")

    def evolve_from_instinct(self, instinct_trigger: str, instinct_pattern: str) -> Command:
        cmd = Command(
            name=instinct_trigger.replace(" ", "_").lower(),
            description=f"Auto-evolved from instinct: {instinct_trigger}",
            pattern=instinct_pattern,
        )
        self._commands[cmd.name] = cmd
        return cmd

    def execute(self, command_name: str, *args: Any, **kwargs: Any) -> Any:
        handler = self._handlers.get(command_name)
        if not handler:
            raise ValueError(f"No handler for command: {command_name}")
        cmd = self._commands.get(command_name)
        if cmd:
            cmd.hit_count += 1
        return handler(*args, **kwargs)

    def get_command(self, name: str) -> Command | None:
        return self._commands.get(name)

    @property
    def all_commands(self) -> list[Command]:
        return list(self._commands.values())

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "total": len(self._commands),
            "with_handlers": len(self._handlers),
            "most_used": max(self._commands.values(), key=lambda c: c.hit_count).name
            if self._commands else None,
        }
