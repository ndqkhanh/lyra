"""
Lyra Auto-Compaction Engine — AOI-style compression with progressive disclosure.

Implements context optimization patterns from:
- AOI (ICLR 2026): Observer/Probe/Executor 3-agent compression, 72.4% compression
- Norm-Guided KV-Cache Eviction: ℓ2-norm key vector scoring
- R-KVHash: SimHash/LSH redundant token eviction, ~2× decoding throughput

Key capabilities:
- Adaptive compression: compress when context exceeds threshold
- Progressive disclosure: 3-level loading (metadata→body→references)
- Token budgeting: hard cap on context tokens per turn
"""

from __future__ import annotations

from .compactor import AutoCompactor, CompactResult, CompactionStrategy

__all__ = ["AutoCompactor", "CompactResult", "CompactionStrategy"]
