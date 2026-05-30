"""Benchmark integration for Lyra memory system.

This module provides benchmark runners for evaluating memory system performance
against standard benchmarks:
- LoCoMo: Long-context memory benchmark
- LongMemEval: Long-term conversational memory evaluation

Target metrics:
- LoCoMo: 93%+ accuracy
- LongMemEval: 95%+ accuracy
- Compression effectiveness tracking
"""

from lyra_memory.benchmarks.compression_tracker import (
    CompressionMetrics,
    CompressionReport,
    CompressionTracker,
    RetentionMetrics,
)
from lyra_memory.benchmarks.locomo_runner import (
    LoCoMoBenchmark,
    LoCoMoDocument,
    LoCoMoQuery,
    LoCoMoResult,
)
from lyra_memory.benchmarks.longmem_eval import (
    ConversationTurn,
    LongMemEvalBenchmark,
    LongMemEvalQuestion,
    LongMemEvalResult,
    QuestionType,
)

__all__ = [
    # LoCoMo
    "LoCoMoBenchmark",
    "LoCoMoDocument",
    "LoCoMoQuery",
    "LoCoMoResult",
    # LongMemEval
    "LongMemEvalBenchmark",
    "LongMemEvalQuestion",
    "LongMemEvalResult",
    "ConversationTurn",
    "QuestionType",
    # Compression
    "CompressionTracker",
    "CompressionMetrics",
    "CompressionReport",
    "RetentionMetrics",
]
