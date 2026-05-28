"""ECC-inspired interactive help surface for the Lyra REPL.

Provides a rich categorized command reference that mirrors ECC's
everything-claude-code command surface — commands grouped by category,
with aliases, usage hints, and quick-search.

Exposes two entry points:
  • ``cmd_help_enhanced()`` — slash handler replacing /help
  • ``show_workflow_reference()`` — focused /workflow subcommand ref

ECC reference: everything-claude-code's command/feature-development.md +
database-migration.md + add-language-rules.md structured command docs.
"""
from __future__ import annotations

from typing import Any

from ..commands.registry import CommandResult, commands_by_category

# ── ECC-inspired command categories with emoji ─────────────────────────

CATEGORY_EMOJI = {
    "session": "💬",
    "mode": "🎯",
    "model": "🧠",
    "workflow": "📋",
    "research": "🔍",
    "memory": "💾",
    "skills": "🔧",
    "tools": "🛠",
    "debug": "🐛",
    "admin": "⚙",
    "mcp": "🔌",
    "system": "⚡",
    "output": "📝",
    "navigation": "🧭",
    "help": "❓",
}

# ECC-style quick-reference cheatsheet
QUICK_REFERENCE = [
    ("💬", "/mode", "agent | plan | debug | ask", "Switch interaction mode"),
    ("🧠", "/model", "<name>", "Switch LLM model"),
    ("📋", "/workflow", "start | next | status", "Structured task workflow"),
    ("🔍", "/research", "<topic>", "Deep multi-source research"),
    ("🔧", "/skills", "list | search | install", "Manage skills"),
    ("💾", "/memory", "save | search | clear", "Manage session memory"),
    ("💬", "/status", "", "Session health overview"),
    ("🧭", "/history", "[--verbose]", "Session history"),
    ("🐛", "/undo", "[--diff] [N]", "Undo recent change"),
    ("⚡", "/compact", "", "Compress context window"),
    ("🛠", "/tools", "", "Available tool list"),
    ("🔌", "/mcp", "list | add | remove", "MCP server management"),
    ("⚙", "/config", "set | get | list", "Configuration"),
    ("❓", "/help", "[topic]", "Command reference"),
]


def cmd_help_enhanced(session: Any, args: str) -> CommandResult:
    """Enhanced categorized help — ECC-style command reference.

    Usage:
      /help            — categorized overview of all commands
      /help <command>  — detailed help for one command
      /help --quick    — compact cheatsheet
    """
    parts = args.strip().split() if args.strip() else []

    # ── Detail for one command ─────────────────────────────────────────
    if parts and parts[0] not in ("--quick", "-q", "--categories", "-c"):
        topic = parts[0]
        by_cat = commands_by_category()
        for cat, specs in by_cat.items():
            for spec in specs:
                if spec.name == topic or topic in spec.aliases:
                    emoji = CATEGORY_EMOJI.get(spec.category, "📋")
                    alias_str = f" [dim](aliases: {', '.join(spec.aliases)})[/]" if spec.aliases else ""
                    hint = f" [dim]{spec.args_hint}[/]" if spec.args_hint else ""
                    return CommandResult(
                        output=f"{spec.name}: {spec.description}",
                        renderable=(
                            f"[bold]{emoji} /{spec.name}{hint}[/]{alias_str}\n"
                            f"[dim]{spec.description}[/]\n"
                            f"[dim]category: {spec.category}[/]"
                        ),
                    )
        return CommandResult(output=f"Unknown command: /{topic}")

    # ── Quick cheatsheet ───────────────────────────────────────────────
    if parts and parts[0] in ("--quick", "-q"):
        lines = ["[bold]Lyra Quick Reference[/]"]
        for emoji, cmd, args_hint, desc in QUICK_REFERENCE:
            cmd_col = f"[accent]/{cmd:<12}[/]"
            hint_col = f"[dim]{args_hint:<20}[/]" if args_hint else " " * 20
            lines.append(f"  {emoji}  {cmd_col} {hint_col} {desc}")
        return CommandResult(
            output="Lyra quick reference (" + ", ".join(cmd for _, cmd, _, _ in QUICK_REFERENCE[:8]) + ")",
            renderable="\n".join(lines),
        )

    # ── Categorized overview ───────────────────────────────────────────
    by_cat = commands_by_category()
    # Sort by predefined category order
    cat_order = ["session", "mode", "model", "workflow", "research", "memory",
                  "skills", "tools", "debug", "admin", "mcp", "system", "output", "help"]
    lines = ["[bold]Lyra Commands[/]  [dim]— categorized reference[/]\n"]

    for cat_name in cat_order:
        specs = by_cat.get(cat_name, [])
        if not specs:
            continue
        emoji = CATEGORY_EMOJI.get(cat_name, "📋")
        lines.append(f"[bold]{emoji}  {cat_name.title()}[/]")
        for spec in specs:
            alias_str = f" [dim]({', '.join(spec.aliases)})[/]" if spec.aliases else ""
            hint = f" [dim]{spec.args_hint}[/]" if spec.args_hint else ""
            lines.append(f"  [accent]/{spec.name:<12}[/]{hint:<22}{spec.description}{alias_str}")
        lines.append("")

    # Check remaining categories not in the ordered list
    for cat_name, specs in by_cat.items():
        if cat_name in cat_order:
            continue
        emoji = CATEGORY_EMOJI.get(cat_name, "📋")
        lines.append(f"[bold]{emoji}  {cat_name.title()}[/]")
        for spec in specs:
            hint = f" [dim]{spec.args_hint}[/]" if spec.args_hint else ""
            lines.append(f"  [accent]/{spec.name:<12}[/]{hint:<22}{spec.description}")
        lines.append("")

    lines.append("[dim]Tip: /help <command> for detail · /help --quick for compact · Tab to autocomplete[/]")

    return CommandResult(
        output=f"Lyra commands: {sum(len(v) for v in by_cat.values())} commands in {len(by_cat)} categories",
        renderable="\n".join(lines),
    )


def show_workflow_reference() -> str:
    """Return formatted /workflow subcommand reference.

    Called by /help workflow and /workflow --help.
    """
    return (
        "[bold]📋  /workflow — Structured Task Workflow[/]\n\n"
        "  /workflow list              List available workflow templates\n"
        "  /workflow start <name>      Start a new workflow\n"
        "  /workflow status            Show current workflow progress\n"
        "  /workflow next              Advance to next step\n"
        "  /workflow step [N]          Jump to step N\n"
        "  /workflow done              Mark current step complete\n"
        "  /workflow note <text>       Add note to current step\n"
        "  /workflow cancel            Cancel active workflow\n\n"
        "[dim]Templates: feature, bugfix, research, migration, review[/]"
    )


__all__ = ["cmd_help_enhanced", "show_workflow_reference", "QUICK_REFERENCE"]
