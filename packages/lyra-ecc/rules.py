"""
ECC Rules Engine

Implements ECC-compatible rules engine for Lyra.
"""

from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class RuleSeverity(Enum):
    """Rule violation severity levels."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


@dataclass(frozen=True)
class Rule:
    """A code quality or style rule."""
    name: str
    description: str
    severity: RuleSeverity
    language: Optional[str] = None
    pattern: Optional[str] = None

    def applies_to(self, file_path: Path) -> bool:
        """Check if rule applies to file."""
        if not self.language:
            return True

        language_extensions = {
            "python": [".py"],
            "typescript": [".ts", ".tsx"],
            "javascript": [".js", ".jsx"],
            "go": [".go"],
            "rust": [".rs"],
            "java": [".java"],
            "kotlin": [".kt"],
            "swift": [".swift"],
            "cpp": [".cpp", ".cc", ".cxx", ".hpp", ".h"],
        }

        extensions = language_extensions.get(self.language, [])
        return file_path.suffix in extensions

    def check(self, code: str) -> 'RuleCheckResult':
        """Check code against rule."""
        # Simple pattern matching (would be more sophisticated in production)
        if self.pattern and self.pattern in code:
            return RuleCheckResult(
                passed=False,
                message=f"Rule violation: {self.description}",
                line=self._find_line(code, self.pattern)
            )
        return RuleCheckResult(passed=True)

    def _find_line(self, code: str, pattern: str) -> int:
        """Find line number of pattern in code."""
        lines = code.split('\n')
        for i, line in enumerate(lines, 1):
            if pattern in line:
                return i
        return 0


@dataclass(frozen=True)
class RuleCheckResult:
    """Result of checking code against a rule."""
    passed: bool
    message: Optional[str] = None
    line: int = 0


@dataclass(frozen=True)
class RuleViolation:
    """A rule violation found in code."""
    rule: str
    severity: RuleSeverity
    message: str
    line: int
    file_path: Optional[Path] = None


class RulesEngine:
    """ECC-compatible rules engine for Lyra."""

    def __init__(self, rules_path: Optional[Path] = None):
        """
        Initialize rules engine.

        Args:
            rules_path: Path to rules directory
        """
        self.rules_path = rules_path or Path.home() / ".claude" / "rules"
        self.common_rules: List[Rule] = []
        self.language_rules: Dict[str, List[Rule]] = {}
        self.active_rules: List[Rule] = []

        self._load_rules()

    def _load_rules(self) -> None:
        """Load all rules from rules directory."""
        if not self.rules_path.exists():
            logger.warning(f"Rules path not found: {self.rules_path}")
            return

        # Load common rules
        common_path = self.rules_path / "common"
        if common_path.exists():
            self.common_rules = self._load_rules_from_dir(common_path)

        # Load language-specific rules
        for lang_dir in self.rules_path.iterdir():
            if lang_dir.is_dir() and lang_dir.name != "common":
                lang_rules = self._load_rules_from_dir(lang_dir, lang_dir.name)
                self.language_rules[lang_dir.name] = lang_rules

        logger.info(f"Loaded {len(self.common_rules)} common rules")
        logger.info(f"Loaded rules for {len(self.language_rules)} languages")

    def _load_rules_from_dir(
        self,
        rules_dir: Path,
        language: Optional[str] = None
    ) -> List[Rule]:
        """Load rules from a directory."""
        rules: List[Rule] = []

        for rule_file in rules_dir.glob("*.md"):
            try:
                rule = self._parse_rule_file(rule_file, language)
                rules.append(rule)
            except Exception as e:
                logger.error(f"Failed to parse rule {rule_file}: {e}")

        return rules

    def _parse_rule_file(self, rule_file: Path, language: Optional[str]) -> Rule:
        """Parse a rule file."""
        content = rule_file.read_text()

        # Extract rule name and description
        lines = content.split('\n')
        name = rule_file.stem
        description = ""

        for line in lines:
            if line.startswith('# '):
                description = line[2:].strip()
                break

        return Rule(
            name=name,
            description=description or name,
            severity=RuleSeverity.MEDIUM,
            language=language
        )

    def activate_for_project(self, project_path: Path) -> None:
        """
        Activate rules based on project languages.

        Args:
            project_path: Path to project directory
        """
        languages = self._detect_languages(project_path)

        # Always include common rules
        self.active_rules = self.common_rules.copy()

        # Add language-specific rules
        for lang in languages:
            if lang in self.language_rules:
                self.active_rules.extend(self.language_rules[lang])

        logger.info(f"Activated {len(self.active_rules)} rules for project")

    def _detect_languages(self, project_path: Path) -> List[str]:
        """Detect programming languages used in project."""
        languages = set()

        # Simple detection based on file extensions
        for file_path in project_path.rglob("*"):
            if file_path.is_file():
                suffix = file_path.suffix
                if suffix == ".py":
                    languages.add("python")
                elif suffix in [".ts", ".tsx"]:
                    languages.add("typescript")
                elif suffix in [".js", ".jsx"]:
                    languages.add("javascript")
                elif suffix == ".go":
                    languages.add("go")
                elif suffix == ".rs":
                    languages.add("rust")
                elif suffix == ".java":
                    languages.add("java")
                elif suffix == ".kt":
                    languages.add("kotlin")
                elif suffix == ".swift":
                    languages.add("swift")
                elif suffix in [".cpp", ".cc", ".cxx"]:
                    languages.add("cpp")

        return list(languages)

    def check(self, code: str, file_path: Path) -> List[RuleViolation]:
        """
        Check code against active rules.

        Args:
            code: Code to check
            file_path: Path to file being checked

        Returns:
            List of rule violations
        """
        violations: List[RuleViolation] = []

        for rule in self.active_rules:
            if rule.applies_to(file_path):
                result = rule.check(code)
                if not result.passed:
                    violations.append(RuleViolation(
                        rule=rule.name,
                        severity=rule.severity,
                        message=result.message or "Rule violation",
                        line=result.line,
                        file_path=file_path,
                    ))

        return violations

    def get_rules_summary(self) -> Dict[str, Any]:
        """Get summary of loaded rules."""
        return {
            "common_rules": len(self.common_rules),
            "language_rules": len(self.language_rules),
            "active_rules": len(self.active_rules),
            "languages": list(self.language_rules.keys()),
        }
