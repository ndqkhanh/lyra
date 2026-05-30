"""Rule validator for checking files against configured rules."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .rule_metadata import RuleCategory, RuleMetadata, RuleSeverity
from .rule_registry import RuleRegistry


@dataclass(frozen=True)
class RuleViolation:
    rule_name: str
    severity: RuleSeverity
    message: str
    file_path: str | None = None
    line_number: int | None = None


@dataclass(frozen=True)
class ValidationResult:
    passed: bool
    violations: tuple[RuleViolation, ...]
    rules_checked: int


class RuleValidator:
    """Validates files against registered rules with pattern-based checks.

    Rules define patterns derived from their names. Violations are raised
    when file content matches a rule's intended check area.
    """

    _RULE_PATTERNS: dict[str, str] = {
        "no-hardcoded-secrets": r"""(?i)(api[_-]?key|password|secret|token)\s*[:=]\s*["'][^"']+["']""",
        "no-console-log": r"\bconsole\.(log|warn|error|debug)\(",
        "no-debug-statements": r"\b(breakpoint|debugger)\b",
        "no-todo-without-ticket": r"\bTODO\b(?!.*#[0-9]+)",
        "max-function-length": r"",
        "max-file-length": r"",
    }

    def __init__(self, registry: RuleRegistry) -> None:
        self._registry = registry

    def validate(
        self, context: dict[str, Any] | None = None
    ) -> ValidationResult:
        violations: list[RuleViolation] = []
        rules = [r for r in self._registry.list_rules() if r.enabled]

        for rule in rules:
            rule_violations = self._check_rule(rule, context)
            violations.extend(rule_violations)

        return ValidationResult(
            passed=len(violations) == 0,
            violations=tuple(violations),
            rules_checked=len(rules),
        )

    def validate_category(
        self, category: RuleCategory, context: dict[str, Any] | None = None
    ) -> ValidationResult:
        violations: list[RuleViolation] = []
        rules = self._registry.get_rules_by_category(category)

        for rule in rules:
            if not rule.enabled:
                continue
            rule_violations = self._check_rule(rule, context)
            violations.extend(rule_violations)

        return ValidationResult(
            passed=len(violations) == 0,
            violations=tuple(violations),
            rules_checked=len(rules),
        )

    def validate_file(self, file_path: str, rules: list[RuleMetadata] | None = None) -> list[RuleViolation]:
        path = Path(file_path)
        if not path.exists():
            return [RuleViolation(
                rule_name="file-exists", severity=RuleSeverity.CRITICAL,
                message=f"File not found: {file_path}", file_path=file_path,
            )]
        if not path.is_file():
            return []

        content = path.read_text()
        lines = content.splitlines()
        violations: list[RuleViolation] = []

        targets = rules or [r for r in self._registry.list_rules() if r.enabled]
        for rule in targets:
            pattern = self._RULE_PATTERNS.get(rule.name)
            if not pattern:
                continue
            for i, line in enumerate(lines, start=1):
                if re.search(pattern, line):
                    violations.append(RuleViolation(
                        rule_name=rule.name, severity=rule.severity,
                        message=rule.description, file_path=file_path, line_number=i,
                    ))

        return violations

    def _check_rule(
        self, rule: RuleMetadata, context: dict[str, Any] | None = None
    ) -> list[RuleViolation]:
        violations: list[RuleViolation] = []

        if context and "files" in context:
            for file_path in context["files"]:
                violations.extend(self.validate_file(str(file_path), [rule]))
                return violations

        if context and "content" in context:
            pattern = self._RULE_PATTERNS.get(rule.name)
            if not pattern:
                return []
            content = context["content"]
            lines = content.splitlines()
            for i, line in enumerate(lines, start=1):
                if re.search(pattern, line):
                    violations.append(RuleViolation(
                        rule_name=rule.name, severity=rule.severity,
                        message=rule.description,
                        file_path=context.get("file_path"), line_number=i,
                    ))

        return violations
