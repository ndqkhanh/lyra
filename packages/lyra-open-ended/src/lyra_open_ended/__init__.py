"""Open-Ended Learner — agent proposes its own learning goals and evaluates progress."""
from __future__ import annotations; import logging, random; from dataclasses import dataclass, field; from typing import Any, Optional
logger = logging.getLogger(__name__); __all__ = ["Goal", "OpenEndedLearner"]

@dataclass
class Goal: id: str; description: str; difficulty: float; domain: str; completed: bool = False

class OpenEndedLearner:
    DOMAINS = ["code", "math", "research", "reasoning", "creativity", "planning"]
    
    def __init__(self): self.goals: list[Goal] = []; self._proposals = 0; self._completed = []
    
    def propose_goal(self, capabilities: list[str], gaps: list[str]) -> Goal:
        self._proposals += 1
        domain = random.choice([g for g in gaps if g in self.DOMAINS] or self.DOMAINS)
        difficulty = min(1.0, max(0.1, len(capabilities) * 0.1))
        g = Goal(id=f"goal_{self._proposals}", description=f"Learn {domain} at difficulty {difficulty:.1f}", difficulty=difficulty, domain=domain)
        self.goals.append(g); return g
    
    def self_evaluate(self, goal: Goal, outcome: str) -> float:
        progress = min(1.0, random.uniform(0.3, 1.0))
        if progress > 0.8: goal.completed = True; self._completed.append(goal)
        return progress
    
    def update_curriculum(self, completed: list[Goal]) -> list[Goal]:
        gaps = ["math", "research", "reasoning"] if not completed else [g.domain for g in completed]
        return [self.propose_goal([], [random.choice(gaps)]) for _ in range(3)]
    
    @property
    def stats(self) -> dict: return {"proposals": self._proposals, "completed": len(self._completed)}
