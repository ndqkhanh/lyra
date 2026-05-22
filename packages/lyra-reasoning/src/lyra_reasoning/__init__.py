"""
Lyra Reasoning - Deep Reasoning Research Agent

A breakthrough reasoning system combining:
- Test-time compute scaling (o1/o3-style)
- Multiple reasoning engines (CoT, Tree Search, Debate, Hypothesis)
- Multi-level verification
- Reasoning memory and learning
- Self-improvement through evolution

Example:
    >>> from lyra_reasoning import DeepReasoningAgent
    >>> 
    >>> agent = DeepReasoningAgent()
    >>> result = agent.reason(
    ...     task="Analyze the impact of attention mechanisms in transformers",
    ...     strategy="auto",
    ...     depth="comprehensive"
    ... )
    >>> print(result.conclusion)
    >>> print(f"Verification score: {result.verification_score:.2f}")
"""

__version__ = "1.0.0"

from .agent import DeepReasoningAgent
from .types import (
    ReasoningConfig,
    ReasoningDepth,
    ReasoningResult,
    ReasoningStrategy,
    ReasoningTrace,
)

__all__ = [
    "DeepReasoningAgent",
    "ReasoningConfig",
    "ReasoningStrategy",
    "ReasoningDepth",
    "ReasoningResult",
    "ReasoningTrace",
]
