"""
Heterogeneous model collaboration for Lyra Research.

This module provides model routing, cross-model verification, prompt optimization,
cost optimization, and performance tracking across different LLM providers.
"""

from .model_router import ModelRouter
from .cross_model_verifier import CrossModelVerifier, VerificationResult
from .prompt_optimizer import PromptOptimizer
from .cost_optimizer import CostOptimizer
from .performance_tracker import ModelPerformanceTracker, ModelStats

__all__ = [
    "ModelRouter",
    "CrossModelVerifier",
    "VerificationResult",
    "PromptOptimizer",
    "CostOptimizer",
    "ModelPerformanceTracker",
    "ModelStats",
]
