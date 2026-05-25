"""
Gated Memory Consolidation — selectively gates short-term memories
into long-term storage using salience-based thresholds and cooldown.
"""

from lyra_memory.consolidation.gated import ConsolidationGate, GateConfig, GatedMemory

__all__ = [
    "ConsolidationGate",
    "GateConfig",
    "GatedMemory",
]
