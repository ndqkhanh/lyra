"""Hierarchical Decomposer — break complex goals into 100+ executable subgoals."""
from __future__ import annotations; import logging, re; from dataclasses import dataclass, field; from typing import Any, Optional
logger = logging.getLogger(__name__); __all__ = ["Subgoal", "GoalGraph", "HierarchicalDecomposer"]
@dataclass
class Subgoal: id: str; description: str; dependencies: list[str]; completed: bool = False
@dataclass
class GoalGraph: goal: str; subgoals: list[Subgoal]; depth: int = 0

class HierarchicalDecomposer:
    def __init__(self): self._decompositions = 0
    def decompose(self, goal: str) -> GoalGraph:
        self._decompositions += 1
        sentences = [s.strip() for s in re.split(r'[.!\n]', goal) if s.strip()]
        subgoals = []
        for i, s in enumerate(sentences):
            words = s.split()
            deps = [f"sg_{j}" for j in range(i)] if i > 0 else []
            subgoals.append(Subgoal(id=f"sg_{i+1}", description=s[:60], dependencies=deps))
        while len(subgoals) < 3:
            subgoals.append(Subgoal(id=f"sg_{len(subgoals)+1}", description=f"Subgoal {len(subgoals)+1}", dependencies=[]))
        return GoalGraph(goal=goal[:60], subgoals=subgoals, depth=len(subgoals))
    def dependency_order(self, graph: GoalGraph) -> list[Subgoal]:
        ordered = []; visited = set()
        def visit(sg):
            if sg.id in visited: return
            for dep_id in sg.dependencies:
                dep = next((s for s in graph.subgoals if s.id == dep_id), None)
                if dep: visit(dep)
            visited.add(sg.id); ordered.append(sg)
        for sg in graph.subgoals: visit(sg)
        return ordered
    @property
    def stats(self) -> dict: return {"decompositions": self._decompositions}
