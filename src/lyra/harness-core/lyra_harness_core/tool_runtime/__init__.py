"""lyra_harness_core.tool_runtime — guarded tool execution composing harness primitives.

The package wraps :class:`lyra_harness_core.tools.ToolRegistry` with a configurable
guard chain:

    - :class:`lyra_harness_core.verifier.VerifierComposer` — pre-call multi-axis gate.
    - :class:`lyra_harness_core.evals.BudgetController` — pre-call token reservation.
    - :class:`lyra_harness_core.cost.CostTracker` — post-call cost recording.
    - :class:`lyra_harness_core.provenance.WitnessLattice` — post-call witness trail.
    - :class:`lyra_harness_core.replay.TraceBuilder` — post-call event log.
    - :class:`RetryPolicy` — transient-failure retry with backoff.

Returns :class:`ToolExecution` capturing every gate decision + the result.

Used by Orion-Code (sandbox tool dispatch), Aegis-Ops (post-mortem-grade audit
on every action), Polaris (research tool calls with budget caps), Helix-Bio
(HITL-gated tool dispatch), Atlas-Research (cost-attributed synthesis tools).
"""
from __future__ import annotations

from .engine import ToolEngine
from .retry import ExponentialBackoff, NoRetry
from .types import RetryPolicy, ToolExecution

__all__ = [
    "ExponentialBackoff",
    "NoRetry",
    "RetryPolicy",
    "ToolEngine",
    "ToolExecution",
]
