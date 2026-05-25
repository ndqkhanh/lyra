"""Intent -> Autonomous Action -> Audit (IAA) engine.

The IAA engine processes natural-language intents, generates previews of
predicted actions, executes approved actions, and produces audit records
for every autonomous operation.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass

from .exceptions import IAAEngineError


@dataclass(frozen=True)
class IAAConfig:
    """Configuration for the IAA engine.

    Attributes:
        preview_timeout: Maximum seconds to wait for intent preview generation.
        auto_execute_threshold: Confidence threshold above which execution
            proceeds without explicit human approval.
        audit_enabled: Whether audit records are produced on every action.
        max_preview_tokens: Maximum tokens for preview text.
    """

    preview_timeout: float = 5.0
    auto_execute_threshold: float = 0.85
    audit_enabled: bool = True
    max_preview_tokens: int = 200


@dataclass(frozen=True)
class IntentPreview:
    """A preview of predicted actions for a given intent.

    Attributes:
        intent_id: Unique identifier for this intent.
        description: The original intent description text.
        predicted_actions: Ordered tuple of predicted action type strings.
        risk_score: Computed risk score between 0.0 and 1.0.
        requires_approval: Whether this intent needs explicit human approval.
    """

    intent_id: str
    description: str
    predicted_actions: tuple[str, ...]
    risk_score: float
    requires_approval: bool


@dataclass(frozen=True)
class AutonomousAction:
    """A recorded autonomous action.

    Attributes:
        action_id: Unique identifier for this action.
        intent_id: The intent that triggered this action.
        action_type: The type/category of action executed.
        payload: String payload associated with the action.
        executed_at: Unix timestamp of execution.
        success: Whether the action succeeded.
    """

    action_id: str
    intent_id: str
    action_type: str
    payload: str
    executed_at: float
    success: bool


@dataclass(frozen=True)
class AuditRecord:
    """An audit record for an autonomous action.

    Attributes:
        audit_id: Unique identifier for this audit record.
        action: The autonomous action being audited.
        trace: Ordered tuple of trace messages recorded during execution.
        verified: Whether the action was verified by the audit process.
        anomalies: Tuple of anomaly strings detected during audit.
    """

    audit_id: str
    action: AutonomousAction
    trace: tuple[str, ...]
    verified: bool
    anomalies: tuple[str, ...]


class IAAEngine:
    """Intent -> Autonomous Action -> Audit engine.

    Processes intents through a three-stage pipeline:
    preview (predict actions), execute (perform action), audit (verify).
    """

    def __init__(self, config: IAAConfig | None = None) -> None:
        """Initialize the IAA engine.

        Args:
            config: Optional IAA configuration. Uses defaults if not provided.
        """
        self._config = config or IAAConfig()
        self._intent_history: list[IntentPreview] = []
        self._action_history: list[AutonomousAction] = []
        self._audit_history: list[AuditRecord] = []

    @property
    def config(self) -> IAAConfig:
        """Return the engine configuration."""
        return self._config

    async def preview_intent(self, description: str) -> IntentPreview:
        """Analyse an intent description and produce a preview of predicted actions.

        Args:
            description: The natural-language intent description.

        Returns:
            An IntentPreview with predicted actions, risk score, and
            approval requirement flag.

        Raises:
            IAAEngineError: If the description is empty.
        """
        if not description or not description.strip():
            raise IAAEngineError("Intent description cannot be empty")

        intent_id = f"int-{uuid.uuid4().hex[:12]}"

        # Simulate action prediction based on description keywords
        predicted_actions: list[str] = []
        description_lower = description.lower()

        capability_map: dict[str, str] = {
            "research": "Research",
            "analyze": "Analysis",
            "deploy": "Deployment",
            "test": "Testing",
            "build": "Build",
            "review": "Review",
            "monitor": "Monitoring",
            "optimize": "Optimization",
            "query": "Query",
            "generate": "Generation",
        }

        for keyword, action_type in capability_map.items():
            if keyword in description_lower:
                predicted_actions.append(action_type)

        if not predicted_actions:
            predicted_actions.append("Unknown")

        # Risk scoring based on action types
        high_risk_keywords = ["deploy", "delete", "modify", "execute", "shell", "network"]
        risk_score = sum(0.2 for kw in high_risk_keywords if kw in description_lower)
        risk_score = min(risk_score, 1.0)

        requires_approval = (
            risk_score >= 0.5
            or any(a in ("Deployment",) for a in predicted_actions)
        )

        preview = IntentPreview(
            intent_id=intent_id,
            description=description,
            predicted_actions=tuple(predicted_actions),
            risk_score=risk_score,
            requires_approval=requires_approval,
        )
        self._intent_history.append(preview)
        return preview

    async def execute_action(self, preview: IntentPreview) -> AutonomousAction:
        """Execute the predicted action for a given intent preview.

        Args:
            preview: The IntentPreview returned by preview_intent.

        Returns:
            An AutonomousAction record of the executed action.

        Raises:
            IAAEngineError: If the preview requires approval (safety check).
        """
        if preview.requires_approval:
            raise IAAEngineError(
                f"Intent {preview.intent_id} requires approval before execution"
            )

        action_id = f"act-{uuid.uuid4().hex[:12]}"
        action_type = preview.predicted_actions[0] if preview.predicted_actions else "Unknown"

        action = AutonomousAction(
            action_id=action_id,
            intent_id=preview.intent_id,
            action_type=action_type,
            payload=f"Executed {action_type} for '{preview.description[:60]}'",
            executed_at=time.time(),
            success=True,
        )
        self._action_history.append(action)
        return action

    async def audit_action(self, action: AutonomousAction) -> AuditRecord:
        """Audit an executed autonomous action.

        Args:
            action: The AutonomousAction to audit.

        Returns:
            An AuditRecord with trace and anomaly information.
        """
        audit_id = f"aud-{uuid.uuid4().hex[:12]}"
        trace = (
            f"Action {action.action_id} of type {action.action_type} executed",
            f"Payload: {action.payload[:80]}",
            f"Success: {action.success}",
        )
        anomalies: list[str] = []

        if not action.success:
            anomalies.append("Action reported failure")

        # Check for potential issues in payload
        if len(action.payload) > 200:
            anomalies.append("Oversized payload")

        verified = len(anomalies) == 0

        record = AuditRecord(
            audit_id=audit_id,
            action=action,
            trace=trace,
            verified=verified,
            anomalies=tuple(anomalies),
        )
        self._audit_history.append(record)
        return record

    async def run_iaa_cycle(
        self, description: str
    ) -> tuple[IntentPreview, AutonomousAction, AuditRecord]:
        """Run a complete IAA cycle: preview -> execute -> audit.

        Args:
            description: The natural-language intent description.

        Returns:
            A tuple of (IntentPreview, AutonomousAction, AuditRecord).

        Raises:
            IAAEngineError: If preview cannot be generated or requires approval.
        """
        preview = await self.preview_intent(description)
        action = await self.execute_action(preview)
        audit = await self.audit_action(action)
        return preview, action, audit
