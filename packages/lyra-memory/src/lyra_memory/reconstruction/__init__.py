"""
Active Memory Reconstruction — MRAgent architecture (ICLR 2026 MemAgent Workshop).

Proves that active reconstruction via iterative cue-tag-content graph traversal
is strictly more expressive than passive retrieval (H_passive ⊊ H_active).

Core components:
    CueTagContentGraph     — Associative graph (Cue → Tag → Content → Cue)
    DualMemoryGraph        — Episodic + Semantic memory with active/passive retrieval
    ActiveReconstructionEngine — Beam search reconstruction via iterative graph traversal
"""

from lyra_memory.reconstruction.graph import CueTagContentGraph, GraphNode, NodeType
from lyra_memory.reconstruction.dual_memory import DualMemoryGraph, ReconstructionProof
from lyra_memory.reconstruction.engine import (
    ActiveReconstructionEngine,
    MemoryEvidence,
    ReconstructionResult,
    ReconstructionTrace,
)

__all__ = [
    "ActiveReconstructionEngine",
    "CueTagContentGraph",
    "DualMemoryGraph",
    "GraphNode",
    "MemoryEvidence",
    "NodeType",
    "ReconstructionProof",
    "ReconstructionResult",
    "ReconstructionTrace",
]
