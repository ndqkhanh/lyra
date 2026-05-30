"""Custom User-Defined Slash Commands — P1-B4 (HIGH, LOW — BREAKTHROUGH).

YAML-configurable slash commands with typed arguments, boolean flags,
fuzzy name matching, and handler dispatch.

See: plan-phase1-harness.md §4.9
"""
from __future__ import annotations

import difflib
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


# ---------------------------------------------------------------------------
# Command Argument & Flag Definitions
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CommandArgument:
    """A positional or named argument for a slash command."""

    name: str
    type: str = "string"  # string, int, float, bool
    required: bool = False
    default: Any = None
    choices: list[Any] | None = None
    description: str = ""


@dataclass(frozen=True)
class CommandFlag:
    """A boolean flag for a slash command (--flag)."""

    name: str
    type: str = "bool"
    description: str = ""


# ---------------------------------------------------------------------------
# Command Definition
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CommandDefinition:
    """A complete slash command definition."""

    name: str
    description: str = ""
    usage: str = ""
    handler: str = ""  # dotted path, e.g. "lyra.research.deep_research"
    arguments: list[CommandArgument] = field(default_factory=list)
    flags: list[CommandFlag] = field(default_factory=list)
    source: str = ""  # path to the YAML file this was loaded from


# ---------------------------------------------------------------------------
# Command Config
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CommandConfig:
    """Container for all loaded command definitions."""

    commands: list[CommandDefinition] = field(default_factory=list)
    source: str = ""


# ---------------------------------------------------------------------------
# Fuzzy Matching
# ---------------------------------------------------------------------------


def fuzzy_match(
    name: str,
    candidates: list[str],
    *,
    cutoff: float = 0.6,
) -> str | None:
    """Return the best fuzzy match for *name* among *candidates*, or None.

    Uses SequenceMatcher ratio; returns the first candidate whose
    similarity ratio exceeds *cutoff* (descending order).
    """
    if not candidates:
        return None
    if name in candidates:
        return name

    scored = sorted(
        ((c, difflib.SequenceMatcher(None, name.lower(), c.lower()).ratio()) for c in candidates),
        key=lambda x: x[1],
        reverse=True,
    )
    best, best_score = scored[0]
    return best if best_score >= cutoff else None


def fuzzy_match_commands(
    name: str,
    commands: list[CommandDefinition],
    *,
    cutoff: float = 0.6,
) -> CommandDefinition | None:
    """Return the best fuzzy-matched command, or None."""
    candidates = [c.name for c in commands]
    matched_name = fuzzy_match(name, candidates, cutoff=cutoff)
    if matched_name is None:
        return None
    for c in commands:
        if c.name == matched_name:
            return c
    return None


# ---------------------------------------------------------------------------
# YAML Loading
# ---------------------------------------------------------------------------


def _validate_command(raw: dict[str, Any]) -> CommandDefinition:
    """Validate and convert a raw command dict to a CommandDefinition."""
    name = raw.get("name", "")
    if not name or not isinstance(name, str):
        raise ValueError(f"command requires a non-empty 'name' string, got: {name!r}")

    arguments: list[CommandArgument] = []
    for arg in raw.get("arguments", []) or []:
        arguments.append(
            CommandArgument(
                name=arg["name"],
                type=arg.get("type", "string"),
                required=arg.get("required", False),
                default=arg.get("default"),
                choices=arg.get("choices"),
                description=arg.get("description", ""),
            )
        )

    flags: list[CommandFlag] = []
    for f in raw.get("flags", []) or []:
        flags.append(
            CommandFlag(
                name=f["name"],
                type=f.get("type", "bool"),
                description=f.get("description", ""),
            )
        )

    return CommandDefinition(
        name=name,
        description=raw.get("description", ""),
        usage=raw.get("usage", ""),
        handler=raw.get("handler", ""),
        arguments=arguments,
        flags=flags,
    )


def load_commands_from_yaml(path: str | Path) -> CommandConfig:
    """Load slash commands from a YAML file.

    Expected format::

        commands:
          research:
            description: "Start a deep research task"
            usage: "/research <topic> [--depth 1-5]"
            handler: "lyra.research.deep_research"
            arguments:
              - name: topic
                type: string
                required: true
              - name: depth
                type: int
                default: 3
                choices: [1, 2, 3, 4, 5]
            flags:
              - name: security
                type: bool

    Returns a CommandConfig with all parsed commands.
    """
    try:
        import yaml as _yaml  # type: ignore[import-untyped]
    except ImportError:
        raise ImportError("PyYAML is required. Install with: pip install pyyaml")

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"commands file not found: {path}")

    with open(path, "r") as f:
        raw = _yaml.safe_load(f)

    if not isinstance(raw, dict):
        raise ValueError(f"YAML root must be a mapping, got: {type(raw).__name__}")

    commands_raw = raw.get("commands", {})
    if not isinstance(commands_raw, dict):
        raise ValueError(f"'commands' must be a mapping, got: {type(commands_raw).__name__}")

    commands: list[CommandDefinition] = []
    for name, spec in commands_raw.items():
        if not isinstance(spec, dict):
            raise ValueError(f"command '{name}' definition must be a mapping")
        spec["name"] = name
        commands.append(_validate_command(spec))

    return CommandConfig(commands=commands, source=str(path))


def load_commands_from_directories(
    directories: list[str | Path] | None = None,
) -> CommandConfig:
    """Load commands from one or more directories containing ``commands.yaml`` files.

    Searches (in order):
    1. Each directory in *directories*
    2. ``$LYRA_COMMANDS_PATH`` (colon-separated)
    3. ``~/.lyra/commands.yaml``
    4. ``./.lyra/commands.yaml`` (project-local)
    """
    search_paths: list[Path] = []

    if directories:
        for d in directories:
            p = Path(d) / "commands.yaml"
            if p.exists():
                search_paths.append(p)

    env_paths = os.environ.get("LYRA_COMMANDS_PATH", "")
    if env_paths:
        for d in env_paths.split(":"):
            p = Path(d.strip()) / "commands.yaml"
            if p.exists() and p not in search_paths:
                search_paths.append(p)

    default_paths = [
        Path.home() / ".lyra" / "commands.yaml",
        Path(".lyra") / "commands.yaml",
    ]
    for p in default_paths:
        if p.exists() and p not in search_paths:
            search_paths.append(p)

    all_commands: list[CommandDefinition] = []
    for p in search_paths:
        try:
            cfg = load_commands_from_yaml(p)
            all_commands.extend(cfg.commands)
        except Exception:
            continue

    return CommandConfig(commands=all_commands)


# ---------------------------------------------------------------------------
# Command Registry
# ---------------------------------------------------------------------------


@dataclass
class SlashCommandRegistry:
    """Registry for slash commands with fuzzy lookup and dispatch."""

    commands: dict[str, CommandDefinition] = field(default_factory=dict)
    _handlers: dict[str, Callable[..., Any]] = field(default_factory=dict)
    fuzzy_threshold: float = 0.6

    # --- Registration -----------------------------------------------------------

    def register(
        self,
        definition: CommandDefinition,
        handler: Callable[..., Any] | None = None,
    ) -> None:
        """Register a command definition and optional handler."""
        self.commands[definition.name] = definition
        if handler is not None:
            self._handlers[definition.name] = handler

    def register_many(self, config: CommandConfig) -> None:
        """Register all commands from a CommandConfig."""
        for cmd in config.commands:
            self.register(cmd)

    def unregister(self, name: str) -> bool:
        """Remove a command. Returns True if it was registered."""
        removed = self.commands.pop(name, None) is not None
        self._handlers.pop(name, None)
        return removed

    # --- Lookup ----------------------------------------------------------------

    def get(self, name: str) -> CommandDefinition | None:
        """Get a command by exact name."""
        return self.commands.get(name)

    def find(self, name: str) -> CommandDefinition | None:
        """Find a command by exact or fuzzy name match."""
        exact = self.commands.get(name)
        if exact is not None:
            return exact
        return fuzzy_match_commands(name, list(self.commands.values()), cutoff=self.fuzzy_threshold)

    def suggest(self, partial: str, *, limit: int = 5) -> list[str]:
        """Return command names that contain *partial* (substring match)."""
        lower = partial.lower()
        matches = [n for n in self.commands if lower in n.lower()]
        matches.sort(key=lambda n: (0 if n.lower().startswith(lower) else 1, n))
        return matches[:limit]

    # --- Dispatch --------------------------------------------------------------

    def dispatch(
        self,
        name: str,
        *,
        args: dict[str, Any] | None = None,
        flags: dict[str, bool] | None = None,
    ) -> Any:
        """Resolve and invoke a command handler.

        Raises KeyError if no matching command is found.
        Raises RuntimeError if the command has no handler registered.
        """
        cmd = self.get(name)
        if cmd is None:
            cmd = self.find(name)
        if cmd is None:
            raise KeyError(f"unknown command: {name!r}")

        handler = self._handlers.get(cmd.name)
        if handler is None:
            raise RuntimeError(f"no handler registered for command: {cmd.name!r}")

        return handler(args=args or {}, flags=flags or {}, definition=cmd)

    # --- Introspection ---------------------------------------------------------

    @property
    def command_names(self) -> list[str]:
        return sorted(self.commands)

    def __len__(self) -> int:
        return len(self.commands)

    def __contains__(self, name: str) -> bool:
        return name in self.commands


__all__ = [
    "CommandArgument",
    "CommandConfig",
    "CommandDefinition",
    "CommandFlag",
    "SlashCommandRegistry",
    "fuzzy_match",
    "fuzzy_match_commands",
    "load_commands_from_directories",
    "load_commands_from_yaml",
]
