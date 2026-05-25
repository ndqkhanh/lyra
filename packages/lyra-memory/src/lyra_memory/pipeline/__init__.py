"""
CoMem — k-step-off Asynchronous Decoupled Memory Pipeline.

A smaller memory compression model compresses history in the background
while the main agent decodes, trained via GRPO with functional equivalence
rewards. Achieves 1.4x latency improvement.

Source: CoMem (tc9GAKlxQC), ICLR 2026 MemAgent Workshop.
"""

from lyra_memory.pipeline.comem import CoMemPipeline, CompressionJob, CompressedContext
from lyra_memory.pipeline.kv_cache import KVCacheCompressor, RKVHash

__all__ = [
    "CoMemPipeline",
    "CompressedContext",
    "CompressionJob",
    "KVCacheCompressor",
    "RKVHash",
]
