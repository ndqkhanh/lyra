"""Phase E.4 contract: ``SubagentRunner`` uses real ``git worktree add``.

Pre-v2.7 the runner always materialised a plain ``mkdir`` under
``worktree_root``. That was honest for tmp-path tests but a lie for
production usage — the docstring claimed "WorktreeManager (Wave-A) is
the production wrapper that adds the git worktree add call" yet
nothing in the runner ever called it. This test pins the new contract:

* When the runner is constructed inside a real git repo, the workdir
  is allocated via :class:`WorktreeManager.allocate` so each spawn
  gets its own branch + checkout.
* The default ``cleanup_on_exit=True`` reaps the worktree (path gone,
  ``git worktree list`` no longer references it) at the end of the run.
* Callers who don't want a real worktree (tests, sandboxes, non-git
  parents) can opt out via ``use_git_worktree=False`` and still get the
  legacy plain ``mkdir`` semantics.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from lyra_core.agent.loop import AgentLoop, IterationBudget


class _ScriptedLLM:
    def __init__(self, responses: list[dict]) -> None:
        self._responses = list(responses)
        self.calls = 0

    def generate(self, messages: list[dict], **_kw: Any) -> dict:
        self.calls += 1
        if not self._responses:
            return {"content": "", "tool_calls": [], "stop_reason": "end_turn"}
        return self._responses.pop(0)


class _NoopStore:
    def append(self, *_a: Any, **_kw: Any) -> None:  # pragma: no cover
        pass


def _agent_loop_factory(llm: Any) -> AgentLoop:
    return AgentLoop(
        llm=llm,
        tools={},
        store=_NoopStore(),
        budget=IterationBudget(max=5),
    )


def _git_available() -> bool:
    return shutil.which("git") is not None


def _init_git_repo(root: Path) -> None:
    subprocess.run(
        ["git", "init", "-q", "-b", "main", str(root)],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(root), "config", "user.email", "lyra@test.local"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(root), "config", "user.name", "lyra-test"],
        check=True,
        capture_output=True,
    )
    # An empty repo can't have worktrees added — we need at least one
    # commit so ``git worktree add -b new-branch <path>`` has a base
    # ref to fork from.
    (root / "README.md").write_text("seed\n", encoding="utf-8")
    subprocess.run(
        ["git", "-C", str(root), "add", "."],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(root), "commit", "-q", "-m", "seed"],
        check=True,
        capture_output=True,
    )


@pytest.mark.skipif(not _git_available(), reason="git not on PATH")
def test_runner_uses_real_git_worktree_when_repo_is_git(tmp_path: Path) -> None:
    """In a real git repo the runner allocates via WorktreeManager."""
    from lyra_core.subagent.runner import SubagentRunner, SubagentRunSpec

    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)

    llm = _ScriptedLLM(
        [{"content": "ok", "tool_calls": [], "stop_reason": "end_turn"}]
    )
    runner = SubagentRunner(
        loop_factory=lambda: _agent_loop_factory(llm),
        repo_root=repo,
        worktree_root=repo / ".lyra" / "worktrees",
    )

    # Construction succeeded → the manager attached.
    assert runner._wt_manager is not None  # noqa: SLF001 — contract pin

    result = runner.run(
        SubagentRunSpec(scope_id="scope-1", description="hi"),
        cleanup_on_exit=False,  # so we can inspect the path
    )
    assert result.status == "ok"
    assert result.workdir is not None

    # Path lives under the worktree state dir AND ``git worktree list``
    # actually references it.
    expected_root = repo / ".lyra" / "worktrees"
    assert expected_root in result.workdir.parents
    assert result.workdir.exists()

    listing = subprocess.run(
        ["git", "-C", str(repo), "worktree", "list", "--porcelain"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert str(result.workdir) in listing

    # Now reap explicitly and verify both the dir and the git
    # bookkeeping go away.
    runner.cleanup("scope-1")
    assert not result.workdir.exists()
    listing_after = subprocess.run(
        ["git", "-C", str(repo), "worktree", "list", "--porcelain"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert str(result.workdir) not in listing_after


@pytest.mark.skipif(not _git_available(), reason="git not on PATH")
def test_runner_cleanup_on_exit_removes_worktree(tmp_path: Path) -> None:
    """Default ``cleanup_on_exit=True`` reaps the worktree post-run."""
    from lyra_core.subagent.runner import SubagentRunner, SubagentRunSpec

    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)

    llm = _ScriptedLLM(
        [{"content": "ok", "tool_calls": [], "stop_reason": "end_turn"}]
    )
    runner = SubagentRunner(
        loop_factory=lambda: _agent_loop_factory(llm),
        repo_root=repo,
        worktree_root=repo / ".lyra" / "worktrees",
    )

    result = runner.run(SubagentRunSpec(scope_id="scope-2", description="hi"))
    assert result.status == "ok"
    assert result.workdir is not None
    assert not result.workdir.exists(), (
        "cleanup_on_exit should remove the worktree after a successful run"
    )


def test_runner_falls_back_to_plain_mkdir_for_non_git_root(
    tmp_path: Path,
) -> None:
    """A non-git repo_root must still produce a workdir (legacy path)."""
    from lyra_core.subagent.runner import SubagentRunner, SubagentRunSpec

    llm = _ScriptedLLM(
        [{"content": "ok", "tool_calls": [], "stop_reason": "end_turn"}]
    )
    runner = SubagentRunner(
        loop_factory=lambda: _agent_loop_factory(llm),
        repo_root=tmp_path,
        worktree_root=tmp_path / "wt",
    )

    # No git repo → manager attachment failed → fall back is active.
    assert runner._wt_manager is None  # noqa: SLF001

    result = runner.run(
        SubagentRunSpec(scope_id="scope-3", description="hi"),
        cleanup_on_exit=False,
    )
    assert result.status == "ok"
    assert result.workdir is not None
    assert (tmp_path / "wt") in result.workdir.parents
    assert result.workdir.exists()


@pytest.mark.skipif(not _git_available(), reason="git not on PATH")
def test_runner_use_git_worktree_false_disables_manager(tmp_path: Path) -> None:
    """Opt-out flag forces the legacy plain-dir path even inside a git repo."""
    from lyra_core.subagent.runner import SubagentRunner, SubagentRunSpec

    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)

    llm = _ScriptedLLM(
        [{"content": "ok", "tool_calls": [], "stop_reason": "end_turn"}]
    )
    runner = SubagentRunner(
        loop_factory=lambda: _agent_loop_factory(llm),
        repo_root=repo,
        worktree_root=repo / ".lyra" / "worktrees",
        use_git_worktree=False,
    )
    assert runner._wt_manager is None  # noqa: SLF001

    result = runner.run(
        SubagentRunSpec(scope_id="scope-4", description="hi"),
        cleanup_on_exit=False,
    )
    assert result.status == "ok"
    assert result.workdir is not None
    # Plain mkdir path lands directly under worktree_root, NOT inside
    # the git worktree state dir.
    assert (repo / ".lyra" / "worktrees") in result.workdir.parents
    listing = subprocess.run(
        ["git", "-C", str(repo), "worktree", "list", "--porcelain"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert str(result.workdir) not in listing
