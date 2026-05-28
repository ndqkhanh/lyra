"""Multi-Representation Agent (MRAgent) memory encoding.

Dual-encoder architecture for cross-modal memory retrieval — encodes
memories into dense (continuous vector) and sparse (symbolic/keyword)
representations for hybrid similarity search.
"""

from lyra_memory.mragent.dual_encoder import (
    DenseVector,
    DualEncodedMemory,
    DualEncoder,
    EncoderConfig,
    SparseVector,
)

__all__ = [
    "DenseVector",
    "DualEncodedMemory",
    "DualEncoder",
    "EncoderConfig",
    "SparseVector",
]
