"""Red tests for parallel subagents with non-overlapping scopes."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from lyra_core.subagent.orchestrator import (
    ScopeCollisionError,
    SubagentOrchestrator,
    SubagentSpec,
)


def _init_repo(p: Path) -> None:
    subprocess.run(["git", "init", "-q", "-b", "main", str(p)], check=True)
    (p / "README.md").write_text("hello\n")
    subprocess.run(["git", "-C", str(p), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(p), "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-q", "-m", "init"],
        check=True,
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    p = tmp_path / "repo"
    p.mkdir()
    _init_repo(p)
    return p


def test_non_overlapping_scopes_complete(repo: Path) -> None:
    def worker(wt: Path, spec: SubagentSpec) -> str:
        # Create the sentinel file within our scope.
        target = wt / spec.scope_globs[0].replace("/**", "") / "sentinel.txt"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(spec.id)
        return "ok"

    orch = SubagentOrchestrator(repo_root=repo)
    specs = [
        SubagentSpec(id="a", scope_globs=["a/**"]),
        SubagentSpec(id="b", scope_globs=["b/**"]),
        SubagentSpec(id="c", scope_globs=["c/**"]),
    ]
    results = orch.run_parallel(specs, worker=worker)
    assert len(results) == 3
    assert all(r.status == "ok" for r in results)


def test_overlapping_scopes_rejected(repo: Path) -> None:
    orch = SubagentOrchestrator(repo_root=repo)
    specs = [
        SubagentSpec(id="a", scope_globs=["a/**"]),
        SubagentSpec(id="dup", scope_globs=["a/**"]),
    ]
    with pytest.raises(ScopeCollisionError):
        orch.run_parallel(specs, worker=lambda _wt, _s: "ok")


def test_depth_recursion_cap(repo: Path) -> None:
    """A subagent attempting to spawn deeper than depth=2 is rejected."""
    from lyra_core.subagent.orchestrator import DepthLimitError

    orch = SubagentOrchestrator(repo_root=repo, max_depth=2)
    with pytest.raises(DepthLimitError):
        orch.check_spawn_depth(current_depth=2)
    orch.check_spawn_depth(current_depth=1)  # still allowed
