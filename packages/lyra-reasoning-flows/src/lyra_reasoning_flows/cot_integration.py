from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ThoughtStrategy(str, Enum):
    COT = "cot"
    TOT = "tot"
    SELF_CONSISTENCY = "self_consistency"
    REFLEXION = "reflexion"


@dataclass(frozen=True)
class ThoughtNode:
    content: str
    score: float = 0.0
    parent: str | None = None
    children: tuple[str, ...] = ()
    depth: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(f"score must be in [0.0, 1.0], got {self.score}")


@dataclass
class ReflexionStep:
    """Mutable step tracking a trial, its outcome, and lessons learned."""

    trial: int
    outcome: str
    reflection: str
    revised_plan: str


class CoTIntegrator:
    """Integrates Chain-of-Thought, Tree-of-Thoughts, Self-Consistency,
    and Reflexion reasoning strategies.

    Provides unified access to multiple thought-based reasoning approaches
    that can be composed by the flow engine.
    """

    def __init__(self, seed: int = 42) -> None:
        self._rng = random.Random(seed)
        self._thought_nodes: dict[str, ThoughtNode] = {}
        self._reflexion_steps: list[ReflexionStep] = []

    def chain_of_thought(self, prompt: str, max_steps: int = 5) -> list[str]:
        steps: list[str] = []
        context = prompt
        for i in range(max_steps):
            step = self._generate_cot_step(context, i, max_steps)
            steps.append(step)
            context += f"\nStep {i + 1}: {step}"
        return steps

    def tree_of_thoughts(
        self, prompt: str, branching_factor: int = 3, max_depth: int = 3
    ) -> ThoughtNode:
        root_id = "root"
        root = ThoughtNode(content=prompt, depth=0)
        self._thought_nodes[root_id] = root

        current_ids: list[str] = [root_id]
        for depth in range(1, max_depth + 1):
            next_ids: list[str] = []
            for parent_id in current_ids:
                parent_node = self._thought_nodes[parent_id]
                child_ids: list[str] = []
                for j in range(branching_factor):
                    child_id = f"node_d{depth}_{j}_{self._rng.randint(0, 100000)}"
                    child_content = self._generate_tot_branch(
                        parent_node.content, depth, j
                    )
                    child_score = self._rng.uniform(0.3, 0.95)
                    child = ThoughtNode(
                        content=child_content,
                        score=child_score,
                        parent=parent_id,
                        depth=depth,
                    )
                    self._thought_nodes[child_id] = child
                    child_ids.append(child_id)
                    next_ids.append(child_id)

                # Update parent with children.
                self._thought_nodes[parent_id] = ThoughtNode(
                    content=parent_node.content,
                    score=parent_node.score,
                    parent=parent_node.parent,
                    children=tuple(child_ids),
                    depth=parent_node.depth,
                    metadata=parent_node.metadata,
                )

            current_ids = next_ids

        return self._thought_nodes.get(root_id, root)

    async def tree_of_thoughts_async(
        self, prompt: str, branching_factor: int = 3, max_depth: int = 3
    ) -> ThoughtNode:
        return self.tree_of_thoughts(prompt, branching_factor, max_depth)

    def self_consistency(self, prompt: str, num_samples: int = 5) -> str:
        samples: list[str] = []
        for i in range(num_samples):
            steps = self.chain_of_thought(prompt, max_steps=3)
            samples.append(steps[-1] if steps else prompt)

        # Majority vote: return the most common final answer.
        counts: dict[str, int] = {}
        for s in samples:
            counts[s] = counts.get(s, 0) + 1

        if not counts:
            return prompt

        best = max(counts, key=lambda k: counts[k])
        return best

    def reflexion(
        self, prompt: str, max_trials: int = 3
    ) -> list[ReflexionStep]:
        self._reflexion_steps = []
        plan = prompt
        for trial in range(1, max_trials + 1):
            outcome = self._simulate_outcome(plan, trial)
            reflection = self._generate_reflection(outcome, trial)
            revised = self._revise_plan(plan, reflection, trial)
            step = ReflexionStep(
                trial=trial,
                outcome=outcome,
                reflection=reflection,
                revised_plan=revised,
            )
            self._reflexion_steps.append(step)
            plan = revised

        return self._reflexion_steps

    def get_thought_node(self, node_id: str) -> ThoughtNode | None:
        return self._thought_nodes.get(node_id)

    def _generate_cot_step(self, context: str, step_num: int, max_steps: int) -> str:
        if step_num == max_steps - 1:
            return f"Conclusion: Based on the reasoning, the answer follows from {context[:30]}..."
        return f"Step {step_num + 1}: Considering {context[:40]}..."

    def _generate_tot_branch(self, parent_content: str, depth: int, branch: int) -> str:
        return f"Branch {branch} at depth {depth}: alternative path from {parent_content[:30]}..."

    def _simulate_outcome(self, plan: str, trial: int) -> str:
        outcomes = ["success", "partial_success", "failure"]
        return self._rng.choice(outcomes)

    def _generate_reflection(self, outcome: str, trial: int) -> str:
        if outcome == "success":
            return f"Trial {trial} succeeded; the approach was effective."
        elif outcome == "partial_success":
            return f"Trial {trial} partially succeeded; need to refine the approach."
        else:
            return f"Trial {trial} failed; the strategy needs fundamental revision."

    def _revise_plan(self, plan: str, reflection: str, trial: int) -> str:
        return f"Revised trial {trial + 1}: {reflection[:40]}"
