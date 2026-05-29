"""
Advanced Reasoning Strategies.

Five complementary strategies that can be composed or selected dynamically:

- **ChainOfThought** — Step-by-step sequential reasoning; simplest and most
  broadly applicable.
- **TreeOfThoughts** — BFS/DFS exploration over a tree of reasoning states
  with score-guided pruning; useful for problems with branching decisions.
- **SelfConsistency** — Sample multiple independent chains and select the
  majority (or highest-scoring) result; reduces variance.
- **StepBack** — Abstract the problem, reason at the abstract level, then
  ground the solution; useful when the problem formulation is noisy.
- **AnalogicalReasoning** — Find analogous problems, map their structure,
  and transfer the solution; useful for novel or cross-domain tasks.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Callable
from typing import Any

from .models import AnaloguePair, ReasoningStep, ReasoningTrace, ThoughtNode

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# Chain-of-Thought
# ═══════════════════════════════════════════════════════════════════════════


class ChainOfThought:
    """Sequential step-by-step reasoning.

    Produces a linear chain of reasoning steps where each step builds on
    the previous. Simple, deterministic, and broadly applicable.
    """

    def __init__(self, max_steps: int = 10) -> None:
        self.max_steps = max_steps

    def reason(self, task: str, context: dict[str, Any] | None = None) -> ReasoningTrace:
        """Execute chain-of-thought reasoning on *task*.

        Args:
            task: The task description.
            context: Optional supplementary context.

        Returns:
            Completed reasoning trace.
        """
        steps: list[ReasoningStep] = []
        _ = context or {}
        current_state = task

        for step_num in range(1, self.max_steps + 1):
            thought = self._produce_thought(step_num, current_state, steps)
            action = self._derive_action(thought)
            observation = self._simulate_observation(action, current_state)
            confidence = self._compute_confidence(step_num, thought, observation)

            step = ReasoningStep(
                step_number=step_num,
                thought=thought,
                action=action,
                observation=observation,
                confidence=confidence,
            )
            steps.append(step)

            current_state = f"{current_state} | step_{step_num}: {observation}"
            logger.debug("CoT step %d: action=%s confidence=%.2f", step_num, action, confidence)

            if confidence >= 0.9:
                break

        return ReasoningTrace(
            task=task,
            steps=tuple(steps),
            outcome="success" if steps and steps[-1].confidence >= 0.7 else "incomplete",
            strategy="chain_of_thought",
        )

    @staticmethod
    def _produce_thought(step_num: int, state: str, previous: list[ReasoningStep]) -> str:
        if step_num == 1:
            return f"Parse the task: {state[:100]}. Identify what is being asked."
        return (
            f"Given previous reasoning, determine the next logical inference for step {step_num}."
        )

    @staticmethod
    def _derive_action(thought: str) -> str:
        if "parse" in thought.lower():
            return "decompose"
        if "inference" in thought.lower() or "logical" in thought.lower():
            return "infer"
        return "analyse"

    @staticmethod
    def _simulate_observation(action: str, state: str) -> str:
        return f"Action '{action}' applied. New understanding derived from state analysis."

    @staticmethod
    def _compute_confidence(step_num: int, thought: str, observation: str) -> float:
        base = 0.5 + min(step_num * 0.08, 0.35)
        return min(1.0, base)


# ═══════════════════════════════════════════════════════════════════════════
# Tree-of-Thoughts
# ═══════════════════════════════════════════════════════════════════════════


class TreeOfThoughts:
    """BFS / DFS exploration over a tree of reasoning states.

    Expands multiple candidate thoughts at each step, scores them, prunes
    low-scoring branches, and explores in breadth-first or depth-first order.

    Attributes:
        beam_width: Number of branches to keep at each level (BFS mode).
        max_depth: Maximum search depth.
        exploration_mode: ``"bfs"`` or ``"dfs"``.
        prune_threshold: Minimum score to retain a node.
    """

    def __init__(
        self,
        beam_width: int = 3,
        max_depth: int = 5,
        exploration_mode: str = "bfs",
        prune_threshold: float = 0.3,
    ) -> None:
        self.beam_width = beam_width
        self.max_depth = max_depth
        self.exploration_mode = exploration_mode
        self.prune_threshold = prune_threshold

    def reason(self, task: str, context: dict[str, Any] | None = None) -> ReasoningTrace:
        """Explore the reasoning tree and return the best path.

        Args:
            task: The task description.
            context: Optional supplementary context.

        Returns:
            Reasoning trace containing the best path found.
        """
        root = ThoughtNode(id="root", content=task, depth=0)
        nodes: dict[str, ThoughtNode] = {root.id: root}
        node_id_counter = [0]

        def _next_id() -> str:
            node_id_counter[0] += 1
            return f"n{node_id_counter[0]}"

        if self.exploration_mode == "bfs":
            frontier: list[str] = [root.id]
        else:
            frontier = [root.id]

        for depth in range(self.max_depth):
            if not frontier:
                break

            next_frontier: list[str] = []

            for parent_id in frontier:
                parent = nodes[parent_id]
                candidates = self._expand(parent, _next_id)

                for candidate in candidates:
                    candidate_score = self._score(candidate, task)
                    nodes[candidate.id] = ThoughtNode(
                        id=candidate.id,
                        content=candidate.content,
                        score=candidate_score,
                        depth=depth + 1,
                        parent_id=parent_id,
                    )

                # Keep top beam_width by score
                children = sorted(
                    [nodes[cid] for cid in [c.id for c in candidates] if cid in nodes],
                    key=lambda n: n.score,
                    reverse=True,
                )
                kept = [c for c in children if c.score >= self.prune_threshold][: self.beam_width]
                next_frontier.extend(c.id for c in kept)

            frontier = next_frontier
            logger.debug("ToT depth %d: %d active nodes", depth + 1, len(frontier))

        # Extract best path
        best_path = self._extract_best_path(nodes, root.id)
        steps = [
            ReasoningStep(
                step_number=i + 1,
                thought=node.content,
                action="explore",
                observation=f"ToT node score={node.score:.2f}",
                confidence=node.score,
            )
            for i, node in enumerate(best_path)
            if node.id != root.id
        ]

        best_score = best_path[-1].score if best_path else 0.0
        return ReasoningTrace(
            task=task,
            steps=tuple(steps),
            outcome="success" if best_score >= 0.6 else "incomplete",
            strategy="tree_of_thoughts",
            metadata={"nodes_explored": len(nodes), "best_score": best_score},
        )

    def _expand(self, parent: ThoughtNode, next_id: Callable[[], str]) -> list[ThoughtNode]:
        """Generate child nodes from *parent*."""
        templates = [
            f"Explore alternative interpretation of: {parent.content[:60]}",
            f"Consider counter-argument to: {parent.content[:60]}",
            f"Extend reasoning with new evidence about: {parent.content[:60]}",
            f"Evaluate practical implications of: {parent.content[:60]}",
        ]
        return [
            ThoughtNode(id=next_id(), content=t, depth=parent.depth + 1, parent_id=parent.id)
            for t in templates
        ]

    @staticmethod
    def _score(node: ThoughtNode, task: str) -> float:
        base = 0.5
        if len(node.content) > 40:
            base += 0.15
        reasoning_terms = ["alternative", "counter", "evidence", "implication", "evaluate"]
        base += 0.05 * sum(1 for t in reasoning_terms if t in node.content.lower())
        return min(1.0, max(0.0, base))

    def _extract_best_path(self, nodes: dict[str, ThoughtNode], root_id: str) -> list[ThoughtNode]:
        """Walk from root to the highest-scoring leaf."""
        path = [nodes[root_id]]
        current_id = root_id

        while True:
            children = [n for n in nodes.values() if n.parent_id == current_id]
            if not children:
                break
            best = max(children, key=lambda n: n.score)
            path.append(best)
            current_id = best.id

        return path


# ═══════════════════════════════════════════════════════════════════════════
# Self-Consistency
# ═══════════════════════════════════════════════════════════════════════════


class SelfConsistency:
    """Sample multiple reasoning chains and select via majority vote.

    Reduces variance by running an inner reasoner *n_samples* times and
    picking the most frequent (or highest aggregate scored) conclusion.
    """

    def __init__(
        self,
        n_samples: int = 5,
        inner_reasoner: ChainOfThought | None = None,
    ) -> None:
        self.n_samples = n_samples
        self.inner_reasoner = inner_reasoner or ChainOfThought()

    def reason(self, task: str, context: dict[str, Any] | None = None) -> ReasoningTrace:
        """Run multiple reasoning chains and return the consensus trace.

        Args:
            task: The task description.
            context: Optional supplementary context.

        Returns:
            Consensus reasoning trace.
        """
        traces: list[ReasoningTrace] = []
        conclusions: dict[str, int] = defaultdict(int)

        for i in range(self.n_samples):
            trace = self.inner_reasoner.reason(task, context)
            traces.append(trace)

            final_step = trace.final_step()
            if final_step:
                conclusions[final_step.observation] += 1

            logger.debug(
                "SelfConsistency sample %d: confidence=%.2f",
                i + 1,
                final_step.confidence if final_step else 0.0,
            )

        # Select majority-vote conclusion
        best_conclusion = max(conclusions, key=conclusions.get) if conclusions else "no_consensus"
        consensus_count = conclusions.get(best_conclusion, 0)

        # Build aggregate trace
        all_steps: list[ReasoningStep] = []
        for trace in traces:
            all_steps.extend(trace.steps)

        avg_confidence = sum(s.confidence for s in all_steps) / len(all_steps) if all_steps else 0.0

        logger.info(
            "SelfConsistency: %d/%d chains agreed on conclusion",
            consensus_count,
            self.n_samples,
        )

        return ReasoningTrace(
            task=task,
            steps=tuple(all_steps),
            outcome="success" if consensus_count >= self.n_samples / 2 else "incomplete",
            strategy="self_consistency",
            metadata={
                "n_samples": self.n_samples,
                "consensus_count": consensus_count,
                "consensus_ratio": consensus_count / self.n_samples,
                "avg_confidence": avg_confidence,
                "unique_conclusions": len(conclusions),
            },
        )


# ═══════════════════════════════════════════════════════════════════════════
# Step-Back
# ═══════════════════════════════════════════════════════════════════════════


class StepBack:
    """Abstract the problem, reason abstractly, then ground the solution.

    Three-phase reasoning:
    1. **Abstract** — Identify the general principle or class of problem.
    2. **Reason** — Solve at the abstract level using known principles.
    3. **Ground** — Map the abstract solution back to the concrete instance.

    Particularly useful when the problem statement is noisy or the domain
    is unfamiliar.
    """

    def __init__(self) -> None:
        pass

    def reason(self, task: str, context: dict[str, Any] | None = None) -> ReasoningTrace:
        """Execute step-back reasoning on *task*.

        Args:
            task: The task description.
            context: Optional supplementary context.

        Returns:
            Completed reasoning trace.
        """
        steps: list[ReasoningStep] = []

        # Phase 1: Abstract
        abstraction = self._abstract(task)
        steps.append(
            ReasoningStep(
                step_number=1,
                thought="What is the general class of problem this belongs to?",
                action="abstract",
                observation=abstraction,
                confidence=0.7,
            )
        )

        # Phase 2: Reason at abstract level
        abstract_solution = self._reason_abstract(abstraction)
        steps.append(
            ReasoningStep(
                step_number=2,
                thought=f"Solve the abstract problem: {abstraction[:80]}",
                action="reason_abstract",
                observation=abstract_solution,
                confidence=0.75,
            )
        )

        # Phase 3: Ground back to concrete
        grounded = self._ground(abstract_solution, task)
        steps.append(
            ReasoningStep(
                step_number=3,
                thought="Map the abstract solution back to the original task.",
                action="ground",
                observation=grounded,
                confidence=0.85,
            )
        )

        logger.info("StepBack completed: abstraction='%s'", abstraction[:60])

        return ReasoningTrace(
            task=task,
            steps=tuple(steps),
            outcome="success",
            strategy="step_back",
            metadata={"abstraction": abstraction, "abstract_solution": abstract_solution},
        )

    @staticmethod
    def _abstract(task: str) -> str:
        """Identify the general class of problem."""
        task_lower = task.lower()
        if any(kw in task_lower for kw in ["optimize", "optimisation", "maximize", "minimize"]):
            return "constrained_optimization_problem"
        if any(kw in task_lower for kw in ["classify", "categorize", "label"]):
            return "classification_problem"
        if any(kw in task_lower for kw in ["predict", "forecast", "estimate"]):
            return "prediction_problem"
        if any(kw in task_lower for kw in ["compare", "difference", "versus", "vs"]):
            return "comparative_analysis_problem"
        if any(kw in task_lower for kw in ["explain", "why", "how does", "mechanism"]):
            return "causal_explanation_problem"
        return "general_reasoning_problem"

    @staticmethod
    def _reason_abstract(abstraction: str) -> str:
        """Solve at the abstract level."""
        solutions = {
            "constrained_optimization_problem": (
                "Apply gradient-based methods with Lagrange multipliers. "
                "Define objective function, constraints, and search for feasible optima."
            ),
            "classification_problem": (
                "Use supervised learning with labeled data. Extract features, "
                "train a classifier, and evaluate with precision/recall."
            ),
            "prediction_problem": (
                "Model the underlying distribution. Use regression or time-series "
                "methods. Validate with holdout data and measure error metrics."
            ),
            "comparative_analysis_problem": (
                "Define comparison dimensions. Collect data for each entity, "
                "normalize, and compute pairwise similarity/difference metrics."
            ),
            "causal_explanation_problem": (
                "Identify potential causal factors. Apply counterfactual reasoning "
                "or intervention analysis. Rule out confounding variables."
            ),
            "general_reasoning_problem": (
                "Decompose into sub-problems. Apply first-principles reasoning. "
                "Validate intermediate conclusions before synthesizing final answer."
            ),
        }
        return solutions.get(abstraction, solutions["general_reasoning_problem"])

    @staticmethod
    def _ground(abstract_solution: str, task: str) -> str:
        """Map the abstract solution back to the concrete task."""
        return (
            f"Applied abstract solution to '{task[:80]}': {abstract_solution[:200]}. "
            f"The concrete implementation follows from instantiating the abstract "
            f"parameters with task-specific values."
        )


# ═══════════════════════════════════════════════════════════════════════════
# Analogical Reasoning
# ═══════════════════════════════════════════════════════════════════════════


class AnalogicalReasoning:
    """Reason by analogy: find analogues, map structure, transfer solutions.

    Three-phase reasoning:
    1. **Retrieve** — Find analogous problems from a knowledge base.
    2. **Map** — Identify structural correspondences between source and target.
    3. **Transfer** — Adapt the source solution to the target domain.
    """

    def __init__(
        self,
        analogue_base: list[AnaloguePair] | None = None,
        similarity_threshold: float = 0.3,
    ) -> None:
        self.analogue_base = analogue_base or []
        self.similarity_threshold = similarity_threshold

    def reason(self, task: str, context: dict[str, Any] | None = None) -> ReasoningTrace:
        """Execute analogical reasoning on *task*.

        Args:
            task: The task description.
            context: Optional supplementary context.

        Returns:
            Completed reasoning trace.
        """
        steps: list[ReasoningStep] = []

        # Phase 1: Retrieve analogues
        analogues = self._retrieve_analogues(task)
        steps.append(
            ReasoningStep(
                step_number=1,
                thought=f"Find problems analogous to: {task[:80]}",
                action="retrieve_analogues",
                observation=f"Found {len(analogues)} analogue(s)",
                confidence=0.6 if analogues else 0.3,
            )
        )

        # Phase 2: Map structure
        if analogues:
            best_analogue = analogues[0]
            mapping_desc = (
                ", ".join(f"{k}->{v}" for k, v in best_analogue.structural_mapping.items())
                if best_analogue.structural_mapping
                else "direct analogy"
            )
            steps.append(
                ReasoningStep(
                    step_number=2,
                    thought=f"Map structure from '{best_analogue.source_domain}' to target.",
                    action="map_structure",
                    observation=f"Structural mapping: {mapping_desc}",
                    confidence=best_analogue.similarity_score,
                )
            )

            # Phase 3: Transfer
            transfer = self._transfer_solution(best_analogue, task)
            steps.append(
                ReasoningStep(
                    step_number=3,
                    thought="Adapt the source solution to the target domain.",
                    action="transfer_solution",
                    observation=transfer,
                    confidence=best_analogue.transfer_confidence,
                )
            )
        else:
            steps.append(
                ReasoningStep(
                    step_number=2,
                    thought="No strong analogues found. Reason from first principles.",
                    action="fallback_reasoning",
                    observation="Applying general problem-solving strategy.",
                    confidence=0.5,
                )
            )

        final_confidence = steps[-1].confidence if steps else 0.0
        logger.info(
            "AnalogicalReasoning: %d analogues, final confidence=%.2f",
            len(analogues),
            final_confidence,
        )

        return ReasoningTrace(
            task=task,
            steps=tuple(steps),
            outcome="success" if final_confidence >= 0.6 else "incomplete",
            strategy="analogical_reasoning",
            metadata={"analogues_found": len(analogues)},
        )

    def add_analogue(self, pair: AnaloguePair) -> None:
        """Register a new analogue pair for future retrieval."""
        self.analogue_base.append(pair)
        logger.debug("Added analogue: %s -> %s", pair.source_domain, pair.target_domain)

    def _retrieve_analogues(self, task: str) -> list[AnaloguePair]:
        """Retrieve analogues sorted by similarity to *task*."""
        if not self.analogue_base:
            return []

        task_tokens = set(task.lower().split())
        scored: list[tuple[float, AnaloguePair]] = []

        for pair in self.analogue_base:
            source_tokens = set(pair.source_domain.lower().split())
            target_tokens = set(pair.target_domain.lower().split())
            all_tokens = source_tokens | target_tokens

            overlap = len(task_tokens & all_tokens)
            similarity = overlap / max(len(task_tokens | all_tokens), 1)
            scored.append((similarity, pair))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [pair for sim, pair in scored if sim >= self.similarity_threshold]

    @staticmethod
    def _transfer_solution(analogue: AnaloguePair, task: str) -> str:
        """Adapt the analogue's solution to the target task."""
        return (
            f"Transferring solution from '{analogue.source_domain}' to '{task[:80]}'. "
            f"Key structural correspondences preserved. "
            f"Adaptation confidence: {analogue.transfer_confidence:.1%}."
        )
