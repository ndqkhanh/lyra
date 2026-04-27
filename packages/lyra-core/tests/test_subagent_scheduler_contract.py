"""Wave-D Task 4: DAG scheduler that actually fans out + joins.

The existing :class:`harnesses.dag_teams.Scheduler` plans level
batches. The new :class:`SubagentScheduler` *executes* a DAG of
:class:`SubagentDAGSpec` nodes through a user-supplied worker, in
topological order, with bounded parallelism.

Six RED tests:

1. Linear chain runs in dependency order.
2. Diamond (A → B, A → C, B+C → D) — D runs *after* B and C.
3. Workers in the same level run concurrently (we observe both
   started before either finished by capturing wall-clock overlap).
4. Cycle detection raises :class:`SchedulerError` before any worker
   runs.
5. Unknown dep id raises :class:`SchedulerError` with the bad id.
6. Failure of an upstream node short-circuits its downstream nodes
   to ``status="skipped"`` without invoking the worker.
"""
from __future__ import annotations

import threading
import time
from typing import Any

import pytest


def _make_specs(*items: tuple[str, list[str]]):
    from lyra_core.subagent.scheduler import SubagentDAGSpec

    return [
        SubagentDAGSpec(id=nid, description=f"task {nid}", depends_on=list(deps))
        for nid, deps in items
    ]


def test_linear_chain_runs_in_order() -> None:
    from lyra_core.subagent.scheduler import SubagentScheduler

    log: list[str] = []
    lock = threading.Lock()

    def worker(spec: Any) -> dict:
        with lock:
            log.append(spec.id)
        return {"id": spec.id, "ok": True}

    specs = _make_specs(("a", []), ("b", ["a"]), ("c", ["b"]))
    out = SubagentScheduler(max_parallel=4).run(specs, worker=worker)

    assert log == ["a", "b", "c"]
    assert {r.id for r in out.results} == {"a", "b", "c"}
    assert all(r.status == "ok" for r in out.results)


def test_diamond_runs_join_after_branches() -> None:
    from lyra_core.subagent.scheduler import SubagentScheduler

    seen: dict[str, list[str]] = {}
    lock = threading.Lock()

    def worker(spec: Any) -> dict:
        with lock:
            seen[spec.id] = list(seen.keys())
        return {"id": spec.id}

    specs = _make_specs(
        ("a", []),
        ("b", ["a"]),
        ("c", ["a"]),
        ("d", ["b", "c"]),
    )
    SubagentScheduler(max_parallel=4).run(specs, worker=worker)

    assert "b" in seen and "c" in seen
    # When d started, both b and c were already complete.
    pre_d = set(seen["d"])
    assert {"a", "b", "c"}.issubset(pre_d)


def test_same_level_runs_concurrently() -> None:
    from lyra_core.subagent.scheduler import SubagentScheduler

    started = threading.Event()
    started_count = 0
    lock = threading.Lock()

    def worker(spec: Any) -> dict:
        nonlocal started_count
        with lock:
            started_count += 1
            local = started_count
        if local == 1:
            # Wait for the second worker to also start before either returns.
            assert started.wait(timeout=2.0), "second worker never started"
        else:
            started.set()
        return {"id": spec.id}

    specs = _make_specs(("a", []), ("b", []))
    SubagentScheduler(max_parallel=2).run(specs, worker=worker)

    assert started.is_set()


def test_cycle_detected_before_any_worker_runs() -> None:
    from lyra_core.subagent.scheduler import SchedulerError, SubagentScheduler

    invoked: list[str] = []

    def worker(spec: Any) -> dict:
        invoked.append(spec.id)
        return {}

    specs = _make_specs(("a", ["b"]), ("b", ["a"]))
    with pytest.raises(SchedulerError, match="cycle"):
        SubagentScheduler(max_parallel=2).run(specs, worker=worker)
    assert invoked == []


def test_unknown_dep_is_caught() -> None:
    from lyra_core.subagent.scheduler import SchedulerError, SubagentScheduler

    specs = _make_specs(("a", ["nope"]))
    with pytest.raises(SchedulerError, match="nope"):
        SubagentScheduler(max_parallel=2).run(specs, worker=lambda _s: {})


def test_failure_skips_downstream() -> None:
    from lyra_core.subagent.scheduler import SubagentScheduler

    invoked: list[str] = []

    def worker(spec: Any) -> dict:
        invoked.append(spec.id)
        if spec.id == "a":
            raise RuntimeError("a blew up")
        return {"id": spec.id}

    specs = _make_specs(("a", []), ("b", ["a"]), ("c", ["b"]), ("d", []))
    out = SubagentScheduler(max_parallel=4).run(specs, worker=worker)

    by_id = {r.id: r for r in out.results}
    assert by_id["a"].status == "failed"
    assert by_id["b"].status == "skipped"
    assert by_id["c"].status == "skipped"
    # Independent node still ran.
    assert by_id["d"].status == "ok"
    # b and c were never invoked.
    assert "b" not in invoked
    assert "c" not in invoked
