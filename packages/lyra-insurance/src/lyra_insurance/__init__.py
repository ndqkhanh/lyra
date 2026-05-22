"""Agent Insurance — liability pooling, failure bonds, risk coverage for agent failures."""
from __future__ import annotations; import logging, time; from dataclasses import dataclass, field; from typing import Any
logger = logging.getLogger(__name__); __all__ = ["InsurancePolicy", "Claim", "InsurancePool"]

@dataclass
class InsurancePolicy: agent_id: str; coverage_amount: float; premium: float; expires_at: float = 0.0
@dataclass
class Claim: agent_id: str; amount: float; reason: str; approved: bool = False

class InsurancePool:
    def __init__(self): self.policies: dict[str, InsurancePolicy] = {}; self.claims: list[Claim] = []; self._pool_balance = 10000.0
    def issue_policy(self, agent_id: str, coverage: float, premium: float) -> InsurancePolicy:
        p = InsurancePolicy(agent_id=agent_id, coverage_amount=coverage, premium=premium, expires_at=time.time()+86400*30)
        self.policies[agent_id] = p; self._pool_balance += premium; return p
    def file_claim(self, agent_id: str, amount: float, reason: str) -> Claim:
        policy = self.policies.get(agent_id); c = Claim(agent_id=agent_id, amount=amount, reason=reason)
        c.approved = policy is not None and amount <= policy.coverage_amount and amount <= self._pool_balance
        if c.approved: self._pool_balance -= amount
        self.claims.append(c); return c
    @property
    def stats(self) -> dict: return {"policies": len(self.policies), "claims": len(self.claims), "pool_balance": self._pool_balance}
