"""Lyra Model Router — Intelligent model routing, capability matching, cost optimization.

Routes agent tasks to optimal LLM models based on capability scoring, cost constraints,
cross-model verification, and tool-usage gap detection. Supports tier-based routing with
budget tracking, usage analytics, and configurable model registry.
"""

from __future__ import annotations

from .capability_analyzer import CapabilityAnalyzer, TaskRequirements

from .cost_optimizer import BudgetLimit, CostOptimizer

from .cross_model_verifier import CrossModelVerifier, VerificationResult

from .exceptions import ModelRouterError

from .knowing_doing_gap import GapReport, KnowingDoingGapDetector

from .router_config import ModelCapability, RouterConfig, default_config

from .usage_tracker import UsageRecord, UsageStats, UsageTracker

__all__ = [
    # Capability Analyzer
    "TaskRequirements",
    "CapabilityAnalyzer",
    # Cost Optimizer
    "BudgetLimit",
    "CostOptimizer",
    # Cross-Model Verifier
    "VerificationResult",
    "CrossModelVerifier",
    # Exceptions
    "ModelRouterError",
    # Knowing-Doing Gap
    "GapReport",
    "KnowingDoingGapDetector",
    # Router Config
    "ModelCapability",
    "RouterConfig",
    "default_config",
    # Usage Tracker
    "UsageRecord",
    "UsageStats",
    "UsageTracker",
]
