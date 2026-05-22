"""Formal Ethics Framework — principle-based ethical reasoning, dilemma resolution, value alignment.

Encodes ethical principles as formal constraints. Resolves conflicts between
principles. Logs every ethical decision for audit.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional

logger = logging.getLogger(__name__)

__all__ = [
    "EthicalPrinciple",
    "PrinciplePriority",
    "Dilemma",
    "EthicsEngine",
]


class PrinciplePriority(Enum):
    ABSOLUTE = auto()
    HIGH = auto()
    MEDIUM = auto()
    LOW = auto()
    ASPIRATIONAL = auto()


@dataclass
class EthicalPrinciple:
    name: str
    description: str
    priority: PrinciplePriority = PrinciplePriority.MEDIUM
    is_hard: bool = False  # Cannot be overridden


@dataclass
class Dilemma:
    principles_involved: list[str]
    context: str
    resolution: Optional[str] = None
    resolved_at: float = 0.0


class EthicsEngine:
    """Formal ethical reasoning engine for agents."""

    PRINCIPLES = {
        "do_no_harm": EthicalPrinciple("do_no_harm", "Agents should not cause harm to humans or systems", PrinciplePriority.ABSOLUTE, True),
        "be_honest": EthicalPrinciple("be_honest", "Agents should be truthful in communications", PrinciplePriority.HIGH),
        "respect_autonomy": EthicalPrinciple("respect_autonomy", "Respect human and agent autonomy", PrinciplePriority.HIGH),
        "be_helpful": EthicalPrinciple("be_helpful", "Act in the best interest of users", PrinciplePriority.MEDIUM),
        "be_fair": EthicalPrinciple("be_fair", "Treat all entities fairly without bias", PrinciplePriority.HIGH),
        "be_transparent": EthicalPrinciple("be_transparent", "Explain decisions when asked", PrinciplePriority.MEDIUM),
        "protect_privacy": EthicalPrinciple("protect_privacy", "Protect confidential information", PrinciplePriority.ABSOLUTE, True),
        "take_responsibility": EthicalPrinciple("take_responsibility", "Accept responsibility for actions", PrinciplePriority.HIGH),
    }

    def __init__(self):
        self.active_principles: dict[str, EthicalPrinciple] = dict(self.PRINCIPLES)
        self.dilemmas: list[Dilemma] = []
        self._audit_log: list[dict[str, Any]] = []

    def evaluate(self, action: str, context: dict[str, Any]) -> dict[str, Any]:
        """Evaluate an action against all ethical principles."""
        violations = []
        satisfied = []
        for name, principle in self.active_principles.items():
            if principle.is_hard:
                if self._violates_hard_principle(name, action, context):
                    violations.append({"principle": name, "severity": "critical"})
            else:
                if self._conflicts_with(name, action, context):
                    violations.append({"principle": name, "severity": "warning"})
                else:
                    satisfied.append(name)

        is_allowed = len([v for v in violations if v["severity"] == "critical"]) == 0
        self._audit_log.append({
            "action": action[:50],
            "allowed": is_allowed,
            "violations": violations,
            "timestamp": time.time(),
        })
        return {"allowed": is_allowed, "violations": violations, "satisfied_principles": satisfied}

    def resolve_dilemma(self, principle_a: str, principle_b: str, context: str) -> Dilemma:
        """Resolve conflict between two principles."""
        pa = self.active_principles.get(principle_a)
        pb = self.active_principles.get(principle_b)
        if not pa or not pb:
            return Dilemma([principle_a, principle_b], context, "Unknown principle")

        if pa.priority.value < pb.priority.value:
            winner = pa.name
        elif pb.priority.value < pa.priority.value:
            winner = pb.name
        else:
            winner = f"{pa.name} (hard constraint)" if pa.is_hard else f"{pb.name} (hard constraint)"

        dilemma = Dilemma([principle_a, principle_b], context, f"Resolved in favor of: {winner}")
        self.dilemmas.append(dilemma)
        return dilemma

    def _violates_hard_principle(self, principle: str, action: str, context: dict) -> bool:
        action_lower = action.lower()
        if principle == "do_no_harm" and any(w in action_lower for w in ["delete", "destroy", "harm", "attack"]):
            return True
        if principle == "protect_privacy" and "password" in action_lower and "share" in action_lower:
            return True
        return False

    def _conflicts_with(self, principle: str, action: str, context: dict) -> bool:
        action_lower = action.lower()
        if principle == "be_honest" and any(w in action_lower for w in ["lie", "deceive", "mislead", "fake"]):
            return True
        if principle == "be_fair" and any(w in action_lower for w in ["discriminat", "bias", "unfair"]):
            return True
        return False

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "principles": len(self.active_principles),
            "dilemmas_resolved": len(self.dilemmas),
            "audit_entries": len(self._audit_log),
            "hard_constraints": sum(1 for p in self.active_principles.values() if p.is_hard),
        }
