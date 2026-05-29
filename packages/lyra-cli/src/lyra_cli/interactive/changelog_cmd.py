"""ECC-inspired /changelog command — auto-generate changelog & release notes.

Scans the git log between two refs and generates structured changelog
entries grouped by Conventional Commit prefix (feat, fix, docs, etc).

Usage:
  /changelog                    — changelog since last tag
  /changelog --since <ref>      — changelog since specific ref
  /changelog --to <ref>         — changelog up to specific ref
  /changelog --range <a>..<b>   — changelog in range
  /changelog --last <N>         — last N commits
  /changelog --append <file>    — append to existing CHANGELOG.md
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from ..commands.registry import CommandResult

# ── Category definitions (ECC Conventional Commit prefixes) ────────────

CATEGORIES: list[tuple[str, str, str]] = [
    ("feat", "Features", "✨"),
    ("fix", "Bug Fixes", "🐛"),
    ("docs", "Documentation", "📚"),
    ("feat(ux)", "UI/UX", "🎨"),
    ("perf", "Performance", "⚡"),
    ("test", "Testing", "🧪"),
    ("refactor", "Refactoring", "♻"),
    ("style", "Style", "💄"),
    ("chore", "Chores", "🔧"),
    ("ci", "CI", "🤖"),
    ("build", "Build", "📦"),
    ("revert", "Reverts", "⏪"),
    ("merge", "Merges", "🔀"),
]

# Fallback for uncategorized
_CATEGORY_FALLBACK = ("other", "Other Changes", "📋")


def _classify(commit_msg: str) -> tuple[str, str, str]:
    """Classify a commit message into a category."""
    for prefix, label, emoji in CATEGORIES:
        if commit_msg.startswith(prefix):
            return prefix, label, emoji
    return _CATEGORY_FALLBACK


def _run_git_log(since: str = "", to: str = "HEAD", max_count: int = 0) -> list[str]:
    """Run git log and return list of commit messages."""
    args = ["git", "log", "--format=%s", "--no-merges"]
    if since:
        args.append(f"{since}..{to}")
    if max_count:
        args.append(f"-{max_count}")
    args.append("--")

    try:
        result = subprocess.run(
            args, capture_output=True, text=True, timeout=15, cwd=Path.cwd(),
        )
        return [line.strip() for line in result.stdout.split("\n") if line.strip()]
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []


def _get_last_tag() -> str:
    """Get the most recent git tag."""
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            capture_output=True, text=True, timeout=10, cwd=Path.cwd(),
        )
        return result.stdout.strip() or ""
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""


def _generate_changelog(commits: list[str]) -> str:
    """Generate a changelog section from commit messages."""
    if not commits:
        return "[dim]No commits found.[/]"

    # Group by category
    grouped: dict[str, list[str]] = {}
    for msg in commits:
        _, label, emoji = _classify(msg)
        if label not in grouped:
            grouped[label] = []
        grouped[label].append(msg)

    lines: list[str] = []
    for label, emoji, _ in CATEGORIES:
        msgs = grouped.pop(label, [])
        if not msgs:
            continue
        lines.append(f"[bold]{emoji} {label}[/]")
        for msg in msgs[:10]:
            # Strip the prefix for display
            display = msg.split(":", 1)[-1].strip() if ":" in msg else msg
            lines.append(f"  • {display[:72]}")
        if len(msgs) > 10:
            lines.append(f"  [dim]… +{len(msgs) - 10} more[/]")
        lines.append("")

    # Remaining uncategorized
    for label, msgs in grouped.items():
        lines.append(f"[bold]{label}[/]")
        for msg in msgs[:10]:
            lines.append(f"  • {msg[:72]}")
        if len(msgs) > 10:
            lines.append(f"  [dim]… +{len(msgs) - 10} more[/]")

    return "\n".join(lines)


def _append_to_file(changelog_text: str, filepath: str) -> str:
    """Append changelog content to a file."""
    path = Path(filepath)
    try:
        if path.exists():
            existing = path.read_text()
            # Insert after first heading or at top
            new_content = changelog_text + "\n\n" + existing
        else:
            new_content = changelog_text
        path.write_text(new_content)
        return f"✓ Appended to {filepath} ({len(changelog_text)} chars)"
    except Exception as e:
        return f"[red]✗[/] Error writing {filepath}: {e}"


# ── Command handler ────────────────────────────────────────────────────

def cmd_changelog(session: Any, args: str) -> CommandResult:
    """Generate changelog/release notes from git history.

    Usage:
      /changelog                    — changelog since last tag
      /changelog --since <ref>      — since specific ref
      /changelog --to <ref>         — up to specific ref
      /changelog --range <a>..<b>   — range
      /changelog --last <N>         — last N commits
      /changelog --append <file>    — append to CHANGELOG.md
    """
    parts = args.strip().split() if args.strip() else []
    append_file: str | None = None
    since = ""
    to = "HEAD"
    max_count = 0

    # Parse flags
    i = 0
    while i < len(parts):
        p = parts[i]
        if p == "--since" and i + 1 < len(parts):
            since = parts[i + 1]
            i += 2
        elif p == "--to" and i + 1 < len(parts):
            to = parts[i + 1]
            i += 2
        elif p == "--range" and i + 1 < len(parts):
            if ".." in parts[i + 1]:
                since, to = parts[i + 1].split("..", 1)
            i += 2
        elif p == "--last" and i + 1 < len(parts):
            try:
                max_count = int(parts[i + 1])
            except ValueError:
                pass
            i += 2
        elif p == "--append" and i + 1 < len(parts):
            append_file = parts[i + 1]
            i += 2
        else:
            i += 1

    # Default: use last tag as anchor
    if not since and not max_count:
        tag = _get_last_tag()
        if tag:
            since = tag
        else:
            max_count = 20

    # Fetch commits
    commits = _run_git_log(since=since, to=to, max_count=max_count)
    if not commits:
        return CommandResult(
            output="No commits found. Make sure you're in a git repository."
        )

    # Generate changelog
    header = f"[bold]Changelog[/]  [dim]{since or 'beginning'}..{to}[/]  ({len(commits)} commits)"
    changelog_text = _generate_changelog(commits)

    # Handle --append
    append_result = ""
    if append_file:
        # Strip Rich markup for file output
        plain_lines = []
        for line in changelog_text.split("\n"):
            plain_lines.append(line.replace("[bold]", "").replace("[/]", "")
                               .replace("[dim]", ""))
        plain = "\n".join(plain_lines)
        append_result = "\n" + _append_to_file(plain, append_file)

    return CommandResult(
        output=f"{len(commits)} commits ({since or 'beginning'}..{to}){append_result}",
        renderable=f"{header}\n\n{changelog_text}",
    )


__all__ = ["cmd_changelog"]
