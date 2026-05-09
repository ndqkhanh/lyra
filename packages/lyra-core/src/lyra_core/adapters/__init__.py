"""Adapter plugins for upstream orchestration strategies (v3.5+).

Renamed from :mod:`lyra_core.harnesses` in v3.5 because Lyra IS the
harness — these modules are *adapters* that plug Lyra into specific
orchestration shapes (single-agent loop, three-agent planner /
executor / verifier, DAG-team scheduler, etc.). The legacy import
path :mod:`lyra_core.harnesses` continues to work via a thin
re-export shim — see ``../harnesses/__init__.py``.
"""
from __future__ import annotations

from .base import HarnessPlugin, get_harness, register_harness
from .dag_teams import DAG, DAGValidationError, Node, Scheduler, validate_dag

__all__ = [
    "DAG",
    "DAGValidationError",
    "HarnessPlugin",
    "Node",
    "Scheduler",
    "get_harness",
    "register_harness",
    "validate_dag",
]
