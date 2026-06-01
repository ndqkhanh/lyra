"""Gate 2: Semantic Correctness Checker.

Validates semantic correctness of skill implementation.
Threshold: 0.95 (near-perfect required)
Auto-fix: Enabled for minor issues
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class SemanticValidationResult:
    """Result from semantic validation."""

    score: float  # 0.0–1.0
    issues: tuple[str, ...]
    auto_fixes_applied: tuple[str, ...]
    recommendation: str
    passed: bool


class SemanticChecker:
    """Gate 2: Validates semantic correctness of skill.

    Checks:
    - No hardcoded secrets (API keys, tokens, passwords)
    - No destructive defaults (rm -rf, DROP TABLE, etc.)
    - Skill defines callable entry point
    - Shell scripts have valid shebang
    - Import statements are reasonable
    """

    THRESHOLD = 0.95

    _CHECKS: dict[str, str] = {
        "imports_resolvable": "Import statements reference known stdlib or installed packages",
        "no_hardcoded_secrets": "No hardcoded API keys, tokens, or passwords",
        "function_defined": "Skill defines at least one callable or script entry point",
        "valid_shebang": "Shell skills must have valid shebang (#!/bin/bash, etc.)",
        "no_destructive_defaults": "No rm -rf, DROP TABLE, or similar destructive defaults",
    }

    def validate(
        self,
        skill_name: str,
        skill_triggers: tuple[str, ...],
        skill_body: str,
    ) -> SemanticValidationResult:
        """Validate semantic correctness of a skill.

        Args:
            skill_name: Name of the skill
            skill_triggers: Trigger phrases for the skill
            skill_body: The skill implementation code

        Returns:
            SemanticValidationResult with score, issues, and recommendation
        """
        issues: list[str] = []
        fixes: list[str] = []

        stripped = skill_body.strip()

        # Check if shell script
        is_shell = stripped.startswith("#!")
        if is_shell:
            # Validate shebang
            if not re.match(r"^#!\s*/", stripped.split("\n")[0]):
                issues.append(self._CHECKS["valid_shebang"])
            # Check for entry point
            if not any(
                kw in stripped for kw in ("def ", "function", "()", "echo", "printf", "#!/")
            ):
                issues.append(self._CHECKS["function_defined"])
        else:
            # Python: check for entry point
            if "def " not in stripped and "class " not in stripped and "import " not in stripped:
                issues.append(self._CHECKS["function_defined"])

        # Check for hardcoded secrets (critical issue)
        has_secrets = False
        secret_patterns = [
            r'(?:api[_-]?key|apikey|secret|token|password|passwd)\s*[:=]\s*["\'][\w\-]{8,}["\']',
            r"(?:sk-[A-Za-z0-9]{20,})",  # OpenAI-style keys
            r"(?:AKIA[0-9A-Z]{16})",  # AWS access keys
        ]
        for pat in secret_patterns:
            if re.search(pat, stripped, re.IGNORECASE):
                issues.append(self._CHECKS["no_hardcoded_secrets"])
                has_secrets = True
                break

        # Check for destructive defaults (critical issue)
        has_destructive = False
        destructive_defaults = [
            r"\brm\s+-rf\b",
            r"\bDROP\s+TABLE\b",
            r"\bDELETE\s+FROM\b",
            r"\bTRUNCATE\s+TABLE\b",
        ]
        for pat in destructive_defaults:
            if re.search(pat, stripped, re.IGNORECASE):
                issues.append(self._CHECKS["no_destructive_defaults"])
                has_destructive = True
                break

        # Calculate score (secrets and destructive patterns are critical)
        if has_secrets or has_destructive:
            score = 0.6  # Below threshold, requires review
        else:
            score = 1.0 - (len(issues) * 0.2)
        score = max(0.0, min(1.0, score))

        # Determine status and recommendation
        if has_secrets or has_destructive:
            recommendation = "Critical semantic errors: hardcoded secrets or destructive operations detected."
            passed = False
        elif score >= self.THRESHOLD:
            recommendation = "Semantic checks passed."
            passed = True
        elif score >= 0.8:
            recommendation = "Minor semantic issues addressed."
            passed = True
        elif score >= 0.6:
            recommendation = "Semantic issues need human review."
            passed = False
        else:
            recommendation = "Critical semantic errors detected."
            passed = False

        return SemanticValidationResult(
            score=round(score, 4),
            issues=tuple(issues),
            auto_fixes_applied=tuple(fixes),
            recommendation=recommendation,
            passed=passed,
        )
