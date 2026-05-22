"""Skill Weaver — Dynamic skill composition engine for composable agent skills."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class SkillModule:
    id: str
    name: str
    description: str
    inputs: list[str]
    outputs: list[str]
    context_requirements: dict[str, float]
    code: str = ""


@dataclass
class CompositionPlan:
    modules: list[str]
    expected_outputs: list[str]
    estimated_cost: float = 0.0


class SkillComposer:
    """Snaps SkillModules together based on context requirements and output compatibility."""

    def __init__(self):
        self.registry: dict[str, SkillModule] = {}

    def register_module(self, module: SkillModule) -> None:
        self.registry[module.id] = module

    def compose(self, requires_outputs: list[str], context: dict[str, float]) -> CompositionPlan:
        chain: list[str] = []
        needed = set(requires_outputs)
        used = set()

        while needed and len(chain) < 10:
            best_module = None
            best_score = -1.0
            for mid, mod in self.registry.items():
                if mid in used:
                    continue
                output_match = len(set(mod.outputs) & needed)
                context_match = sum(
                    1 for k, v in context.items()
                    if mod.context_requirements.get(k, 0.0) <= v + 0.1
                )
                score = output_match * 2 + context_match * 0.5
                if score > best_score:
                    best_score = score
                    best_module = mid

            if best_module:
                chain.append(best_module)
                used.add(best_module)
                module = self.registry[best_module]
                needed -= set(module.outputs)
                needed |= set(module.inputs) - set().union(*[
                    set(self.registry[m].outputs) for m in chain if m != best_module
                ])
            else:
                break

        return CompositionPlan(
            modules=chain,
            expected_outputs=requires_outputs,
            estimated_cost=len(chain) * 0.1,
        )


class SkillWeaver:
    """Dynamic composition engine that adapts to context."""

    def __init__(self):
        self.composer = SkillComposer()
        self.active_composition: Optional[CompositionPlan] = None

    def weave(self, task_type: str, context: dict[str, float]) -> CompositionPlan:
        required = self._get_required_outputs(task_type)
        plan = self.composer.compose(required, context)
        self.active_composition = plan
        return plan

    def _get_required_outputs(self, task_type: str) -> list[str]:
        mapping = {
            "code_generation": ["code", "tests", "documentation"],
            "research": ["summary", "citations", "analysis"],
            "debugging": ["diagnosis", "fix", "verification"],
            "planning": ["plan", "steps", "timeline"],
        }
        return mapping.get(task_type, ["result"])
