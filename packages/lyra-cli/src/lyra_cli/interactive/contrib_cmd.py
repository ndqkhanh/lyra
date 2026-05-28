"""ECC-inspired /contrib command — PR conventions, quality gates, review checklist.

Brings ECC's structured CONTRIBUTING.md into the Lyra REPL as a
slash command with quality-gate automation.

Usage:
  /contrib                — show summary
  /contrib pr             — PR title conventions
  /contrib commits         — conventional commit guide
  /contrib review          — review checklist
  /contrib gates           — quality gates & CI expectations
  /contrib changelog       — changelog expectations
"""
from __future__ import annotations

from typing import Any

from ..commands.registry import CommandResult

# ── ECC-inspired quality sections ──────────────────────────────────────

SECTIONS = {
    "pr": {
        "title": "PR Conventions",
        "glyph": "🔀",
        "lines": [
            "Use [accent]imperative mood[/] in PR titles",
            "Prefix with conventional commit type: [accent]feat[/], [accent]fix[/], [accent]refactor[/], etc.",
            "Include the issue/feature number when applicable",
            "Keep PRs focused: one logical change per PR",
            "Examples:",
            "  [dim]feat(ux): add context-aware suggestions panel[/]",
            "  [dim]fix(cli): handle empty session edge case[/]",
            "  [dim]refactor(hud): extract preset loader[/]",
        ],
    },
    "commits": {
        "title": "Conventional Commits",
        "glyph": "📝",
        "lines": [
            "Format: [accent]<type>(<scope>): <description>[/]",
            "",
            "Types:",
            "  [accent]feat[/]       — new feature",
            "  [accent]fix[/]        — bug fix",
            "  [accent]refactor[/]   — code change without fix/feature",
            "  [accent]docs[/]       — documentation only",
            "  [accent]test[/]       — adding/updating tests",
            "  [accent]perf[/]       — performance improvement",
            "  [accent]chore[/]      — maintenance, deps, tooling",
            "  [accent]style[/]      — formatting, linting",
            "",
            "Scopes: [dim]ux, cli, tui, hud, commands, tests, docs[/]",
        ],
    },
    "review": {
        "title": "Review Checklist",
        "glyph": "🔬",
        "lines": [
            "[green]☐[/] Does the code compile without errors?",
            "[green]☐[/] Are new tests included?",
            "[green]☐[/] Do existing tests pass?",
            "[green]☐[/] Are UI changes covered by smoke tests?",
            "[green]☐[/] Are error paths handled?",
            "[green]☐[/] Is the change documented (docstrings)?",
            "[green]☐[/] Are side effects considered?",
            "[green]☐[/] Is the diff minimal (no unrelated changes)?",
        ],
    },
    "gates": {
        "title": "Quality Gates",
        "glyph": "⚡",
        "lines": [
            "1. [green]Compilation[/]  — all .py files must compile (py_compile)",
            "2. [green]Tests[/]        — pytest suite must pass",
            "3. [green]Lint[/]         — ruff / pylint — no new errors",
            "4. [green]Coverage[/]     — new code should have tests",
            "5. [green]Commits[/]      — conventional commit format",
            "6. [green]Changelog[/]    — /changelog reflects changes",
        ],
    },
    "changelog": {
        "title": "Changelog",
        "glyph": "📋",
        "lines": [
            "Run [accent]/changelog[/] before opening a PR",
            "Group entries by conventional commit type",
            "Use [accent]/changelog --append CHANGELOG.md[/]",
            "Follow existing format in CHANGELOG.md",
        ],
    },
}


def cmd_contrib(session: Any, args: str) -> CommandResult:
    """ECC-style contributing guide with quality gates.

    Usage:
      /contrib              — overview
      /contrib pr           — PR conventions
      /contrib commits      — conventional commit guide
      /contrib review        — review checklist
      /contrib gates         — quality gates & CI expectations
    """
    parts = args.strip().split() if args.strip() else []
    topic = parts[0].lower() if parts else "overview"

    if topic == "overview":
        lines = [
            "[bold]Contributing to Lyra[/]",
            "  [accent]/contrib pr[/]         — PR title conventions",
            "  [accent]/contrib commits[/]     — Conventional commit guide",
            "  [accent]/contrib review[/]      — Review checklist",
            "  [accent]/contrib gates[/]       — Quality gates",
            "  [accent]/contrib changelog[/]   — Changelog expectations",
            "",
            "[dim]Inspired by ECC's structured CONTRIBUTING.md standard.[/]",
        ]
        return CommandResult(
            message="Contributing guide: /contrib [pr|commits|review|gates|changelog]",
            renderable="\n".join(lines),
        )

    section = SECTIONS.get(topic)
    if not section:
        valid = ", ".join(SECTIONS)
        return CommandResult(message=f"Unknown topic '{topic}'. Try: {valid}")

    lines = [f"[bold]{section['glyph']} {section['title']}[/]\n"]
    for line in section["lines"]:
        lines.append(f"  {line}")

    return CommandResult(
        message=f"{section['title']}: {len(section['lines'])} items",
        renderable="\n".join(lines),
    )


__all__ = ["cmd_contrib"]
