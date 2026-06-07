"""Steer-by-exception panel — peek, reply, approve, redirect agents."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SteerAction(str, Enum):
    APPROVE = "approve"       # Approve and continue
    REJECT = "reject"         # Reject and redo
    REDIRECT = "redirect"     # Change direction
    PAUSE = "pause"           # Pause the agent
    RESUME = "resume"         # Resume the agent
    ABORT = "abort"           # Abort the session


@dataclass
class ApprovalGate:
    """Gate that requires human approval before sensitive actions.

    Three-level model:
    - ALLOW: always permitted (read-only actions)
    - ASK: require human approval (file writes, API calls, mutations)
    - DENY: never permitted (credential access, system changes)
    """

    auto_approve_patterns: list[str] = field(default_factory=list)
    require_approval_patterns: list[str] = field(default_factory=list)
    deny_patterns: list[str] = field(default_factory=list)

    _pending_approvals: dict[str, Any] = field(default_factory=dict)

    def needs_approval(self, action: str, context: dict | None = None) -> bool:
        """Check if an action requires human approval."""
        if any(p in action for p in self.deny_patterns):
            return False  # Denied entirely — don't even ask
        if any(p in action for p in self.auto_approve_patterns):
            return False  # Auto-approved
        if any(p in action for p in self.require_approval_patterns):
            return True
        return True  # Default: ask for unknown actions

    def request_approval(self, request_id: str, action: str, context: dict):
        """Queue an approval request for human review."""
        self._pending_approvals[request_id] = {
            "action": action,
            "context": context,
        }

    def approve(self, request_id: str) -> bool:
        """Human approves the request."""
        return self._pending_approvals.pop(request_id, None) is not None

    def reject(self, request_id: str, reason: str = "") -> bool:
        """Human rejects the request."""
        self._pending_approvals.pop(request_id, None)
        return True

    @property
    def pending_count(self) -> int:
        return len(self._pending_approvals)

    def pending_requests(self) -> list[dict]:
        return [
            {"id": rid, **req}
            for rid, req in self._pending_approvals.items()
        ]


@dataclass
class SteerPanel:
    """Steer-by-exception panel for human oversight of running agents.

    Modeled on Claude Code's Agent View: peek at agent state, reply
    to questions, approve sensitive actions, redirect task direction,
    all without attaching to the full session.
    """

    approval_gate: ApprovalGate = field(default_factory=ApprovalGate)
    _agent_states: dict[str, dict] = field(default_factory=dict)

    def peek(self, session_id: str) -> dict | None:
        """Get a lightweight summary of what an agent is doing."""
        return self._agent_states.get(session_id)

    def update_state(self, session_id: str, state: dict):
        """Update the tracked state for an agent session."""
        self._agent_states[session_id] = state

    def redirect(self, session_id: str, new_direction: str) -> bool:
        """Redirect an agent to a new task or approach."""
        if session_id in self._agent_states:
            self._agent_states[session_id]["redirect"] = new_direction
            return True
        return False

    def request_decision(self, session_id: str, question: str,
                         options: list[str]) -> str | None:
        """Present a decision to the human and return their choice."""
        # In production, this surfaces in the fleet view UI
        self._agent_states.setdefault(session_id, {})["pending_decision"] = {
            "question": question,
            "options": options,
        }
        return None  # Async — human responds via the panel

    def remove_session(self, session_id: str):
        self._agent_states.pop(session_id, None)
        self.approval_gate._pending_approvals.pop(session_id, None)
