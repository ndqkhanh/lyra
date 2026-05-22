"""Theory of Mind — model what other agents believe, know, and intend."""
from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)
__all__ = ["BeliefState", "TheoryOfMind"]

@dataclass
class BeliefState:
    agent_id: str; known_facts: set[str] = field(default_factory=set); unknown_facts: set[str] = field(default_factory=set)

class TheoryOfMind:
    def __init__(self):
        self.beliefs: dict[str, BeliefState] = {}

    def register(self, agent_id: str) -> BeliefState:
        bs = BeliefState(agent_id=agent_id)
        self.beliefs[agent_id] = bs
        return bs

    def knows(self, agent_id: str, fact: str) -> bool:
        bs = self.beliefs.get(agent_id)
        return bs is not None and fact in bs.known_facts

    def teach(self, agent_id: str, fact: str) -> None:
        bs = self.beliefs.get(agent_id)
        if bs: bs.known_facts.add(fact); bs.unknown_facts.discard(fact)

    def beliefs_about(self, agent_id: str) -> dict:
        bs = self.beliefs.get(agent_id)
        if not bs: return {}
        return {"agent": agent_id, "known_count": len(bs.known_facts), "unknown_count": len(bs.unknown_facts)}

    @property
    def stats(self) -> dict: return {"agents": len(self.beliefs), "total_beliefs": sum(len(b.known_facts) for b in self.beliefs.values())}
