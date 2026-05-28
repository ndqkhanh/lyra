"""
Modular Compression with Interference Control.

Formal interference bounds Δ_t(Q) ≤ ρ_t ε_t prove that stability is governed
by retrieval-update overlap. Modular design minimizes overlap; monolithic
designs (ρ_t ≈ 1) cannot localize interference.

Source: Modular Compression (ztmwHisqJ4), ICLR 2026 MemAgent Workshop.
"""

from lyra_memory.modular.composer import ComposerResult, CrossModuleComposer
from lyra_memory.modular.memory_module import (
    InterferenceTracker,
    ModularMemoryModule,
)
from lyra_memory.modular.sparse_router import ModularRouter, RouteDecision

__all__ = [
    "ComposerResult",
    "CrossModuleComposer",
    "InterferenceTracker",
    "ModularMemoryModule",
    "ModularRouter",
    "RouteDecision",
]
