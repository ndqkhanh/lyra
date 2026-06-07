"""
Safety module for Lyra.

Provides deterministic tool-call gating (P2: Breakthrough #3), a Policy
data model, the ToolGate class for intercepting and enforcing
least-privilege tool permissions, a defense-in-depth safety pipeline
(P3), and a self-evolving guardrails subsystem (P8).

Sub-modules
-----------
policy:
    ``Policy`` dataclass and ``GateDecision`` enum.
tool_gate:
    ``ToolGate`` — LLM-assisted policy generation + deterministic enforcement.
pipeline:
    ``SafetyPipeline`` — defense-in-depth safety pipeline orchestrating 5 layers.
evolution:
    ``EvolutionGuard`` — gated promotion system, ``FrozenEvaluator``,
    and ``HumanApprovalGate`` for self-evolving safety rules.
"""

from lyra.safety.evolution import (
    EvalCase,
    EvolutionGuard,
    FrozenEvaluator,
    HumanApprovalGate,
    RuleEvaluation,
    RuleMode,
    SafetyRule,
)
from lyra.safety.policy import GateDecision, Policy
from lyra.safety.tool_gate import ToolGate, _DEFAULT_POLICY as DEFAULT_POLICY

from lyra.safety.pipeline import (
    AlignmentCheck,
    ContinuousEval,
    DataFlowTracker,
    LayerDecision,
    LayerResult,
    LexicalGate,
    SafetyContext,
    SafetyPipeline,
    ToolCallGateLayer,
)

__all__ = [
    "Policy",
    "GateDecision",
    "ToolGate",
    "DEFAULT_POLICY",
    "SafetyPipeline",
    "SafetyContext",
    "LayerResult",
    "LayerDecision",
    "LexicalGate",
    "ToolCallGateLayer",
    "AlignmentCheck",
    "DataFlowTracker",
    "ContinuousEval",
    "SafetyRule",
    "RuleMode",
    "RuleEvaluation",
    "EvalCase",
    "EvolutionGuard",
    "FrozenEvaluator",
    "HumanApprovalGate",
]

__version__ = "3.1.0"
