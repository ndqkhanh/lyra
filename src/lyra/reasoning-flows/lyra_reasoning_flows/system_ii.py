from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


@dataclass(frozen=True)
class SimulationResult:
    outcome: str
    confidence: float
    trace: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be in [0.0, 1.0], got {self.confidence}")


@dataclass(frozen=True)
class PlanTree:
    nodes: tuple[dict[str, Any], ...]
    root_id: str
    depth: int = 0


@dataclass(frozen=True)
class CritiqueResult:
    verdict: str  # "accept", "revise", "reject"
    score: float
    feedback: str
    suggestions: tuple[str, ...] = ()


class BranchingFactor(int, Enum):
    NARROW = 2
    STANDARD = 4
    WIDE = 8


class SystemIIReasoner:
    """System II simulative/planning reasoner using MCTS-guided exploration.

    Implements the Planner/Simulator/Critic triplet pattern for complex
    multi-step reasoning tasks.
    """

    async def plan(
        self, task: str, branching_factor: BranchingFactor = BranchingFactor.STANDARD
    ) -> PlanTree:
        # Generate a plan tree from the task using the branching factor.
        factor = branching_factor.value
        root_id = str(uuid.uuid4())
        nodes: list[dict[str, Any]] = [
            {"id": root_id, "task": task, "depth": 0, "children": []}
        ]

        # Build a shallow tree of depth ~3 with `factor` children per node.
        for depth in range(1, 4):
            parent_pool = [n for n in nodes if n["depth"] == depth - 1]
            for parent in parent_pool:
                for j in range(factor):
                    child_id = str(uuid.uuid4())
                    child = {
                        "id": child_id,
                        "task": f"{task[:40]} sub-{depth}-{j}",
                        "depth": depth,
                        "children": [],
                    }
                    nodes.append(child)
                    parent["children"].append(child_id)

        return PlanTree(nodes=tuple(nodes), root_id=root_id, depth=3)

    async def simulate(self, plan_node: dict[str, Any], depth: int = 0) -> SimulationResult:
        task_desc = plan_node.get("task", "unknown")
        sim_trace = (f"simulate({task_desc}, depth={depth})",)
        # Produce a confidence proportional to depth: deeper simulations are harder.
        confidence = max(0.1, 0.9 - depth * 0.15)
        return SimulationResult(
            outcome=f"simulated_{task_desc[:20]}",
            confidence=confidence,
            trace=sim_trace,
        )

    async def critique(
        self, plan: PlanTree, simulation_results: list[SimulationResult]
    ) -> CritiqueResult:
        if not simulation_results:
            return CritiqueResult(
                verdict="reject",
                score=0.0,
                feedback="No simulations available for critique",
            )

        avg_confidence = sum(r.confidence for r in simulation_results) / len(simulation_results)

        if avg_confidence >= 0.7:
            return CritiqueResult(
                verdict="accept",
                score=avg_confidence,
                feedback=f"Plan shows adequate confidence ({avg_confidence:.2f})",
            )
        elif avg_confidence >= 0.4:
            return CritiqueResult(
                verdict="revise",
                score=avg_confidence,
                feedback=f"Plan needs revision (confidence={avg_confidence:.2f})",
                suggestions=("increase branching factor", "add more context"),
            )
        else:
            return CritiqueResult(
                verdict="reject",
                score=avg_confidence,
                feedback=f"Plan rejected (confidence={avg_confidence:.2f})",
                suggestions=("reformulate task", "escalate to System III"),
            )
