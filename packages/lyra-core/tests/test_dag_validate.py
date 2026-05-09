"""Red tests for DAG validation."""
from __future__ import annotations

import pytest

from lyra_core.harnesses.dag_teams import (
    DAG,
    DAGValidationError,
    Node,
    validate_dag,
)


def test_simple_linear_dag_valid() -> None:
    dag = DAG(
        nodes=[Node(id="a"), Node(id="b", deps=["a"])],
        width_budget=4,
    )
    validate_dag(dag)  # no raise


def test_cycle_rejected() -> None:
    dag = DAG(
        nodes=[Node(id="a", deps=["b"]), Node(id="b", deps=["a"])],
        width_budget=4,
    )
    with pytest.raises(DAGValidationError):
        validate_dag(dag)


def test_unknown_dependency_rejected() -> None:
    dag = DAG(
        nodes=[Node(id="a", deps=["ghost"])],
        width_budget=4,
    )
    with pytest.raises(DAGValidationError):
        validate_dag(dag)


def test_unreferenced_node_rejected_when_strict() -> None:
    dag = DAG(
        nodes=[
            Node(id="a"),
            Node(id="unused"),  # no deps, no dependents, no sinks label
        ],
        sinks=["a"],
        width_budget=4,
    )
    with pytest.raises(DAGValidationError):
        validate_dag(dag, strict=True)


def test_width_budget_enforced() -> None:
    dag = DAG(
        nodes=[Node(id=str(i)) for i in range(6)],
        width_budget=4,
    )
    with pytest.raises(DAGValidationError):
        validate_dag(dag)


def test_duplicate_node_ids_rejected() -> None:
    dag = DAG(
        nodes=[Node(id="a"), Node(id="a")],
        width_budget=4,
    )
    with pytest.raises(DAGValidationError):
        validate_dag(dag)
