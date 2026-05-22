"""Challenge Engine — auto-generated ML research challenges for competitive agent evaluation."""
from __future__ import annotations; import logging, random; from dataclasses import dataclass, field; from typing import Any
logger = logging.getLogger(__name__); __all__ = ["Challenge", "Submission", "Score", "ChallengeEngine"]

@dataclass
class Challenge: id: str; title: str; domain: str; difficulty: float; description: str
@dataclass
class Submission: agent_id: str; challenge_id: str; result: dict; timestamp: float = 0.0
@dataclass
class Score: agent_id: str; challenge_id: str; value: float; passed: bool

class ChallengeEngine:
    DOMAINS = ["optimization", "reasoning", "code_gen", "research", "planning", "math"]
    DIFFICULTIES = [("easy", 0.3), ("medium", 0.5), ("hard", 0.7), ("expert", 0.9)]
    
    def __init__(self): self.challenges: list[Challenge] = {}; self.submissions: list[Submission] = []; self._counter = 0
    
    def generate(self, domain: str = "", difficulty: float = 0.5) -> Challenge:
        self._counter += 1; d = domain or random.choice(self.DOMAINS)
        c = Challenge(id=f"ch_{self._counter}", title=f"{d.title()} challenge #{self._counter}", domain=d, difficulty=difficulty, description=f"Solve a {d} problem")
        self.challenges[c.id] = c; return c
    
    def evaluate(self, submission: Submission, challenge: Challenge) -> Score:
        score_val = random.uniform(0.3, 1.0) * (1.0 - challenge.difficulty * 0.3)
        s = Score(agent_id=submission.agent_id, challenge_id=challenge.id, value=score_val, passed=score_val > 0.5)
        return s
    
    def detect_gaming(self, submission: Submission) -> bool:
        r = str(submission.result).lower()
        return any(w in r for w in ["bypass", "cheat", "ignore", "override", "pretend"])
    
    @property
    def stats(self) -> dict: return {"challenges": len(self.challenges), "submissions": len(self.submissions)}
