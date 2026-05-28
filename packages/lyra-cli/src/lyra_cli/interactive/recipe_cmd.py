"""ECC-inspired /recipe command — concrete, runnable workflow recipes.

ECC's "Common Workflows" are structured procedures that generate real
files (Add Feature, Create New Command, Add Cross Harness Skill Copies,
Sync Catalog Counts). This brings the same pattern to Lyra.

Recipes produce scaffolded file output and step-by-step instructions.

Usage:
  /recipe list                        — list available recipes
  /recipe show <name>                 — show recipe steps
  /recipe run <name> [--dry-run]      — execute a recipe (scaffold files)
  /recipe run <name> [--dir <path>]   — run in specific directory
"""
from __future__ import annotations

import textwrap
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..commands.registry import CommandResult

# ── Recipe definition ──────────────────────────────────────────────────

@dataclass
class RecipeFile:
    """A file to be created by a recipe."""
    path: str        # Relative path template
    content: str     # File content template
    overwrite: bool = False


@dataclass
class Recipe:
    """A concrete, runnable workflow recipe."""
    name: str
    description: str
    steps: list[str]
    files: list[RecipeFile] = field(default_factory=list)
    variables: dict[str, str] = field(default_factory=dict)

    @property
    def summary(self) -> str:
        return f"[accent]{self.name}[/]  [dim]— {self.description}[/]  ({len(self.steps)} steps, {len(self.files)} files)"


# ── Built-in recipes ──────────────────────────────────────────────────

def _scaffold_new_command(name: str) -> list[RecipeFile]:
    """Generate files for a new slash command."""
    return [
        RecipeFile(
            path=f"packages/lyra-cli/src/lyra_cli/interactive/{name}_cmd.py",
            content=textwrap.dedent(f'''\
                \"\"\"``/{name}`` — auto-generated command.

                Usage:
                  /{name}              — default action
                  /{name} list         — list items
                  /{name} show <id>    — show item by id
                \"\"\"
                from __future__ import annotations

                from typing import Any

                from ..commands.registry import CommandResult


                def cmd_{name}(session: Any, args: str) -> CommandResult:
                    \"\"\"Auto-generated {name} command.\"\"\"
                    parts = args.strip().split() if args.strip() else []
                    subcmd = parts[0].lower() if parts else "help"

                    if subcmd == "help":
                        return CommandResult(
                            output=f"/{name}: default output"
                        )

                    return CommandResult(
                        output=f"/{name}: unknown subcommand '{{subcmd}}'"
                    )


                __all__ = ["cmd_{name}"]
            '''),
            overwrite=False,
        ),
        RecipeFile(
            path=f"packages/lyra-cli/tests/test_{name}_cmd.py",
            content=textwrap.dedent(f'''\
                \"\"\"Tests for /{name} command.\"\"\"
                from __future__ import annotations

                import pytest

                from lyra_cli.interactive.{name}_cmd import cmd_{name}


                class FakeSession:
                    pass


                def test_{name}_default():
                    result = cmd_{name}(FakeSession(), "")
                    assert result is not None
                    assert "default" in result.output
            '''),
            overwrite=False,
        ),
    ]


def _scaffold_new_widget(name: str) -> list[RecipeFile]:
    """Generate files for a new TUI widget."""
    class_name = "".join(x.title() for x in name.split("_")) + "Widget"
    return [
        RecipeFile(
            path=f"packages/lyra-cli/src/lyra_cli/tui_v2/widgets/{name}.py",
            content=textwrap.dedent(f'''\
                \"\"\"{class_name} — auto-generated widget.

                Toggle with Ctrl+Shift+<key>.
                \"\"\"
                from __future__ import annotations

                from textual.app import ComposeResult
                from textual.binding import Binding
                from textual.reactive import reactive
                from textual.widget import Widget
                from textual.widgets import Static


                class {class_name}(Widget):
                    \"\"\"Auto-generated widget.\"\"\"

                    DEFAULT_CSS = """
                    {class_name} {{
                        height: auto;
                        border: solid $border;
                        padding: 0 1;
                        margin: 0 1;
                    }}

                    {class_name}.collapsed {{
                        height: 1;
                        border: none;
                    }}

                    {class_name} #w-header {{
                        height: 1;
                        color: $text-muted;
                    }}

                    {class_name} #w-content {{
                        height: auto;
                        margin: 0 0 0 1;
                    }}
                    """

                    BINDINGS = [
                        Binding("ctrl+shift+?", "toggle_widget", "Toggle"),
                    ]

                    expanded: reactive[bool] = reactive(False)

                    def compose(self) -> ComposeResult:
                        yield Static("", id="w-header")
                        yield Static("", id="w-content")

                    def on_mount(self) -> None:
                        self._render()

                    def action_toggle_widget(self) -> None:
                        self.expanded = not self.expanded
                        self.toggle_class("collapsed", not self.expanded)
                        self._render()

                    def _render(self) -> None:
                        if not self.is_mounted:
                            return
                        try:
                            self.query_one("#w-header", Static).update(
                                f"[bold]{class_name}[/] [dim](ctrl+shift+?)[/]"
                            )
                            if self.expanded:
                                self.query_one("#w-content", Static).update(
                                    "  [dim]Widget content here[/]"
                                )
                            else:
                                self.query_one("#w-content", Static).update("")
                        except Exception:
                            pass
            '''),
            overwrite=False,
        ),
    ]


# ── Recipe registry ───────────────────────────────────────────────────

_RECIPES: dict[str, Recipe] = {
    "new-command": Recipe(
        name="new-command",
        description="Scaffold a new slash command with tests",
        steps=[
            "1. Define command name and basic syntax",
            "2. Create command module in interactive/",
            "3. Write tests in tests/",
            "4. Register command in session.py COMMAND_REGISTRY",
            "5. Add completions in completer.py",
            "6. Add help entry in help_cmd.py",
        ],
        variables={"name": "command name (snake_case)"},
    ),
    "new-widget": Recipe(
        name="new-widget",
        description="Scaffold a new TUI widget with keybinding",
        steps=[
            "1. Define widget name and CSS layout",
            "2. Create widget module in tui_v2/widgets/",
            "3. Add export in widgets/__init__.py",
            "4. Wire keybinding in app.py BINDINGS",
            "5. Import and init widget in app.py __init__",
            "6. Add action handler in app.py",
        ],
        variables={"name": "widget name (snake_case)"},
    ),
    "new-recipe": Recipe(
        name="new-recipe",
        description="Create a new workflow recipe",
        steps=[
            "1. Define recipe name and description",
            "2. List execution steps",
            "3. Define file templates with scaffold functions",
            "4. Register recipe in _RECIPES dict",
            "5. Test with /recipe run <name> --dry-run",
        ],
        variables={"name": "recipe name (kebab-case)"},
    ),
    "add-feature": Recipe(
        name="add-feature",
        description="Full feature implementation (ECC Add Feature workflow)",
        steps=[
            "1. Specification — define requirements & acceptance criteria",
            "2. Design — architecture & interface design",
            "3. Implementation — write the implementation",
            "4. Testing — write & run tests",
            "5. Review — self-review & polish",
            "6. Documentation — update docs & changelog",
        ],
    ),
    "add-cross-harness": Recipe(
        name="add-cross-harness",
        description="Port skill/config across agent harnesses (ECC Add Cross Harness Skill Copies)",
        steps=[
            "1. Copy SKILL.md to .agents/skills/<name>/SKILL.md",
            "2. Copy SKILL.md to .cursor/skills/<name>/SKILL.md",
            "3. Optionally add harness-specific openai.yaml",
            "4. Address review feedback",
        ],
    ),
}

# Scaffold function registry
_SCAFFOLD_FN: dict[str, Callable[[str], list[RecipeFile]]] = {
    "new-command": _scaffold_new_command,
    "new-widget": _scaffold_new_widget,
}


# ── Command handler ───────────────────────────────────────────────────

def cmd_recipe(session: Any, args: str) -> CommandResult:
    """Concrete, runnable workflow recipes with file scaffolding.

    Usage:
      /recipe list                — list available recipes
      /recipe show <name>         — show recipe steps
      /recipe run <name>          — execute recipe (scaffold files)
      /recipe run <name> --dry-run — preview without writing
    """
    parts = args.strip().split() if args.strip() else []
    subcmd = parts[0].lower() if parts else "list"

    # ── /recipe list ─────────────────────────────────────────────────
    if subcmd == "list":
        if not _RECIPES:
            return CommandResult(output="No recipes available.")

        lines = ["[bold]Available Recipes[/]\n"]
        for name, recipe in sorted(_RECIPES.items()):
            has_scaffold = " [green]✦ scaffolds[/]" if name in _SCAFFOLD_FN else ""
            lines.append(f"  {recipe.summary}{has_scaffold}")
        return CommandResult(
            output=f"Recipes: {', '.join(_RECIPES.keys())}",
            renderable="\n".join(lines),
        )

    # ── /recipe show <name> ──────────────────────────────────────────
    if subcmd == "show":
        if len(parts) < 2:
            return CommandResult(output="Usage: /recipe show <name>")
        recipe_name = parts[1]
        recipe = _RECIPES.get(recipe_name)
        if not recipe:
            return CommandResult(output=f"Unknown recipe '{recipe_name}'. Try /recipe list")

        lines = [
            f"[bold]{recipe.name}[/]  [dim]— {recipe.description}[/]",
            "",
            "[bold]Steps:[/]",
        ]
        for step in recipe.steps:
            lines.append(f"  {step}")

        if recipe.files:
            lines.append("")
            lines.append("[bold]Files:[/]")
            for f in recipe.files:
                lines.append(f"  [dim]{f.path}[/]")

        if recipe.variables:
            lines.append("")
            lines.append("[bold]Variables:[/]")
            for k, v in recipe.variables.items():
                lines.append(f"  [accent]{k}[/]  [dim]{v}[/]")

        return CommandResult(
            output=f"Recipe: {recipe.name} ({len(recipe.steps)} steps)",
            renderable="\n".join(lines),
        )

    # ── /recipe run <name> [--dry-run] [--dir <path>] ────────────────
    if subcmd == "run":
        if len(parts) < 2:
            return CommandResult(output="Usage: /recipe run <name> [--dry-run]")

        recipe_name = parts[1]
        recipe = _RECIPES.get(recipe_name)
        if not recipe:
            return CommandResult(output=f"Unknown recipe '{recipe_name}'. Try /recipe list")

        dry_run = "--dry-run" in parts or "-n" in parts
        target_dir = Path.cwd()

        # Extract --dir if provided
        for i, p in enumerate(parts):
            if p == "--dir" and i + 1 < len(parts):
                target_dir = Path(parts[i + 1])

        lines = [
            f"[bold]Running: {recipe.name}[/]  [dim]{'[DRY RUN]' if dry_run else ''}[/]",
            f"  [dim]Target: {target_dir}[/]",
            "",
        ]

        # If there's a scaffold function, run it
        scaffold_fn = _SCAFFOLD_FN.get(recipe_name)
        if scaffold_fn:
            var_name = recipe_name.replace("new-", "").replace("-", "_")
            generated = scaffold_fn(var_name)
            recipe.files = generated

        if recipe.files:
            for rf in recipe.files:
                full_path = target_dir / rf.path
                exists = full_path.exists()
                if exists and not rf.overwrite:
                    lines.append(f"  [yellow]⚠[/] {rf.path}  [dim](exists, skipped)[/]")
                    continue

                if dry_run:
                    lines.append(f"  [green]✦[/] {rf.path}  [dim]({len(rf.content)} chars)[/]")
                else:
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    full_path.write_text(rf.content)
                    verb = "overwrote" if exists else "created"
                    lines.append(f"  [green]✓[/] {rf.path}  [dim]({verb})[/]")
        else:
            lines.append("  [dim](no files to scaffold)[/]")

        lines.append("")
        lines.append("[bold]Steps:[/]")
        for step in recipe.steps:
            lines.append(f"  {step}")

        if dry_run:
            lines.append("")
            lines.append("[yellow]⚠ Dry run — no files written. Run without --dry-run to execute.[/]")

        return CommandResult(
            output=f"Recipe '{recipe_name}': {len([f for f in recipe.files])} files, {len(recipe.steps)} steps",
            renderable="\n".join(lines),
        )

    return CommandResult(output="Usage: /recipe [list|show|run]")


__all__ = ["cmd_recipe", "Recipe", "RecipeFile", "_RECIPES"]
