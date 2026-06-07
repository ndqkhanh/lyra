"""Effort-Aware Model Routing — P3-B3 BREAKTHROUGH primitive.

Routes tasks to appropriate model families based on an effort tier (low, medium,
high, xhigh, max). Each tier defines a preferred model family, max_token budget,
and fallback options.

Integrates with the multi-provider abstraction layer (ProviderKind) and follows
the same composable pattern as BELLERouter.

See: plan-phase3-skills-routing.md §B1, plan-phase5-master-plan.md §P3-B3
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field

from lyra.harness_core.providers import ProviderKind


class EffortTier(str, enum.Enum):
    """Five effort tiers for model routing.

    LOW — trivial lookups, simple formatting, no reasoning needed
    MEDIUM — standard coding tasks, single-file edits
    HIGH — complex multi-file refactors, architectural reasoning
    XHIGH — deep analysis, security review, research synthesis
    MAX — maximum reasoning budget, adversarial verification
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    XHIGH = "xhigh"
    MAX = "max"


@dataclass(frozen=True)
class EffortConfig:
    """Configuration for a single effort tier."""

    tier: EffortTier
    preferred: ProviderKind          # first-choice provider family
    max_tokens: int                   # output token budget
    fallbacks: tuple[ProviderKind, ...] = ()  # ordered fallback providers
    description: str = ""

    @classmethod
    def defaults(cls) -> dict[EffortTier, "EffortConfig"]:
        """Factory-default effort tier configurations.

        Designed to minimize cost while maximizing capability:
        - LOW uses haiku-tier models (fastest, cheapest)
        - MEDIUM uses sonnet-tier models (best coding)
        - HIGH uses opus-tier models (deepest reasoning)
        - XHIGH uses opus with maximum tokens
        - MAX uses opus with absolute max + all fallbacks
        """
        return {
            EffortTier.LOW: cls(
                tier=EffortTier.LOW,
                preferred=ProviderKind.DEEPSEEK,
                max_tokens=1024,
                fallbacks=(ProviderKind.OPEN_WEIGHTS, ProviderKind.MOCK),
                description="Trivial lookups, simple formatting — haiku/deepseek-flash",
            ),
            EffortTier.MEDIUM: cls(
                tier=EffortTier.MEDIUM,
                preferred=ProviderKind.ANTHROPIC,
                max_tokens=4096,
                fallbacks=(ProviderKind.DEEPSEEK, ProviderKind.OPENAI),
                description="Standard coding tasks, single-file edits — sonnet",
            ),
            EffortTier.HIGH: cls(
                tier=EffortTier.HIGH,
                preferred=ProviderKind.ANTHROPIC,
                max_tokens=8192,
                fallbacks=(ProviderKind.OPENAI, ProviderKind.DEEPSEEK),
                description="Complex multi-file refactors, architectural reasoning — opus",
            ),
            EffortTier.XHIGH: cls(
                tier=EffortTier.XHIGH,
                preferred=ProviderKind.ANTHROPIC,
                max_tokens=16384,
                fallbacks=(ProviderKind.OPENAI, ProviderKind.DEEPSEEK, ProviderKind.QWEN),
                description="Deep analysis, security review, research synthesis",
            ),
            EffortTier.MAX: cls(
                tier=EffortTier.MAX,
                preferred=ProviderKind.ANTHROPIC,
                max_tokens=32768,
                fallbacks=(
                    ProviderKind.OPENAI,
                    ProviderKind.DEEPSEEK,
                    ProviderKind.QWEN,
                    ProviderKind.OPEN_WEIGHTS,
                ),
                description="Maximum reasoning budget, adversarial verification",
            ),
        }


@dataclass(frozen=True)
class EffortDecision:
    """Result of effort-aware routing."""

    effort: EffortTier
    provider: ProviderKind
    max_tokens: int
    is_fallback: bool = False
    reason: str = ""


@dataclass
class EffortRouter:
    """Routes tasks to model families based on effort tier.

    Composes a tier→config mapping with runtime provider availability.
    If the preferred provider is unavailable, falls back through the
    ordered fallback list.

    Usage::

        router = EffortRouter()
        decision = router.route(EffortTier.HIGH)
        # decision.provider → ProviderKind.ANTHROPIC
        # decision.max_tokens → 8192

        # With runtime constraints:
        router.unavailable = {ProviderKind.ANTHROPIC}
        decision = router.route(EffortTier.HIGH)
        # decision.provider → ProviderKind.OPENAI (first available fallback)
    """

    configs: dict[EffortTier, EffortConfig] = field(default_factory=EffortConfig.defaults)
    unavailable: set[ProviderKind] = field(default_factory=set)

    def route(self, effort: EffortTier) -> EffortDecision:
        """Route an effort tier to a concrete provider + token budget.

        Args:
            effort: The effort tier for the task.

        Returns:
            An EffortDecision with the chosen provider and max_tokens.

        Raises:
            ValueError: If no provider is available for the given tier.
        """
        config = self.configs.get(effort)
        if config is None:
            raise ValueError(f"unknown effort tier: {effort}")

        # Try preferred provider first
        if config.preferred not in self.unavailable:
            return EffortDecision(
                effort=effort,
                provider=config.preferred,
                max_tokens=config.max_tokens,
                reason=f"preferred {config.preferred.value} available for {effort.value}",
            )

        # Try fallbacks in order
        for fb in config.fallbacks:
            if fb not in self.unavailable:
                return EffortDecision(
                    effort=effort,
                    provider=fb,
                    max_tokens=config.max_tokens,
                    is_fallback=True,
                    reason=f"preferred {config.preferred.value} unavailable; "
                    f"fell back to {fb.value} for {effort.value}",
                )

        raise ValueError(
            f"no available provider for effort tier {effort.value}. "
            f"Preferred: {config.preferred.value}, "
            f"Fallbacks: {[f.value for f in config.fallbacks]}, "
            f"Unavailable: {[u.value for u in self.unavailable]}"
        )

    def route_with_override(
        self,
        effort: EffortTier,
        preferred_override: ProviderKind | None = None,
        max_tokens_override: int | None = None,
    ) -> EffortDecision:
        """Route with optional overrides for provider and token budget.

        Args:
            effort: The effort tier for the task.
            preferred_override: If set, try this provider first (before tier config).
            max_tokens_override: If set, use this token budget instead of tier default.

        Returns:
            An EffortDecision with the chosen provider and max_tokens.
        """
        config = self.configs.get(effort)
        if config is None:
            raise ValueError(f"unknown effort tier: {effort}")

        tokens = max_tokens_override if max_tokens_override is not None else config.max_tokens
        preferred = preferred_override if preferred_override is not None else config.preferred

        if preferred not in self.unavailable:
            return EffortDecision(
                effort=effort,
                provider=preferred,
                max_tokens=tokens,
                reason=f"provider {preferred.value} for {effort.value}",
            )

        # If override is unavailable, try tier's preferred first
        if preferred != config.preferred and config.preferred not in self.unavailable:
            return EffortDecision(
                effort=effort,
                provider=config.preferred,
                max_tokens=tokens,
                is_fallback=True,
                reason=f"override {preferred.value} unavailable; "
                f"fell back to tier default {config.preferred.value}",
            )

        # Try tier fallbacks
        for fb in config.fallbacks:
            if fb not in self.unavailable:
                return EffortDecision(
                    effort=effort,
                    provider=fb,
                    max_tokens=tokens,
                    is_fallback=True,
                    reason=f"override {preferred.value} unavailable; "
                    f"fell back to {fb.value}",
                )

        raise ValueError(
            f"no available provider for effort tier {effort.value} "
            f"(override: {preferred.value})"
        )

    def mark_unavailable(self, provider: ProviderKind) -> None:
        """Mark a provider as unavailable (e.g., circuit breaker tripped)."""
        self.unavailable.add(provider)

    def mark_available(self, provider: ProviderKind) -> None:
        """Re-mark a provider as available (e.g., circuit breaker reset)."""
        self.unavailable.discard(provider)

    def available_providers(self) -> set[ProviderKind]:
        """Return all providers not currently marked unavailable."""
        all_kinds = {c.preferred for c in self.configs.values()}
        for c in self.configs.values():
            all_kinds.update(c.fallbacks)
        return all_kinds - self.unavailable

    def get_config(self, effort: EffortTier) -> EffortConfig | None:
        """Get the EffortConfig for a tier, or None if not configured."""
        return self.configs.get(effort)


# --- Effort-from-tags inference ----------------------------------------------


_EFFORT_KEYWORD_MAP: dict[str, EffortTier] = {
    # LOW triggers
    "trivial": EffortTier.LOW,
    "lookup": EffortTier.LOW,
    "format": EffortTier.LOW,
    "typo": EffortTier.LOW,
    # MEDIUM triggers
    "implement": EffortTier.MEDIUM,
    "refactor": EffortTier.MEDIUM,
    "fix": EffortTier.MEDIUM,
    # HIGH triggers
    "architect": EffortTier.HIGH,
    "design": EffortTier.HIGH,
    "migrate": EffortTier.HIGH,
    # XHIGH triggers
    "audit": EffortTier.XHIGH,
    "security": EffortTier.XHIGH,
    "research": EffortTier.XHIGH,
    "analyze": EffortTier.XHIGH,
    # MAX triggers
    "adversarial": EffortTier.MAX,
    "verify": EffortTier.MAX,
    "prove": EffortTier.MAX,
}


def infer_effort(description: str) -> EffortTier:
    """Infer a suitable effort tier from a task description.

    Heuristic keyword matching; production can layer an LM classifier.

    >>> infer_effort("fix a typo in the README")
    <EffortTier.LOW: 'low'>
    >>> infer_effort("implement user authentication system")
    <EffortTier.MEDIUM: 'medium'>
    >>> infer_effort("audit the entire codebase for security vulnerabilities")
    <EffortTier.XHIGH: 'xhigh'>
    """
    desc_lower = description.lower()

    # Score tiers by keyword count
    tier_scores: dict[EffortTier, int] = dict.fromkeys(EffortTier, 0)
    for keyword, tier in _EFFORT_KEYWORD_MAP.items():
        if keyword in desc_lower:
            tier_scores[tier] += 1

    max_score = max(tier_scores.values())
    if max_score > 0:
        # Lowest tier wins in case of ties (conservative: prefer cheaper model)
        for tier in (EffortTier.LOW, EffortTier.MEDIUM, EffortTier.HIGH, EffortTier.XHIGH, EffortTier.MAX):
            if tier_scores[tier] == max_score:
                return tier

    # No keywords matched — default to MEDIUM
    # Unless description looks very simple (short + no technical terms)
    if len(description.split()) <= 3:
        return EffortTier.LOW
    return EffortTier.MEDIUM


__all__ = [
    "EffortConfig",
    "EffortDecision",
    "EffortRouter",
    "EffortTier",
    "infer_effort",
]
