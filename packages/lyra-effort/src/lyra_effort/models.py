"""
Data models for the Lyra Effort Scale.

Defines the six effort levels, per-provider effort mappings, and the
orchestration configuration that distinguishes ``ultracode`` from ``xhigh``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class EffortLevel(str, Enum):
    """
    Six-item effort scale — mirrors Claude Code's `/effort` menu.

    Levels **low** through **max** control reasoning budget.
    **ultracode** is special: it sends ``xhigh`` to the model AND flips on
    auto-orchestration — it is NOT a distinct 6th API budget tier.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    XHIGH = "xhigh"
    MAX = "max"
    ULTRACODE = "ultracode"

    @property
    def is_persistent(self) -> bool:
        """
        ``low`` through ``xhigh`` persist across sessions.
        ``max`` and ``ultracode`` are session-only (reset on restart).
        """
        return self in (EffortLevel.LOW, EffortLevel.MEDIUM, EffortLevel.HIGH, EffortLevel.XHIGH)

    @property
    def reasoning_budget(self) -> int:
        """
        Default reasoning budget in tokens for this effort level.

        These are the Anthropic ``budget_tokens`` equivalents; other providers
        translate these into prompt instructions or ``reasoning_effort`` params.
        """
        return _DEFAULT_BUDGETS[self]

    @property
    def orchestration_enabled(self) -> bool:
        """Only ``ultracode`` enables automatic workflow orchestration."""
        return self == EffortLevel.ULTRACODE


# Default Anthropic budget_tokens per effort level
_DEFAULT_BUDGETS: dict[EffortLevel, int] = {
    EffortLevel.LOW: 1024,
    EffortLevel.MEDIUM: 4096,
    EffortLevel.HIGH: 8192,
    EffortLevel.XHIGH: 16384,
    EffortLevel.MAX: 32000,
    EffortLevel.ULTRACODE: 16384,  # Same as xhigh — orchestration is the difference
}


@dataclass(frozen=True)
class EffortMapping:
    """
    Per-provider effort translation.

    Each provider maps the six effort levels to its own API primitives.
    For Anthropic that's ``budget_tokens``; for DeepSeek it's a prompt-level
    thinking instruction; for OpenAI it's ``reasoning_effort``.

    Attributes:
        level: The Lyra effort level this mapping applies to.
        provider: Provider identifier (``anthropic``, ``deepseek``, ``openai``, ``google``).
        budget_tokens: Token budget for reasoning (Anthropic native; advisory for others).
        thinking_instruction: Prompt-level instruction for models without a native
            reasoning-budget API (DeepSeek, open-weights).
        reasoning_effort: OpenAI ``reasoning_effort`` parameter value.
        max_tokens_per_turn: Hard cap on output tokens per turn.
        orchestration_enabled: Whether auto-orchestration is active (True only for ultracode).
    """

    level: EffortLevel
    provider: str
    budget_tokens: int
    thinking_instruction: str = ""
    reasoning_effort: str = ""
    max_tokens_per_turn: int = 4096
    orchestration_enabled: bool = False


@dataclass(frozen=True)
class OrchestrationConfig:
    """
    Configuration for the auto-orchestration toggle (Primitive 2).

    Attributes:
        enabled: Whether auto-orchestration is active.
        auto_trigger_threshold: Minimum task complexity to auto-trigger a workflow.
            One of ``trivial``, ``low``, ``medium``, ``high``, ``all``.
        keyword_trigger_enabled: Whether the ``workflow`` keyword in user prompts
            triggers a one-off workflow without changing session effort.
    """

    enabled: bool = False
    auto_trigger_threshold: str = "medium"
    keyword_trigger_enabled: bool = True


@dataclass(frozen=True)
class ProviderEffortCapability:
    """
    Documents what effort-related features a provider supports.

    Used by the effort manager to decide which strategy to use for each provider.

    Attributes:
        provider: Provider identifier.
        supports_budget_tokens: Has a native API parameter for reasoning budget.
        supports_reasoning_effort: Has a native ``reasoning_effort`` API parameter.
        supports_prompt_instructions: Can follow prompt-level thinking instructions.
        max_effort_level: The highest effort level this provider supports.
    """

    provider: str
    supports_budget_tokens: bool = False
    supports_reasoning_effort: bool = False
    supports_prompt_instructions: bool = True
    max_effort_level: EffortLevel = EffortLevel.HIGH


@dataclass(frozen=True)
class EffortConfig:
    """
    Session-level effort configuration, persisted to ``.lyra/config.json``.

    Attributes:
        current_level: Active effort level.
        orchestration: Orchestration toggle configuration.
        provider_overrides: Per-provider effort level overrides, if any.
    """

    current_level: EffortLevel = EffortLevel.HIGH
    orchestration: OrchestrationConfig = field(default_factory=OrchestrationConfig)
    provider_overrides: dict[str, EffortLevel] = field(default_factory=dict)
