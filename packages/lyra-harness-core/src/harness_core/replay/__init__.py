"""harness_core.replay — unified trace primitive for incident replay + audit.

Composes :mod:`harness_core.provenance` witnesses + :mod:`harness_core.forensic`
trajectories + :mod:`harness_core.orchestration` decisions into one typed
:class:`Trace` that supports:

    1. **Incident replay** — Aegis-Ops post-mortem reconstruction.
    2. **Sabotage detection** — diff against reference traces (Orion/Cipher).
    3. **Audit reconstruction** — provenance-grounded claim attribution
       (Polaris/Helix).
    4. **Deterministic re-execution** — replay agent decisions through pure-
       function policies to confirm the trace reproduces.

Per [docs/188-witness-provenance-memory-techniques-synthesis.md](../../../../../../research/harness-engineering/docs/188-witness-provenance-memory-techniques-synthesis.md)
+ [docs/186-mnema-witness-lattice.md](../../../../../../research/harness-engineering/docs/186-mnema-witness-lattice.md)
+ [docs/220-orion-code-multi-hop-collaborative-apply-plan.md](../../../../../../research/harness-engineering/docs/220-orion-code-multi-hop-collaborative-apply-plan.md) §4.9
+ [docs/221-aegis-ops-multi-hop-collaborative-apply-plan.md](../../../../../../research/harness-engineering/docs/221-aegis-ops-multi-hop-collaborative-apply-plan.md) §3.5.
"""
from __future__ import annotations

from .builder import TraceBuilder
from .comparator import TraceComparator, TraceDelta, TraceDeltaKind
from .types import ReplayEvent, ReplayEventKind, Trace

__all__ = [
    "ReplayEvent",
    "ReplayEventKind",
    "Trace",
    "TraceBuilder",
    "TraceComparator",
    "TraceDelta",
    "TraceDeltaKind",
]
