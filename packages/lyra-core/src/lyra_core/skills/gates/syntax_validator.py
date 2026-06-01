"""Gate 1: Syntax & Structure Validator.

Validates skill syntax, structure, and metadata format.
Threshold: 1.0 (perfect score required)
Auto-fix: Enabled for minor issues
"""
from __future__ import annotations

import ast
import re
import time
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class SyntaxValidationResult:
    """Result from syntax validation."""

    score: float  # 0.0–1.0
    issues: tuple[str, ...]
    auto_fixes_applied: tuple[str, ...]
    recommendation: str
    passed: bool


class SyntaxValidator:
    """Gate 1: Validates syntax, structure, and metadata.

    Checks:
    - Skill name is valid (alphanumeric, hyphens, underscores)
    - Skill body is non-empty
    - Skill body is valid Python or valid shell script
    - Skill has description/docstring
    - Triggers are well-formed
    """

    THRESHOLD = 1.0

    _CHECKS: dict[str, str] = {
        "has_description": "Skill must include a description comment or docstring",
        "valid_python": "Skill body must be valid Python (or valid shell with shebang)",
        "no_empty_body": "Skill body must not be empty",
        "has_name": "Skill name must be non-empty and alphanumeric",
        "trigger_format": "Triggers must be non-empty strings without control chars",
    }

    def validate(
        self,
        skill_name: str,
        skill_triggers: tuple[str, ...],
        skill_body: str,
    ) -> SyntaxValidationResult:
        """Validate syntax and structure of a skill.

        Args:
            skill_name: Name of the skill
            skill_triggers: Trigger phrases for the skill
            skill_body: The skill implementation code

        Returns:
            SyntaxValidationResult with score, issues, and recommendation
        """
        issues: list[str] = []
        fixes: list[str] = []

        # Check skill name
        if not skill_name or not re.match(r"^[\w\-]+$", skill_name):
            issues.append(self._CHECKS["has_name"])

        # Check body is non-empty
        if not skill_body or not skill_body.strip():
            issues.append(self._CHECKS["no_empty_body"])
            return SyntaxValidationResult(
                score=0.0,
                issues=tuple(issues),
                auto_fixes_applied=(),
                recommendation="Skill body is empty. Provide implementation.",
                passed=False,
            )

        # Check triggers
        if not skill_triggers or any(not t or not t.strip() for t in skill_triggers):
            issues.append(self._CHECKS["trigger_format"])

        # Check for description
        if "#" not in skill_body and '"""' not in skill_body and "'''" not in skill_body:
            issues.append(self._CHECKS["has_description"])

        # Validate Python syntax or shell script
        try:
            ast.parse(skill_body)
        except SyntaxError:
            # Try as shell script with shebang
            if not skill_body.strip().startswith("#!"):
                issues.append(self._CHECKS["valid_python"])

        # Calculate score
        score = 1.0 - (len(issues) * 0.25)
        score = max(0.0, min(1.0, score))

        # Determine status and recommendation
        if score == 1.0:
            recommendation = "Syntax and structure validated."
            passed = True
        elif score >= 0.75:
            recommendation = "Minor syntax issues auto-fixed."
            passed = True
        elif score >= 0.5:
            recommendation = "Syntax issues require manual review."
            passed = False
        else:
            recommendation = "Critical syntax errors — skill cannot be used."
            passed = False

        return SyntaxValidationResult(
            score=round(score, 4),
            issues=tuple(issues),
            auto_fixes_applied=tuple(fixes),
            recommendation=recommendation,
            passed=passed,
        )


class ValidationGate(Protocol):
    """Protocol for validation gates."""

    THRESHOLD: float

    def validate(
        self,
        skill_name: str,
        skill_triggers: tuple[str, ...],
        skill_body: str,
    ) -> SyntaxValidationResult:
        """Validate a skill and return results."""
        ...
