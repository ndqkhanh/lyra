"""harness_core.provenance — typed append-only witness ledger.

Per [docs/188-witness-provenance-memory-techniques-synthesis.md](../../../../../../research/harness-engineering/docs/188-witness-provenance-memory-techniques-synthesis.md)
and [docs/186-mnema-witness-lattice.md](../../../../../../research/harness-engineering/docs/186-mnema-witness-lattice.md).

A *witness* is a typed, content-addressed (SHA256) record of an event:
agent decision, tool result, verifier verdict, human approval, retrieval,
inference. Witnesses can cite *parent witnesses* — the provenance chain
records which prior witnesses justify a new claim.

Composes with:
    - :mod:`harness_core.forensic` — replay-log entries become witnesses.
    - :mod:`harness_core.isolation` — per-namespace witness scoping.
    - :mod:`harness_core.verifier` — composer verdicts become witnesses.
    - :mod:`harness_core.orchestration` — agent decisions become witnesses.
    - :mod:`harness_core.routines` — fires become witnesses.

Used by every project that needs auditable claim provenance — Polaris's
ProvenanceLedger ([docs/172] §2), Helix-Bio's KG-grounded fact attribution
([docs/219] §4.4), Aegis-Ops's incident replay ([docs/221] §3.5).
"""
from __future__ import annotations

from .lattice import WitnessLattice
from .ledger import ProvenanceLedger
from .types import Witness, WitnessKind, compute_witness_id

__all__ = [
    "ProvenanceLedger",
    "Witness",
    "WitnessKind",
    "WitnessLattice",
    "compute_witness_id",
]
