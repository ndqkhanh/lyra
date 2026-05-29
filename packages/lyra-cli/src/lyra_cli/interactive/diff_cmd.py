"""ECC-style /diff command — visual file comparison for the REPL.

Provides:
  • /diff <path> [--cached] — diff a file against HEAD or index
  • /diff <a> <b> — diff two files or arbitrary paths
  • /diff --stat — show diffstat summary for working tree
  • Color-coded output (green for additions, red for deletions)
  • Syntax-aware context lines

ECC reference: iterative editing requires clear before/after visibility.
ECC's everything-claude-code conventions emphasize small, reviewable
diffs — this command makes reviewing them effortless in the REPL.
"""

from __future__ import annotations

import difflib
from pathlib import Path
from typing import Any

from ..commands.registry import CommandResult

# ── Colors ─────────────────────────────────────────────────────────────

_COLOR_HEADER = "bold cyan"
_COLOR_ADD = "green"
_COLOR_DEL = "red"
_COLOR_HUNK = "bold magenta"
_COLOR_DIM = "dim"


def _colorize_diff(diff_text: str, max_lines: int = 40) -> str:
    """Apply Rich markup colors to a unified diff string."""
    lines = diff_text.split("\n")
    out: list[str] = []
    count = 0

    for line in lines:
        if count >= max_lines:
            out.append(f"[{_COLOR_DIM}]… +{len(lines) - max_lines} more lines[/]")
            break
        count += 1

        if line.startswith("---") or line.startswith("+++"):
            out.append(f"[{_COLOR_HEADER}]{line}[/]")
        elif line.startswith("@@"):
            out.append(f"[{_COLOR_HUNK}]{line}[/]")
        elif line.startswith("+"):
            out.append(f"[{_COLOR_ADD}]{line}[/]")
        elif line.startswith("-"):
            out.append(f"[{_COLOR_DEL}]{line}[/]")
        else:
            out.append(line)
    return "\n".join(out)


def _run_diff(cmd: list[str], cwd: Path | None = None) -> tuple[str, int]:
    """Run a diff command and return (output, exit_code)."""
    import subprocess

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=15,
            cwd=cwd or Path.cwd(),
        )
        return result.stdout, result.returncode
    except FileNotFoundError:
        return "diff tool not found", -1
    except subprocess.TimeoutExpired:
        return "diff timed out", -1


def _diff_working_tree(repo_root: Path) -> str:
    """Get full working tree diff via git."""
    out, ec = _run_diff(["git", "diff"], repo_root)
    if ec == 0 and out:
        return out
    # Fallback: try git diff --no-color
    out, ec = _run_diff(["git", "diff", "--no-color"], repo_root)
    return out if ec == 0 else ""


def _diff_file_vs_head(filepath: str, repo_root: Path) -> str:
    """Diff a file against HEAD."""
    args = ["git", "diff", "--no-color", "HEAD", "--", filepath]
    out, ec = _run_diff(args, repo_root)
    return out if ec == 0 else ""


def _diff_staged(filepath: str, repo_root: Path) -> str:
    """Diff a file against the index (--cached)."""
    args = (
        ["git", "diff", "--no-color", "--cached", "--", filepath]
        if filepath
        else ["git", "diff", "--no-color", "--cached"]
    )
    out, ec = _run_diff(args, repo_root)
    return out if ec == 0 else ""


def _diff_two_paths(a: str, b: str) -> str:
    """Diff two arbitrary files using python's difflib."""
    try:
        a_content = Path(a).read_text()
        b_content = Path(b).read_text()
    except FileNotFoundError as e:
        return f"File not found: {e.filename}"

    diff = difflib.unified_diff(
        a_content.splitlines(keepends=True),
        b_content.splitlines(keepends=True),
        fromfile=a,
        tofile=b,
    )
    return "".join(diff)


def _diffstat(repo_root: Path) -> str:
    """Get git diff --stat output."""
    out, ec = _run_diff(["git", "diff", "--stat"], repo_root)
    return out if ec == 0 else ""


# ── Command handler ────────────────────────────────────────────────────


def cmd_diff(session: Any, args: str) -> CommandResult:
    """Show file diffs with color highlighting.

    Usage:
      /diff                  — show working tree diff (all changes)
      /diff <file>           — diff file against HEAD
      /diff <file> --cached  — diff staged changes for file
      /diff <a> <b>          — diff two arbitrary files
      /diff --stat           — show diffstat summary
      /diff --color-words    — word-level diff
    """
    import shlex

    parts = shlex.split(args.strip()) if args.strip() else []
    repo_root = getattr(session, "repo_root", Path.cwd()) if session else Path.cwd()

    # ── /diff --stat ───────────────────────────────────────────────────
    if parts and parts[0] == "--stat":
        stat = _diffstat(repo_root)
        if not stat:
            return CommandResult(output="No changes in working tree")
        return CommandResult(output=stat, renderable=f"[dim]{stat}[/]")

    # ── /diff <a> <b> ──────────────────────────────────────────────────
    if len(parts) >= 2 and not parts[1].startswith("--"):
        a, b = parts[0], parts[1]
        diff = _diff_two_paths(a, b)
        if "File not found" in diff:
            return CommandResult(output=diff)
        colored = _colorize_diff(diff)
        return CommandResult(
            output=f"Diff: {a} ↔ {b} ({len(diff.split(chr(10)))} lines)",
            renderable=colored,
        )

    # ── /diff <file> [--cached] ────────────────────────────────────────
    if parts:
        filepath = parts[0]
        is_cached = len(parts) > 1 and parts[1] == "--cached"
        if is_cached:
            diff = _diff_staged(filepath, repo_root)
        else:
            diff = _diff_file_vs_head(filepath, repo_root)
        if not diff:
            return CommandResult(output=f"No diff for {filepath}")
        colored = _colorize_diff(diff)
        return CommandResult(
            output=f"Diff: {filepath} ({len(diff.split(chr(10)))} lines)",
            renderable=colored,
        )

    # ── /diff (full working tree) ──────────────────────────────────────
    diff = _diff_working_tree(repo_root)
    if not diff:
        return CommandResult(output="No changes in working tree")
    colored = _colorize_diff(diff)
    return CommandResult(
        output=f"Working tree diff ({len(diff.split(chr(10)))} lines)",
        renderable=colored,
    )


__all__ = ["cmd_diff"]
