"""
RL Optimizer — Gradient-free prompt evolution, misevolution guardrails,
and advanced self-evolving features (GRPO, CODESKILL, CaTS).

Core modules:
- ``GEPAOptimizer`` — Reflective prompt evolution loop (GEPA-style).
  Works on any provider (including closed models) because it operates
  at the prompt / skill level rather than on model weights.

- ``MisevolutionGuardrails`` — Four mandatory safety gates preventing
  the safety degradation documented in the Misevolve paper.

- ``GRPOTrainer`` — MetaAgent-X-style Designer+Executor co-evolution
  via GRPO with GAE advantage estimation and KL penalty.

- ``SkillEnvironment`` / ``SkillAgent`` / ``EvolutionLoop`` — CODESKILL:
  self-evolving coding skills via reinforcement learning.

- ``CaTSScheduler`` — Calibrated Test-Time Scaling for efficient
  compute-effort allocation based on problem difficulty.

References
----------
- GEPA: Genetic-Pareto Evolutionary Prompt Optimisation (ICLR 2026 Oral)
  gepa-ai/gepa, arXiv:2507.19457
- SkillOpt: Validation-Gated Text Optimization (Microsoft Research)
  arXiv:2605.23904v2
- Misevolve: Safety Degradation in Self-Evolving Agents
  Shao et al., 2025, arXiv:2509.26354v2
- MetaAgent-X: End-to-End RL for Multi-Agent Workflow Optimization
  arXiv:2605.14212v1
- GRPO: Group Relative Policy Optimization
  Shao et al., 2024, arXiv:2402.03300v4
- CaTS: Calibrated Test-Time Scaling
  Zhu et al., 2025, arXiv:2509.18128v2
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
from lyra.rl_optimizer.grpo_trainer import (
    GRPOTrainer,
    GRPOConfig,
    DesignerPolicy,
    ExecutorPolicy,
    DesignerAction,
    ExecutorAction,
    TrainingBatch,
    GRPOOutput,
    compute_gae,
    compute_kl_penalty,
)
from lyra.rl_optimizer.codeskill import (
    SkillEnvironment,
    SkillAgent,
    EvolutionLoop,
    EvolutionLoopConfig,
    CodingTask,
    SkillExecution,
    EvolutionRecord,
    compute_reward,
)
from lyra.rl_optimizer.cats_scheduler import (
    CaTSScheduler,
    EffortBudget,
    Problem,
    DifficultyLevel,
    EarlyStoppingCriteria,
    StoppingDecision,
    compute_effort,
    compute_effort_continuous,
    adaptive_sampling,
    should_stop_early,
    classify_difficulty,
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
    # GRPO
    "GRPOTrainer",
    "GRPOConfig",
    "DesignerPolicy",
    "ExecutorPolicy",
    "DesignerAction",
    "ExecutorAction",
    "TrainingBatch",
    "GRPOOutput",
    "compute_gae",
    "compute_kl_penalty",
    # CODESKILL
    "SkillEnvironment",
    "SkillAgent",
    "EvolutionLoop",
    "EvolutionLoopConfig",
    "CodingTask",
    "SkillExecution",
    "EvolutionRecord",
    "compute_reward",
    # CaTS
    "CaTSScheduler",
    "EffortBudget",
    "Problem",
    "DifficultyLevel",
    "EarlyStoppingCriteria",
    "StoppingDecision",
    "compute_effort",
    "compute_effort_continuous",
    "adaptive_sampling",
    "should_stop_early",
    "classify_difficulty",
]
