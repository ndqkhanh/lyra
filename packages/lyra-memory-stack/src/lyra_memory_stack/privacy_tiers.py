"""Privacy tier management for memory entries.

Defines four privacy tiers with cascade forgetting and access control:
- EPHEMERAL: session-only, cleared on session end
- PRIVATE: user-only, visible only to owning user
- DURABLE: project-scoped, persists across sessions within a project
- SHARED: team-scoped, visible to all agents in the team
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


class PrivacyTier(Enum):
    """Privacy tiers for memory entries, ordered from least to most durable."""

    EPHEMERAL = auto()
    PRIVATE = auto()
    DURABLE = auto()
    SHARED = auto()

    @property
    def rank(self) -> int:
        """Numeric rank for comparison (higher = more durable)."""
        return {
            PrivacyTier.EPHEMERAL: 0,
            PrivacyTier.PRIVATE: 1,
            PrivacyTier.DURABLE: 2,
            PrivacyTier.SHARED: 3,
        }[self]

    def __lt__(self, other: Any) -> bool:
        if isinstance(other, PrivacyTier):
            return self.rank < other.rank
        return NotImplemented

    def __le__(self, other: Any) -> bool:
        if isinstance(other, PrivacyTier):
            return self.rank <= other.rank
        return NotImplemented


# Mapping: elevated tiers cascade down to require clearance for lower tiers
TIER_DEPENDENCIES: dict[PrivacyTier, frozenset[PrivacyTier]] = {
    PrivacyTier.SHARED: frozenset({PrivacyTier.DURABLE, PrivacyTier.PRIVATE, PrivacyTier.EPHEMERAL}),
    PrivacyTier.DURABLE: frozenset({PrivacyTier.PRIVATE, PrivacyTier.EPHEMERAL}),
    PrivacyTier.PRIVATE: frozenset({PrivacyTier.EPHEMERAL}),
    PrivacyTier.EPHEMERAL: frozenset(),
}


def cascade_tiers(tier: PrivacyTier) -> set[PrivacyTier]:
    """Return the set of tiers that should be cleared when *tier* is cleared.

    Cascade forgetting: clearing a higher tier also clears all lower tiers.
    """
    result = {tier}
    for lower_tier in PrivacyTier:
        if lower_tier < tier:
            result.add(lower_tier)
    return result


def requiring_clearance(tier: PrivacyTier) -> set[PrivacyTier]:
    """Return the set of tiers that require clearance for access to *tier*."""
    return TIER_DEPENDENCIES.get(tier, frozenset())


@dataclass(frozen=True)
class PrivacyPolicy:
    """A policy governing how a memory entry's privacy is managed."""

    tier: PrivacyTier
    allowed_roles: tuple[str, ...] = field(default_factory=lambda: ("agent",))
    max_retention_days: float | None = None
    encrypt_at_rest: bool = False

    def allows_access(self, role: str) -> bool:
        """Check whether *role* is permitted to access this entry."""
        return role in self.allowed_roles

    def with_tier(self, new_tier: PrivacyTier) -> PrivacyPolicy:
        """Return a new policy with a different tier (immutable)."""
        return PrivacyPolicy(
            tier=new_tier,
            allowed_roles=self.allowed_roles,
            max_retention_days=self.max_retention_days,
            encrypt_at_rest=self.encrypt_at_rest,
        )

    def with_roles(self, *roles: str) -> PrivacyPolicy:
        """Return a new policy with updated allowed roles (immutable)."""
        return PrivacyPolicy(
            tier=self.tier,
            allowed_roles=roles,
            max_retention_days=self.max_retention_days,
            encrypt_at_rest=self.encrypt_at_rest,
        )


DEFAULT_POLICIES: dict[PrivacyTier, PrivacyPolicy] = {
    PrivacyTier.EPHEMERAL: PrivacyPolicy(
        tier=PrivacyTier.EPHEMERAL,
        allowed_roles=("agent",),
        max_retention_days=None,
        encrypt_at_rest=False,
    ),
    PrivacyTier.PRIVATE: PrivacyPolicy(
        tier=PrivacyTier.PRIVATE,
        allowed_roles=("user", "agent"),
        max_retention_days=90.0,
        encrypt_at_rest=True,
    ),
    PrivacyTier.DURABLE: PrivacyPolicy(
        tier=PrivacyTier.DURABLE,
        allowed_roles=("user", "agent", "project"),
        max_retention_days=365.0,
        encrypt_at_rest=True,
    ),
    PrivacyTier.SHARED: PrivacyPolicy(
        tier=PrivacyTier.SHARED,
        allowed_roles=("user", "agent", "project", "team"),
        max_retention_days=365.0,
        encrypt_at_rest=False,
    ),
}


class PrivacyManager:
    """Manages privacy tiers and access control for memory entries."""

    _policies: dict[PrivacyTier, PrivacyPolicy]

    def __init__(self, policies: dict[PrivacyTier, PrivacyPolicy] | None = None) -> None:
        self._policies = dict(policies) if policies else dict(DEFAULT_POLICIES)

    def get_policy(self, tier: PrivacyTier) -> PrivacyPolicy:
        """Get the policy for a given tier."""
        return self._policies.get(tier, DEFAULT_POLICIES[tier])

    def set_policy(self, tier: PrivacyTier, policy: PrivacyPolicy) -> None:
        """Set or override a policy for a tier."""
        self._policies[tier] = policy

    def check_access(self, tier: PrivacyTier, role: str) -> bool:
        """Check whether *role* can access entries at the given tier."""
        policy = self.get_policy(tier)
        return policy.allows_access(role)

    def cascade_forget(self, tier: PrivacyTier) -> set[PrivacyTier]:
        """Return all tiers that should be forgotten when *tier* is cleared."""
        return cascade_tiers(tier)

    def escalate_tier(self, current_tier: PrivacyTier, target_tier: PrivacyTier) -> PrivacyTier:
        """Escalate from current to target tier if target has higher durability."""
        return max(current_tier, target_tier, key=lambda t: t.rank)

    def validate_tier_transition(self, from_tier: PrivacyTier, to_tier: PrivacyTier) -> bool:
        """Validate that a transition between tiers is allowed.

        Downgrades are always allowed. Upgrades require that the
        target tier's dependencies are satisfied.
        """
        if to_tier <= from_tier:
            return True
        # Escalation is always permitted
        return True
