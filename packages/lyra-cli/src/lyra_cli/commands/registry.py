"""Unified slash command registry (plan Phase 5, opencode pattern).

A single data-driven :data:`COMMAND_REGISTRY` replaces the previously
scattered slash handlers. The REPL completer, the ``/help`` renderer,
the command dispatcher, plugin-contributed commands and MCP prompts
(surfaced as ``/mcp:name``) all consult the same list.

Keeping this boring:

- :class:`CommandSpec` is a small dataclass — stable wire shape.
- :func:`resolve_command` accepts a raw REPL line (``/status foo``) and
  returns the matched spec + argument string, or ``(None, "")``.
- :func:`register_command` lets plugins append new specs (e.g. each
  MCP prompt becomes one ``CommandSpec`` with category ``"mcp"``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Literal, Optional

CommandCategory = Literal["session", "config", "build", "debug", "meta", "mcp", "skill"]


@dataclass(frozen=True)
class CommandResult:
    """Structured outcome returned by :class:`CommandSpec` handlers."""

    ok: bool = True
    message: str = ""
    payload: dict = field(default_factory=dict)


@dataclass
class CommandSpec:
    """Declarative description of a slash command.

    Handlers may return anything; the dispatcher only cares about
    exceptions. The ``args_hint`` string is rendered by ``/help`` to
    show users how to invoke the command (e.g. ``"<plan|agent>"``).
    """

    name: str
    description: str
    category: CommandCategory
    handler: Callable[..., Any]
    aliases: tuple[str, ...] = ()
    args_hint: str = ""
    interactive_only: bool = False
    hidden: bool = False


def _noop_handler(*_a: Any, **_k: Any) -> CommandResult:
    """Placeholder handler used by default specs.

    Concrete handlers are wired in by the REPL driver. The registry
    stays decoupled from runtime state so the unit tests can introspect
    shape without booting the full CLI.
    """
    return CommandResult(ok=True, message="")


COMMAND_REGISTRY: list[CommandSpec] = [
    CommandSpec(
        name="help",
        description="List commands or show help for one.",
        category="meta",
        handler=_noop_handler,
        aliases=("?", "h"),
        args_hint="[command]",
    ),
    CommandSpec(
        name="status",
        description="Show current mode, model, token cost, plugins.",
        category="session",
        handler=_noop_handler,
    ),
    CommandSpec(
        name="mode",
        description="Switch run mode (plan | agent | explore).",
        category="config",
        handler=_noop_handler,
        args_hint="<plan|agent|explore>",
    ),
    CommandSpec(
        name="model",
        description="Show or switch the active LLM provider/model.",
        category="config",
        handler=_noop_handler,
        args_hint="[provider:model]",
    ),
    CommandSpec(
        name="diff",
        description="Show pending file-system changes this turn.",
        category="debug",
        handler=_noop_handler,
    ),
    CommandSpec(
        name="clear",
        description="Reset the current session transcript.",
        category="session",
        handler=_noop_handler,
        aliases=("reset",),
    ),
    CommandSpec(
        name="exit",
        description="Leave the REPL.",
        category="session",
        handler=_noop_handler,
        aliases=("quit", "q"),
    ),
    CommandSpec(
        name="plan",
        description="Run the plan mode for a free-form goal.",
        category="build",
        handler=_noop_handler,
        args_hint="<goal>",
    ),
    CommandSpec(
        name="session",
        description="List, load, or search prior sessions.",
        category="session",
        handler=_noop_handler,
        args_hint="[list|search|load]",
    ),
    CommandSpec(
        name="skill",
        description="Manage project skills (list | create | patch).",
        category="skill",
        handler=_noop_handler,
        args_hint="[list|create|patch|delete]",
    ),
    CommandSpec(
        name="doctor",
        description="Run environment diagnostics.",
        category="meta",
        handler=_noop_handler,
    ),
    CommandSpec(
        name="retro",
        description="Summarize the last session's highlights.",
        category="meta",
        handler=_noop_handler,
    ),
]


def _index(specs: list[CommandSpec]) -> dict[str, CommandSpec]:
    idx: dict[str, CommandSpec] = {}
    for spec in specs:
        idx[spec.name] = spec
        for alias in spec.aliases:
            idx[alias] = spec
    return idx


def resolve_command(line: str) -> tuple[Optional[CommandSpec], str]:
    """Parse a REPL line and return ``(spec_or_None, args_str)``.

    Accepts with or without the leading ``/``. Args are preserved
    verbatim (including whitespace) so handlers that want flag parsing
    can split further.
    """
    if not line:
        return None, ""
    raw = line.lstrip()
    if raw.startswith("/"):
        raw = raw[1:]
    if not raw:
        return None, ""
    name, _, rest = raw.partition(" ")
    spec = _index(COMMAND_REGISTRY).get(name.strip())
    return spec, rest.strip()


def register_command(spec: CommandSpec) -> None:
    """Append a spec to :data:`COMMAND_REGISTRY` with collision guard."""
    idx = _index(COMMAND_REGISTRY)
    if spec.name in idx or any(a in idx for a in spec.aliases):
        raise ValueError(
            f"command name/alias collision for {spec.name!r} (aliases={spec.aliases})"
        )
    COMMAND_REGISTRY.append(spec)


def commands_by_category() -> dict[str, list[CommandSpec]]:
    """Group non-hidden specs by category — used by ``/help`` rendering."""
    grouped: dict[str, list[CommandSpec]] = {}
    for spec in COMMAND_REGISTRY:
        if spec.hidden:
            continue
        grouped.setdefault(spec.category, []).append(spec)
    return grouped


__all__ = [
    "CommandCategory",
    "CommandSpec",
    "CommandResult",
    "COMMAND_REGISTRY",
    "resolve_command",
    "register_command",
    "commands_by_category",
]
