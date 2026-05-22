"""MoE Agent Router — mixture-of-experts dispatch for agent skills."""
from __future__ import annotations; import logging; from dataclasses import dataclass, field; from typing import Any, Callable
logger = logging.getLogger(__name__); __all__ = ["Expert", "MoERouter"]

@dataclass
class Expert: name: str; domain: str; weight: float = 1.0

class MoERouter:
    def __init__(self): self.experts: dict[str, Expert] = {}
    def register(self, name: str, domain: str) -> Expert:
        e = Expert(name=name, domain=domain); self.experts[name] = e; return e
    def route(self, task: str) -> list[Expert]:
        tl = task.lower(); matched = []
        for e in self.experts.values():
            if e.domain in tl: matched.append(e)
        return matched if matched else list(self.experts.values())[:2]
    @property
    def stats(self) -> dict: return {"experts": len(self.experts)}
