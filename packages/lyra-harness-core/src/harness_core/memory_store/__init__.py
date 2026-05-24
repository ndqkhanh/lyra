"""harness_core.memory_store — typed layered memory primitive.

Per [docs/184-strongest-memory-techniques-synthesis-may-2026.md](../../../../../../research/harness-engineering/docs/184-strongest-memory-techniques-synthesis-may-2026.md),
[docs/185-memory-integration-playbook.md](../../../../../../research/harness-engineering/docs/185-memory-integration-playbook.md),
[docs/186-mnema-witness-lattice.md](../../../../../../research/harness-engineering/docs/186-mnema-witness-lattice.md),
[docs/187-multi-agent-shared-memory-landscape.md](../../../../../../research/harness-engineering/docs/187-multi-agent-shared-memory-landscape.md).

A *layered* memory store with four canonical kinds:

    - **SEMANTIC** — general facts the agent knows about the world.
    - **EPISODIC** — specific past events the agent participated in.
    - **WORKING** — bounded scratchpad for the current task (separate
      :class:`WorkingMemory` class with capacity cap).
    - **PROCEDURAL** — how-to skills (largely covered by :mod:`harness_core.skill_auto`).

Composes with:
    - :mod:`harness_core.isolation` — namespace-scoped memory.
    - :mod:`harness_core.provenance` — every write can be witnessed.
    - :mod:`harness_core.constitution` — per-user memory by namespace=user_id.
    - :mod:`harness_core.forensic` — replay reconstructs memory state.

Used by Mentat-Learn (per-channel persistent memory per [docs/210]),
Lyra (procedural memory per [docs/208] V3.7-V3.10),
Polaris (research notes per [docs/172]),
Helix-Bio (per-project lab notes), and any project that needs typed,
namespace-scoped persistent knowledge with retrieval.
"""
from __future__ import annotations

from .store import MemoryStore
from .types import MemoryItem, MemoryKind, RetrievalSpec
from .working import WorkingMemory

__all__ = [
    "MemoryItem",
    "MemoryKind",
    "MemoryStore",
    "RetrievalSpec",
    "WorkingMemory",
]
