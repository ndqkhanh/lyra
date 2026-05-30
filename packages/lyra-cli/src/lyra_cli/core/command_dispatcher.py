"""Command dispatcher for executing commands via agents or skills."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from .command_registry import CommandRegistry


@dataclass(frozen=True)
class CommandResult:
    success: bool
    output: str
    error: str | None = None
    command_name: str = ""
    duration_ms: float = 0.0


class CommandDispatcher:
    """Dispatches commands to their registered agent or skill handler.

    Commands are defined via YAML frontmatter with optional agent/skill
    routing. Dispatch resolves the target and invokes it with args.
    """

    def __init__(self, registry: CommandRegistry) -> None:
        self._registry = registry
        self._agent_callback: Any = None
        self._skill_callback: Any = None

    def dispatch(
        self, command_name: str, args: dict[str, Any] | None = None
    ) -> CommandResult:
        cmd_meta = self._registry.get_command(command_name)
        if not cmd_meta:
            return CommandResult(
                success=False, output="", error=f"Command '{command_name}' not found",
                command_name=command_name,
            )

        t0 = time.monotonic()
        try:
            if cmd_meta.agent and self._agent_callback:
                output = self._agent_callback(cmd_meta.agent, command_name, args)
            elif cmd_meta.skill and self._skill_callback:
                output = self._skill_callback(cmd_meta.skill, command_name, args)
            else:
                output = f"Command '{command_name}' dispatched (agent={cmd_meta.agent}, skill={cmd_meta.skill})"

            duration = (time.monotonic() - t0) * 1000
            return CommandResult(
                success=True, output=output, command_name=command_name, duration_ms=duration,
            )
        except Exception as exc:
            duration = (time.monotonic() - t0) * 1000
            return CommandResult(
                success=False, output="", error=str(exc),
                command_name=command_name, duration_ms=duration,
            )

    def set_agent_handler(self, handler: Any) -> None:
        self._agent_callback = handler

    def set_skill_handler(self, handler: Any) -> None:
        self._skill_callback = handler
