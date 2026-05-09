"""Three-way merge with an optional LLM conflict resolver."""
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

Resolver = Callable[[Path, str], Optional[str]]


@dataclass
class MergeResult:
    clean: bool
    conflicts: list[str] = field(default_factory=list)
    escalated: bool = False


_CONFLICT_RE = re.compile(r"^<<<<<<< .*?^=======.*?^>>>>>>> .*?$", re.DOTALL | re.MULTILINE)


def _conflicted_paths(repo_root: Path) -> list[str]:
    res = subprocess.run(
        ["git", "-C", str(repo_root), "diff", "--name-only", "--diff-filter=U"],
        capture_output=True, text=True,
    )
    return [p for p in res.stdout.splitlines() if p.strip()]


def _run_resolver(repo_root: Path, resolver: Resolver) -> bool:
    escalated = False
    for p in _conflicted_paths(repo_root):
        full = repo_root / p
        content = full.read_text(encoding="utf-8", errors="replace")
        resolved = resolver(full, content)
        if resolved is None:
            escalated = True
            continue
        full.write_text(resolved, encoding="utf-8")
        subprocess.run(
            ["git", "-C", str(repo_root), "add", p],
            capture_output=True, text=True, check=False,
        )
    return not escalated


def three_way_merge(
    *,
    repo_root: Path,
    branches: list[str],
    resolver: Resolver | None = None,
) -> MergeResult:
    subprocess.run(
        ["git", "-C", str(repo_root), "-c", "user.email=oc@oc", "-c", "user.name=oc",
         "merge", "--no-edit", "--no-ff", *branches],
        capture_output=True, text=True,
    )
    conflicts = _conflicted_paths(repo_root)
    if not conflicts:
        return MergeResult(clean=True, conflicts=[], escalated=False)

    if resolver is None:
        # Leave conflicts for the user; abort merge to keep repo clean.
        subprocess.run(
            ["git", "-C", str(repo_root), "merge", "--abort"],
            capture_output=True, text=True,
        )
        return MergeResult(clean=False, conflicts=conflicts, escalated=False)

    ok = _run_resolver(repo_root, resolver)
    if not ok:
        subprocess.run(
            ["git", "-C", str(repo_root), "merge", "--abort"],
            capture_output=True, text=True,
        )
        return MergeResult(clean=False, conflicts=conflicts, escalated=True)

    commit = subprocess.run(
        ["git", "-C", str(repo_root), "-c", "user.email=oc@oc", "-c", "user.name=oc",
         "commit", "--no-edit"],
        capture_output=True, text=True,
    )
    if commit.returncode != 0:
        return MergeResult(
            clean=False, conflicts=conflicts, escalated=True
        )
    return MergeResult(clean=True, conflicts=[], escalated=False)
