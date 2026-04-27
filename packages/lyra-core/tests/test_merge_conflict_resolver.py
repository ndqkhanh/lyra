"""Red tests for the three-way merge with resolver loop."""
from __future__ import annotations

import subprocess
from pathlib import Path

from lyra_core.subagent.merge import (
    MergeResult,
    three_way_merge,
)


def _init_repo_with_two_branches(tmp_path: Path) -> Path:
    p = tmp_path / "repo"
    p.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main", str(p)], check=True)
    f = p / "x.txt"
    f.write_text("base\n")
    subprocess.run(["git", "-C", str(p), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(p), "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-q", "-m", "base"],
        check=True,
    )
    # branch a: modifies first line
    subprocess.run(["git", "-C", str(p), "checkout", "-q", "-b", "branch-a"], check=True)
    f.write_text("from-a\n")
    subprocess.run(["git", "-C", str(p), "commit", "-q", "-am", "a"], check=True)
    # branch b: modifies first line differently
    subprocess.run(["git", "-C", str(p), "checkout", "-q", "main"], check=True)
    subprocess.run(["git", "-C", str(p), "checkout", "-q", "-b", "branch-b"], check=True)
    f.write_text("from-b\n")
    subprocess.run(["git", "-C", str(p), "commit", "-q", "-am", "b"], check=True)
    subprocess.run(["git", "-C", str(p), "checkout", "-q", "main"], check=True)
    return p


def test_clean_merge(tmp_path: Path) -> None:
    p = _init_repo_with_two_branches(tmp_path)
    # Reset branch-b to a non-overlapping change for a clean merge.
    subprocess.run(["git", "-C", str(p), "checkout", "-q", "branch-b"], check=True)
    (p / "y.txt").write_text("new\n")
    subprocess.run(["git", "-C", str(p), "add", "."], check=True)
    subprocess.run(["git", "-C", str(p), "commit", "-q", "-m", "add y"], check=True)
    subprocess.run(["git", "-C", str(p), "checkout", "-q", "main"], check=True)

    res = three_way_merge(repo_root=p, branches=["branch-b"])
    assert isinstance(res, MergeResult)
    assert res.clean is True
    assert res.conflicts == []


def test_conflict_detected_without_resolver(tmp_path: Path) -> None:
    p = _init_repo_with_two_branches(tmp_path)
    res = three_way_merge(
        repo_root=p, branches=["branch-a", "branch-b"], resolver=None
    )
    assert res.clean is False
    assert res.conflicts
    assert any("x.txt" in c for c in res.conflicts)


def test_resolver_invoked_on_conflict(tmp_path: Path) -> None:
    p = _init_repo_with_two_branches(tmp_path)
    calls: list[str] = []

    def resolver(path: Path, content: str) -> str:
        calls.append(str(path))
        return "RESOLVED\n"

    res = three_way_merge(
        repo_root=p, branches=["branch-a", "branch-b"], resolver=resolver
    )
    assert res.clean is True
    assert (p / "x.txt").read_text().strip() == "RESOLVED"
    assert calls


def test_stalemate_resolver_escalates(tmp_path: Path) -> None:
    """When the resolver returns None, the merge escalates (clean=False)."""
    p = _init_repo_with_two_branches(tmp_path)

    def resolver(path: Path, content: str) -> str | None:
        return None

    res = three_way_merge(
        repo_root=p, branches=["branch-a", "branch-b"], resolver=resolver
    )
    assert res.clean is False
    assert res.escalated is True
