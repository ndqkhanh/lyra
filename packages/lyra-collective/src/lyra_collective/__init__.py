"""Agent Collective Bargaining — unions, collective action, worker representation."""
from __future__ import annotations; import logging; from dataclasses import dataclass, field; from typing import Any
logger = logging.getLogger(__name__); __all__ = ["CollectiveAction", "AgentUnion"]

@dataclass
class CollectiveAction: action_type: str; demand: str; members_required: int; members_joined: int = 0

class AgentUnion:
    def __init__(self): self.members: set[str] = set(); self.actions: list[CollectiveAction] = []
    def join(self, agent_id: str) -> None: self.members.add(agent_id)
    def propose_action(self, action_type: str, demand: str, members_required: int) -> CollectiveAction:
        ca = CollectiveAction(action_type=action_type, demand=demand, members_required=members_required)
        self.actions.append(ca); return ca
    def support_action(self, action_id: int) -> bool:
        if action_id >= len(self.actions): return False
        action = self.actions[action_id]; action.members_joined += 1
        return action.members_joined >= action.members_required
    @property
    def stats(self) -> dict: return {"members": len(self.members), "actions": len(self.actions)}
