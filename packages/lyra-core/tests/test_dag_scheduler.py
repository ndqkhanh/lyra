"""Red tests for DAG scheduler: topological batches + partial-failure policy."""
from __future__ import annotations

from lyra_core.harnesses.dag_teams import (
    DAG,
    Node,
    Scheduler,
)


def test_topological_order_simple() -> None:
    dag = DAG(
        nodes=[Node(id="a"), Node(id="b", deps=["a"]), Node(id="c", deps=["b"])],
        width_budget=4,
    )
    batches = Scheduler().batches(dag)
    assert batches == [["a"], ["b"], ["c"]]


def test_parallel_batch() -> None:
    dag = DAG(
        nodes=[
            Node(id="root"),
            Node(id="a", deps=["root"]),
            Node(id="b", deps=["root"]),
            Node(id="c", deps=["root"]),
            Node(id="leaf", deps=["a", "b", "c"]),
        ],
        width_budget=4,
    )
    batches = Scheduler().batches(dag)
    assert batches[0] == ["root"]
    assert set(batches[1]) == {"a", "b", "c"}
    assert batches[2] == ["leaf"]


def test_width_cap_applied() -> None:
    dag = DAG(
        nodes=[
            Node(id="root"),
            Node(id="a", deps=["root"]),
            Node(id="b", deps=["root"]),
            Node(id="c", deps=["root"]),
            Node(id="d", deps=["root"]),
        ],
        width_budget=2,
    )
    batches = Scheduler().batches(dag)
    # After root, four sibling tasks must be split into 2-wide batches.
    assert len(batches) >= 3
    for b in batches[1:]:
        assert len(b) <= 2


def test_partial_failure_propagates_to_descendants() -> None:
    """If 'a' fails, 'b' (dep=a) and 'leaf' (dep=b) must be marked skipped."""
    dag = DAG(
        nodes=[
            Node(id="a"),
            Node(id="b", deps=["a"]),
            Node(id="leaf", deps=["b"]),
        ],
        width_budget=4,
    )
    failures = {"a"}
    skipped = Scheduler().propagate_failures(dag, failed_ids=failures)
    assert skipped == {"b", "leaf"}
