"""Wave-D Task 4: a fan-out/join scheduler for subagent DAGs.

The :class:`harnesses.dag_teams.Scheduler` plans levels but doesn't
execute them; the orchestrator in :mod:`.orchestrator` executes a
flat list of specs but doesn't honour dependencies. This scheduler
sits between them — given a list of :class:`SubagentDAGSpec` nodes
with ``depends_on`` edges, it:

1. Validates the graph (no duplicate ids, no unknown deps, no cycles).
2. Topologically sorts into levels.
3. Runs each level concurrently (bounded by ``max_parallel``).
4. Skips downstream nodes when an upstream node fails so a single
   bad spec doesn't poison the run with cascading exceptions.

The scheduler is **worker-agnostic**. Tests pass a function that
takes a spec and returns a dict; production wires the
:class:`SubagentRunner` (Wave-D Task 1) so each node spawns into a
worktree-isolated agent loop. That separation is intentional —
testing the topology is much easier without dragging the loop into
the picture.
"""
from __future__ import annotations

import concurrent.futures as cf
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Literal, Set


class SchedulerError(Exception):
    """Raised before any worker runs when the DAG itself is invalid."""


@dataclass
class SubagentDAGSpec:
    """One node in the DAG."""

    id: str
    description: str = ""
    depends_on: list[str] = field(default_factory=list)
    preset_name: str | None = None
    extras: dict[str, Any] = field(default_factory=dict)


SubagentNodeStatus = Literal["ok", "failed", "skipped", "cancelled"]


@dataclass
class SubagentNodeResult:
    """The outcome of one DAG node."""

    id: str
    status: SubagentNodeStatus
    payload: Any = None
    error: str | None = None


@dataclass
class SubagentDAGRun:
    """The summary the scheduler hands back to the caller."""

    results: list[SubagentNodeResult] = field(default_factory=list)
    failed_ids: set[str] = field(default_factory=set)
    skipped_ids: set[str] = field(default_factory=set)


WorkerFn = Callable[[SubagentDAGSpec], Any]


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------


class SubagentScheduler:
    """Run a DAG of :class:`SubagentDAGSpec` through a worker callable."""

    def __init__(self, *, max_parallel: int = 4) -> None:
        if max_parallel < 1:
            raise ValueError("max_parallel must be >= 1")
        self.max_parallel = max_parallel

    # ---- public API ---------------------------------------------------

    def run(
        self,
        specs: list[SubagentDAGSpec],
        *,
        worker: WorkerFn,
    ) -> SubagentDAGRun:
        by_id: Dict[str, SubagentDAGSpec] = {}
        for spec in specs:
            if spec.id in by_id:
                raise SchedulerError(f"duplicate spec id: {spec.id!r}")
            by_id[spec.id] = spec

        for spec in specs:
            for dep in spec.depends_on:
                if dep not in by_id:
                    raise SchedulerError(
                        f"node {spec.id!r} depends on unknown id {dep!r}"
                    )

        levels = _topological_levels(by_id)

        run = SubagentDAGRun()
        results_by_id: Dict[str, SubagentNodeResult] = {}
        for level in levels:
            # Skip nodes whose deps already failed/were skipped.
            runnable: List[SubagentDAGSpec] = []
            for nid in level:
                spec = by_id[nid]
                blocked = [
                    d for d in spec.depends_on
                    if results_by_id.get(d) is None
                    or results_by_id[d].status != "ok"
                ]
                if blocked:
                    res = SubagentNodeResult(
                        id=nid,
                        status="skipped",
                        error=f"upstream not ok: {','.join(sorted(blocked))}",
                    )
                    results_by_id[nid] = res
                    run.skipped_ids.add(nid)
                else:
                    runnable.append(spec)

            if not runnable:
                continue

            with cf.ThreadPoolExecutor(
                max_workers=min(self.max_parallel, len(runnable))
            ) as pool:
                fut_map = {pool.submit(worker, spec): spec for spec in runnable}
                for fut in cf.as_completed(fut_map):
                    spec = fut_map[fut]
                    try:
                        payload = fut.result()
                        results_by_id[spec.id] = SubagentNodeResult(
                            id=spec.id, status="ok", payload=payload
                        )
                    except Exception as exc:
                        results_by_id[spec.id] = SubagentNodeResult(
                            id=spec.id,
                            status="failed",
                            error=f"{type(exc).__name__}: {exc}",
                        )
                        run.failed_ids.add(spec.id)

        # Stable order: insertion order of original ``specs``.
        run.results = [results_by_id[s.id] for s in specs if s.id in results_by_id]
        return run


# ---------------------------------------------------------------------------
# Topology helpers
# ---------------------------------------------------------------------------


def _topological_levels(
    by_id: Dict[str, SubagentDAGSpec],
) -> list[list[str]]:
    remaining: Dict[str, Set[str]] = {
        nid: set(spec.depends_on) for nid, spec in by_id.items()
    }
    levels: list[list[str]] = []
    while remaining:
        ready = sorted(nid for nid, deps in remaining.items() if not deps)
        if not ready:
            raise SchedulerError(
                f"cycle detected; remaining nodes: {sorted(remaining)}"
            )
        levels.append(ready)
        for nid in ready:
            remaining.pop(nid, None)
        for deps in remaining.values():
            for done in ready:
                deps.discard(done)
    return levels


__all__ = [
    "SchedulerError",
    "SubagentDAGRun",
    "SubagentDAGSpec",
    "SubagentNodeResult",
    "SubagentNodeStatus",
    "SubagentScheduler",
    "WorkerFn",
]
