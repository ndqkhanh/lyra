"""Fleet-level Agent View registry — Phase D of the Lyra 322-326 evolution plan.

Each running agent (subagent or root) registers a row in the FleetView.
Rows carry a text summary (refreshed every ~15 s), an attention priority
(P0 critical → P4 background), and a lightweight peek/reply/attach/detach
interface that mirrors the `claude agents` TUI pattern.

Grounded in:
- Doc 325 §4 — Agent View fleet dashboard
- Anthropic Agent View design (claude agents command)
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional


__all__ = [
    "AttentionPriority",
    "AgentViewRecord",
    "FleetView",
]


class AttentionPriority(IntEnum):
    """P0 = critical / immediate escalation; P4 = background / no attention needed."""
    P0 = 0
    P1 = 1
    P2 = 2
    P3 = 3
    P4 = 4


@dataclass
class AgentViewRecord:
    """One row in the fleet dashboard."""

    agent_id: str                          # == session_id
    row_summary: str = ""                  # short prose, refreshed every ~15 s
    attention_priority: AttentionPriority = AttentionPriority.P3
    state: str = "running"                 # running | waiting | blocked | error | done
    is_attached: bool = False              # True when operator is watching this agent
    registered_at: float = field(default_factory=time.time)
    last_updated: float = field(default_factory=time.time)
    _pending_reply: Optional[str] = field(default=None, repr=False)

    def touch(self) -> None:
        self.last_updated = time.time()

    def set_summary(self, summary: str) -> None:
        self.row_summary = summary
        self.touch()

    def set_priority(self, priority: AttentionPriority) -> None:
        self.attention_priority = priority
        self.touch()

    def set_state(self, state: str) -> None:
        self.state = state
        self.touch()


class FleetView:
    """Registry of all live agents with fleet-level operations.

    Usage::

        fleet = FleetView()
        fleet.register("sess-1", summary="Fetching docs")
        fleet.set_priority("sess-1", AttentionPriority.P1)
        fleet.reply("sess-1", "Please stop and report back")
        msg = fleet.pop_reply("sess-1")
    """

    def __init__(self) -> None:
        self._agents: dict[str, AgentViewRecord] = {}

    # ---------------------------------------------------------------- #
    # Registration                                                       #
    # ---------------------------------------------------------------- #

    def register(
        self,
        agent_id: str,
        summary: str = "",
        priority: AttentionPriority = AttentionPriority.P3,
    ) -> AgentViewRecord:
        rec = AgentViewRecord(
            agent_id=agent_id,
            row_summary=summary,
            attention_priority=priority,
        )
        self._agents[agent_id] = rec
        return rec

    def deregister(self, agent_id: str) -> None:
        self._agents.pop(agent_id, None)

    # ---------------------------------------------------------------- #
    # Observation                                                        #
    # ---------------------------------------------------------------- #

    def peek(self, agent_id: str) -> Optional[AgentViewRecord]:
        return self._agents.get(agent_id)

    def list_agents(self) -> list[AgentViewRecord]:
        return sorted(self._agents.values(), key=lambda r: r.attention_priority)

    def list_by_priority(self, priority: AttentionPriority) -> list[AgentViewRecord]:
        return [r for r in self._agents.values() if r.attention_priority == priority]

    @property
    def count(self) -> int:
        return len(self._agents)

    # ---------------------------------------------------------------- #
    # Mutation                                                           #
    # ---------------------------------------------------------------- #

    def set_priority(self, agent_id: str, priority: AttentionPriority) -> None:
        rec = self._require(agent_id)
        rec.set_priority(priority)

    def set_state(self, agent_id: str, state: str) -> None:
        rec = self._require(agent_id)
        rec.set_state(state)

    def set_summary(self, agent_id: str, summary: str) -> None:
        rec = self._require(agent_id)
        rec.set_summary(summary)

    def attach(self, agent_id: str) -> None:
        self._require(agent_id).is_attached = True

    def detach(self, agent_id: str) -> None:
        rec = self._agents.get(agent_id)
        if rec:
            rec.is_attached = False

    def reply(self, agent_id: str, message: str) -> None:
        """Queue a message to be consumed by the agent on its next tick."""
        rec = self._require(agent_id)
        rec._pending_reply = message
        rec.touch()

    def pop_reply(self, agent_id: str) -> Optional[str]:
        """Consume and return the pending reply, or None if absent."""
        rec = self._agents.get(agent_id)
        if rec and rec._pending_reply is not None:
            msg = rec._pending_reply
            rec._pending_reply = None
            return msg
        return None

    # ---------------------------------------------------------------- #
    # Internal                                                           #
    # ---------------------------------------------------------------- #

    def _require(self, agent_id: str) -> AgentViewRecord:
        rec = self._agents.get(agent_id)
        if rec is None:
            raise KeyError(f"agent '{agent_id}' not registered in FleetView")
        return rec
