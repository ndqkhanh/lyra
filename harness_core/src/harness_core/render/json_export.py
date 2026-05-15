"""JSON renderers — Trace, WitnessLattice, EvalRun → JSON-serialisable dicts.

Used for dashboards, CI artefacts, log aggregators. Pure-dict output (callers
``json.dumps`` themselves) so the renderer doesn't impose JSON-encoding
choices (indent, separators, default-handler).
"""
from __future__ import annotations

from typing import Any

from ..eval_runner import EvalRun
from ..provenance import WitnessLattice
from ..replay import Trace


def trace_to_json(trace: Trace) -> dict[str, Any]:
    """Render a :class:`Trace` as a JSON-serialisable dict."""
    return {
        "trace_id": trace.trace_id,
        "stats": trace.stats(),
        "events": [
            {
                "event_id": e.event_id,
                "kind": e.kind.value,
                "timestamp": e.timestamp,
                "issued_by": e.issued_by,
                "namespace_id": e.namespace_id,
                "payload": _serialise(e.payload),
                "parent_event_ids": list(e.parent_event_ids),
            }
            for e in trace.events
        ],
    }


def witness_lattice_to_json(lattice: WitnessLattice) -> dict[str, Any]:
    """Render a :class:`WitnessLattice` as a JSON-serialisable dict."""
    return {
        "stats": lattice.ledger.stats(),
        "witnesses": [
            {
                "witness_id": w.witness_id,
                "kind": w.kind.value,
                "issued_by": w.issued_by,
                "issued_at": w.issued_at,
                "content": _serialise(w.content),
                "parent_witnesses": list(w.parent_witnesses),
            }
            for w in lattice.ledger.witnesses_for()
        ],
    }


def eval_run_to_json(run: EvalRun) -> dict[str, Any]:
    """Render an :class:`EvalRun` as a JSON-serialisable dict."""
    return {
        "run_id": run.run_id,
        "suite_id": run.suite_id,
        "timestamp": run.timestamp,
        "metadata": _serialise(dict(run.metadata)),
        "summary": {
            "pass_rate": run.pass_rate,
            "mean_score": run.mean_score,
            "n_passed": run.n_passed,
            "n_failed": run.n_failed,
            "n_errors": run.n_errors,
            "total_cost_usd": run.total_cost_usd,
            "total_duration_ms": run.total_duration_ms,
        },
        "results": [
            {
                "result_id": r.result_id,
                "case_id": r.case_id,
                "score": r.score,
                "passed": r.passed,
                "actual_output": _serialise(r.actual_output),
                "cost_usd": r.cost_usd,
                "duration_ms": r.duration_ms,
                "error": r.error,
                "weight": r.weight,
                "timestamp": r.timestamp,
            }
            for r in run.results
        ],
    }


# --- Helpers ----------------------------------------------------------


def _serialise(obj: Any) -> Any:
    """Make an object JSON-serialisable.

    Best-effort: dicts → recursive serialise, lists/tuples → recursive list,
    sets → sorted list, frozensets → sorted list, primitives unchanged,
    everything else → str.
    """
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    if isinstance(obj, dict):
        return {str(k): _serialise(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_serialise(v) for v in obj]
    if isinstance(obj, (set, frozenset)):
        return sorted([_serialise(v) for v in obj], key=str)
    return str(obj)


__all__ = [
    "eval_run_to_json",
    "trace_to_json",
    "witness_lattice_to_json",
]
