"""Scrum Master Skill — Agile/Scrum process validation and facilitation.

Validates Scrum practices:
- Sprint planning and backlog grooming
- Definition of Ready/Done
- Retrospective action items
- Team velocity and capacity planning
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class CeremonyHealth(StrEnum):
    HEALTHY = "healthy"
    AT_RISK = "at_risk"
    MISSING = "missing"


@dataclass(frozen=True)
class ProcessCheck:
    ceremony: str
    health: CeremonyHealth
    detail: str
    action: str


class ScrumMasterSkill:
    """Validates Scrum process health and team practices."""

    _REQUIRED_CEREMONIES = frozenset(
        {"sprint_planning", "daily_standup", "sprint_review", "retrospective", "backlog_refinement"}
    )

    def run(self, input_data: dict) -> dict:
        ceremonies = input_data.get("ceremonies", [])
        sprint = input_data.get("sprint", {})
        checks: list[ProcessCheck] = []

        ceremony_names = {c.get("name", "").lower().replace(" ", "_") for c in ceremonies}
        for required in self._REQUIRED_CEREMONIES:
            if required not in ceremony_names:
                readable = required.replace("_", " ").title()
                checks.append(
                    ProcessCheck(
                        required,
                        CeremonyHealth.MISSING,
                        f"'{readable}' ceremony is not scheduled.",
                        f"Schedule {readable} at the appropriate cadence.",
                    )
                )

        if not sprint.get("goal"):
            checks.append(
                ProcessCheck(
                    "sprint",
                    CeremonyHealth.AT_RISK,
                    "No sprint goal defined.",
                    "Define a clear, measurable sprint goal.",
                )
            )

        if not sprint.get("definition_of_done"):
            checks.append(
                ProcessCheck(
                    "sprint",
                    CeremonyHealth.AT_RISK,
                    "No Definition of Done documented.",
                    "Create and agree on a Definition of Done checklist.",
                )
            )

        total_points = sprint.get("total_story_points", 0)
        velocity = sprint.get("average_velocity", 0)
        if velocity > 0 and total_points > velocity * 1.5:
            checks.append(
                ProcessCheck(
                    "sprint",
                    CeremonyHealth.AT_RISK,
(
                        f"Sprint commitment ({total_points} pts) exceeds average velocity ("
                        f"{velocity} pts)."
                    ),
                    "Reduce sprint commitment to match historical velocity.",
                )
            )

        return {
            "checks": [c.__dict__ for c in checks],
            "health_score": max(
                0,
                100
                - len([c for c in checks if c.health == CeremonyHealth.MISSING]) * 20
                - len([c for c in checks if c.health == CeremonyHealth.AT_RISK]) * 10,
            ),
            "ceremonies_covered": len(ceremony_names & self._REQUIRED_CEREMONIES),
            "total_required": len(self._REQUIRED_CEREMONIES),
        }
