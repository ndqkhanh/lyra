"""
Autonomy controller for Lyra personalization system.

Determines the appropriate level of autonomous behavior based on
user profile, task characteristics, and historical outcomes of
escalation decisions.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from lyra_personalization.models import (
    AutonomyLevel,
    InteractionRecord,
    SkillLevel,
    UserProfile,
)

logger = logging.getLogger(__name__)

HIGH_STAKES_KEYWORDS = [
    "delete", "remove", "destroy", "overwrite", "reset",
    "permission", "admin", "sudo", "production", "deploy",
    "financial", "payment", "database", "migration",
]

SENSITIVE_DOMAINS = [
    "security", "auth", "payments", "compliance", "privacy",
    "infrastructure", "production",
]


@dataclass
class EscalationRecord:
    """Record of a human escalation event."""
    action: str
    confidence: float
    approved: bool
    timestamp: datetime = field(default_factory=datetime.now)
    task_type: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class AutonomyController:
    """
    Controls autonomous decision-making based on user and task context.

    Features:
    - Per-task autonomy level determination
    - Confidence-based escalation triggers
    - Learning from escalation outcomes
    - Trust score computation
    """

    def __init__(self) -> None:
        self._escalations: List[EscalationRecord] = []

    def get_autonomy_level(
        self,
        user: UserProfile,
        task: str,
    ) -> AutonomyLevel:
        """
        Determine appropriate autonomy level for a given task.

        Considers user trust score, skill in relevant domains,
        task criticality, and past escalation outcomes.

        Args:
            user: The user profile.
            task: Description of the task to be performed.

        Returns:
            Appropriate AutonomyLevel for this task.
        """
        if self._task_critical(task):
            return AutonomyLevel.MANUAL

        if user.trust_score >= 0.8 and not self._in_sensitive_domain(task):
            return AutonomyLevel.FULLY_AUTONOMOUS

        if user.trust_score >= 0.4 or self._user_skilled_for_task(user, task):
            return AutonomyLevel.SUGGEST_ONLY

        return AutonomyLevel.MANUAL

    def should_escalate(
        self,
        action: str,
        confidence: float,
    ) -> bool:
        """
        Determine if an action needs human approval.

        Escalation is triggered when:
        - Confidence is below threshold
        - Action involves high-stakes operations
        - Recent escalation history suggests caution

        Args:
            action: Description of the action.
            confidence: Model confidence in the action (0.0-1.0).

        Returns:
            True if the action should be escalated for approval.
        """
        if confidence < 0.3:
            logger.info("Escalating due to low confidence: %.2f", confidence)
            return True

        if self._is_high_stakes(action):
            logger.info("Escalating high-stakes action: %s", action[:50])
            return True

        recent_denials = sum(
            1 for e in self._escalations[-10:]
            if not e.approved
        )
        if recent_denials >= 3 and confidence < 0.7:
            logger.info(
                "Escalating due to recent denials (%d) and moderate confidence",
                recent_denials,
            )
            return True

        return False

    def record_escalation_outcome(self, escalation: EscalationRecord) -> None:
        """
        Record the outcome of an escalation for learning.

        Tracks whether approvals/denials were correct so the
        system can adjust autonomy behavior over time.

        Args:
            escalation: The escalation record to record.
        """
        self._escalations.append(escalation)
        logger.info(
            "Recorded escalation: action=%s, approved=%s",
            escalation.action[:30],
            escalation.approved,
        )

    def compute_trust_score(self, user: UserProfile) -> float:
        """
        Compute trust score for autonomous decision-making.

        Factors:
        - Interaction history volume and success rate
        - Skill levels across domains
        - Escalation approval/disapproval ratio
        - Recency of positive interactions

        Args:
            user: The user profile to compute trust for.

        Returns:
            Trust score between 0.0 and 1.0.
        """
        score = user.trust_score

        interactions = user.rich_repr.interaction_history
        if interactions:
            recent = interactions[-50:]
            success_rate = sum(
                1 for i in recent
                if i.outcome and "success" in i.outcome.lower()
            ) / len(recent)
            score = score * 0.6 + success_rate * 0.4

        if self._escalations:
            approved_rate = sum(
                1 for e in self._escalations
                if e.approved
            ) / len(self._escalations)
            score = score * 0.7 + approved_rate * 0.3

        skill_values = user.rich_repr.skill_levels.values()
        if skill_values:
            avg_skill = self._average_skill_level(list(skill_values))
            score = score * 0.8 + avg_skill * 0.2

        return max(0.0, min(1.0, score))

    def get_escalation_history(self) -> List[EscalationRecord]:
        """Get the full escalation history."""
        return list(self._escalations)

    def _task_critical(self, task: str) -> bool:
        """Check if a task is critical enough to require manual oversight."""
        task_lower = task.lower()
        critical_count = sum(
            1 for kw in HIGH_STAKES_KEYWORDS
            if kw in task_lower
        )
        return critical_count >= 2

    def _in_sensitive_domain(self, task: str) -> bool:
        """Check if a task falls in a sensitive domain."""
        task_lower = task.lower()
        return any(domain in task_lower for domain in SENSITIVE_DOMAINS)

    def _is_high_stakes(self, action: str) -> bool:
        """Check if an action has high stakes."""
        action_lower = action.lower()
        return any(kw in action_lower for kw in HIGH_STAKES_KEYWORDS)

    def _user_skilled_for_task(self, user: UserProfile, task: str) -> bool:
        """Check if the user has sufficient skill for a task."""
        for domain, skill in user.rich_repr.skill_levels.items():
            if domain.lower() in task.lower():
                return skill in (
                    SkillLevel.ADVANCED,
                    SkillLevel.EXPERT,
                )
        return False

    @staticmethod
    def _average_skill_level(levels: List[SkillLevel]) -> float:
        """Convert skill levels to numeric average."""
        order = ["novice", "beginner", "intermediate", "advanced", "expert"]
        numeric = [
            order.index(s.value) / (len(order) - 1)
            for s in levels
            if s.value in order
        ]
        if not numeric:
            return 0.5
        return sum(numeric) / len(numeric)
