"""Task-Phase-Aware Model Routing — P3-B5.

Routes model selection by agent lifecycle phase. Planning tasks prefer deep
reasoning models (opus), execution prefers fast capable models (sonnet),
review prefers an independent model for unbiased evaluation.

Composes with the EffortRouter (P3-B3) for provider selection and token budgets.
Supports YAML policy overrides for phase→model mappings.

See: plan-phase3-skills-routing.md §B5, plan-phase5-master-plan.md §P3-B5
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field

from lyra.harness_core.providers import ProviderKind
from lyra.harness_core.routing.effort_router import EffortDecision, EffortRouter, EffortTier


class AgentPhase(str, enum.Enum):
    """Agent lifecycle phases for phase-aware routing.

    PLANNING — architecture design, task decomposition, strategy
    EXECUTION — implementation, code generation, tool use
    REVIEW — quality verification, code review, test evaluation
    RESEARCH — deep investigation, literature review, analysis
    ORCHESTRATION — multi-agent coordination, task dispatch
    """

    PLANNING = "planning"
    EXECUTION = "execution"
    REVIEW = "review"
    RESEARCH = "research"
    ORCHESTRATION = "orchestration"


@dataclass(frozen=True)
class PhaseConfig:
    """Provider + effort configuration for a single agent phase."""

    phase: AgentPhase
    provider: ProviderKind           # preferred provider family for this phase
    effort: EffortTier               # effort tier for token budget
    description: str = ""

    @classmethod
    def defaults(cls) -> dict[AgentPhase, "PhaseConfig"]:
        """Factory-default phase configurations.

        Planning → opus (deep reasoning for architecture)
        Execution → sonnet (fast, capable coding)
        Review → sonnet (independent review model, different temperature)
        Research → opus (deep investigation, synthesis)
        Orchestration → haiku/sonnet (lightweight coordination)
        """
        return {
            AgentPhase.PLANNING: cls(
                phase=AgentPhase.PLANNING,
                provider=ProviderKind.ANTHROPIC,
                effort=EffortTier.HIGH,
                description="Deep reasoning for architecture design and task decomposition",
            ),
            AgentPhase.EXECUTION: cls(
                phase=AgentPhase.EXECUTION,
                provider=ProviderKind.ANTHROPIC,
                effort=EffortTier.MEDIUM,
                description="Fast capable coding and tool execution",
            ),
            AgentPhase.REVIEW: cls(
                phase=AgentPhase.REVIEW,
                provider=ProviderKind.ANTHROPIC,
                effort=EffortTier.HIGH,
                description="Independent review with high reasoning budget",
            ),
            AgentPhase.RESEARCH: cls(
                phase=AgentPhase.RESEARCH,
                provider=ProviderKind.ANTHROPIC,
                effort=EffortTier.XHIGH,
                description="Deep investigation and research synthesis",
            ),
            AgentPhase.ORCHESTRATION: cls(
                phase=AgentPhase.ORCHESTRATION,
                provider=ProviderKind.ANTHROPIC,
                effort=EffortTier.LOW,
                description="Lightweight multi-agent coordination",
            ),
        }


@dataclass(frozen=True)
class PhaseDecision:
    """Result of phase-aware routing."""

    phase: AgentPhase
    provider: ProviderKind
    effort: EffortTier
    max_tokens: int
    is_fallback: bool = False
    reason: str = ""


@dataclass
class PhaseRouter:
    """Routes tasks to models based on agent lifecycle phase.

    Composes with EffortRouter for provider selection and token budgets.
    Each phase maps to a preferred provider + effort tier. The effort
    tier determines the token budget via EffortRouter.

    Usage::

        router = PhaseRouter()
        decision = router.route(AgentPhase.PLANNING)
        # decision.provider → ProviderKind.ANTHROPIC
        # decision.effort → EffortTier.HIGH
        # decision.max_tokens → 8192
    """

    phase_configs: dict[AgentPhase, PhaseConfig] = field(
        default_factory=PhaseConfig.defaults
    )
    effort_router: EffortRouter = field(default_factory=EffortRouter)

    def route(self, phase: AgentPhase) -> PhaseDecision:
        """Route a lifecycle phase to a concrete provider + token budget.

        Args:
            phase: The agent lifecycle phase.

        Returns:
            A PhaseDecision with the chosen provider, effort tier, and max_tokens.

        Raises:
            ValueError: If the phase is not configured or no provider is available.
        """
        config = self.phase_configs.get(phase)
        if config is None:
            raise ValueError(f"unknown agent phase: {phase}")

        # Route via effort router, using the phase's preferred provider
        effort_decision = self.effort_router.route_with_override(
            effort=config.effort,
            preferred_override=config.provider,
        )

        return PhaseDecision(
            phase=phase,
            provider=effort_decision.provider,
            effort=config.effort,
            max_tokens=effort_decision.max_tokens,
            is_fallback=effort_decision.is_fallback,
            reason=effort_decision.reason,
        )

    def set_phase_config(self, phase: AgentPhase, config: PhaseConfig) -> None:
        """Override the configuration for a specific phase."""
        self.phase_configs[phase] = config

    def get_config(self, phase: AgentPhase) -> PhaseConfig | None:
        """Get the PhaseConfig for a phase, or None if not configured."""
        return self.phase_configs.get(phase)

    @classmethod
    def from_policy_dict(
        cls,
        policy: dict,
        base_effort_router: EffortRouter | None = None,
    ) -> "PhaseRouter":
        """Build a PhaseRouter from a policy dictionary (e.g., loaded from YAML).

        Policy format::

            phases:
              planning:
                provider: anthropic
                effort: high
              execution:
                provider: deepseek
                effort: medium

        Args:
            policy: Dict with a 'phases' key mapping phase names to config dicts.
            base_effort_router: Optional pre-configured EffortRouter.

        Returns:
            A configured PhaseRouter instance.
        """
        router = cls(effort_router=base_effort_router or EffortRouter())

        phases_raw = policy.get("phases", {})
        for phase_name, phase_cfg in phases_raw.items():
            try:
                phase = AgentPhase(phase_name)
            except ValueError:
                continue  # skip unknown phases

            provider_str = phase_cfg.get("provider", "anthropic")
            provider = _parse_provider(provider_str)

            effort_str = phase_cfg.get("effort", "medium")
            try:
                effort = EffortTier(effort_str)
            except ValueError:
                effort = EffortTier.MEDIUM

            router.set_phase_config(
                phase,
                PhaseConfig(
                    phase=phase,
                    provider=provider,
                    effort=effort,
                    description=phase_cfg.get("description", ""),
                ),
            )

        return router


def _parse_provider(raw: str) -> ProviderKind:
    """Parse a provider string into a ProviderKind, with fallback to ANTHROPIC."""
    provider_map = {p.value: p for p in ProviderKind}
    return provider_map.get(raw.lower(), ProviderKind.ANTHROPIC)


# --- Phase inference from task description -----------------------------------


_PHASE_KEYWORD_MAP: dict[str, AgentPhase] = {
    # Planning
    "plan": AgentPhase.PLANNING,
    "design": AgentPhase.PLANNING,
    "architect": AgentPhase.PLANNING,
    "decompose": AgentPhase.PLANNING,
    "break down": AgentPhase.PLANNING,
    "strategy": AgentPhase.PLANNING,
    # Execution
    "implement": AgentPhase.EXECUTION,
    "write code": AgentPhase.EXECUTION,
    "fix": AgentPhase.EXECUTION,
    "refactor": AgentPhase.EXECUTION,
    # Review
    "review": AgentPhase.REVIEW,
    "audit": AgentPhase.REVIEW,
    "verify": AgentPhase.REVIEW,
    "check": AgentPhase.REVIEW,
    "evaluate": AgentPhase.REVIEW,
    # Research
    "research": AgentPhase.RESEARCH,
    "investigate": AgentPhase.RESEARCH,
    "analyze": AgentPhase.RESEARCH,
    "explore": AgentPhase.RESEARCH,
    "study": AgentPhase.RESEARCH,
    # Orchestration
    "orchestrate": AgentPhase.ORCHESTRATION,
    "coordinate": AgentPhase.ORCHESTRATION,
    "dispatch": AgentPhase.ORCHESTRATION,
    "delegate": AgentPhase.ORCHESTRATION,
}


def infer_phase(description: str) -> AgentPhase:
    """Infer the agent lifecycle phase from a task description.

    Heuristic keyword matching; production can layer an LM classifier.

    >>> infer_phase("design a new caching architecture")
    <AgentPhase.PLANNING: 'planning'>
    >>> infer_phase("implement the user authentication module")
    <AgentPhase.EXECUTION: 'execution'>
    >>> infer_phase("review the PR for security issues")
    <AgentPhase.REVIEW: 'review'>
    """
    desc_lower = description.lower()

    phase_scores: dict[AgentPhase, int] = dict.fromkeys(AgentPhase, 0)
    for keyword, phase in _PHASE_KEYWORD_MAP.items():
        if keyword in desc_lower:
            phase_scores[phase] += 1

    max_score = max(phase_scores.values())
    if max_score > 0:
        # Execution wins ties (most common phase)
        priority = (
            AgentPhase.EXECUTION,
            AgentPhase.PLANNING,
            AgentPhase.REVIEW,
            AgentPhase.RESEARCH,
            AgentPhase.ORCHESTRATION,
        )
        for phase in priority:
            if phase_scores[phase] == max_score:
                return phase

    # Default: execution for short commands, planning for longer descriptions
    if len(description.split()) <= 5:
        return AgentPhase.EXECUTION
    return AgentPhase.PLANNING


__all__ = [
    "AgentPhase",
    "PhaseConfig",
    "PhaseDecision",
    "PhaseRouter",
    "infer_phase",
]
