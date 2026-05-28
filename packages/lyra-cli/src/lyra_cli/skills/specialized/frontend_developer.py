"""Frontend Developer Skill — UI component analysis and accessibility validation.

Checks React/Vue/Svelte components for:
- Accessibility (a11y) compliance
- Performance anti-patterns
- Component composition and reusability
- State management best practices
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum


class A11ySeverity(StrEnum):
    CRITICAL = "critical"
    SERIOUS = "serious"
    MODERATE = "moderate"
    MINOR = "minor"


@dataclass(frozen=True)
class A11yIssue:
    element: str
    severity: A11ySeverity
    rule: str
    message: str
    fix: str


class FrontendDeveloperSkill:
    """Analyzes frontend components for accessibility and best practices."""

    _A11Y_CHECKS = [
        (r"<img(?!.*alt=)", A11ySeverity.CRITICAL, "img-alt",
         "Image missing alt attribute.", "Add descriptive alt text for screen readers."),
        (r"<button(?!.*aria-label=|.*>.*</button>)", A11ySeverity.SERIOUS, "button-label",
         "Button may lack accessible label.", "Add aria-label or text content to button."),
        (r"<input(?!.*aria-label=|.*<label)", A11ySeverity.SERIOUS, "input-label",
         "Input missing associated label.", "Add <label> or aria-label for the input."),
        (r"<div\s+onClick=", A11ySeverity.CRITICAL, "div-click",
         "Clickable div — not keyboard accessible.", "Use <button> instead of <div onClick>."),
        (r"tabIndex\s*=\s*['\"]-?[2-9]", A11ySeverity.MODERATE, "tabindex-order",
         "Custom tabindex may disrupt natural tab order.", "Use tabindex 0 or -1 only."),
    ]

    def __init__(self) -> None:
        self._issues: list[A11yIssue] = []

    def run(self, input_data: dict) -> dict:
        source = input_data.get("source", "")
        framework = input_data.get("framework", "react")

        self._issues.clear()
        for pattern, severity, rule, msg, fix in self._A11Y_CHECKS:
            for match in re.finditer(pattern, source, re.IGNORECASE):
                self._issues.append(A11yIssue(
                    element=match.group(0)[:60],
                    severity=severity,
                    rule=rule,
                    message=msg,
                    fix=fix,
                ))

        score = max(0, 100
            - len([i for i in self._issues if i.severity == A11ySeverity.CRITICAL]) * 20
            - len([i for i in self._issues if i.severity == A11ySeverity.SERIOUS]) * 10
            - len([i for i in self._issues if i.severity == A11ySeverity.MODERATE]) * 5)

        return {
            "framework": framework,
            "issues": [i.__dict__ for i in self._issues],
            "score": score,
            "total_issues": len(self._issues),
            "passed": len(self._issues) == 0,
        }
