"""Lyra Context Optimizer — Context window optimization for agent systems.

Provides agent-driven compaction, verbatim pruning, async compression with
judge-based validation, knowledge blocks that survive compaction, RTK-style
input compression, Caveman-style output compression, DACS switching, and
metrics tracking for compression effectiveness.
"""

from __future__ import annotations

from .agent_driven_compaction import (
    CompactionDecider,
    CompactionStrategy,
    CompactionPlanner,
    CompactionAction,
)

from .verbatim_pruner import (
    VerbatimPruner,
    PruneStrategy,
    PruneResult,
)

from .async_compactor import (
    AsyncCompactor,
    CompactionJudge,
    JudgeVerdict,
)

from .knowledge_blocks import (
    KnowledgeBlock,
    PriorityLevel,
    KnowledgeBlockRegistry,
)

from .input_compressor import (
    InputCompressor,
    CompressionStrategy,
    CompressionResult,
)

from .output_compressor import (
    OutputCompressor,
    CompressionConfig,
)

from .dacs_switcher import (
    DACSManager,
    DACSMode,
    DACSConfig,
)

from .compression_metrics import (
    CompressionMetrics,
    MetricsSnapshot,
    StrategyStats,
    MetricsReport,
)

from .exceptions import (
    ContextOptimizerError,
    CompactionError,
    CompressionError,
    KnowledgeBlockNotFoundError,
    DACSConfigError,
    FidelityLossError,
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
