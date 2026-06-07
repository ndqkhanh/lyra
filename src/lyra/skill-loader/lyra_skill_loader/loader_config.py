"""Loading policies, budget thresholds, and configuration presets."""
from __future__ import annotations

from dataclasses import dataclass, field

from lyra.skill_loader.exceptions import ConfigError


@dataclass(frozen=True)
class TierConfig:
    """Token budget per load tier."""

    tier1_max_tokens: int = 50
    tier2_max_tokens: int = 500
    tier3_max_tokens: int = 2000


@dataclass(frozen=True)
class CacheConfig:
    """Skill cache policy."""

    max_cached_skills: int = 100
    cache_ttl_seconds: int = 300


@dataclass(frozen=True)
class LoaderConfig:
    """Master configuration for the skill loading system."""

    tier_config: TierConfig = field(default_factory=TierConfig)
    cache_config: CacheConfig = field(default_factory=CacheConfig)
    max_skills_per_load: int = 10
    enable_progressive_loading: bool = True
    enable_trigger_precompilation: bool = True
    enable_dependency_resolution: bool = True


STRICT_BUDGET: LoaderConfig = LoaderConfig(
    tier_config=TierConfig(tier1_max_tokens=30, tier2_max_tokens=100, tier3_max_tokens=500),
    max_skills_per_load=3,
)
"""Aggressive token conservation — use when context window is near capacity."""

BALANCED: LoaderConfig = LoaderConfig(
    tier_config=TierConfig(tier1_max_tokens=50, tier2_max_tokens=500, tier3_max_tokens=2000),
    max_skills_per_load=10,
)
"""Default profile for general use."""

FULL_LOAD: LoaderConfig = LoaderConfig(
    tier_config=TierConfig(tier1_max_tokens=200, tier2_max_tokens=2000, tier3_max_tokens=10000),
    max_skills_per_load=50,
    enable_progressive_loading=False,
)
"""Prefer completeness over token economy — load everything fully."""

MINIMAL: LoaderConfig = LoaderConfig(
    tier_config=TierConfig(tier1_max_tokens=20, tier2_max_tokens=50, tier3_max_tokens=100),
    max_skills_per_load=1,
)
"""Minimum viable loading — only the most essential metadata."""

_PRESETS: dict[str, LoaderConfig] = {
    "STRICT_BUDGET": STRICT_BUDGET,
    "BALANCED": BALANCED,
    "FULL_LOAD": FULL_LOAD,
    "MINIMAL": MINIMAL,
}


def get_preset(name: str) -> LoaderConfig:
    """Look up a built-in :class:`LoaderConfig` preset by name.

    Args:
        name: One of ``STRICT_BUDGET``, ``BALANCED``, ``FULL_LOAD``, ``MINIMAL``.

    Returns:
        The matching preset.

    Raises:
        ConfigError: If *name* is not a known preset.
    """
    try:
        return _PRESETS[name]
    except KeyError:
        msg = f"Unknown preset: {name!r}. Available: {list(_PRESETS)}"
        raise ConfigError(msg) from None
