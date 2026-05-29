"""HandoffWidget + /handoff command — generate paste-able PR descriptions.

Ports the 125-line handoff.py renderer into both a TUI widget and a
REPL slash command:
  • /handoff         — render PR description from session state
  • /handoff --copy  — render and copy to clipboard
  • /handoff --save <file> — render and save to file
  • HandoffWidget    — TUI preview panel (Ctrl+Shift+H)

ECC reference: structured handoff documentation for PR creation.
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static

from ..commands.registry import CommandResult


@dataclass
class HandoffContent:
    """A generated handoff/PR description."""
    title: str = ""
    summary: str = ""
    changes: list[str] = field(default_factory=list)
    test_plan: list[str] = field(default_factory=list)
    files_changed: int = 0
    warnings: list[str] = field(default_factory=list)

    def render(self) -> str:
        lines = [
            f"[bold]{self.title}[/]",
        ]
        if self.summary:
            lines.append(f"  {self.summary[:120]}")
        if self.changes:
            lines.append("")
            lines.append("[bold]Changes[/]")
            for c in self.changes[:5]:
                lines.append(f"  • {c[:80]}")
            if len(self.changes) > 5:
                lines.append(f"  [dim]… +{len(self.changes) - 5} more[/]")
        if self.test_plan:
            lines.append("")
            lines.append("[bold]Test Plan[/]")
            for t in self.test_plan[:5]:
                lines.append(f"  • {t[:80]}")
        if self.warnings:
            lines.append("")
            for w in self.warnings:
                lines.append(f"  [yellow]⚠[/] {w[:80]}")
        return "\n".join(lines)

    def render_plain(self) -> str:
        """Render without Rich markup for file/clipboard output."""
        lines = [self.title, ""]
        if self.summary:
            lines.append(self.summary)
        if self.changes:
            lines.append("")
            lines.append("## Changes")
            for c in self.changes:
                lines.append(f"- {c}")
        if self.test_plan:
            lines.append("")
            lines.append("## Test Plan")
            for t in self.test_plan:
                lines.append(f"- {t}")
        if self.warnings:
            lines.append("")
            lines.append("## Notes")
            for w in self.warnings:
                lines.append(f"> {w}")
        return "\n".join(lines)


# ── Git helpers ────────────────────────────────────────────────────────

def _git_diff_stat() -> str:
    try:
        r = subprocess.run(["git", "diff", "--stat"], capture_output=True, text=True, timeout=10)
        return r.stdout.strip()
    except Exception:
        return ""


def _git_log_recent(count: int = 5) -> list[str]:
    try:
        r = subprocess.run(
            ["git", "log", "--format=%s", f"-{count}", "--"],
            capture_output=True, text=True, timeout=10,
        )
        return [line.strip() for line in r.stdout.split("\n") if line.strip()]
    except Exception:
        return []


def _git_branch() -> str:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        return r.stdout.strip()
    except Exception:
        return ""


def _generate_handoff(session: Any = None) -> HandoffContent:
    """Generate handoff content from session state and git."""
    branch = _git_branch()
    commits = _git_log_recent()
    diff_stat = _git_diff_stat()

    files_changed = len([line for line in diff_stat.split("\n") if line.strip()]) if diff_stat else 0

    title = f"PR: {branch or 'current-branch'} — {commits[0] if commits else 'changeset'}"

    warnings = []
    if not diff_stat:
        warnings.append("No uncommitted changes found")
    if files_changed > 20:
        warnings.append(f"{files_changed} files changed — consider splitting")

    changes = []
    if diff_stat:
        for line in diff_stat.split("\n")[:8]:
            line = line.strip()
            if line:
                changes.append(line)

    test_plan = []
    turn_count = getattr(session, "turn_index", 0) if session else 0
    if turn_count > 0:
        test_plan.append(f"Run {turn_count} recorded test cases")
    test_plan.append("Verify with `pytest` or `npm test`")

    return HandoffContent(
        title=title,
        summary=f"Branch: {branch} · {files_changed} files · {len(commits)} recent commits",
        changes=changes,
        test_plan=test_plan,
        files_changed=files_changed,
        warnings=warnings,
    )


# ── Slash command ──────────────────────────────────────────────────────

def cmd_handoff(session: Any, args: str) -> CommandResult:
    """Generate a paste-able PR description.

    Usage:
      /handoff          — render PR description
      /handoff --copy   — copy to clipboard
      /handoff --save <file> — save to file
    """
    parts = args.strip().split() if args.strip() else []

    handoff = _generate_handoff(session)
    rich_renderable = handoff.render()
    plain = handoff.render_plain()

    copy_flag = "--copy" in parts or "-c" in parts
    save_file = None
    for i, p in enumerate(parts):
        if p in ("--save", "-s") and i + 1 < len(parts):
            save_file = parts[i + 1]

    result_msg = f"Handoff: {handoff.title[:60]}"

    if copy_flag:
        try:
            subprocess.run(
                ["pbcopy"], input=plain, text=True, timeout=5, capture_output=True,
            )
            result_msg += " (copied to clipboard)"
        except Exception:
            result_msg += " (clipboard unavailable)"

    if save_file:
        try:
            Path(save_file).write_text(plain)
            result_msg += f" (saved to {save_file})"
        except Exception as e:
            result_msg += f" (save error: {e})"

    return CommandResult(
        output=result_msg,
        renderable=rich_renderable,
    )


# ── TUI Widget ─────────────────────────────────────────────────────────

class HandoffWidget(Widget):
    """PR description preview — Ctrl+Shift+H to toggle.

    Shows: title, branch info, file changes, test plan, warnings.
    Auto-refreshes on toggle.
    """

    DEFAULT_CSS = """
    HandoffWidget {
        height: auto;
        border: solid $border;
        padding: 0 1;
        margin: 0 1;
    }

    HandoffWidget.collapsed {
        height: 1;
        border: none;
    }

    HandoffWidget #ho-header {
        height: 1;
        color: $text-muted;
    }

    HandoffWidget #ho-content {
        height: auto;
        max-height: 12;
        margin: 0 0 0 1;
    }
    """

    BINDINGS = [
        Binding("ctrl+shift+h", "toggle_handoff", "Handoff"),
    ]

    expanded: reactive[bool] = reactive(False)

    def compose(self) -> ComposeResult:
        yield Static("", id="ho-header")
        yield Static("", id="ho-content")

    def on_mount(self) -> None:
        self._render()

    def action_toggle_handoff(self) -> None:
        self.expanded = not self.expanded
        self.toggle_class("collapsed", not self.expanded)
        self._render()

    def _render(self) -> None:
        if not self.is_mounted:
            return
        try:
            hint = "[dim](ctrl+shift+h)[/]"
            handoff = _generate_handoff()
            if self.expanded:
                self.query_one("#ho-header", Static).update(
                    f"[bold]Handoff[/]  [dim]{handoff.files_changed} files[/]  {hint}"
                )
                self.query_one("#ho-content", Static).update(handoff.render())
            else:
                self.query_one("#ho-header", Static).update(
                    f"[bold]Handoff[/]  "
                    f"{handoff.title[:50]}  "
                    f"[dim]{len(handoff.changes)} changes[/]  {hint}"
                )
                self.query_one("#ho-content", Static).update("")
        except Exception:
            pass


__all__ = ["cmd_handoff", "HandoffWidget", "HandoffContent"]
