"""Git operation tools for repository management."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from enum import StrEnum


class GitOperation(StrEnum):
    STATUS = "status"
    DIFF = "diff"
    LOG = "log"
    BRANCH = "branch"
    COMMIT = "commit"
    PULL = "pull"
    PUSH = "push"
    STASH = "stash"
    ADD = "add"
    CHECKOUT = "checkout"


@dataclass(frozen=True)
class GitFileStatus:
    path: str
    status: str  # M, A, D, R, ??, etc.
    staged: bool


@dataclass(frozen=True)
class GitStatus:
    branch: str
    files: tuple[GitFileStatus, ...]
    ahead: int = 0
    behind: int = 0
    dirty: bool = False


@dataclass(frozen=True)
class GitCommit:
    hash: str
    author: str
    date: str
    message: str


@dataclass(frozen=True)
class GitDiff:
    file_path: str
    additions: int
    deletions: int
    patch: str


class GitTool:
    """Git operations wrapper for agent-driven version control.

    Usage::

        tool = GitTool(repo_path="/app/repo")
        status = tool.status()
        log = tool.log(max_count=10)
        diff = tool.diff("HEAD~1")
    """

    def __init__(self, repo_path: str = ".") -> None:
        self._cwd = repo_path

    def _run(self, *args: str) -> str:
        result = subprocess.run(
            ["git"] + list(args),
            capture_output=True,
            text=True,
            cwd=self._cwd,
        )
        return result.stdout.strip()

    def status(self) -> GitStatus:
        branch = self._run("rev-parse", "--abbrev-ref", "HEAD")
        output = self._run("status", "--porcelain")
        files: list[GitFileStatus] = []
        for line in output.splitlines():
            if not line:
                continue
            staged = line[0] != " "
            status_code = line[:2].strip()
            path = line[3:].strip()
            files.append(GitFileStatus(path=path, status=status_code, staged=staged))

        ahead_raw = self._run("rev-list", "HEAD...@{u}", "--count")
        behind_raw = self._run("rev-list", "@{u}...HEAD", "--count")
        return GitStatus(
            branch=branch,
            files=tuple(files),
            ahead=int(ahead_raw) if ahead_raw.isdigit() else 0,
            behind=int(behind_raw) if behind_raw.isdigit() else 0,
            dirty=len(files) > 0,
        )

    def log(self, max_count: int = 20, author: str = "") -> list[GitCommit]:
        args = ["log", f"--max-count={max_count}", "--format=%H||%an||%ai||%s"]
        if author:
            args.append(f"--author={author}")
        output = self._run(*args)
        commits: list[GitCommit] = []
        for line in output.splitlines():
            parts = line.split("||", 3)
            if len(parts) == 4:
                commits.append(
                    GitCommit(hash=parts[0], author=parts[1], date=parts[2], message=parts[3])
                )
        return commits

    def diff(
        self, ref: str = "HEAD", staged: bool = False, paths: str = ""
    ) -> list[GitDiff]:
        args = ["diff"]
        if staged:
            args.append("--staged")
        args.append(ref)
        if paths:
            args.append("--")
            args.append(paths)
        output = self._run(*args)
        diffs: list[GitDiff] = []
        current_file = ""
        current_add = 0
        current_del = 0
        patch_lines: list[str] = []
        for line in output.splitlines():
            if line.startswith("diff --git"):
                if current_file:
                    diffs.append(
                        GitDiff(
                            file_path=current_file,
                            additions=current_add,
                            deletions=current_del,
                            patch="\n".join(patch_lines),
                        )
                    )
                current_file = line.split(" b/")[-1]
                current_add = 0
                current_del = 0
                patch_lines = [line]
            else:
                patch_lines.append(line)
                if line.startswith("+") and not line.startswith("+++"):
                    current_add += 1
                elif line.startswith("-") and not line.startswith("---"):
                    current_del += 1

        if current_file:
            diffs.append(
                GitDiff(
                    file_path=current_file,
                    additions=current_add,
                    deletions=current_del,
                    patch="\n".join(patch_lines),
                )
            )
        return diffs

    def branches(self) -> list[str]:
        output = self._run("branch", "--format=%(refname:short)")
        return output.splitlines()

    def stash_list(self) -> list[str]:
        output = self._run("stash", "list", "--format=%s")
        return output.splitlines()
