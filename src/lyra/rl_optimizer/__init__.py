"""
RL Optimizer — Gradient-free prompt evolution and misevolution guardrails.

Core modules:
- ``GEPAOptimizer`` — Reflective prompt evolution loop (GEPA-style).
  Works on any provider (including closed models) because it operates
  at the prompt / skill level rather than on model weights.

- ``MisevolutionGuardrails`` — Four mandatory safety gates preventing
  the safety degradation documented in the Misevolve paper.

References
----------
- GEPA: Genetic-Pareto Evolutionary Prompt Optimisation (ICLR 2026 Oral)
  gepa-ai/gepa, arXiv:2507.19457
- SkillOpt: Validation-Gated Text Optimization (Microsoft Research)
  arXiv:2605.23904v2
- Misevolve: Safety Degradation in Self-Evolving Agents
  Shao et al., 2025, arXiv:2509.26354v2
"""

from lyra.rl_optimizer.gepa_optimizer import (
    GEPAOptimizer,
    Gene,
    GeneEvaluator,
    SkillOptMutator,
    VariantResult,
)
from lyra.rl_optimizer.evolution_guard import (
    MisevolutionGuardrails,
    EvolutionArtifact,
    GateResult,
    GateVerdict,
    GateType,
    RegressionGate,
    FrozenEvaluatorGate,
    HumanApprovalGate,
    ExecutionBiasDetector,
)
from lyra.rl_optimizer.maker_checker import (
    MakerChecker,
    Proposal,
    CheckResult,
    ProposalStatus,
)

__all__ = [
    # Optimizer
    "GEPAOptimizer",
    "Gene",
    "GeneEvaluator",
    "SkillOptMutator",
    "VariantResult",
    # Guardrails
    "MisevolutionGuardrails",
    "EvolutionArtifact",
    "GateResult",
    "GateVerdict",
    "GateType",
    "RegressionGate",
    "FrozenEvaluatorGate",
    "HumanApprovalGate",
    "ExecutionBiasDetector",
    # Maker-Checker
    "MakerChecker",
    "Proposal",
    "CheckResult",
    "ProposalStatus",
]
