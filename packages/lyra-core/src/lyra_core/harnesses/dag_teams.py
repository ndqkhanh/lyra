"""Deprecated re-export: :mod:`lyra_core.harnesses.dag_teams` → :mod:`lyra_core.adapters.dag_teams`."""
from __future__ import annotations

from lyra_core.adapters.dag_teams import (
    DAG,
    DAGValidationError,
    Node,
    Scheduler,
    validate_dag,
)

__all__ = ["DAG", "DAGValidationError", "Node", "Scheduler", "validate_dag"]
