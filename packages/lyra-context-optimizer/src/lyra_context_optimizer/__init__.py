"""Lyra Context Optimizer — Context window optimization for agent systems.

Provides agent-driven compaction, verbatim pruning, async compression with
judge-based validation, knowledge blocks that survive compaction, RTK-style
input compression, Caveman-style output compression, DACS switching, and
metrics tracking for compression effectiveness.
"""

from __future__ import annotations

from .agent_driven_compaction import (
    CompactionAction,
    CompactionDecider,
    CompactionPlanner,
    CompactionStrategy,
)
from .async_compactor import (
    AsyncCompactor,
    CompactionJudge,
    JudgeVerdict,
)
from .compression_metrics import (
    CompressionMetrics,
    MetricsReport,
    MetricsSnapshot,
    StrategyStats,
)
from .dacs_switcher import (
    DACSConfig,
    DACSManager,
    DACSMode,
)
from .exceptions import (
    CompactionError,
    CompressionError,
    ContextOptimizerError,
    DACSConfigError,
    FidelityLossError,
    KnowledgeBlockNotFoundError,
)
from .input_compressor import (
    CompressionResult,
    CompressionStrategy,
    InputCompressor,
)
from .knowledge_blocks import (
    KnowledgeBlock,
    KnowledgeBlockRegistry,
    PriorityLevel,
)
from .output_compressor import (
    CompressionConfig,
    OutputCompressor,
)
from .verbatim_pruner import (
    PruneResult,
    PruneStrategy,
    VerbatimPruner,
)

__all__ = [
    # Agent-driven compaction
    "CompactionDecider",
    "CompactionStrategy",
    "CompactionPlanner",
    "CompactionAction",
    # Verbatim pruner
    "VerbatimPruner",
    "PruneStrategy",
    "PruneResult",
    # Async compactor
    "AsyncCompactor",
    "CompactionJudge",
    "JudgeVerdict",
    # Knowledge blocks
    "KnowledgeBlock",
    "PriorityLevel",
    "KnowledgeBlockRegistry",
    # Input compressor
    "InputCompressor",
    "CompressionStrategy",
    "CompressionResult",
    # Output compressor
    "OutputCompressor",
    "CompressionConfig",
    # DACS switcher
    "DACSManager",
    "DACSMode",
    "DACSConfig",
    # Compression metrics
    "CompressionMetrics",
    "MetricsSnapshot",
    "StrategyStats",
    "MetricsReport",
    # Exceptions
    "ContextOptimizerError",
    "CompactionError",
    "CompressionError",
    "KnowledgeBlockNotFoundError",
    "DACSConfigError",
    "FidelityLossError",
]
