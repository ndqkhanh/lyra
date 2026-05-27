"""Git tool implementations — status, diff, log, branch operations.

Structured Git command wrappers providing parseable output for LLM consumption.
All operations respect the current working directory's git repository.
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any


def _git(args: list[str], workdir: str = ".", timeout: int = 15) -> dict[str, Any]:
    """Run a git command and return structured output."""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=workdir,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "code": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }
    except subprocess.TimeoutExpired:
        return {"code": -1, "stdout": "", "stderr": "git command timed out"}
    except FileNotFoundError:
        return {"code": -1, "stdout": "", "stderr": "git not found"}


def _repo_root(path: str = ".") -> str:
    """Find the git repository root."""
    result = _git(["rev-parse", "--show-toplevel"], workdir=path)
    if result["code"] == 0 and result["stdout"]:
        return result["stdout"]
    return str(Path(path).resolve())


def git_status(
    path: str = ".",
    *,
    short: bool = False,
) -> dict[str, Any]:
    """Show the working tree status."""
    repo = _repo_root(path)
    args = ["status"]
    if short:
        args.append("--short")
    else:
        args.append("--porcelain")

    result = _git(args, workdir=repo)

    files: list[dict[str, str]] = []
    for line in result["stdout"].split("\n"):
        if not line.strip():
            continue
        if short or line.startswith(("M", "A", "D", "R", "C", "U", "?", "!")):
            status_code = line[:2].strip()
            filename = line[3:].strip().split(" -> ")[-1] if " -> " in line else line[3:].strip()
            files.append({
                "status": status_code,
                "file": filename,
                "status_desc": _status_desc(status_code),
            })

    has_changes = len(files) > 0
    return {
        "repository": repo,
        "has_changes": has_changes,
        "changed_files": len(files),
        "files": files,
        "branch": _current_branch(repo),
    }


def _status_desc(code: str) -> str:
    mapping = {
        "M": "modified",
        "A": "added",
        "D": "deleted",
        "R": "renamed",
        "C": "copied",
        "U": "updated-but-unmerged",
        "??": "untracked",
        "!!": "ignored",
        "AM": "added-modified",
        "MM": "modified-modified",
        " M": "modified-in-worktree",
        " D": "deleted-in-worktree",
    }
    return mapping.get(code.strip(), "unknown")


def git_diff(
    target: str = "",
    *,
    path: str = ".",
    staged: bool = False,
    context_lines: int = 3,
) -> dict[str, Any]:
    """Show changes between commits or working tree."""
    repo = _repo_root(path)
    args = ["diff"]
    if staged:
        args.append("--staged")
    if context_lines:
        args.extend([f"-U{context_lines}"])

    if target:
        args.append(target)
    else:
        args.append("HEAD")

    result = _git(args, workdir=repo)

    return {
        "repository": repo,
        "target": target or "HEAD",
        "staged": staged,
        "patch": result["stdout"] if result["stdout"] else "(no changes)",
        "has_changes": bool(result["stdout"]),
    }


def git_log(
    n: int = 10,
    *,
    path: str = ".",
    format: str = "oneline",
) -> dict[str, Any]:
    """Show commit history."""
    repo = _repo_root(path)
    formats = {
        "oneline": "--oneline",
        "short": "--format=%h %s (%an, %ar)",
        "medium": "--format=commit %H%nAuthor: %an <%ae>%nDate: %ad%n%n    %s%n",
        "full": "--format=full",
    }
    fmt_flag = formats.get(format, formats["oneline"])

    result = _git(["log", f"-{n}", fmt_flag], workdir=repo)

    commits: list[str] = []
    for line in result["stdout"].split("\n"):
        if line.strip():
            commits.append(line.strip())

    return {
        "repository": repo,
        "commits": commits,
        "count": len(commits),
        "format": format,
    }


def _current_branch(repo: str) -> str:
    result = _git(["branch", "--show-current"], workdir=repo)
    return result["stdout"] if result["code"] == 0 else "unknown"


__all__ = ["git_status", "git_diff", "git_log"]
