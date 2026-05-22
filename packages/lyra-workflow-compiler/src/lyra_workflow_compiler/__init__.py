"""Workflow Compiler — compile multi-step agent workflows into optimized execution plans."""
from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)
__all__ = ["WorkflowStep", "CompiledWorkflow", "WorkflowCompiler"]

@dataclass
class WorkflowStep: name: str; action: str; inputs: list[str]; outputs: list[str]; is_parallel: bool = False

@dataclass
class CompiledWorkflow: steps: list[WorkflowStep]; estimated_cost: float = 0.0; estimated_latency_ms: float = 0.0

class WorkflowCompiler:
    def __init__(self): self._compilations = 0

    def compile(self, steps: list[dict]) -> CompiledWorkflow:
        self._compilations += 1
        parsed = []
        for s in steps:
            ws = WorkflowStep(name=s.get("name", f"step_{len(parsed)+1}"), action=s.get("action", "process"), inputs=s.get("inputs", []), outputs=s.get("outputs", []), is_parallel=s.get("parallel", False))
            parsed.append(ws)
        # Optimize: merge sequential steps, parallelize independent ones
        optimized = self._optimize(parsed)
        cost = len(optimized) * 0.005; latency = sum(1 for s in optimized if not s.is_parallel) * 1000
        return CompiledWorkflow(steps=optimized, estimated_cost=cost, estimated_latency_ms=latency)

    def _optimize(self, steps: list[WorkflowStep]) -> list[WorkflowStep]:
        if len(steps) < 2: return steps
        optimized = [steps[0]]
        for s in steps[1:]:
            last = optimized[-1]
            if set(last.outputs) & set(s.inputs):
                optimized.append(s)
            else:
                last.is_parallel = True; s.is_parallel = True; optimized.append(s)
        return optimized

    @property
    def stats(self) -> dict: return {"compilations": self._compilations}
