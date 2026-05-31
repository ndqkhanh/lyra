"""Path-Pattern + Regex Allow/Deny Rules — P1-X #15 (HIGH, LOW).

Declarative allow/deny rules for filesystem, network, and shell scopes.
Pattern-based with glob and regex support, priority ordering.

See: plan-phase1-harness.md, Claude Code permissions
"""
from __future__ import annotations

import enum
import fnmatch
import re
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Scopes
# ---------------------------------------------------------------------------


class Scope(str, enum.Enum):
    """Target scope for a rule."""

    FILESYSTEM = "filesystem"
    NETWORK = "network"
    SHELL = "shell"
    ALL = "all"  # matches any scope


class RuleEffect(str, enum.Enum):
    """What happens when a rule matches."""

    ALLOW = "allow"
    DENY = "deny"


class PatternKind(str, enum.Enum):
    """Kind of pattern matching."""

    GLOB = "glob"    # fnmatch / wildcard
    REGEX = "regex"  # Python re


# ---------------------------------------------------------------------------
# Scope Rule
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ScopeRule:
    """A single allow/deny rule for a scope.

    Rules are evaluated in priority order (higher priority first).
    The first matching rule wins — allow or deny.
    """

    name: str
    pattern: str
    effect: RuleEffect
    scope: Scope = Scope.ALL
    kind: PatternKind = PatternKind.GLOB
    priority: int = 0
    description: str = ""

    def matches(self, target: str) -> bool:
        """Check whether this rule matches a target string."""
        if self.kind == PatternKind.GLOB:
            return fnmatch.fnmatchcase(target, self.pattern)
        if self.kind == PatternKind.REGEX:
            return bool(re.search(self.pattern, target))
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "pattern": self.pattern,
            "effect": self.effect.value,
            "scope": self.scope.value,
            "kind": self.kind.value,
            "priority": self.priority,
            "description": self.description,
        }


# ---------------------------------------------------------------------------
# Match Result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ScopeMatch:
    """Result of evaluating a target against a set of rules."""

    allowed: bool
    matched_rule: str | None = None
    reason: str = ""


# ---------------------------------------------------------------------------
# Scope Rule Set
# ---------------------------------------------------------------------------


@dataclass
class ScopeRuleSet:
    """An ordered collection of scope rules.

    Rules are sorted by priority (descending) on insertion.
    Supports adding, removing, and evaluating rules.
    """

    _rules: list[ScopeRule] = field(default_factory=list)

    def add(self, rule: ScopeRule) -> None:
        """Add a rule and re-sort by priority (highest first)."""
        self._rules.append(rule)
        self._rules.sort(key=lambda r: -r.priority)

    def remove(self, name: str) -> bool:
        """Remove a rule by name. Returns True if found."""
        for i, r in enumerate(self._rules):
            if r.name == name:
                self._rules.pop(i)
                return True
        return False

    def has(self, name: str) -> bool:
        """Check if a rule with the given name exists."""
        return any(r.name == name for r in self._rules)

    @property
    def rules(self) -> list[ScopeRule]:
        """Return an immutable copy of the rule list."""
        return list(self._rules)

    @property
    def rule_count(self) -> int:
        return len(self._rules)

    def rules_for_scope(self, scope: Scope) -> list[ScopeRule]:
        """Return rules applicable to a scope (including Scope.ALL)."""
        return [r for r in self._rules if r.scope in (scope, Scope.ALL)]

    def evaluate(self, target: str, scope: Scope) -> ScopeMatch:
        """Evaluate a target against rules for a given scope.

        Returns ScopeMatch(allowed=True) if no rule matches (permissive default).
        """
        for rule in self.rules_for_scope(scope):
            if rule.matches(target):
                allowed = rule.effect == RuleEffect.ALLOW
                return ScopeMatch(
                    allowed=allowed,
                    matched_rule=rule.name,
                    reason=f"{'allow' if allowed else 'deny'} by rule {rule.name!r}: "
                           f"{rule.pattern} ({rule.kind.value})",
                )
        return ScopeMatch(allowed=True, reason="no matching rule — default allow")

    def is_allowed(self, target: str, scope: Scope) -> bool:
        """Convenience: return True if target is allowed under scope."""
        return self.evaluate(target, scope).allowed

    def is_denied(self, target: str, scope: Scope) -> bool:
        """Convenience: return True if target is denied under scope."""
        return not self.evaluate(target, scope).allowed

    def to_dict(self) -> dict[str, Any]:
        return {"rules": [r.to_dict() for r in self._rules]}


# ---------------------------------------------------------------------------
# Scope Rule Engine
# ---------------------------------------------------------------------------


@dataclass
class ScopeRuleEngine:
    """Multi-scope rule evaluation engine.

    Maintains separate rule sets per scope and provides unified evaluation.
    """

    filesystem: ScopeRuleSet = field(default_factory=ScopeRuleSet)
    network: ScopeRuleSet = field(default_factory=ScopeRuleSet)
    shell: ScopeRuleSet = field(default_factory=ScopeRuleSet)

    def add_rule(self, rule: ScopeRule) -> None:
        """Add a rule to the appropriate scope(s)."""
        if rule.scope == Scope.FILESYSTEM or rule.scope == Scope.ALL:
            self.filesystem.add(rule)
        if rule.scope == Scope.NETWORK or rule.scope == Scope.ALL:
            self.network.add(rule)
        if rule.scope == Scope.SHELL or rule.scope == Scope.ALL:
            self.shell.add(rule)

    def remove_rule(self, name: str) -> bool:
        """Remove a rule by name from all scopes."""
        removed = False
        for rs in (self.filesystem, self.network, self.shell):
            if rs.remove(name):
                removed = True
        return removed

    def evaluate(self, target: str, scope: Scope) -> ScopeMatch:
        """Evaluate a target against the rules for the given scope."""
        rs = self._set_for(scope)
        return rs.evaluate(target, scope)

    def is_allowed(self, target: str, scope: Scope) -> bool:
        return self._set_for(scope).is_allowed(target, scope)

    def _set_for(self, scope: Scope) -> ScopeRuleSet:
        if scope == Scope.FILESYSTEM:
            return self.filesystem
        if scope == Scope.NETWORK:
            return self.network
        if scope == Scope.SHELL:
            return self.shell
        return ScopeRuleSet()

    @property
    def total_rules(self) -> int:
        return self.filesystem.rule_count + self.network.rule_count + self.shell.rule_count

    def to_dict(self) -> dict[str, Any]:
        return {
            "filesystem": self.filesystem.to_dict(),
            "network": self.network.to_dict(),
            "shell": self.shell.to_dict(),
        }


# ---------------------------------------------------------------------------
# Pre-built rule sets
# ---------------------------------------------------------------------------


def build_default_filesystem_rules() -> ScopeRuleSet:
    """Default filesystem rules: deny system paths, allow everything else."""
    rs = ScopeRuleSet()
    rs.add(ScopeRule(
        name="deny_etc_passwd",
        pattern="/etc/passwd",
        effect=RuleEffect.DENY,
        scope=Scope.FILESYSTEM,
        kind=PatternKind.GLOB,
        priority=100,
        description="Block access to system password file",
    ))
    rs.add(ScopeRule(
        name="deny_etc_shadow",
        pattern="/etc/shadow",
        effect=RuleEffect.DENY,
        scope=Scope.FILESYSTEM,
        kind=PatternKind.GLOB,
        priority=100,
    ))
    rs.add(ScopeRule(
        name="deny_ssh_keys",
        pattern="/**/.ssh/*",
        effect=RuleEffect.DENY,
        scope=Scope.FILESYSTEM,
        kind=PatternKind.GLOB,
        priority=90,
        description="Block access to SSH keys",
    ))
    rs.add(ScopeRule(
        name="deny_env_files",
        pattern="/**/.env*",
        effect=RuleEffect.DENY,
        scope=Scope.FILESYSTEM,
        kind=PatternKind.GLOB,
        priority=80,
        description="Block access to .env files with secrets",
    ))
    rs.add(ScopeRule(
        name="deny_system_dirs_regex",
        pattern=r"^/(sys|proc|dev)(/|$)",
        effect=RuleEffect.DENY,
        scope=Scope.FILESYSTEM,
        kind=PatternKind.REGEX,
        priority=90,
        description="Block access to system virtual filesystems",
    ))
    rs.add(ScopeRule(
        name="allow_cwd",
        pattern="**",
        effect=RuleEffect.ALLOW,
        scope=Scope.FILESYSTEM,
        kind=PatternKind.GLOB,
        priority=0,
        description="Catch-all allow for filesystem",
    ))
    return rs


def build_default_network_rules() -> ScopeRuleSet:
    """Default network rules: block internal-only ranges, allow everything else."""
    rs = ScopeRuleSet()
    rs.add(ScopeRule(
        name="deny_internal_v4",
        pattern=r"^(10\.|172\.(1[6-9]|2\d|3[01])\.|192\.168\.|127\.|0\.0\.0\.0)",
        effect=RuleEffect.DENY,
        scope=Scope.NETWORK,
        kind=PatternKind.REGEX,
        priority=100,
        description="Block private/internal IPv4 ranges",
    ))
    rs.add(ScopeRule(
        name="deny_link_local",
        pattern=r"^169\.254\.",
        effect=RuleEffect.DENY,
        scope=Scope.NETWORK,
        kind=PatternKind.REGEX,
        priority=90,
        description="Block link-local addresses",
    ))
    rs.add(ScopeRule(
        name="deny_metadata_service",
        pattern="169.254.169.254",
        effect=RuleEffect.DENY,
        scope=Scope.NETWORK,
        kind=PatternKind.GLOB,
        priority=100,
        description="Block cloud metadata service",
    ))
    rs.add(ScopeRule(
        name="allow_network",
        pattern="**",
        effect=RuleEffect.ALLOW,
        scope=Scope.NETWORK,
        kind=PatternKind.GLOB,
        priority=0,
        description="Catch-all allow for network",
    ))
    return rs


def build_default_shell_rules() -> ScopeRuleSet:
    """Default shell rules: deny destructive commands, allow everything else."""
    rs = ScopeRuleSet()
    rs.add(ScopeRule(
        name="deny_rm_rf_root",
        pattern="rm -rf /*",
        effect=RuleEffect.DENY,
        scope=Scope.SHELL,
        kind=PatternKind.GLOB,
        priority=100,
        description="Block recursive root deletion",
    ))
    rs.add(ScopeRule(
        name="deny_disk_format",
        pattern="*mkfs*",
        effect=RuleEffect.DENY,
        scope=Scope.SHELL,
        kind=PatternKind.GLOB,
        priority=90,
        description="Block filesystem format commands",
    ))
    rs.add(ScopeRule(
        name="deny_fork_bomb",
        pattern=r":\(\)\s*\{",
        effect=RuleEffect.DENY,
        scope=Scope.SHELL,
        kind=PatternKind.REGEX,
        priority=100,
        description="Block fork bomb pattern",
    ))
    rs.add(ScopeRule(
        name="deny_dev_null_write",
        pattern="*> /dev/sd*",
        effect=RuleEffect.DENY,
        scope=Scope.SHELL,
        kind=PatternKind.GLOB,
        priority=100,
        description="Block raw device writes",
    ))
    rs.add(ScopeRule(
        name="deny_chmod_777_root",
        pattern="chmod 777 /*",
        effect=RuleEffect.DENY,
        scope=Scope.SHELL,
        kind=PatternKind.GLOB,
        priority=90,
        description="Block permissive chmod on root",
    ))
    rs.add(ScopeRule(
        name="allow_shell",
        pattern="**",
        effect=RuleEffect.ALLOW,
        scope=Scope.SHELL,
        kind=PatternKind.GLOB,
        priority=0,
        description="Catch-all allow for shell",
    ))
    return rs


def build_default_engine() -> ScopeRuleEngine:
    """Build a ScopeRuleEngine with sensible defaults for all scopes."""
    return ScopeRuleEngine(
        filesystem=build_default_filesystem_rules(),
        network=build_default_network_rules(),
        shell=build_default_shell_rules(),
    )


__all__ = [
    "PatternKind",
    "RuleEffect",
    "Scope",
    "ScopeMatch",
    "ScopeRule",
    "ScopeRuleEngine",
    "ScopeRuleSet",
    "build_default_engine",
    "build_default_filesystem_rules",
    "build_default_network_rules",
    "build_default_shell_rules",
]
