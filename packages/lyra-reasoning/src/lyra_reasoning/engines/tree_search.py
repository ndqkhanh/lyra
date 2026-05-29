"""
Tree Search Reasoning Engine - MCTS-style exploration.
"""

import math
import time
from dataclasses import dataclass, field
from typing import List, Optional

from anthropic import Anthropic

from ..types import (
    ComputeBudget,
    ReasoningConfig,
    ReasoningStep,
    ReasoningTrace,
    StepType,
)


@dataclass
class ReasoningNode:
    """Node in the reasoning tree."""

    content: str
    step_type: StepType
    parent: Optional["ReasoningNode"] = None
    children: List["ReasoningNode"] = field(default_factory=list)
    visits: int = 0
    value: float = 0.0
    depth: int = 0

    def add_child(self, child: "ReasoningNode") -> None:
        """Add a child node."""
        child.parent = self
        child.depth = self.depth + 1
        self.children.append(child)

    def update(self, value: float) -> None:
        """Update node value and visit count."""
        self.visits += 1
        self.value += value

    def get_average_value(self) -> float:
        """Get average value."""
        return self.value / self.visits if self.visits > 0 else 0.0

    def uct_score(self, exploration_weight: float = 1.414) -> float:
        """Calculate UCT (Upper Confidence Bound for Trees) score."""
        if self.visits == 0:
            return float('inf')

        if self.parent is None or self.parent.visits == 0:
            return self.get_average_value()

        exploitation = self.get_average_value()
        exploration = exploration_weight * math.sqrt(
            math.log(self.parent.visits) / self.visits
        )

        return exploitation + exploration


class TreeSearchEngine:
    """
    Tree search reasoning engine using MCTS-style exploration.

    Features:
    - Monte Carlo Tree Search
    - Beam search
    - Best-of-N sampling
    - Path pruning
    """

    def __init__(self, api_key: Optional[str] = None):
        self.client = Anthropic(api_key=api_key) if api_key else Anthropic()

    def reason(
        self,
        task: str,
        budget: ComputeBudget,
        config: ReasoningConfig,
    ) -> ReasoningTrace:
        """
        Execute tree search reasoning.

        Args:
            task: The task to reason about
            budget: Compute budget
            config: Reasoning configuration

        Returns:
            Best reasoning trace found
        """
        start_time = time.time()

        # Initialize root node
        root = ReasoningNode(
            content=task,
            step_type=StepType.HYPOTHESIS,
            depth=0,
        )

        # MCTS loop
        iteration = 0
        while budget.has_budget() and iteration < config.max_steps:
            # Selection: Pick most promising node
            node = self._select_node(root)

            # Expansion: Generate child nodes
            if node.depth < 10:  # Max depth
                children = self._expand_node(node, config)

                # Simulation: Evaluate each child
                for child in children:
                    score = self._simulate(child, config)
                    child.update(score)
                    budget.use_tokens(100)  # Rough estimate

                # Backpropagation: Update parent values
                self._backpropagate(node, children)

            # Pruning: Remove low-value branches
            self._prune_tree(root, threshold=0.3)

            budget.use_step()
            iteration += 1

        # Extract best path
        best_path = self._extract_best_path(root)

        # Convert to reasoning trace
        trace = ReasoningTrace(
            task=task,
            strategy=config.strategy,
            steps=[
                ReasoningStep(
                    content=node.content,
                    step_type=node.step_type,
                    verification_score=node.get_average_value(),
                )
                for node in best_path
            ],
            duration=time.time() - start_time,
            token_count=budget.tokens_used,
            outcome="success" if best_path else "incomplete",
        )

        return trace

    def _select_node(self, root: ReasoningNode) -> ReasoningNode:
        """
        Select most promising node using UCT.

        Returns:
            Node to expand
        """
        node = root

        while node.children:
            # Select child with highest UCT score
            node = max(node.children, key=lambda n: n.uct_score())

        return node

    def _expand_node(
        self,
        node: ReasoningNode,
        config: ReasoningConfig,
        num_children: int = 3,
    ) -> List[ReasoningNode]:
        """
        Expand node by generating child nodes.

        Args:
            node: Node to expand
            config: Reasoning configuration
            num_children: Number of children to generate

        Returns:
            List of child nodes
        """
        children = []

        # Determine next step type
        next_step_type = self._get_next_step_type(node.step_type)

        # Generate multiple alternative reasoning steps
        for i in range(num_children):
            content = self._generate_alternative(node, i, config)

            if content:
                child = ReasoningNode(
                    content=content,
                    step_type=next_step_type,
                )
                node.add_child(child)
                children.append(child)

        return children

    def _generate_alternative(
        self,
        node: ReasoningNode,
        alternative_num: int,
        config: ReasoningConfig,
    ) -> Optional[str]:
        """Generate an alternative reasoning step."""
        prompt = f"""Given this reasoning step:
{node.content}

Generate alternative reasoning step #{alternative_num + 1} that explores a different approach or perspective.
Be creative but stay relevant to the task.

Alternative reasoning step:"""

        try:
            response = self.client.messages.create(
                model=config.model,
                max_tokens=300,
                temperature=config.temperature + 0.2,  # Higher temp for diversity
                messages=[{"role": "user", "content": prompt}],
            )

            return response.content[0].text
        except Exception:
            return None

    def _simulate(self, node: ReasoningNode, config: ReasoningConfig) -> float:
        """
        Simulate reasoning from this node to estimate value.

        Returns:
            Estimated value (0.0 to 1.0)
        """
        # Simple heuristic evaluation
        score = 0.5  # Base score

        # Reward longer, more detailed reasoning
        word_count = len(node.content.split())
        if word_count > 50:
            score += 0.2
        elif word_count > 20:
            score += 0.1

        # Reward reasoning indicators
        reasoning_words = ["because", "therefore", "thus", "evidence", "analysis"]
        score += 0.05 * sum(1 for word in reasoning_words if word in node.content.lower())

        # Penalize very short or generic responses
        if word_count < 10:
            score -= 0.3

        return min(1.0, max(0.0, score))

    def _backpropagate(
        self,
        node: ReasoningNode,
        children: List[ReasoningNode],
    ) -> None:
        """Backpropagate values up the tree."""
        if not children:
            return

        # Update node with average child value
        avg_value = sum(c.get_average_value() for c in children) / len(children)
        node.update(avg_value)

        # Recursively update parents
        if node.parent:
            self._backpropagate(node.parent, [node])

    def _prune_tree(self, root: ReasoningNode, threshold: float = 0.3) -> None:
        """Prune low-value branches."""
        if not root.children:
            return

        # Remove children below threshold
        root.children = [
            child for child in root.children
            if child.get_average_value() >= threshold or child.visits < 2
        ]

        # Recursively prune children
        for child in root.children:
            self._prune_tree(child, threshold)

    def _extract_best_path(self, root: ReasoningNode) -> List[ReasoningNode]:
        """Extract the best path from root to leaf."""
        path = [root]
        node = root

        while node.children:
            # Select child with highest average value
            best_child = max(node.children, key=lambda n: n.get_average_value())
            path.append(best_child)
            node = best_child

        return path

    def _get_next_step_type(self, current_type: StepType) -> StepType:
        """Determine next step type in reasoning progression."""
        progression = {
            StepType.HYPOTHESIS: StepType.EVIDENCE,
            StepType.EVIDENCE: StepType.ANALYSIS,
            StepType.ANALYSIS: StepType.CONCLUSION,
            StepType.CONCLUSION: StepType.CONCLUSION,
        }

        return progression.get(current_type, StepType.ANALYSIS)
