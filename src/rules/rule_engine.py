"""
Rule execution engine.
"""

from pathlib import Path
from typing import Any

from .rule import Rule, RuleCategory, RuleViolation
from .rule_registry import RuleRegistry


class RuleEngine:
    """
    Engine for checking and enforcing rules.

    Validates code against registered rules and reports violations.
    """

    def __init__(self, registry: RuleRegistry | None = None):
        """
        Initialize rule engine.

        Args:
            registry: Rule registry (creates new if not provided)
        """
        self.registry = registry or RuleRegistry()
        self.violations: list[RuleViolation] = []

    def check_file(
        self,
        file_path: str,
        content: str | None = None,
        language: str | None = None,
    ) -> list[RuleViolation]:
        """
        Check a file against applicable rules.

        Args:
            file_path: Path to file
            content: Optional file content (reads from disk if not provided)
            language: Optional language hint

        Returns:
            List of rule violations
        """
        violations = []

        # Detect language from file extension if not provided
        if not language:
            language = self._detect_language(file_path)

        # Find applicable rules
        rules = self.registry.find_rules_for_file(file_path, language=language)

        # Read content if not provided
        if content is None:
            try:
                with open(file_path) as f:
                    content = f.read()
            except Exception:
                # Can't read file, skip checks
                return violations

        # Check each rule
        for rule in rules:
            rule_violations = self._check_rule(rule, file_path, content)
            violations.extend(rule_violations)

        # Store violations
        self.violations.extend(violations)

        return violations

    def _check_rule(
        self,
        rule: Rule,
        file_path: str,
        content: str,
    ) -> list[RuleViolation]:
        """
        Check a single rule against file content.

        Args:
            rule: Rule to check
            file_path: File path
            content: File content

        Returns:
            List of violations
        """
        violations = []

        # Basic checks based on rule category
        if rule.category == RuleCategory.CODING_STYLE:
            violations.extend(self._check_coding_style(rule, file_path, content))
        elif rule.category == RuleCategory.SECURITY:
            violations.extend(self._check_security(rule, file_path, content))
        elif rule.category == RuleCategory.TESTING:
            violations.extend(self._check_testing(rule, file_path, content))

        return violations

    def _check_coding_style(
        self,
        rule: Rule,
        file_path: str,
        content: str,
    ) -> list[RuleViolation]:
        """Check coding style rules."""
        violations = []

        # Example: Check for hardcoded values
        if "no-hardcoded" in rule.rule_id.lower():
            # Simple pattern matching (in production, use AST)
            if "TODO" in content or "FIXME" in content:
                violations.append(RuleViolation(
                    rule_id=rule.rule_id,
                    severity=rule.severity,
                    message="Found TODO/FIXME comment",
                    file_path=file_path,
                ))

        return violations

    def _check_security(
        self,
        rule: Rule,
        file_path: str,
        content: str,
    ) -> list[RuleViolation]:
        """Check security rules."""
        violations = []

        # Example: Check for hardcoded secrets
        if "no-secrets" in rule.rule_id.lower():
            patterns = ["password", "api_key", "secret", "token"]
            for pattern in patterns:
                if pattern in content.lower():
                    violations.append(RuleViolation(
                        rule_id=rule.rule_id,
                        severity=rule.severity,
                        message=f"Possible hardcoded secret: {pattern}",
                        file_path=file_path,
                    ))

        return violations

    def _check_testing(
        self,
        rule: Rule,
        file_path: str,
        content: str,
    ) -> list[RuleViolation]:
        """Check testing rules."""
        violations = []

        # Example: Check for test coverage
        if "test-coverage" in rule.rule_id.lower():
            # In production, integrate with coverage tools
            pass

        return violations

    def _detect_language(self, file_path: str) -> str | None:
        """
        Detect language from file extension.

        Args:
            file_path: File path

        Returns:
            Language name or None
        """
        ext_map = {
            ".py": "python",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".js": "javascript",
            ".jsx": "javascript",
            ".go": "golang",
            ".rs": "rust",
            ".java": "java",
            ".kt": "kotlin",
            ".swift": "swift",
            ".php": "php",
            ".cpp": "cpp",
            ".cc": "cpp",
            ".c": "c",
        }

        ext = Path(file_path).suffix
        return ext_map.get(ext)

    def get_violations(
        self,
        severity: str | None = None,
        file_path: str | None = None,
    ) -> list[RuleViolation]:
        """
        Get recorded violations.

        Args:
            severity: Filter by severity
            file_path: Filter by file path

        Returns:
            List of violations
        """
        violations = self.violations

        if severity:
            violations = [v for v in violations if v.severity.value == severity]

        if file_path:
            violations = [v for v in violations if v.file_path == file_path]

        return violations

    def clear_violations(self) -> None:
        """Clear recorded violations."""
        self.violations.clear()

    def get_statistics(self) -> dict[str, Any]:
        """
        Get violation statistics.

        Returns:
            Statistics dictionary
        """
        total = len(self.violations)

        by_severity = {}
        for violation in self.violations:
            severity = violation.severity.value
            by_severity[severity] = by_severity.get(severity, 0) + 1

        by_file = {}
        for violation in self.violations:
            if violation.file_path:
                by_file[violation.file_path] = by_file.get(violation.file_path, 0) + 1

        return {
            "total_violations": total,
            "by_severity": by_severity,
            "by_file": by_file,
            "files_with_violations": len(by_file),
            "registry_stats": self.registry.get_statistics(),
        }
