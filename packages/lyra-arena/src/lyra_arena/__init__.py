"""Agent Arena — competitive agent tournaments with Elo ratings."""
from __future__ import annotations; import logging, math, random; from dataclasses import dataclass, field; from typing import Any, Optional
logger = logging.getLogger(__name__); __all__ = ["Match", "TournamentResult", "AgentArena"]

@dataclass
class Match: agent_a: str; agent_b: str; winner: Optional[str]

class AgentArena:
    def __init__(self): self.ratings: dict[str, float] = {}; self.matches: list[Match] = []; self._K = 32
    
    def register(self, agent_id: str, rating: float = 1200.0) -> None: self.ratings[agent_id] = rating
    
    async def run_match(self, agent_a: str, agent_b: str) -> Match:
        ra, rb = self.ratings.get(agent_a, 1200), self.ratings.get(agent_b, 1200)
        ea = 1.0 / (1 + 10 ** ((rb - ra) / 400))
        winner = agent_a if random.random() < ea else agent_b
        if winner == agent_a: self.ratings[agent_a] += self._K * (1 - ea); self.ratings[agent_b] += self._K * (0 - (1 - ea))
        else: self.ratings[agent_b] += self._K * (1 - (1-ea)); self.ratings[agent_a] += self._K * (0 - (1-ea))
        m = Match(agent_a=agent_a, agent_b=agent_b, winner=winner)
        self.matches.append(m); return m
    
    async def run_tournament(self, agent_ids: list[str]) -> TournamentResult:
        for i in range(len(agent_ids)):
            for j in range(i+1, len(agent_ids)):
                await self.run_match(agent_ids[i], agent_ids[j])
        from dataclasses import dataclass
        return {"matches": len(self.matches), "top_agent": max(self.ratings, key=self.ratings.get)}
    
    @property
    def stats(self) -> dict: return {"registered": len(self.ratings), "matches": len(self.matches), "top": max(self.ratings, key=self.ratings.get) if self.ratings else None}
