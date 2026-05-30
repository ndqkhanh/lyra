"""Multi-Representation Agent (MRAgent) memory encoding.

Dual-encoder architecture for cross-modal memory retrieval — encodes
memories into dense (continuous vector) and sparse (symbolic/keyword)
representations for hybrid similarity search.

MRAgent-style dual-path encoding:
  - Cue-tag-episode: Context-aware episodic memory
  - Cue-tag-semantic: Fact-aware semantic memory
  - RRF fusion: Reciprocal Rank Fusion for 98%+ Precision@5
"""

from lyra_memory.mragent.cue_tag_episode import (
    CueTagEpisodeEncoder,
    EpisodeEncoding,
)
from lyra_memory.mragent.cue_tag_semantic import (
    CueTagSemanticEncoder,
    SemanticEncoding,
)
from lyra_memory.mragent.dual_encoder import (
    DenseVector,
    DualEncodedMemory,
    DualEncoder,
    EncoderConfig,
    MRAgentDualEncoder,
    SparseVector,
)

__all__ = [
    # Original dual encoder
    "DenseVector",
    "DualEncodedMemory",
    "DualEncoder",
    "EncoderConfig",
    "SparseVector",
    # MRAgent dual-path encoding
    "CueTagEpisodeEncoder",
    "CueTagSemanticEncoder",
    "EpisodeEncoding",
    "MRAgentDualEncoder",
    "SemanticEncoding",
]
