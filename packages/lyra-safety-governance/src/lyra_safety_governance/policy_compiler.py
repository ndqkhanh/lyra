from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from .exceptions import PolicyError
from .governance_engine import ActionType, Decision, GovernanceLayer
from .static_rules import RulePriority, SafetyRule


@dataclass(frozen=True)
class GovernancePolicy:
    policy_id: str
    name: str
    rules: tuple[SafetyRule, ...] = ()
    layers_applied: tuple[GovernanceLayer, ...] = ()
    compiled_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    version: str = "0.1.0"


@dataclass(frozen=True)
class PolicyValidationResult:
    valid: bool
    issues: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


class PolicySource(Enum):
    BUILTIN = "builtin"
    USER_DEFINED = "user_defined"
    LEARNED = "learned"
    EXTERNAL = "external"


class CompiledPolicy:
    """A governance policy compiled and optimized for runtime enforcement.

    Pre-compiles rule patterns into regex objects and indexes them by
    action type for fast lookup during evaluation.
    """

    def __init__(self, policy: GovernancePolicy) -> None:
        self._policy = policy
        self._compiled_at = datetime.now(timezone.utc)
        self._rule_index: dict[ActionType, list[tuple[re.Pattern, Decision, RulePriority]]] = {}

        for rule in policy.rules:
            compiled_pattern = re.compile(rule.pattern, re.IGNORECASE)
            for action_type in rule.action_types:
                if action_type not in self._rule_index:
                    self._rule_index[action_type] = []
                self._rule_index[action_type].append(
                    (compiled_pattern, rule.decision, rule.priority)
                )

        # Sort each action type's rules by priority descending
        for action_type in self._rule_index:
            self._rule_index[action_type].sort(
                key=lambda x: x[2].value,
                reverse=True,
            )

    @property
    def policy(self) -> GovernancePolicy:
        return self._policy

    @property
    def compiled_at(self) -> datetime:
        return self._compiled_at

    def get_matching_rules(self, action_type: ActionType, target: str) -> list[tuple[Decision, RulePriority]]:
        """Get all rules that match the given action type and target."""
        results: list[tuple[Decision, RulePriority]] = []
        for pattern, decision, priority in self._rule_index.get(action_type, []):
            if pattern.search(target):
                results.append((decision, priority))
        return results


class PolicyCompiler:
    """Compiles governance rules into enforceable policies.

    Supports validation, compilation, and merging of policies from
    multiple sources (built-in, user-defined, learned, external).
    """

    def compile_policy(self, policy: GovernancePolicy) -> CompiledPolicy:
        """Compile a governance policy for runtime enforcement."""
        if not policy.rules:
            raise PolicyError(f"Cannot compile policy '{policy.policy_id}': no rules defined")

        validation = self.validate_policy(policy)
        if not validation.valid:
            raise PolicyError(
                f"Cannot compile invalid policy '{policy.policy_id}': "
                f"{'; '.join(validation.issues)}"
            )

        return CompiledPolicy(policy)

    def validate_policy(self, policy: GovernancePolicy) -> PolicyValidationResult:
        """Validate a governance policy for correctness."""
        issues: list[str] = []
        warnings: list[str] = []

        if not policy.policy_id:
            issues.append("Policy ID is required")

        if not policy.name:
            warnings.append("Policy has no name")

        if not policy.rules:
            warnings.append("Policy has no rules defined")

        seen_rule_ids: set[str] = set()
        for rule in policy.rules:
            if rule.rule_id in seen_rule_ids:
                issues.append(f"Duplicate rule ID: {rule.rule_id}")
            seen_rule_ids.add(rule.rule_id)

            try:
                re.compile(rule.pattern)
            except re.error as e:
                issues.append(f"Invalid regex pattern in rule '{rule.rule_id}': {e}")

        if not policy.layers_applied:
            warnings.append("Policy has no governance layers configured")

        return PolicyValidationResult(
            valid=len(issues) == 0,
            issues=tuple(issues),
            warnings=tuple(warnings),
        )

    def merge_policies(self, policies: Sequence[GovernancePolicy]) -> GovernancePolicy:
        """Merge multiple policies into a single combined policy."""
        if not policies:
            raise PolicyError("Cannot merge empty list of policies")

        all_rules: dict[str, SafetyRule] = {}
        all_layers: set[GovernanceLayer] = set()

        for policy in policies:
            all_layers.update(policy.layers_applied)
            for rule in policy.rules:
                if rule.rule_id in all_rules:
                    # Higher priority wins on collision
                    existing = all_rules[rule.rule_id]
                    if rule.priority.value > existing.priority.value:
                        all_rules[rule.rule_id] = rule
                else:
                    all_rules[rule.rule_id] = rule

        return GovernancePolicy(
            policy_id=f"merged-{'-'.join(p.policy_id for p in policies[:3])}",
            name=f"Merged ({len(policies)} sources)",
            rules=tuple(all_rules.values()),
            layers_applied=tuple(all_layers),
            version="0.1.0",
        )
