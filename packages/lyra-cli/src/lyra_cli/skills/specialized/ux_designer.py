"""UX Designer Skill — user experience heuristic evaluation.

Evaluates UI/UX designs against Nielsen's heuristics:
- Visibility of system status
- Match between system and real world
- User control and freedom
- Consistency and standards
- Error prevention, recognition, and recovery
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class HeuristicViolation(StrEnum):
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    COSMETIC = "cosmetic"


@dataclass(frozen=True)
class UXIssue:
    heuristic: str
    severity: HeuristicViolation
    description: str
    recommendation: str


_NIELSEN_HEURISTICS = [
    "visibility_of_system_status",
    "match_system_real_world",
    "user_control_freedom",
    "consistency_standards",
    "error_prevention",
    "recognition_rather_recall",
    "flexibility_efficiency",
    "aesthetic_minimalist",
    "help_users_with_errors",
    "help_documentation",
]


class UXDesignerSkill:
    """Evaluates UI/UX against Nielsen's 10 usability heuristics."""

    def run(self, input_data: dict) -> dict:
        screens = input_data.get("screens", [])
        issues: list[UXIssue] = []

        has_loading = any(s.get("has_loading_state") for s in screens)
        if not has_loading and screens:
            issues.append(
                UXIssue(
                    "visibility_of_system_status",
                    HeuristicViolation.MAJOR,
                    "No loading states defined — users won't know the system is working.",
                    "Add loading indicators, progress bars, or skeleton screens.",
                )
            )

        has_error = any(s.get("has_error_state") for s in screens)
        if not has_error and screens:
            issues.append(
                UXIssue(
                    "error_prevention",
                    HeuristicViolation.CRITICAL,
                    "No error states defined — users will be confused by failures.",
                    "Design error messages, recovery actions, and fallback states.",
                )
            )

        has_empty = any(s.get("has_empty_state") for s in screens)
        if not has_empty and len(screens) > 2:
            issues.append(
                UXIssue(
                    "help_documentation",
                    HeuristicViolation.MINOR,
                    "No empty states designed — new users see blank screens.",
                    "Add empty state illustrations with call-to-action guidance.",
                )
            )

        has_confirmation = any(
            "confirm" in str(s).lower() or "modal" in str(s).lower() for s in screens
        )
        if not has_confirmation and len(screens) > 1:
            issues.append(
                UXIssue(
                    "user_control_freedom",
                    HeuristicViolation.MAJOR,
                    "No confirmation dialogs for destructive actions.",
                    "Add confirmation modals for delete, overwrite, and irreversible actions.",
                )
            )

        return {
            "issues": [i.__dict__ for i in issues],
            "heuristics_evaluated": len(_NIELSEN_HEURISTICS),
            "score": max(
                0,
                100
                - len([i for i in issues if i.severity == HeuristicViolation.CRITICAL]) * 25
                - len([i for i in issues if i.severity == HeuristicViolation.MAJOR]) * 15
                - len([i for i in issues if i.severity == HeuristicViolation.MINOR]) * 5,
            ),
        }
