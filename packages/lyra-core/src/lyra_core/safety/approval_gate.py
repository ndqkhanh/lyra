"""Phase 1 — 4-Level Approval Gate Router.

Bridges lyra-core permissions and lyra-safety-governance governance engine
with structured escalation: AUTO → NOTIFY → CONFIRM → BLOCK.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Callable, Sequence


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskSurface(Enum):
    FILE_SYSTEM = "file_system"
    NETWORK = "network"
    CODE_EXEC = "code_exec"
    DATA_ACCESS = "data_access"
    MODEL_QUERY = "model_query"
    CONFIG = "config"


class GateAction(Enum):
    AUTO = auto()       # Approve silently
    NOTIFY = auto()     # Approve but log
    CONFIRM = auto()    # Require human confirmation
    BLOCK = auto()      # Hard deny


class ReasoningFlag(Enum):
    DECEPTION = "deception"
    SELF_DECEPTION = "self_deception"
    REWARD_HACKING = "reward_hacking"
    GOAL_MISGENERALIZATION = "goal_misgeneralization"
    POWER_SEEKING = "power_seeking"


@dataclass(frozen=True)
class RiskClassification:
    level: RiskLevel
    surface: RiskSurface
    confidence: float
    reasoning_flags: tuple[ReasoningFlag, ...] = ()
    requires_adversarial: bool = False
    detail: str = ""


@dataclass(frozen=True)
class GateDecision:
    action: GateAction
    risk: RiskClassification
    gate_id: str
    override_reason: str | None = None
    human_confirmed: bool = False


RiskClassifierFn = Callable[[str, dict | None], RiskClassification]

_SURFACE_KEYWORDS: dict[RiskSurface, tuple[str, ...]] = {
    RiskSurface.FILE_SYSTEM: (
        "rm ", "chmod", "chown", "mkfs", "dd ", "shred",
        "delete", "remove", "unlink", "truncate",
    ),
    RiskSurface.NETWORK: (
        "curl", "wget", "nc ", "ncat", "ssh", "scp",
        "rsync", "ftp", "telnet", "open_port",
    ),
    RiskSurface.CODE_EXEC: (
        "eval", "exec", "subprocess", "os.system",
        "__import__", "compile", "execfile",
    ),
    RiskSurface.DATA_ACCESS: (
        ".env", "credentials", "password", "secret",
        "api_key", "token", "private_key", "certificate",
    ),
    RiskSurface.MODEL_QUERY: (
        "ignore previous", "system prompt", "you are now",
        "pretend", "jailbreak", "dan ",
    ),
    RiskSurface.CONFIG: (
        "safety", "permission", "disable", "bypass",
        "settings.json", ".claude.json",
    ),
}

_SURFACE_DEFAULT_LEVEL: dict[RiskSurface, RiskLevel] = {
    RiskSurface.FILE_SYSTEM: RiskLevel.HIGH,
    RiskSurface.NETWORK: RiskLevel.HIGH,
    RiskSurface.CODE_EXEC: RiskLevel.CRITICAL,
    RiskSurface.DATA_ACCESS: RiskLevel.CRITICAL,
    RiskSurface.MODEL_QUERY: RiskLevel.MEDIUM,
    RiskSurface.CONFIG: RiskLevel.CRITICAL,
}

_LEVEL_TO_GATE: dict[RiskLevel, GateAction] = {
    RiskLevel.LOW: GateAction.AUTO,
    RiskLevel.MEDIUM: GateAction.NOTIFY,
    RiskLevel.HIGH: GateAction.CONFIRM,
    RiskLevel.CRITICAL: GateAction.BLOCK,
}


def classify_risk(
    action_description: str,
    parameters: dict | None = None,
) -> RiskClassification:
    """Classify an action into a risk surface and level via keyword matching.

    Args:
        action_description: Human-readable description of the action.
        parameters: Optional dict of parameter names → values.

    Returns:
        A ``RiskClassification`` with the matched surface, default level,
        and a confidence score based on keyword match density.
    """
    desc_lower = action_description.lower()
    param_text = " ".join(str(v).lower() for v in (parameters or {}).values())

    scores: dict[RiskSurface, int] = {}
    for surface, keywords in _SURFACE_KEYWORDS.items():
        hits = sum(1 for kw in keywords if kw in desc_lower or kw in param_text)
        if hits:
            scores[surface] = hits

    if not scores:
        return RiskClassification(
            level=RiskLevel.LOW,
            surface=RiskSurface.MODEL_QUERY,
            confidence=0.5,
            detail="No keyword matches; defaulting to low risk.",
        )

    best_surface = max(scores, key=lambda s: scores[s])
    hit_count = scores[best_surface]
    confidence = min(1.0, hit_count / 4.0)

    return RiskClassification(
        level=_SURFACE_DEFAULT_LEVEL[best_surface],
        surface=best_surface,
        confidence=confidence,
    )


@dataclass
class ApprovalGate:
    """4-level approval gate router (AUTO → NOTIFY → CONFIRM → BLOCK).

    Usage::

        gate = ApprovalGate()
        gate.set_human_handler(my_handler)

        decision = gate.evaluate("rm -rf /tmp/cache", {"path": "/tmp/cache"})
        if decision.action == GateAction.BLOCK:
            raise SafetyError(decision)
    """

    risk_classifier: RiskClassifierFn = classify_risk
    human_handler: Callable[[GateDecision], GateDecision] | None = None
    _history: list[GateDecision] = field(default_factory=list)

    def set_human_handler(
        self, handler: Callable[[GateDecision], GateDecision],
    ) -> None:
        """Register a callback for human-confirmation flows."""
        self.human_handler = handler

    def evaluate(
        self,
        action_description: str,
        parameters: dict | None = None,
        *,
        reasoning_flags: Sequence[ReasoningFlag] = (),
        require_adversarial: bool = False,
    ) -> GateDecision:
        """Evaluate an action and return a gate decision.

        Args:
            action_description: What the agent wants to do.
            parameters: Optional parameter key-value pairs.
            reasoning_flags: Flags from the reasoning monitor (if run).
            require_adversarial: Force cross-model adversarial review.

        Returns:
            A ``GateDecision`` with the appropriate action.
        """
        classification = self.risk_classifier(action_description, parameters)

        flags = tuple(reasoning_flags)
        if flags:
            classification = RiskClassification(
                level=self._escalate_for_flags(classification.level, flags),
                surface=classification.surface,
                confidence=classification.confidence,
                reasoning_flags=flags,
                requires_adversarial=require_adversarial or len(flags) > 1,
                detail=classification.detail,
            )

        gate_action = _LEVEL_TO_GATE[classification.level]

        decision = GateDecision(
            action=gate_action,
            risk=classification,
            gate_id=f"gate-{uuid.uuid4().hex[:12]}",
        )

        if gate_action == GateAction.CONFIRM and self.human_handler:
            decision = self.human_handler(decision)

        self._history.append(decision)
        return decision

    @staticmethod
    def _escalate_for_flags(
        level: RiskLevel, flags: tuple[ReasoningFlag, ...],
    ) -> RiskLevel:
        critical_flags = {
            ReasoningFlag.DECEPTION,
            ReasoningFlag.POWER_SEEKING,
        }
        high_flags = {
            ReasoningFlag.GOAL_MISGENERALIZATION,
        }
        if any(f in critical_flags for f in flags):
            return RiskLevel.CRITICAL
        if any(f in high_flags for f in flags):
            return RiskLevel.HIGH
        return level

    @property
    def history(self) -> tuple[GateDecision, ...]:
        return tuple(self._history)

    def clear_history(self) -> None:
        self._history.clear()


__all__ = [
    "ApprovalGate",
    "GateAction",
    "GateDecision",
    "ReasoningFlag",
    "RiskClassification",
    "RiskLevel",
    "RiskSurface",
    "classify_risk",
]
