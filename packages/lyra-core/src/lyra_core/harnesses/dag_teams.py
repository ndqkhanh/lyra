"""DAG teams: dynamic LLM-planned DAG + deterministic scheduler."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


class DAGValidationError(Exception):
    pass


@dataclass
class Node:
    id: str
    deps: list[str] = field(default_factory=list)


@dataclass
class DAG:
    nodes: list[Node]
    sinks: list[str] = field(default_factory=list)
    width_budget: int = 4


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _detect_cycle(nodes: dict[str, Node]) -> bool:
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {nid: WHITE for nid in nodes}

    def dfs(nid: str) -> bool:
        color[nid] = GRAY
        for dep in nodes[nid].deps:
            if dep not in nodes:
                continue
            if color[dep] == GRAY:
                return True
            if color[dep] == WHITE and dfs(dep):
                return True
        color[nid] = BLACK
        return False

    return any(color[n] == WHITE and dfs(n) for n in nodes)


def validate_dag(dag: DAG, *, strict: bool = False) -> None:
    seen: set[str] = set()
    by_id: dict[str, Node] = {}
    for n in dag.nodes:
        if n.id in seen:
            raise DAGValidationError(f"duplicate node id: {n.id}")
        seen.add(n.id)
        by_id[n.id] = n

    if len(dag.nodes) > dag.width_budget * len(dag.nodes):
        # Trivially true; real width check below.
        pass
    if len(dag.nodes) > dag.width_budget and dag.width_budget > 0 and _max_width_of(by_id) > dag.width_budget:
        raise DAGValidationError(
            f"max level width {_max_width_of(by_id)} exceeds budget {dag.width_budget}"
        )

    for n in dag.nodes:
        for dep in n.deps:
            if dep not in by_id:
                raise DAGValidationError(
                    f"node {n.id!r} depends on unknown node {dep!r}"
                )

    if _detect_cycle(by_id):
        raise DAGValidationError("cycle detected in DAG")

    if strict:
        dependents: dict[str, set[str]] = {nid: set() for nid in by_id}
        for n in dag.nodes:
            for dep in n.deps:
                dependents[dep].add(n.id)
        sinks = set(dag.sinks)
        for nid, node in by_id.items():
            if nid in sinks:
                continue
            if not node.deps and not dependents[nid]:
                raise DAGValidationError(
                    f"unreferenced node {nid!r} (no deps, no dependents, not a sink)"
                )


# ---------------------------------------------------------------------------
# Scheduling
# ---------------------------------------------------------------------------


def _levels(by_id: dict[str, Node]) -> list[list[str]]:
    remaining = {nid: set(n.deps) for nid, n in by_id.items()}
    levels: list[list[str]] = []
    while remaining:
        current = sorted(nid for nid, deps in remaining.items() if not deps)
        if not current:
            raise DAGValidationError("cycle detected during scheduling")
        levels.append(current)
        for nid in current:
            remaining.pop(nid, None)
        for deps in remaining.values():
            for c in current:
                deps.discard(c)
    return levels


def _max_width_of(by_id: dict[str, Node]) -> int:
    try:
        levels = _levels(by_id)
    except DAGValidationError:
        return max(1, len(by_id))
    return max((len(level) for level in levels), default=0)


@dataclass
class ParkingResult:
    completed: list[str]
    pending: list[str]
    halted: bool


class Scheduler:
    def batches(self, dag: DAG) -> list[list[str]]:
        by_id = {n.id: n for n in dag.nodes}
        levels = _levels(by_id)
        out: list[list[str]] = []
        for level in levels:
            for i in range(0, len(level), max(1, dag.width_budget)):
                out.append(level[i : i + max(1, dag.width_budget)])
        return out

    def propagate_failures(self, dag: DAG, *, failed_ids: set[str]) -> set[str]:
        by_id = {n.id: n for n in dag.nodes}
        skipped: set[str] = set()

        def downstream(src: str) -> None:
            for nid, node in by_id.items():
                if src in node.deps and nid not in skipped:
                    skipped.add(nid)
                    downstream(nid)

        for f in failed_ids:
            downstream(f)
        return skipped

    def run_with_parking(
        self,
        dag: DAG,
        *,
        park_hook: Callable[[list[str], list[str]], bool],
    ) -> ParkingResult:
        completed: list[str] = []
        batches = self.batches(dag)
        pending_ids = [nid for batch in batches for nid in batch]
        for batch in batches:
            # Simulate execution of the batch in order.
            for nid in batch:
                completed.append(nid)
                if nid in pending_ids:
                    pending_ids.remove(nid)
            if not park_hook(list(completed), list(pending_ids)):
                return ParkingResult(
                    completed=completed, pending=pending_ids, halted=True
                )
        return ParkingResult(completed=completed, pending=pending_ids, halted=False)
