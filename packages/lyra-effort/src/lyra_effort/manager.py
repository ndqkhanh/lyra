"""
Effort Manager — maps Lyra's six-item effort scale to provider-specific API parameters.

Core design principle: **ultracode = xhigh + orchestration toggle**, NOT a 6th API
budget tier. This makes the effort scale portable to providers that only expose a
couple of effort levels (DeepSeek, open-weights).

Implements the per-provider mapping table from the ultracode replication plan §3.1
with Dynamic Effort Calibration (§3.2 Breakthrough).
"""

from __future__ import annotations

import logging
from .models import (
    EffortConfig,
    EffortLevel,
    EffortMapping,
    OrchestrationConfig,
    ProviderEffortCapability,
)

logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────────────
# Per-provider EFFORT-SPECIFIC capability declarations
#
# These complement (do NOT duplicate) lyra_provider.CapabilityMatrix:
# - CapabilityMatrix: general features (tool_calling, vision, streaming)
# - _PROVIDER_CAPABILITIES: effort-specific features (budget_tokens,
#   reasoning_effort, max_effort_level)
#
# The two are intentionally separate concerns. EffortManager queries
# CapabilityMatrix for general features, and _PROVIDER_CAPABILITIES
# for effort-specific clamping.
# ────────────────────────────────────────────────────────────────────

_PROVIDER_CAPABILITIES: dict[str, ProviderEffortCapability] = {
    "anthropic": ProviderEffortCapability(
        provider="anthropic",
        supports_budget_tokens=True,
        supports_reasoning_effort=False,
        supports_prompt_instructions=True,
        max_effort_level=EffortLevel.MAX,
    ),
    "deepseek": ProviderEffortCapability(
        provider="deepseek",
        supports_budget_tokens=False,
        supports_reasoning_effort=False,
        supports_prompt_instructions=True,
        max_effort_level=EffortLevel.XHIGH,
    ),
    "openai": ProviderEffortCapability(
        provider="openai",
        supports_budget_tokens=False,
        supports_reasoning_effort=True,
        supports_prompt_instructions=True,
        max_effort_level=EffortLevel.XHIGH,
    ),
    "google": ProviderEffortCapability(
        provider="google",
        supports_budget_tokens=False,
        supports_reasoning_effort=False,
        supports_prompt_instructions=True,
        max_effort_level=EffortLevel.HIGH,
    ),
    "openrouter": ProviderEffortCapability(
        provider="openrouter",
        supports_budget_tokens=True,
        supports_reasoning_effort=False,
        supports_prompt_instructions=True,
        max_effort_level=EffortLevel.MAX,
    ),
    "openweights": ProviderEffortCapability(
        provider="openweights",
        supports_budget_tokens=False,
        supports_reasoning_effort=False,
        supports_prompt_instructions=True,
        max_effort_level=EffortLevel.HIGH,
    ),
}

# ────────────────────────────────────────────────────────────────────
# Per-provider thinking instructions (for providers without native API)
# ────────────────────────────────────────────────────────────────────

_THINKING_INSTRUCTIONS: dict[str, dict[EffortLevel, str]] = {
    "deepseek": {
        EffortLevel.LOW: "Be concise. No thinking needed.",
        EffortLevel.MEDIUM: "Think briefly before answering.",
        EffortLevel.HIGH: "Think step by step before answering.",
        EffortLevel.XHIGH: "Think deeply. Consider alternatives. Verify your reasoning.",
        EffortLevel.MAX: "Maximum reasoning. Explore all angles. Consider edge cases. Verify thoroughly.",
        EffortLevel.ULTRACODE: "Think deeply. Consider alternatives. Verify your reasoning.",
    },
    "google": {
        EffortLevel.LOW: "Be concise. No thinking needed.",
        EffortLevel.MEDIUM: "Think briefly before answering.",
        EffortLevel.HIGH: "Think step by step before answering.",
        EffortLevel.XHIGH: "Think deeply. Consider alternatives. Verify your reasoning.",
        EffortLevel.MAX: "Maximum reasoning. Explore all angles. Consider edge cases. Verify thoroughly.",
        EffortLevel.ULTRACODE: "Think deeply. Consider alternatives. Verify your reasoning.",
    },
    "openweights": {
        EffortLevel.LOW: "Quick answer:",
        EffortLevel.MEDIUM: "Brief analysis:",
        EffortLevel.HIGH: "Careful analysis:",
        EffortLevel.XHIGH: "Deep analysis:",
        EffortLevel.MAX: "Deep analysis:",
        EffortLevel.ULTRACODE: "Deep analysis:",
    },
}

# ────────────────────────────────────────────────────────────────────
# OpenAI reasoning_effort mapping
# ────────────────────────────────────────────────────────────────────

_OPENAI_REASONING_EFFORT: dict[EffortLevel, str] = {
    EffortLevel.LOW: "low",
    EffortLevel.MEDIUM: "low",
    EffortLevel.HIGH: "medium",
    EffortLevel.XHIGH: "high",
    EffortLevel.MAX: "high",
    EffortLevel.ULTRACODE: "high",
}

# ────────────────────────────────────────────────────────────────────
# Max tokens per turn (hard cap)
# ────────────────────────────────────────────────────────────────────

_MAX_TOKENS: dict[EffortLevel, int] = {
    EffortLevel.LOW: 2048,
    EffortLevel.MEDIUM: 4096,
    EffortLevel.HIGH: 8192,
    EffortLevel.XHIGH: 16384,
    EffortLevel.MAX: 32768,
    EffortLevel.ULTRACODE: 16384,
}


class EffortManager:
    """
    Maps Lyra's six-item effort scale to provider-specific API parameters.

    Each provider gets a tailored :class:`EffortMapping` that translates
    the abstract effort level into concrete API primitives:

    - **Anthropic**: native ``budget_tokens`` API parameter
    - **DeepSeek**: prompt-level thinking instruction appended to system prompt
    - **OpenAI**: ``reasoning_effort`` API parameter
    - **Google**: prompt-level thinking instruction
    - **Open-weights**: prefix prepended to first user message

    Usage::

        mgr = EffortManager()
        mapping = mgr.map_effort(EffortLevel.XHIGH, provider="deepseek")
        # mapping.thinking_instruction == "Think deeply. Consider alternatives. Verify."
        # mapping.budget_tokens == 16384 (advisory)
        # mapping.orchestration_enabled == False

        ultra = mgr.map_effort(EffortLevel.ULTRACODE, provider="anthropic")
        # ultra.budget_tokens == 16384  (same as xhigh)
        # ultra.orchestration_enabled == True  (THIS is what makes it ultracode)
    """

    def __init__(self, config: EffortConfig | None = None) -> None:
        """
        Args:
            config: Optional session-level effort config. Creates default (HIGH, no
                    orchestration) if None.
        """
        self._config = config or EffortConfig()
        self._calibration_data: dict[str, dict[EffortLevel, dict[str, float]]] = {}

    # ── Public API ─────────────────────────────────────────────────

    @property
    def current_level(self) -> EffortLevel:
        """The active effort level for this session."""
        return self._config.current_level

    @property
    def orchestration_enabled(self) -> bool:
        """Whether auto-orchestration is currently active."""
        return self._config.orchestration.enabled

    def set_level(self, level: EffortLevel) -> None:
        """
        Set the session effort level.

        ``ultracode`` automatically enables orchestration.
        All other levels leave orchestration unchanged.
        """
        self._config = EffortConfig(
            current_level=level,
            orchestration=OrchestrationConfig(
                enabled=(level == EffortLevel.ULTRACODE),
                auto_trigger_threshold=self._config.orchestration.auto_trigger_threshold,
                keyword_trigger_enabled=self._config.orchestration.keyword_trigger_enabled,
            ),
            provider_overrides=self._config.provider_overrides,
        )
        logger.info("Effort set to %s (orchestration: %s)", level.value, self.orchestration_enabled)

    def set_orchestration(
        self, enabled: bool, auto_trigger_threshold: str = "medium"
    ) -> None:
        """Configure the orchestration toggle directly."""
        self._config = EffortConfig(
            current_level=self._config.current_level,
            orchestration=OrchestrationConfig(
                enabled=enabled,
                auto_trigger_threshold=auto_trigger_threshold,
                keyword_trigger_enabled=self._config.orchestration.keyword_trigger_enabled,
            ),
            provider_overrides=self._config.provider_overrides,
        )

    def map_effort(
        self,
        level: EffortLevel | None = None,
        provider: str = "anthropic",
    ) -> EffortMapping:
        """
        Map an effort level to provider-specific API parameters.

        Args:
            level: Effort level to map. Uses the current session level if None.
            provider: Target provider identifier.

        Returns:
            An :class:`EffortMapping` with provider-specific parameters.
        """
        level = level or self._config.current_level

        # Check for provider-specific override
        if provider in self._config.provider_overrides:
            level = self._config.provider_overrides[provider]

        # ── Handle ultracode specially ─────────────────────────
        # Ultracode = xhigh budget + orchestration toggle. It is NOT a
        # distinct API budget tier. We resolve it to xhigh for the actual
        # API call but preserve the orchestration flag.
        is_ultracode = level == EffortLevel.ULTRACODE
        effective_level = EffortLevel.XHIGH if is_ultracode else level

        # Clamp effective level to provider's max supported level
        capability = _PROVIDER_CAPABILITIES.get(provider)
        if capability:
            # Clamp the *effective* level (xhigh for ultracode), not ultracode itself
            effective_level = self._clamp_to_capability(effective_level, capability)

        budget = effective_level.reasoning_budget

        # Apply calibration if available
        budget = self._apply_calibration(provider, effective_level, budget)

        # Orchestration is enabled if: session orchestration is on, OR
        # the originally-requested level is ultracode
        orchestration = (
            self._config.orchestration.enabled or is_ultracode
        )

        # Report level: for ultracode, keep the label; for all others report
        # the effective (clamped) level so consumers know what was actually used.
        reported_level = level if is_ultracode else effective_level

        return EffortMapping(
            level=reported_level,
            provider=provider,
            budget_tokens=budget,  # Budget from the clamped effective level
            thinking_instruction=self._get_thinking_instruction(provider, effective_level),
            reasoning_effort=self._get_reasoning_effort(provider, effective_level),
            max_tokens_per_turn=_MAX_TOKENS[effective_level],
            orchestration_enabled=orchestration,
        )

    def get_provider_capability(self, provider: str) -> ProviderEffortCapability | None:
        """Return the declared effort capabilities for a provider."""
        return _PROVIDER_CAPABILITIES.get(provider)

    def record_calibration(
        self,
        provider: str,
        level: EffortLevel,
        accuracy: float,
        tokens_used: int,
        latency_ms: float,
    ) -> None:
        """
        Record a calibration data point for dynamic effort mapping.

        This feeds the Breakthrough calibration system (§3.2): over time,
        Lyra learns the minimum tokens each (provider, model, effort_level)
        needs to achieve target accuracy.

        Args:
            provider: Provider identifier.
            level: Effort level that was used.
            accuracy: Measured accuracy on the calibration task (0-1).
            tokens_used: Tokens actually consumed.
            latency_ms: Measured latency in milliseconds.
        """
        if provider not in self._calibration_data:
            self._calibration_data[provider] = {}
        self._calibration_data[provider][level] = {
            "accuracy": accuracy,
            "tokens_used": tokens_used,
            "latency_ms": latency_ms,
        }
        logger.debug(
            "Calibration recorded: %s @ %s → acc=%.2f, tokens=%d, latency=%.0fms",
            provider, level.value, accuracy, tokens_used, latency_ms,
        )

    @property
    def config(self) -> EffortConfig:
        """Return the current effort configuration (for serialization)."""
        return self._config

    @classmethod
    def from_config(cls, config: EffortConfig) -> EffortManager:
        """Restore an EffortManager from a persisted config."""
        return cls(config=config)

    @classmethod
    def list_providers(cls) -> list[str]:
        """Return all known provider identifiers."""
        return list(_PROVIDER_CAPABILITIES.keys())

    @classmethod
    def validate_against_capability_matrix(cls) -> dict[str, list[str]]:
        """
        Cross-validate effort capabilities against lyra_provider.CapabilityMatrix.

        Returns a dict of provider → list of discrepancies (empty if aligned).
        This ensures the two capability systems stay in sync.
        """
        discrepancies: dict[str, list[str]] = {}
        try:
            from lyra_provider import get_capability_matrix  # Lazy import
            matrix = get_capability_matrix()

            for provider, effort_cap in _PROVIDER_CAPABILITIES.items():
                general_cap = matrix.get(provider)
                if general_cap is None:
                    discrepancies[provider] = [f"Provider '{provider}' in effort caps but not in CapabilityMatrix"]
                    continue

                # Cross-check reasoning_budget support
                if effort_cap.supports_budget_tokens and not general_cap.reasoning_budget:
                    discrepancies.setdefault(provider, []).append(
                        "Effort caps say budget_tokens=True, CapabilityMatrix says reasoning_budget=False"
                    )
        except ImportError:
            pass  # lyra_provider not installed — validation skipped
        return discrepancies

    # ── Internal helpers ───────────────────────────────────────────

    @staticmethod
    def _clamp_to_capability(
        level: EffortLevel, capability: ProviderEffortCapability
    ) -> EffortLevel:
        """Clamp an effort level to what the provider supports."""
        levels = list(EffortLevel)
        max_idx = levels.index(capability.max_effort_level)
        level_idx = levels.index(level)
        if level_idx > max_idx:
            clamped = levels[max_idx]
            logger.debug(
                "Clamped effort %s → %s (provider max: %s)",
                level.value, clamped.value, capability.max_effort_level.value,
            )
            return clamped
        return level

    def _apply_calibration(
        self, provider: str, level: EffortLevel, default_budget: int
    ) -> int:
        """Apply calibration data to adjust the token budget, if available."""
        provider_data = self._calibration_data.get(provider, {})
        if level not in provider_data:
            return default_budget

        cal = provider_data[level]
        target_accuracy = self._target_accuracy(level)
        current_accuracy = cal.get("accuracy", 0.0)

        if current_accuracy >= target_accuracy:
            # We're meeting the target — could potentially reduce budget
            return default_budget

        # Not meeting target — increase budget proportionally
        shortfall = target_accuracy - current_accuracy
        adjustment = 1.0 + shortfall * 2.0  # Scale budget up by shortfall
        adjusted = int(default_budget * min(adjustment, 2.0))  # Cap at 2x
        logger.debug(
            "Calibration adjusted budget: %d → %d (accuracy %.2f < target %.2f)",
            default_budget, adjusted, current_accuracy, target_accuracy,
        )
        return adjusted

    @staticmethod
    def _target_accuracy(level: EffortLevel) -> float:
        """Target accuracy for each effort level."""
        return {
            EffortLevel.LOW: 0.70,
            EffortLevel.MEDIUM: 0.80,
            EffortLevel.HIGH: 0.88,
            EffortLevel.XHIGH: 0.93,
            EffortLevel.MAX: 0.96,
            EffortLevel.ULTRACODE: 0.93,  # Same as xhigh
        }[level]

    @staticmethod
    def _get_thinking_instruction(provider: str, level: EffortLevel) -> str:
        """Get the prompt-level thinking instruction for a provider."""
        provider_instructions = _THINKING_INSTRUCTIONS.get(provider, {})
        return provider_instructions.get(level, "")

    @staticmethod
    def _get_reasoning_effort(provider: str, level: EffortLevel) -> str:
        """Get the OpenAI reasoning_effort value for a level."""
        if provider == "openai":
            return _OPENAI_REASONING_EFFORT.get(level, "")
        return ""
