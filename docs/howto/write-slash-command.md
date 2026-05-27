---
title: Write a slash command
description: Register a custom /command that shows up in /help, in tab completion, and in the HUD's recent line.
---

# Write a slash command <span class="lyra-badge intermediate">intermediate</span>

Slash commands are out-of-band actions: they bypass the model and run
Python directly. Lyra has a **unified command registry** so a command
you register from a plugin lights up everywhere — `/help`, the
completer, the HUD, the audit log — automatically.

## The registry

Source: [`lyra_cli/commands/registry.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-cli/src/lyra_cli/commands/registry.py).

```python
@dataclass(frozen=True)
class CommandSpec:
    name: str
    handler: SlashHandler
    description: str
    category: str
    aliases: tuple[str, ...] = ()
    args_hint: str = ""
    subcommands: tuple[str, ...] = ()
```

A `CommandSpec` is the single source of truth for everything the CLI
needs to know about a command. Once registered, the completer, the
help menu, and the HUD pick it up automatically.

## A minimal command

```python title="my_plugin/commands/standup.py"
from lyra_cli.commands.registry import CommandSpec, register_command
from lyra_cli.interactive.context import SessionContext

def _standup_handler(ctx: SessionContext, *args: str) -> None:
    """Print yesterday/today/blockers from .lyra/standup.md."""
    standup = ctx.repo_path / ".lyra" / "standup.md"
    if not standup.exists():
        ctx.print_warning("no standup file at .lyra/standup.md")
        return
    ctx.print_markdown(standup.read_text())

register_command(CommandSpec(
    name="standup",
    handler=_standup_handler,
    description="Show today's standup notes from .lyra/standup.md",
    category="session",
    aliases=("s", "su"),
    args_hint="",
))
```

That's it. After your plugin is loaded:

```
❯ /standup
# Standup notes — 2026-05-01

- yesterday: shipped the HUD
- today: finish the docs site
- blockers: none
```

`/help` lists `standup` under `session`, tab completion offers it on
`/s` and `/su`, and the HUD shows it in the "recent commands" widget.

## Categories

The registry groups commands into 12 categories, displayed in `/help`:

| Category | Purpose |
|---|---|
| `session` | Status, save, exit, resume |
| `plan-build-run` | Mode + execution flow |
| `tools-agents` | Direct tool calls + subagents |
| `observability` | Trace, logs, HIR |
| `config-theme` | Settings + theming |
| `collaboration` | Team / shared workflows |
| `meta` | Commands that operate on commands |
| `skill` | Skill catalogue management |
| `mcp` | MCP server management |
| `plugin` | Plugin lifecycle |
| `tdd` | TDD gate controls |
| `hud` | HUD presets and previews |

Pick the one that fits; if none does, add a new one to
`_CATEGORY_DISPLAY` in the registry.

## Argument-bearing commands

```python
def _grep_handler(ctx: SessionContext, *args: str) -> None:
    if not args:
        ctx.print_warning("usage: /grep <pattern> [path]")
        return
    pattern = args[0]
    path = args[1] if len(args) > 1 else "."
    ctx.run_tool("grep", pattern=pattern, path=path)

register_command(CommandSpec(
    name="grep",
    handler=_grep_handler,
    description="ripgrep across the workspace",
    category="tools-agents",
    args_hint="<pattern> [path]",
))
```

`args_hint` shows in `/help <name>` and in tab completion as a
trailing hint after you type `/grep `.

## Sub-commanded commands

```python
register_command(CommandSpec(
    name="skill",
    handler=_skill_dispatcher,
    description="Manage skills",
    category="skill",
    args_hint="<subcommand>",
    subcommands=("list", "add", "remove", "smoke", "curator-report"),
))
```

The completer uses `subcommands` to offer `/skill list`, `/skill add`,
etc. after you type `/skill `.

## Pipe-substitution patterns

If your command interpolates from the current selection (`%file`,
`%selection`, `%line`), the registry has `_PIPE_SUBS_RE` and
`_extract_subs` helpers. The completer will refuse to suggest the
command if a required substitution isn't satisfiable.

## Where commands actually register

Command registration is **lazy and side-effecting**. Two paths:

1. **Built-in commands** — registered by
   `lyra_cli.interactive.session._populate_canonical_registry()` on
   first import.
2. **Plugin commands** — call `register_command(...)` from your
   plugin's `__init__.py`. The plugin loader imports plugins on
   `SESSION_START`, which in turn registers all your commands.

To verify your command is in the registry without launching a
session:

```python
from lyra_cli.commands.registry import COMMAND_REGISTRY, commands_by_category

print({c.name: c.category for c in COMMAND_REGISTRY})
print(commands_by_category()["skill"])
```

## Tests for slash commands

The slash test suite is in
`packages/lyra-cli/tests/test_command_registry_unified.py`. The
canonical assertion every command should be able to satisfy:

```python
def test_my_command_registered():
    spec = next((c for c in COMMAND_REGISTRY if c.name == "standup"), None)
    assert spec is not None
    assert spec.category == "session"
    assert spec.handler is not None
```

[← Write a skill](write-skill.md){ .md-button }
[Configure providers →](configure-providers.md){ .md-button .md-button--primary }
