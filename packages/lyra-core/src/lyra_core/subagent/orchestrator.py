"""Subagent orchestrator: allocate worktrees, fan out, merge results."""
from __future__ import annotations

import concurrent.futures as cf
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .worktree import WorktreeManager


class ScopeCollisionError(Exception):
    pass


class DepthLimitError(Exception):
    pass


@dataclass
class SubagentSpec:
    id: str
    scope_globs: list[str] = field(default_factory=list)


@dataclass
class SubagentResult:
    id: str
    status: str  # "ok" | "error"
    payload: object | None = None
    error: str | None = None


WorkerFn = Callable[[Path, SubagentSpec], object]


def _scopes_collide(a: list[str], b: list[str]) -> bool:
    return bool(set(a) & set(b))


@dataclass
class SubagentOrchestrator:
    repo_root: Path
    max_depth: int = 2

    # ------------------------------------------------------------------ depth
    def check_spawn_depth(self, *, current_depth: int) -> None:
        if current_depth >= self.max_depth:
            raise DepthLimitError(
                f"subagent spawn depth {current_depth} would exceed max_depth "
                f"{self.max_depth}"
            )

    # ------------------------------------------------------------------ runner
    def run_parallel(
        self, specs: list[SubagentSpec], *, worker: WorkerFn
    ) -> list[SubagentResult]:
        for i, a in enumerate(specs):
            for b in specs[i + 1 :]:
                if _scopes_collide(a.scope_globs, b.scope_globs):
                    raise ScopeCollisionError(
                        f"scope collision: {a.id} and {b.id} share "
                        f"{set(a.scope_globs) & set(b.scope_globs)}"
                    )

        mgr = WorktreeManager(repo_root=self.repo_root)
        allocations = [(spec, mgr.allocate(scope_id=spec.id)) for spec in specs]

        out: list[SubagentResult] = []
        try:
            with cf.ThreadPoolExecutor(max_workers=max(1, len(allocations))) as pool:
                fut_map = {
                    pool.submit(worker, wt.path, spec): spec
                    for spec, wt in allocations
                }
                for fut in cf.as_completed(fut_map):
                    spec = fut_map[fut]
                    try:
                        payload = fut.result()
                        out.append(SubagentResult(id=spec.id, status="ok", payload=payload))
                    except Exception as e:
                        out.append(
                            SubagentResult(id=spec.id, status="error", error=str(e))
                        )
        finally:
            for _spec, wt in allocations:
                mgr.cleanup(wt)
        return out
