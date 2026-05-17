"""Rule validator for checking code against rules."""
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from .rule_registry import RuleRegistry
from .rule_metadata import RuleCategory, RuleSeverity, RuleMetadata


@dataclass
class RuleViolation:
    """A rule violation."""
    rule_name: str
    severity: RuleSeverity
    message: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None


@dataclass
class ValidationResult:
    """Result from rule validation."""
    passed: bool
    violations: List[RuleViolation]
    rules_checked: int


class RuleValidator:
    """Validator for checking code against rules."""

    def __init__(self, registry: RuleRegistry):
        self.registry = registry

    def validate(self, context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """Validate code against all enabled rules."""
        violations = []
        rules = [r for r in self.registry.list_rules() if r.enabled]

        for rule in rules:
            rule_violations = self._check_rule(rule, context)
            violations.extend(rule_violations)

        return ValidationResult(
            passed=len(violations) == 0,
            violations=violations,
            rules_checked=len(rules)
        )

    def validate_category(self, category: RuleCategory, context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """Validate code against rules in a specific category."""
        violations = []
        rules = self.registry.get_rules_by_category(category)

        for rule in rules:
            rule_violations = self._check_rule(rule, context)
            violations.extend(rule_violations)

        return ValidationResult(
            passed=len(violations) == 0,
            violations=violations,
            rules_checked=len(rules)
        )

    def _check_rule(self, rule: RuleMetadata, context: Optional[Dict[str, Any]] = None) -> List[RuleViolation]:
        """Check a single rule."""
        # TODO: Implement actual rule checking
        # For now, return empty list (no violations)
        return []
