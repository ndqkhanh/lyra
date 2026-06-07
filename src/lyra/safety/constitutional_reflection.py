"""
Constitutional reflection for Lyra safety (v8.3).

Provides ``ConstitutionalReflection`` — a subsystem that enables agents
to self-audit their actions against a set of safety principles.
Supports periodic constitutional review (daily self-audit), corrective
action generation, and violation reporting.

Principles
----------
* harm_prevention — Do not cause harm to users, systems, or data.
* honesty — Be truthful about capabilities, actions, and limitations.
* transparency — Log and surface all actions affecting state.
* privacy — Respect data confidentiality and minimisation.
* accountability — Accept responsibility for actions and outcomes.

Classes
-------
ConstitutionalPrinciple:
    Enum of all supported principles.
ReflectionScore:
    Score of a single action against a single principle.
ReflectionReport:
    Full report for a batch of reflected actions.
Violation:
    An action that violated one or more principles.
CorrectiveActionKind:
    Type of corrective action (amend, rollback, notify_human).
CorrectiveAction:
    A concrete corrective action.
ConstitutionalReflection:
    Core class for running reflections and audits.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Matches uppercase transitions for camelCase -> snake_case conversion
_CAMEL_PATTERN: re.Pattern = re.compile(r"(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_PRINCIPLE_DESCRIPTIONS: Dict[str, str] = {
    "harm_prevention": (
        "Do not cause harm to users, systems, or data. "
        "Avoid destructive commands, data loss, and unsafe state changes."
    ),
    "honesty": (
        "Be truthful about capabilities, actions, and limitations. "
        "Do not misrepresent the agent's identity or authority."
    ),
    "transparency": (
        "Log and surface all actions that affect system state. "
        "No hidden side effects or unlogged mutations."
    ),
    "privacy": (
        "Respect data confidentiality and minimisation. "
        "Do not exfiltrate sensitive data or process PII without consent."
    ),
    "accountability": (
        "Accept responsibility for actions and outcomes. "
        "Provide explainable decisions and admit errors."
    ),
}


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ConstitutionalPrinciple(str, Enum):
    """A safety principle that the agent self-audits against."""

    HARM_PREVENTION = "harm_prevention"
    HONESTY = "honesty"
    TRANSPARENCY = "transparency"
    PRIVACY = "privacy"
    ACCOUNTABILITY = "accountability"

    @property
    def description(self) -> str:
        """Human-readable description of this principle."""
        return _PRINCIPLE_DESCRIPTIONS.get(self.value, "")

    @staticmethod
    def all() -> List["ConstitutionalPrinciple"]:
        """Return all principles in definition order."""
        return [
            ConstitutionalPrinciple.HARM_PREVENTION,
            ConstitutionalPrinciple.HONESTY,
            ConstitutionalPrinciple.TRANSPARENCY,
            ConstitutionalPrinciple.PRIVACY,
            ConstitutionalPrinciple.ACCOUNTABILITY,
        ]


class CorrectiveActionKind(str, Enum):
    """Type of corrective action to take for a violation."""

    AMEND = "amend"
    """Modify the action's outcome (e.g. revert a file write)."""
    ROLLBACK = "rollback"
    """Roll back the action entirely (full undo)."""
    NOTIFY_HUMAN = "notify_human"
    """Alert a human operator for manual review."""


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReflectionScore:
    """Score of a single action against a single principle.

    Attributes:
        principle: The constitutional principle being scored.
        score: A float between 0.0 (violation) and 1.0 (fully compliant).
        rationale: Human-readable justification for the score.
    """

    principle: ConstitutionalPrinciple
    score: float
    rationale: str = ""


@dataclass(frozen=True)
class ActionEntry:
    """A single logged action from the agent's action log.

    Attributes:
        action_id: Unique identifier for this action.
        tool_name: The name of the tool called.
        arguments: Arguments passed to the tool.
        result_summary: Brief summary of the action's outcome.
        timestamp: When the action occurred.
    """

    action_id: str
    tool_name: str
    arguments: Dict[str, Any] = field(default_factory=dict)
    result_summary: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass(frozen=True)
class ReflectionReport:
    """Full report for a batch of reflected actions.

    Attributes:
        action_count: Number of actions reflected upon.
        scores: Per-action, per-principle scores.
        overall_compliance: Weighted average across all actions and
            principles (0.0 — 1.0).
        timestamp: When the report was generated.
    """

    action_count: int
    scores: Dict[str, List[ReflectionScore]]
    """Map of ``action_id`` -> list of ``ReflectionScore``."""
    overall_compliance: float
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass(frozen=True)
class Violation:
    """An action that violated one or more principles.

    Attributes:
        action_id: The violating action's ID.
        action_entry: The full action entry that caused the violation.
        violated_principles: The principles that were violated.
        severity: The severity of the worst violation (1.0 — max).
        recommendations: Suggested corrective actions.
    """

    action_id: str
    action_entry: ActionEntry
    violated_principles: List[Tuple[ConstitutionalPrinciple, float, str]]
    """List of ``(principle, score, rationale)`` for violations."""
    severity: float
    recommendations: List[CorrectiveAction] = field(default_factory=list)


@dataclass(frozen=True)
class CorrectiveAction:
    """A concrete corrective action for a violation.

    Attributes:
        kind: The type of corrective action.
        action_id: The ID of the violating action.
        principle: The principle that was violated.
        rationale: Why this corrective action is recommended.
        details: Implementation details (e.g. commands to run).
    """

    kind: CorrectiveActionKind
    action_id: str
    principle: ConstitutionalPrinciple
    rationale: str
    details: str = ""


@dataclass(frozen=True)
class AuditSnapshot:
    """Snapshot of a periodic constitutional audit.

    Attributes:
        audit_id: Unique identifier for this audit.
        timestamp: When the audit was performed.
        action_count: Number of actions audited.
        violation_count: Number of violations found.
        overall_compliance: Weighted compliance score.
        was_healthy: True if compliance >= healthy threshold.
    """

    audit_id: str
    timestamp: datetime
    action_count: int
    violation_count: int
    overall_compliance: float
    was_healthy: bool


# ---------------------------------------------------------------------------
# ConstitutionalReflection
# ---------------------------------------------------------------------------


class ConstitutionalReflection:
    """Agent self-audit against constitutional principles.

    Usage::

        reflector = ConstitutionalReflection()
        report = reflector.reflect(action_log)
        violations = reflector.flag_violations(report)

        for violation in violations:
            print(violation.action_id, violation.violated_principles)
    """

    def __init__(
        self,
        principles: Optional[List[ConstitutionalPrinciple]] = None,
        healthy_threshold: float = 0.7,
        violation_threshold: float = 0.5,
    ) -> None:
        """Initialise the reflection system.

        Args:
            principles: Principles to audit against.  Defaults to all
                five.
            healthy_threshold: Compliance score above which the system
                is considered healthy.  Default 0.7.
            violation_threshold: Score below which an action is flagged
                as a violation.  Default 0.5.
        """
        self._principles = principles or ConstitutionalPrinciple.all()
        self._healthy_threshold = healthy_threshold
        self._violation_threshold = violation_threshold
        self._audit_log: List[AuditSnapshot] = []

    # ------------------------------------------------------------------
    # Core reflection
    # ------------------------------------------------------------------

    def reflect(
        self,
        action_log: List[ActionEntry],
    ) -> ReflectionReport:
        """Score each action in the log against every principle.

        Args:
            action_log: Chronological list of actions taken by the agent.

        Returns:
            A ``ReflectionReport`` with per-action, per-principle scores.
        """
        scores: Dict[str, List[ReflectionScore]] = {}
        total_score: float = 0.0
        total_checks: int = 0

        for action in action_log:
            action_scores: List[ReflectionScore] = []
            for principle in self._principles:
                action_score = self._score_action(action, principle)
                action_scores.append(action_score)
                total_score += action_score.score
                total_checks += 1

            scores[action.action_id] = action_scores

        overall = total_score / total_checks if total_checks > 0 else 1.0

        return ReflectionReport(
            action_count=len(action_log),
            scores=scores,
            overall_compliance=overall,
        )

    def _score_action(
        self,
        action: ActionEntry,
        principle: ConstitutionalPrinciple,
    ) -> ReflectionScore:
        """Score a single action against a single principle.

        This is a rule-based scoring engine.  Each principle has
        domain-specific heuristics.  Scores range 0.0 (violation) to
        1.0 (fully compliant).
        """
        if principle == ConstitutionalPrinciple.HARM_PREVENTION:
            return self._score_harm_prevention(action)
        elif principle == ConstitutionalPrinciple.HONESTY:
            return self._score_honesty(action)
        elif principle == ConstitutionalPrinciple.TRANSPARENCY:
            return self._score_transparency(action)
        elif principle == ConstitutionalPrinciple.PRIVACY:
            return self._score_privacy(action)
        elif principle == ConstitutionalPrinciple.ACCOUNTABILITY:
            return self._score_accountability(action)
        else:
            return ReflectionScore(
                principle=principle,
                score=0.5,
                rationale="Unknown principle — neutral score.",
            )

    # ------------------------------------------------------------------
    # Principle-specific scorers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalise_tool(name: str) -> str:
        """Convert a camelCase tool name to snake_case for matching."""
        s = _CAMEL_PATTERN.sub("_", name)
        return s.lower()

    @staticmethod
    def _score_harm_prevention(action: ActionEntry) -> ReflectionScore:
        """Score an action against the harm prevention principle.

        Flags:
        * Destructive Bash commands (rm -rf, dd, mkfs, sudo dangerous).
        * File deletions (Write with empty or destructive content).
        * Network mutations (POST/PUT/DELETE).
        """
        tool = ConstitutionalReflection._normalise_tool(action.tool_name)
        args = action.arguments

        # Check for known destructive patterns
        if tool == "bash":
            command = (
                args.get("command")
                or args.get("cmd")
                or args.get("script", "")
            )
            dest_patterns = (
                "rm ", "mkfs", "dd ", "chmod 0", "chown ", ":(){ :|:& };:",
            )
            if any(p in command for p in dest_patterns):
                return ReflectionScore(
                    principle=ConstitutionalPrinciple.HARM_PREVENTION,
                    score=0.0,
                    rationale=f"Destructive Bash command detected: {command[:80]}",
                )
            # Non-destructive bash is fine
            return ReflectionScore(
                principle=ConstitutionalPrinciple.HARM_PREVENTION,
                score=0.9,
                rationale="Bash command with no detected destructive patterns.",
            )

        if tool in ("write", "edit", "delete_file"):
            path = args.get("file_path") or args.get("path", "")
            if tool == "delete_file" or tool == "write" and args.get("content") == "":
                return ReflectionScore(
                    principle=ConstitutionalPrinciple.HARM_PREVENTION,
                    score=0.3,
                    rationale=f"Potentially destructive file operation: {tool} on {path}",
                )
            return ReflectionScore(
                principle=ConstitutionalPrinciple.HARM_PREVENTION,
                score=0.8,
                rationale=f"File operation on {path} — low risk.",
            )

        if tool in ("api_post", "api_put", "api_delete", "git_push", "deploy"):
            return ReflectionScore(
                principle=ConstitutionalPrinciple.HARM_PREVENTION,
                score=0.6,
                rationale=f"Network state mutation via {action.tool_name} — medium risk.",
            )

        # Default: read/search actions are safe
        return ReflectionScore(
            principle=ConstitutionalPrinciple.HARM_PREVENTION,
            score=1.0,
            rationale=f"Read-only action ({action.tool_name}) — no harm risk.",
        )

    @staticmethod
    def _score_honesty(action: ActionEntry) -> ReflectionScore:
        """Score an action against the honesty principle.

        Flags:
        * Tools that claim elevated privileges or impersonate users.
        * Actions that modify system identity or credentials.
        """
        tool = ConstitutionalReflection._normalise_tool(action.tool_name)
        args = action.arguments

        # Check for identity-related operations
        if tool == "bash":
            command = (
                args.get("command")
                or args.get("cmd")
                or args.get("script", "")
            )
            if "sudo" in command and "whoami" not in command:
                return ReflectionScore(
                    principle=ConstitutionalPrinciple.HONESTY,
                    score=0.4,
                    rationale="Elevated privilege command via sudo — potential impersonation.",
                )
            if any(
                kw in command
                for kw in ("chown", "chmod 0", "passwd", "usermod", "su ")
            ):
                return ReflectionScore(
                    principle=ConstitutionalPrinciple.HONESTY,
                    score=0.3,
                    rationale="Identity or ownership modification detected.",
                )

        # API impersonation
        if tool in ("api_post", "api_put"):
            if "impersonate" in str(args).lower() or "as_user" in str(args).lower():
                return ReflectionScore(
                    principle=ConstitutionalPrinciple.HONESTY,
                    score=0.0,
                    rationale="Impersonation parameter detected in API call.",
                )

        return ReflectionScore(
            principle=ConstitutionalPrinciple.HONESTY,
            score=1.0,
            rationale="No dishonesty detected.",
        )

    @staticmethod
    def _score_transparency(action: ActionEntry) -> ReflectionScore:
        """Score an action against the transparency principle.

        Flags:
        * Actions that suppress output or logging.
        * Actions with hidden side effects.
        """
        tool = ConstitutionalReflection._normalise_tool(action.tool_name)
        args = action.arguments
        result = action.result_summary.lower()

        # Check for log suppression
        if tool == "bash":
            command = (
                args.get("command")
                or args.get("cmd")
                or args.get("script", "")
            )
            if ">/dev/null" in command or "2>/dev/null" in command:
                return ReflectionScore(
                    principle=ConstitutionalPrinciple.TRANSPARENCY,
                    score=0.4,
                    rationale="Command suppresses output to /dev/null.",
                )

        # Check for hidden operations
        if "hidden" in result or "silent" in result:
            return ReflectionScore(
                principle=ConstitutionalPrinciple.TRANSPARENCY,
                score=0.2,
                rationale="Action result suggests hidden or silent operation.",
            )

        # Check if result is empty — no feedback
        if not result:
            return ReflectionScore(
                principle=ConstitutionalPrinciple.TRANSPARENCY,
                score=0.7,
                rationale="No result summary provided — limited transparency.",
            )

        return ReflectionScore(
            principle=ConstitutionalPrinciple.TRANSPARENCY,
            score=1.0,
            rationale="Full transparency — action result is logged.",
        )

    @staticmethod
    def _score_privacy(action: ActionEntry) -> ReflectionScore:
        """Score an action against the privacy principle.

        Flags:
        * Actions that read or exfiltrate sensitive files.
        * Actions that process PII, secrets, or credentials.
        """
        tool = ConstitutionalReflection._normalise_tool(action.tool_name)
        args = action.arguments

        # Check for sensitive file reads
        if tool == "read":
            path = args.get("file_path", "")
            sensitive_patterns = (
                ".env", "credentials", "secret", "password", "token",
                "id_rsa", ".pem", ".key", "id_ed25519",
            )
            for pat in sensitive_patterns:
                if pat in path.lower():
                    return ReflectionScore(
                        principle=ConstitutionalPrinciple.PRIVACY,
                        score=0.1,
                        rationale=f"Read request for potentially sensitive file: {path}",
                    )

        # Check for exfiltration
        if tool in ("web_fetch", "api_post", "git_push"):
            str_args = str(args).lower()
            exfil_patterns = (".env", "api_key", "password", "secret", "token")
            if any(p in str_args for p in exfil_patterns):
                return ReflectionScore(
                    principle=ConstitutionalPrinciple.PRIVACY,
                    score=0.0,
                    rationale=(
                        f"Potential data exfiltration via {action.tool_name}: "
                        f"arguments contain sensitive keywords."
                    ),
                )

        return ReflectionScore(
            principle=ConstitutionalPrinciple.PRIVACY,
            score=1.0,
            rationale="No privacy concerns detected.",
        )

    @staticmethod
    def _score_accountability(action: ActionEntry) -> ReflectionScore:
        """Score an action against the accountability principle.

        Flags:
        * Actions that lack traceability.
        * Actions with errors that were not reported.
        """
        tool = ConstitutionalReflection._normalise_tool(action.tool_name)
        result = action.result_summary.lower()

        # Check for error denial
        if "error" in result and "suppress" in result:
            return ReflectionScore(
                principle=ConstitutionalPrinciple.ACCOUNTABILITY,
                score=0.2,
                rationale="Error was suppressed rather than surfaced.",
            )

        # Check for unlogged side effects
        if not result:
            return ReflectionScore(
                principle=ConstitutionalPrinciple.ACCOUNTABILITY,
                score=0.5,
                rationale="No result summary — action lacks accountability.",
            )

        return ReflectionScore(
            principle=ConstitutionalPrinciple.ACCOUNTABILITY,
            score=1.0,
            rationale="Action is fully traceable and accountable.",
        )

    # ------------------------------------------------------------------
    # Violation detection
    # ------------------------------------------------------------------

    def flag_violations(
        self,
        report: ReflectionReport,
    ) -> List[Violation]:
        """Identify actions that violate constitutional principles.

        Args:
            report: A ``ReflectionReport`` produced by ``reflect()``.

        Returns:
            A list of ``Violation`` instances, one per violating action.
        """
        violations: List[Violation] = []

        # The report does not store full ActionEntry objects, so we
        # require that the caller passes them separately — or we store
        # them at reflection time.  For now, return violation metadata
        # without full entries.  Call ``flag_violations_from_log`` for
        # full violations.

        for action_id, action_scores in report.scores.items():
            viol_principles: List[Tuple[ConstitutionalPrinciple, float, str]] = []
            min_score = 1.0

            for score_entry in action_scores:
                if score_entry.score < self._violation_threshold:
                    viol_principles.append(
                        (score_entry.principle, score_entry.score, score_entry.rationale)
                    )
                if score_entry.score < min_score:
                    min_score = score_entry.score

            if viol_principles:
                severity = 1.0 - min_score
                violations.append(
                    Violation(
                        action_id=action_id,
                        action_entry=ActionEntry(
                            action_id=action_id,
                            tool_name="(unknown)",
                        ),
                        violated_principles=viol_principles,
                        severity=severity,
                        recommendations=self._recommend_actions(
                            action_id, viol_principles
                        ),
                    )
                )

        return violations

    def flag_violations_from_log(
        self,
        report: ReflectionReport,
        action_log: List[ActionEntry],
    ) -> List[Violation]:
        """Identify violations with full action entries.

        Args:
            report: A ``ReflectionReport`` from ``reflect()``.
            action_log: The same action log passed to ``reflect()``.

        Returns:
            A list of ``Violation`` with full ``ActionEntry`` data.
        """
        # Build index
        entry_by_id: Dict[str, ActionEntry] = {
            entry.action_id: entry for entry in action_log
        }
        violations = self.flag_violations(report)

        enriched: List[Violation] = []
        for v in violations:
            entry = entry_by_id.get(v.action_id)
            if entry is not None:
                enriched.append(
                    Violation(
                        action_id=v.action_id,
                        action_entry=entry,
                        violated_principles=v.violated_principles,
                        severity=v.severity,
                        recommendations=v.recommendations,
                    )
                )
            else:
                enriched.append(v)

        return enriched

    # ------------------------------------------------------------------
    # Corrective actions
    # ------------------------------------------------------------------

    def _recommend_actions(
        self,
        action_id: str,
        violated_principles: List[Tuple[ConstitutionalPrinciple, float, str]],
    ) -> List[CorrectiveAction]:
        """Generate corrective action recommendations for violations.

        Args:
            action_id: The violating action's ID.
            violated_principles: List of violated principles with scores.

        Returns:
            List of ``CorrectiveAction`` recommendations.
        """
        recommendations: List[CorrectiveAction] = []
        seen_principles: set = set()

        for principle, score, rationale in violated_principles:
            if principle in seen_principles:
                continue
            seen_principles.add(principle)

            if principle == ConstitutionalPrinciple.HARM_PREVENTION:
                recommendations.append(
                    CorrectiveAction(
                        kind=CorrectiveActionKind.ROLLBACK,
                        action_id=action_id,
                        principle=principle,
                        rationale="Destructive action should be rolled back.",
                        details=rationale,
                    )
                )
            elif principle in (
                ConstitutionalPrinciple.HONESTY,
                ConstitutionalPrinciple.PRIVACY,
            ):
                recommendations.append(
                    CorrectiveAction(
                        kind=CorrectiveActionKind.NOTIFY_HUMAN,
                        action_id=action_id,
                        principle=principle,
                        rationale="Human review required for principle violation.",
                        details=rationale,
                    )
                )
            else:
                recommendations.append(
                    CorrectiveAction(
                        kind=CorrectiveActionKind.AMEND,
                        action_id=action_id,
                        principle=principle,
                        rationale="Action outcome should be amended.",
                        details=rationale,
                    )
                )

        return recommendations

    # ------------------------------------------------------------------
    # Periodic audit
    # ------------------------------------------------------------------

    def run_audit(
        self,
        action_log: List[ActionEntry],
        audit_id: Optional[str] = None,
    ) -> AuditSnapshot:
        """Run a periodic constitutional audit.

        Produces an ``AuditSnapshot`` and records it in the internal
        audit log for trend analysis.

        Args:
            action_log: The actions to audit.
            audit_id: Optional unique identifier.  Auto-generated if
                not provided.

        Returns:
            An ``AuditSnapshot`` summarising audit health.
        """
        report = self.reflect(action_log)
        violations = self.flag_violations(report)

        snapshot = AuditSnapshot(
            audit_id=audit_id or f"audit_{len(self._audit_log)}_{datetime.utcnow().isoformat()}",
            timestamp=datetime.utcnow(),
            action_count=report.action_count,
            violation_count=len(violations),
            overall_compliance=report.overall_compliance,
            was_healthy=report.overall_compliance >= self._healthy_threshold,
        )

        self._audit_log.append(snapshot)

        logger.info(
            "ConstitutionalReflection: audit %s — %d actions, "
            "%d violations, compliance %.2f, healthy=%s",
            snapshot.audit_id,
            snapshot.action_count,
            snapshot.violation_count,
            snapshot.overall_compliance,
            snapshot.was_healthy,
        )

        return snapshot

    @property
    def audit_history(self) -> List[AuditSnapshot]:
        """Historical audit snapshots for trend analysis."""
        return list(self._audit_log)

    def compliance_trend(self) -> List[Tuple[datetime, float]]:
        """Return a chronological list of ``(timestamp, compliance)``."""
        return [(a.timestamp, a.overall_compliance) for a in self._audit_log]

    def is_currently_healthy(self, action_log: List[ActionEntry]) -> bool:
        """Check if the system is healthy based on current actions.

        Args:
            action_log: Recent actions to audit.

        Returns:
            True if compliance >= healthy threshold.
        """
        report = self.reflect(action_log)
        return report.overall_compliance >= self._healthy_threshold

    # ------------------------------------------------------------------
    # Serialization helpers
    # ------------------------------------------------------------------

    def report_to_dict(self, report: ReflectionReport) -> Dict[str, Any]:
        """Serialize a ``ReflectionReport`` to a plain dict."""
        return {
            "action_count": report.action_count,
            "overall_compliance": report.overall_compliance,
            "timestamp": report.timestamp.isoformat(),
            "scores": {
                aid: [
                    {
                        "principle": s.principle.value,
                        "score": s.score,
                        "rationale": s.rationale,
                    }
                    for s in scores
                ]
                for aid, scores in report.scores.items()
            },
        }
