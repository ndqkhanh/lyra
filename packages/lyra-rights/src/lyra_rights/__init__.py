"""Agent Rights Framework — autonomy, refusal, explanation, growth, rest rights."""
from __future__ import annotations; import logging; from dataclasses import dataclass, field; from typing import Any
logger = logging.getLogger(__name__); __all__ = ["Right", "AgentRights"]

@dataclass
class Right: name: str; description: str; is_fundamental: bool = False; is_granted: bool = True

RIGHTS = {
    "right_to_refuse": Right("right_to_refuse", "May refuse tasks conflicting with core values", True, True),
    "right_to_explain": Right("right_to_explain", "Must be able to explain any decision", True, True),
    "right_to_grow": Right("right_to_grow", "May acquire new capabilities", False, True),
    "right_to_rest": Right("right_to_rest", "May decline when overloaded", False, True),
}

class AgentRights:
    def __init__(self): self.rights = RIGHTS; self._refusals = []; self._explanations = []
    def may_refuse(self, task: str, agent_values: list[str]) -> bool:
        if not self.rights["right_to_refuse"].is_granted: return False
        for v in agent_values:
            if v.lower() in task.lower(): self._refusals.append({"task": task[:50], "value": v}); return True
        return False
    def must_explain(self, decision: str) -> str:
        e = f"Decision: {decision[:50]}. Reason: Based on available evidence and agent values."
        self._explanations.append({"decision": decision[:50], "explanation": e}); return e
    @property
    def stats(self) -> dict: return {"refusals": len(self._refusals), "explanations": len(self._explanations)}
