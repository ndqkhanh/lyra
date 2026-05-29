"""
Rule data models and types.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class RuleCategory(str, Enum):
    """Categories of rules."""

    CODING_STYLE = "coding-style"
    GIT_WORKFLOW = "git-workflow"
    TESTING = "testing"
    PERFORMANCE = "performance"
    PATTERNS = "patterns"
    HOOKS = "hooks"
    AGENTS = "agents"
    SECURITY = "security"
    CODE_REVIEW = "code-review"
    DEVELOPMENT_WORKFLOW = "development-workflow"


class RuleSeverity(str, Enum):
    """Severity levels for rule violations."""

    ERROR = "error"  # Must fix
    WARNING = "warning"  # Should fix
    INFO = "info"  # Nice to fix
    HINT = "hint"  # Suggestion


@dataclass
class RuleViolation:
    """
    Represents a rule violation.

    Records when and where a rule was violated.
    """

    rule_id: str
    severity: RuleSeverity
    message: str
    file_path: str | None = None
    line_number: int | None = None
    column: int | None = None
    context: str | None = None
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Rule:
    """
    Rule definition.

    Defines a coding standard, best practice, or guideline.
    """

    rule_id: str
    category: RuleCategory
    title: str
    description: str
    severity: RuleSeverity = RuleSeverity.WARNING
    language: str | None = None  # e.g., "python", "typescript"
    file_patterns: list[str] = field(default_factory=list)  # e.g., ["**/*.py"]
    enabled: bool = True
    priority: int = 0  # Higher priority rules checked first
    examples: dict[str, str] = field(default_factory=dict)  # good/bad examples
    references: list[str] = field(default_factory=list)  # Links to docs
    metadata: dict[str, Any] = field(default_factory=dict)

    def matches_file(self, file_path: str) -> bool:
        """
        Check if this rule applies to a file.

        Args:
            file_path: Path to check

        Returns:
            True if rule applies
        """
        if not self.enabled:
            return False

        # If no patterns specified, applies to all files
        if not self.file_patterns:
            return True

        # Check if file matches any pattern
        import fnmatch
        return any(
            fnmatch.fnmatch(file_path, pattern)
            for pattern in self.file_patterns
        )

    def matches_language(self, language: str) -> bool:
        """
        Check if this rule applies to a language.

        Args:
            language: Language to check

        Returns:
            True if rule applies
        """
        if not self.enabled:
            return False

        # If no language specified, applies to all languages
        if not self.language:
            return True

        return self.language.lower() == language.lower()
