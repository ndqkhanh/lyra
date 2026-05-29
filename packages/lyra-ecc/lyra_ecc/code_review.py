"""
Enhanced Rules Engine with Code Review Integration

Comprehensive rules engine with language detection and code review integration.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from lyra_ecc.rules import Rule, RulesEngine, RuleSeverity, RuleViolation


@dataclass(frozen=True)
class CodeReviewResult:
    """Result of code review with rule violations."""

    file_path: Path
    violations: List[RuleViolation]
    severity_counts: Dict[str, int]
    passed: bool
    summary: str

    @classmethod
    def from_violations(
        cls, file_path: Path, violations: List[RuleViolation]
    ) -> "CodeReviewResult":
        """Create review result from violations."""
        severity_counts = {
            "CRITICAL": 0,
            "HIGH": 0,
            "MEDIUM": 0,
            "LOW": 0,
            "INFO": 0,
        }

        for violation in violations:
            severity_counts[violation.severity.value] += 1

        passed = severity_counts["CRITICAL"] == 0 and severity_counts["HIGH"] == 0

        summary = cls._build_summary(severity_counts, passed)

        return cls(
            file_path=file_path,
            violations=violations,
            severity_counts=severity_counts,
            passed=passed,
            summary=summary,
        )

    @staticmethod
    def _build_summary(severity_counts: Dict[str, int], passed: bool) -> str:
        """Build summary message."""
        if passed and sum(severity_counts.values()) == 0:
            return "✅ No violations found"

        parts = []
        if severity_counts["CRITICAL"] > 0:
            parts.append(f"🔴 {severity_counts['CRITICAL']} CRITICAL")
        if severity_counts["HIGH"] > 0:
            parts.append(f"🟠 {severity_counts['HIGH']} HIGH")
        if severity_counts["MEDIUM"] > 0:
            parts.append(f"🟡 {severity_counts['MEDIUM']} MEDIUM")
        if severity_counts["LOW"] > 0:
            parts.append(f"🔵 {severity_counts['LOW']} LOW")

        status = "⚠️ WARNINGS" if passed else "❌ BLOCKED"
        return f"{status}: {', '.join(parts)}"


class EnhancedRulesEngine(RulesEngine):
    """
    Enhanced rules engine with code review integration.

    Extends base RulesEngine with:
    - Comprehensive language detection
    - Code review workflow integration
    - Batch file checking
    - Severity-based filtering
    """

    def __init__(self, rules_path: Optional[Path] = None):
        """Initialize enhanced rules engine."""
        super().__init__(rules_path)
        self._load_enhanced_rules()

    def _load_enhanced_rules(self) -> None:
        """Load enhanced rule set."""
        # Common rules (apply to all languages)
        common_rules = [
            Rule(
                name="no-hardcoded-secrets",
                description="No hardcoded API keys, passwords, or tokens",
                severity=RuleSeverity.CRITICAL,
                pattern="api_key = ",
            ),
            Rule(
                name="no-console-log",
                description="No console.log statements in production code",
                severity=RuleSeverity.MEDIUM,
                pattern="console.log(",
            ),
            Rule(
                name="no-print-statements",
                description="Use logging instead of print statements",
                severity=RuleSeverity.LOW,
                language="python",
                pattern="print(",
            ),
            Rule(
                name="no-var-keyword",
                description="Use const or let instead of var",
                severity=RuleSeverity.MEDIUM,
                language="javascript",
                pattern="var ",
            ),
            Rule(
                name="no-any-type",
                description="Avoid using 'any' type in TypeScript",
                severity=RuleSeverity.LOW,
                language="typescript",
                pattern=": any",
            ),
        ]

        for rule in common_rules:
            if rule not in self.common_rules:
                self.common_rules.append(rule)

    def detect_language(self, file_path: Path) -> Optional[str]:
        """
        Detect programming language from file extension.

        Args:
            file_path: Path to file

        Returns:
            Language name or None
        """
        extension_map = {
            ".py": "python",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".js": "javascript",
            ".jsx": "javascript",
            ".go": "go",
            ".rs": "rust",
            ".java": "java",
            ".kt": "kotlin",
            ".swift": "swift",
            ".cpp": "cpp",
            ".cc": "cpp",
            ".cxx": "cpp",
            ".hpp": "cpp",
            ".h": "cpp",
            ".php": "php",
            ".rb": "ruby",
            ".c": "c",
            ".cs": "csharp",
        }

        return extension_map.get(file_path.suffix)

    def review_file(self, file_path: Path, code: str) -> CodeReviewResult:
        """
        Review a single file for rule violations.

        Args:
            file_path: Path to file
            code: File contents

        Returns:
            Code review result
        """
        violations = self.check(code, file_path)
        return CodeReviewResult.from_violations(file_path, violations)

    def review_files(
        self, files: List[tuple[Path, str]]
    ) -> List[CodeReviewResult]:
        """
        Review multiple files for rule violations.

        Args:
            files: List of (file_path, code) tuples

        Returns:
            List of code review results
        """
        results = []
        for file_path, code in files:
            result = self.review_file(file_path, code)
            results.append(result)
        return results

    def get_violations_by_severity(
        self, violations: List[RuleViolation], severity: RuleSeverity
    ) -> List[RuleViolation]:
        """
        Filter violations by severity.

        Args:
            violations: List of violations
            severity: Severity level to filter

        Returns:
            Filtered violations
        """
        return [v for v in violations if v.severity == severity]

    def get_blocking_violations(
        self, violations: List[RuleViolation]
    ) -> List[RuleViolation]:
        """
        Get violations that should block code merge.

        Args:
            violations: List of violations

        Returns:
            CRITICAL and HIGH severity violations
        """
        return [
            v
            for v in violations
            if v.severity in [RuleSeverity.CRITICAL, RuleSeverity.HIGH]
        ]

    def should_block_merge(self, violations: List[RuleViolation]) -> bool:
        """
        Determine if violations should block code merge.

        Args:
            violations: List of violations

        Returns:
            True if merge should be blocked
        """
        return len(self.get_blocking_violations(violations)) > 0

    def get_review_summary(
        self, results: List[CodeReviewResult]
    ) -> Dict[str, any]:
        """
        Get summary of code review results.

        Args:
            results: List of review results

        Returns:
            Summary dictionary
        """
        total_files = len(results)
        files_passed = sum(1 for r in results if r.passed)
        files_blocked = total_files - files_passed

        total_violations = sum(len(r.violations) for r in results)

        severity_totals = {
            "CRITICAL": 0,
            "HIGH": 0,
            "MEDIUM": 0,
            "LOW": 0,
            "INFO": 0,
        }

        for result in results:
            for severity, count in result.severity_counts.items():
                severity_totals[severity] += count

        return {
            "total_files": total_files,
            "files_passed": files_passed,
            "files_blocked": files_blocked,
            "total_violations": total_violations,
            "severity_totals": severity_totals,
            "should_block_merge": severity_totals["CRITICAL"] > 0
            or severity_totals["HIGH"] > 0,
        }


def create_code_review_engine(rules_path: Optional[Path] = None) -> EnhancedRulesEngine:
    """
    Create enhanced rules engine for code review.

    Args:
        rules_path: Optional path to custom rules

    Returns:
        Configured enhanced rules engine
    """
    return EnhancedRulesEngine(rules_path)
