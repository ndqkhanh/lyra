"""
Optimization module for token cost reduction.

Achieves 60-70% cost reduction through:
- Intelligent model selection
- Prompt caching
- Context compression
- Output limiting
"""

from optimization.token_optimizer import (
    ContextCompressor,
    CostMetrics,
    LLMRequest,
    ModelSelector,
    ModelTier,
    OptimizedRequest,
    PromptCacheManager,
    TaskType,
    TokenOptimizer,
)

__version__ = "0.1.0"

__all__ = [
    # Enums
    "TaskType",
    "ModelTier",
    # Data types
    "LLMRequest",
    "OptimizedRequest",
    "CostMetrics",
    # Components
    "ModelSelector",
    "ContextCompressor",
    "PromptCacheManager",
    # Main optimizer
    "TokenOptimizer",
]
