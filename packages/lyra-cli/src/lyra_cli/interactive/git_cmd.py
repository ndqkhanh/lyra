"""Git Integration Widget — status badges, /git slash commands, diff preview.

Ports lyra-ui/integration.py's GitIntegration into the Lyra REPL + TUI.
Provides:
  • /git status — Rich table of changed files
  • /git diff — file-level diff preview
  • /git commit — guided commit flow with conventional commit templates
  • /git log --oneline — last 10 commits
  • /git branch — branch overview
  • Status badge in the REPL status bar (branch, dirty count)
  • Auto-suggest commit messages from conventional commit patterns

ECC reference: ECC's everything-claude-code conventional commit conventions
(SKILL.md, instinct rules).
"""
from __future__ import annotations

import subprocess
import shlex
from pathlib import Path
from typing import Optional

from ..commands.registry import CommandResult


# ── Git helpers (pure) ─────────────────────────────────────────────────

def _run_git(args: list[str], cwd: Optional[Path] = None) -> tuple[str, str, int]:
    """Run a git command and return (stdout, stderr, exit_code)."""
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            timeout=15,
            cwd=cwd or Path.cwd(),
        )
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except FileNotFoundError:
        return "", "git not found", -1
    except subprocess.TimeoutExpired:
        return "", "git command timed out", -1


def get_branch(repo_root: Optional[Path] = None) -> str:
    """Get current branch name."""
    out, _, _ = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], repo_root)
    return out or "—"


def get_dirty_count(repo_root: Optional[Path] = None) -> int:
    """Count dirty (modified + untracked) files."""
    out, _, _ = _run_git(["status", "--porcelain"], repo_root)
    return len([l for l in out.split("\n") if l.strip()]) if out else 0


def is_detached(repo_root: Optional[Path] = None) -> bool:
    """Check if HEAD is detached."""
    out, _, _ = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], repo_root)
    return out == "HEAD"


def get_commits_ahead(repo_root: Optional[Path] = None) -> int:
    """Count commits ahead of remote."""
    out, _, ec = _run_git(["rev-list", "--count", "@{upstream}..HEAD", "--"], repo_root)
    return int(out) if out and ec == 0 else 0


def render_status_badge(repo_root: Optional[Path] = None) -> str:
    """Compact status badge for the REPL status bar."""
    branch = get_branch(repo_root)
    dirty = get_dirty_count(repo_root)
    ahead = get_commits_ahead(repo_root)

    parts = [f"[accent]{branch}[/]"]
    if dirty:
        parts.append(f"[yellow]✎ {dirty}[/]")
    if ahead:
        parts.append(f"[cyan]↑ {ahead}[/]")
    if is_detached(repo_root):
        parts.append("[red]detached[/]")

    return " ".join(parts)


def _rich_available() -> bool:
    try:
        from rich.console import Console  # noqa: F401
        from rich.table import Table  # noqa: F401
        return True
    except ImportError:
        return False


# ── Slash command handler ──────────────────────────────────────────────

def cmd_git(session: Any, args: str) -> CommandResult:
    """Git integration — status, diff, commit, log, branch.

    Usage:
      /git status            — show changed files
      /git diff [file]        — show unstaged diff
      /git diff --staged      — show staged diff
      /git log [--oneline]    — show commit history
      /git branch             — show branches
      /git commit <msg>       — commit staged changes
      /git commit --conventional <type> <msg>  — conventional commit
    """
    parts = shlex.split(args.strip()) if args.strip() else []
    subcmd = parts[0].lower() if parts else "status"
    repo_root = getattr(session, 'repo_root', Path.cwd()) if session else Path.cwd()

    # ── /git status ────────────────────────────────────────────────────
    if subcmd == "status":
        out, err, ec = _run_git(["status", "--short"], repo_root)
        if ec != 0:
            return CommandResult(output=f"git error: {err}")

        if not out:
            return CommandResult(output="✓ Working tree clean")

        lines = []
        for line in out.split("\n")[:30]:
            if not line.strip():
                continue
            xy = line[:2]
            path = line[3:]
            if "?" in xy:
                glyph = "[dim]?[/]"
            elif "M" in xy:
                glyph = "[yellow]M[/]"
            elif "A" in xy:
                glyph = "[green]A[/]"
            elif "D" in xy:
                glyph = "[red]D[/]"
            else:
                glyph = f"[dim]{xy[0]}[/]"
            lines.append(f"  {glyph} {path}")

        nlines = out.count("\n")
        if nlines > 30:
            remaining = nlines - 30
            lines.append(f"  [dim]… +{remaining} more[/]")

        # Also show branch info
        branch = get_branch(repo_root)
        ahead = get_commits_ahead(repo_root)
        header = f"[accent]On branch {branch}[/]"
        if ahead:
            header += f" · [cyan]{ahead} ahead[/]"

        return CommandResult(
            output=f"On branch {branch}: {len([l for l in out.split(chr(10)) if l.strip()])} changes",
            renderable=f"{header}\n" + "\n".join(lines) if _rich_available() else None,
        )

    # ── /git diff ──────────────────────────────────────────────────────
    if subcmd == "diff":
        diff_args = ["diff", "--color=never"]
        if len(parts) > 1 and parts[1] == "--staged":
            diff_args.append("--staged")
        elif len(parts) > 1:
            diff_args.append("--")
            diff_args.append(parts[1])

        out, err, ec = _run_git(diff_args, repo_root)
        if ec != 0:
            return CommandResult(output=f"git error: {err}")
        if not out:
            return CommandResult(output="No diff")

        # Truncate very large diffs
        if len(out) > 5000:
            out = out[:5000] + "\n[dim]… diff truncated (use --stat)[/]"

        return CommandResult(output="git diff output", renderable=f"[dim]{out}[/]" if _rich_available() else None)

    # ── /git log ───────────────────────────────────────────────────────
    if subcmd == "log":
        log_args = ["log", "--oneline", "-20", "--abbrev=12"]
        if len(parts) > 1 and parts[1] == "--all":
            log_args.append("--all")

        out, err, ec = _run_git(log_args, repo_root)
        if ec != 0:
            return CommandResult(output=f"git error: {err}")

        lines = []
        for line in out.split("\n")[:20]:
            if line.strip():
                lines.append(f"  [dim]{line}[/]")

        return CommandResult(
            output=f"Last {len(lines)} commits",
            renderable="\n".join(lines) if _rich_available() else None,
        )

    # ── /git branch ────────────────────────────────────────────────────
    if subcmd == "branch":
        out, err, ec = _run_git(["branch", "-a"], repo_root)
        if ec != 0:
            return CommandResult(output=f"git error: {err}")

        lines = []
        for line in out.split("\n"):
            if not line.strip():
                continue
            is_current = line.startswith("*")
            glyph = "[green]●[/]" if is_current else " " * 6
            name = line.strip("* ")
            if is_current:
                lines.append(f"  {glyph} [bold]{name}[/]")
            else:
                lines.append(f"  {glyph} {name}")

        return CommandResult(
            output=f"Branches ({len([l for l in out.split(chr(10)) if l.strip()])})",
            renderable="\n".join(lines) if _rich_available() else None,
        )

    # ── /git commit ────────────────────────────────────────────────────
    if subcmd == "commit":
        if len(parts) < 2:
            return CommandResult(output="Usage: /git commit <message>")
        
        if parts[1] == "--conventional" and len(parts) >= 4:
            msg_type = parts[2]
            msg_body = " ".join(parts[3:])
            full_msg = f"{msg_type}: {msg_body}"
        else:
            full_msg = " ".join(parts[1:])

        out, err, ec = _run_git(["commit", "-m", full_msg], repo_root)
        if ec != 0:
            return CommandResult(output=f"Commit failed: {err}")
        return CommandResult(output=f"✓ {out}")

    return CommandResult(
        output="Usage: /git [status|diff|log|branch|commit]"
    )


__all__ = [
    "cmd_git", "get_branch", "get_dirty_count", "render_status_badge",
    "get_commits_ahead", "is_detached",
]
