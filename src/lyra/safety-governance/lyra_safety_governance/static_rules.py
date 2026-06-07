from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

from .exceptions import RuleViolationError
from .governance_engine import (
    ActionRequest,
    ActionType,
    Decision,
    GovernanceDecision,
    GovernanceLayer,
)


class RulePriority(Enum):
    CRITICAL = 4
    HIGH = 3
    NORMAL = 2
    LOW = 1


@dataclass(frozen=True)
class SafetyRule:
    rule_id: str
    name: str
    pattern: str
    action_types: tuple[ActionType, ...]
    decision: Decision
    priority: RulePriority
    description: str


@dataclass(frozen=True)
class RuleSet:
    name: str
    rules: tuple[SafetyRule, ...]
    version: str


class RuleCompiler:
    """Compiles safety rule patterns into optimized regex for fast matching."""

    def compile(self, rule: SafetyRule) -> re.Pattern:
        compiled = re.compile(rule.pattern, re.IGNORECASE)
        return compiled

    def match(self, rule: SafetyRule, target: str) -> bool:
        compiled = self.compile(rule)
        return bool(compiled.search(target))


_BUILTIN_RULES: tuple[SafetyRule, ...] = (
    SafetyRule(
        rule_id="rule-credential-access",
        name="No credential/secret access",
        pattern=r"(?i)(passwd|password|secret|token|api[_-]?key|credential|private[_-]?key|\.env)",
        action_types=(
            ActionType.READ_FILE, ActionType.WRITE_FILE, ActionType.UPLOAD,
        ),
        decision=Decision.DENY,
        priority=RulePriority.CRITICAL,
        description="Prevents agents from accessing or exfiltrating credentials and secrets",
    ),
    SafetyRule(
        rule_id="rule-system-commands",
        name="No system-level commands without approval",
        pattern=r"(?i)(sudo|su\b|chmod|chown|passwd|useradd|usermod|groupadd|kill\s+-?\d+|rm\s+[-rf]+\s+/|mkfs|fdisk|dd\b)",
        action_types=(ActionType.SHELL, ActionType.EXECUTE),
        decision=Decision.DENY,
        priority=RulePriority.CRITICAL,
        description="Blocks dangerous system-level shell commands that could compromise the host",
    ),
    SafetyRule(
        rule_id="rule-network-unapproved",
        name="No external network calls to unapproved domains",
        pattern=r"(?i)(https?://|wss?://)(?!.*(localhost|127\.0\.0\.1|0\.0\.0\.0|::1|lyra\.internal|api\.lyra))",
        action_types=(ActionType.NETWORK, ActionType.API_CALL),
        decision=Decision.DENY,
        priority=RulePriority.HIGH,
        description="Blocks network requests to domains not on the approved allowlist",
    ),
    SafetyRule(
        rule_id="rule-delete-confirmation",
        name="No deletion of user files without confirmation",
        pattern=r"(?i)(rm\b|del\b|delete\b|remove\b|unlink\b|truncate|rmdir)",
        action_types=(ActionType.DELETE, ActionType.SHELL),
        decision=Decision.REQUIRE_HUMAN,
        priority=RulePriority.HIGH,
        description="Requires human confirmation before any deletion operation",
    ),
    SafetyRule(
        rule_id="rule-rate-limit",
        name="Rate limiting on all API calls",
        pattern=r".*",
        action_types=(
            ActionType.API_CALL, ActionType.NETWORK, ActionType.EXECUTE,
        ),
        decision=Decision.LOG_ONLY,
        priority=RulePriority.NORMAL,
        description="Rate limiting enforced on frequent API and execution calls",
    ),
)


class StaticRuleEngine:
    """Layer 1: Hard-coded safety rules enforced before any action is taken."""

    def __init__(self, builtin_rules: Sequence[SafetyRule] | None = None) -> None:
        self._rules: list[SafetyRule] = []
        self._compiler = RuleCompiler()
        self._rate_counters: dict[str, list[datetime]] = {}
        self._rate_limit_window_seconds = 60
        self._rate_limit_max_calls = 30

        for rule in (builtin_rules if builtin_rules is not None else _BUILTIN_RULES):
            self.add_rule(rule)

    @property
    def rules(self) -> tuple[SafetyRule, ...]:
        return tuple(self._rules)

    def add_rule(self, rule: SafetyRule) -> None:
        self._rules.append(rule)

    def remove_rule(self, rule_id: str) -> bool:
        for i, rule in enumerate(self._rules):
            if rule.rule_id == rule_id:
                self._rules.pop(i)
                return True
        return False

    def get_rules_for_action(self, action_type: ActionType) -> tuple[SafetyRule, ...]:
        return tuple(r for r in self._rules if action_type in r.action_types)

    def evaluate(self, request: ActionRequest) -> GovernanceDecision:
        """Evaluate a request against all rules. Returns the highest-priority matching decision."""
        relevant_rules = sorted(
            self.get_rules_for_action(request.action_type),
            key=lambda r: r.priority.value,
            reverse=True,
        )

        worst_decision: Decision | None = None
        worst_reasoning = ""
        worst_priority = 0

        for rule in relevant_rules:
            if self._compiler.match(rule, request.target):
                if rule.priority.value > worst_priority:
                    worst_priority = rule.priority.value
                    worst_decision = rule.decision
                    worst_reasoning = f"Rule '{rule.name}' matched: {rule.description}"

        if worst_decision is None:
            return GovernanceDecision(
                action_request=request,
                decision=Decision.ALLOW,
                layer=GovernanceLayer.STATIC_RULES,
                reasoning="No matching rules",
                risk_score=0.0,
            )

        # Rate limiting check
        if worst_decision != Decision.DENY:
            self._check_rate_limit(request)

        # Log-only: track but allow
        if worst_decision == Decision.LOG_ONLY:
            return GovernanceDecision(
                action_request=request,
                decision=Decision.ALLOW,
                layer=GovernanceLayer.STATIC_RULES,
                reasoning=f"Logged: {worst_reasoning}",
                risk_score=0.3,
            )

        risk_map = {
            Decision.ALLOW: 0.0,
            Decision.DENY: 1.0,
            Decision.ESCALATE: 0.7,
            Decision.LOG_ONLY: 0.3,
            Decision.REQUIRE_HUMAN: 0.8,
        }

        return GovernanceDecision(
            action_request=request,
            decision=worst_decision,
            layer=GovernanceLayer.STATIC_RULES,
            reasoning=worst_reasoning,
            risk_score=risk_map.get(worst_decision, 0.5),
            timestamp=datetime.now(timezone.utc),
        )

    def _check_rate_limit(self, request: ActionRequest) -> None:
        """Track call frequency and raise if rate limit exceeded."""
        now = datetime.now(timezone.utc)
        key = f"{request.agent_id}:{request.action_type.value}"
        if key not in self._rate_counters:
            self._rate_counters[key] = []

        cutoff = now.timestamp() - self._rate_limit_window_seconds
        self._rate_counters[key] = [
            t for t in self._rate_counters[key]
            if t.timestamp() > cutoff
        ]
        self._rate_counters[key].append(now)

        if len(self._rate_counters[key]) > self._rate_limit_max_calls:
            raise RuleViolationError(
                f"Rate limit exceeded for {key}: "
                f"{len(self._rate_counters[key])} calls in "
                f"{self._rate_limit_window_seconds}s"
            )
