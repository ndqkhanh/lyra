"""Agent-driven compaction — the agent decides when and what to compact.

Implements a Focus-pattern decider that uses slime-mold-inspired
exploration/exploitation balance to decide compaction timing, strategy,
and scope based on context window state.
"""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

from .exceptions import CompactionError
from .knowledge_blocks import KnowledgeBlock, PriorityLevel


class CompactionStrategy(Enum):
    """Available compaction strategies for context window management."""

    PRUNE = auto()  # Remove low-priority content
    SUMMARIZE = auto()  # Summarize verbose sections
    ARCHIVE = auto()  # Move to external storage
    DEFER = auto()  # Skip compaction this round


@dataclass(frozen=True)
class CompactionAction:
    """Record of a compaction action taken.

    Attributes:
        strategy: Which strategy was applied.
        tokens_before: Token count before compaction.
        tokens_after: Token count after compaction.
        tokens_saved: Number of tokens saved.
        blocks_removed: Number of blocks removed.
        blocks_summarized: Number of blocks summarized.
        fidelity_score: Estimated fidelity (0.0 to 1.0).
        time_taken_ms: Time taken in milliseconds.
        reason: Why this compaction was chosen.
        timestamp: When the compaction occurred.
    """

    strategy: CompactionStrategy
    tokens_before: int
    tokens_after: int
    tokens_saved: int = 0
    blocks_removed: int = 0
    blocks_summarized: int = 0
    fidelity_score: float = 1.0
    time_taken_ms: float = 0.0
    reason: str = ""
    timestamp: float = field(default_factory=time.time)


class CompactionDecider:
    """Decides whether and when to compact the context window.

    Uses slime-mold-inspired exploration/exploitation balance:
    - Exploitation: Compact when context is nearly full or recent
      compaction was very effective.
    - Exploration: Occasionally compact even when not strictly necessary
      to discover better compression strategies.

    Factors considered:
    - Context fill percentage.
    - Time since last compaction.
    - Current task phase (research vs. implementation vs. review).
    - Message importance (estimated from message content).
    """

    def __init__(
        self,
        max_context_tokens: int = 128_000,
        compaction_threshold: float = 0.75,
        min_time_between_compactions: float = 30.0,
        exploration_rate: float = 0.1,
    ) -> None:
        self.max_context_tokens = max_context_tokens
        self.compaction_threshold = compaction_threshold
        self.min_time_between_compactions = min_time_between_compactions
        self.exploration_rate = exploration_rate
        self._last_compaction_times: dict[str, float] = {}
        self._decision_history: list[dict[str, Any]] = []

    def should_compact(
        self,
        context_window: int,
        agent_id: str = "default",
        task_phase: str = "general",
        time_since_last_msg: float = 0.0,
    ) -> bool:
        """Determine whether compaction should occur.

        Args:
            context_window: Current context window token count.
            agent_id: Agent identifier.
            task_phase: Current task phase.
            time_since_last_msg: Seconds since last message.

        Returns:
            True if compaction should proceed.
        """
        fill_ratio = context_window / self.max_context_tokens
        last_compact = self._last_compaction_times.get(agent_id, 0.0)
        time_since_compact = time.time() - last_compact

        # Score-based decision
        score = self._compute_compaction_score(
            fill_ratio, time_since_compact, task_phase, time_since_last_msg
        )

        self._decision_history.append({
            "timestamp": time.time(),
            "agent_id": agent_id,
            "context_window": context_window,
            "fill_ratio": fill_ratio,
            "task_phase": task_phase,
            "time_since_last_msg": time_since_last_msg,
            "time_since_compact": time_since_compact,
            "score": score,
            "decision": score >= 0.6,
        })

        return score >= 0.6

    def _compute_compaction_score(
        self,
        fill_ratio: float,
        time_since_compact: float,
        task_phase: str,
        time_since_last_msg: float,
    ) -> float:
        """Compute a compaction score between 0.0 and 1.0.

        Uses multiple weighted factors with slime-mold-inspired
        exploration noise.
        """
        if fill_ratio >= 1.0:
            return 1.0  # Always compact at 100% fill

        # Factor 1: Context fill (primary factor)
        if fill_ratio < 0.3:
            fill_score = 0.0
        elif fill_ratio < self.compaction_threshold:
            fill_score = (fill_ratio - 0.3) / (self.compaction_threshold - 0.3) * 0.5
        else:
            fill_score = 0.5 + (fill_ratio - self.compaction_threshold) / (
                1.0 - self.compaction_threshold
            ) * 0.5

        # Factor 2: Time since last compaction
        min_time = self.min_time_between_compactions
        if time_since_compact < min_time:
            return 0.0  # Always skip if too soon
        elif time_since_compact < min_time * 3:
            time_score = (time_since_compact - min_time) / (min_time * 2)
        else:
            time_score = 1.0

        # Factor 3: Task phase
        phase_scores = {
            "research": 0.3,  # Research needs full context
            "implementation": 0.7,  # Implementation can tolerate compaction
            "review": 0.5,  # Review needs balance
            "debugging": 0.8,  # Debugging benefits from compaction
            "planning": 0.4,  # Planning needs context
            "general": 0.5,
        }
        phase_score = phase_scores.get(task_phase, 0.5)

        # Factor 4: Message recency
        if time_since_last_msg < 5.0:
            msg_score = 0.3  # In conversation, be conservative
        elif time_since_last_msg < 60.0:
            msg_score = 0.6
        else:
            msg_score = 0.9  # Idle, more aggressive

        # Weighted combination
        score = (
            fill_score * 0.5
            + time_score * 0.2
            + phase_score * 0.15
            + msg_score * 0.15
        )

        # Slime-mold-inspired exploration: occasionally try compaction
        # even when score is low to discover better states
        if score < 0.6 and random.random() < self.exploration_rate:
            score = max(score, 0.6)

        return min(1.0, max(0.0, score))

    def record_compaction(self, agent_id: str) -> None:
        """Record that a compaction occurred.

        Args:
            agent_id: Agent that was compacted.
        """
        self._last_compaction_times[agent_id] = time.time()

    def reset(self, agent_id: str | None = None) -> None:
        """Reset compaction timing for an agent or all agents.

        Args:
            agent_id: If provided, reset specific agent. Otherwise reset all.
        """
        if agent_id:
            self._last_compaction_times.pop(agent_id, None)
        else:
            self._last_compaction_times.clear()

    @property
    def decision_history(self) -> list[dict[str, Any]]:
        """Get compaction decision history."""
        return list(self._decision_history)


class CompactionPlanner:
    """Plans what to compact and which strategy to use.

    Analyzes the current context state and knowledge blocks to produce
    a compaction plan optimized for maximum token savings with minimal
    fidelity loss.
    """

    def __init__(self, min_fidelity: float = 0.85) -> None:
        self.min_fidelity = min_fidelity
        self._plan_history: list[dict[str, Any]] = []

    def plan(
        self,
        current_tokens: int,
        target_tokens: int,
        blocks: list[KnowledgeBlock],
        decider_score: float = 0.0,
    ) -> list[CompactionAction]:
        """Create a compaction plan.

        Analyzes blocks by priority and recommends which strategy to use
        for each block or group of blocks.

        Args:
            current_tokens: Current token count.
            target_tokens: Target token count after compaction.
            blocks: Knowledge blocks to consider.
            decider_score: The compaction decider's score.

        Returns:
            Ordered list of compaction actions to take.

        Raises:
            CompactionError: If target_tokens >= current_tokens.
        """
        if target_tokens >= current_tokens:
            raise CompactionError(
                "target_tokens must be less than current_tokens",
                current_tokens,
            )

        actions: list[CompactionAction] = []
        tokens_to_save = current_tokens - target_tokens
        saved_so_far = 0

        # Phase 1: PRUNE low-priority blocks
        low_blocks = [b for b in blocks if b.priority == PriorityLevel.LOW]
        for block in low_blocks:
            if saved_so_far >= tokens_to_save:
                break
            saved = block.token_estimate
            saved_so_far += saved
            actions.append(
                CompactionAction(
                    strategy=CompactionStrategy.PRUNE,
                    tokens_before=current_tokens,
                    tokens_after=current_tokens - saved_so_far,
                    tokens_saved=saved,
                    blocks_removed=1,
                    fidelity_score=0.95,
                    reason=f"Pruned low-priority block: {block.name}",
                )
            )

        # Phase 2: SUMMARIZE normal-priority blocks
        if saved_so_far < tokens_to_save:
            normal_blocks = [
                b for b in blocks if b.priority == PriorityLevel.NORMAL
            ]
            for block in normal_blocks:
                if saved_so_far >= tokens_to_save:
                    break
                # Assume summarization saves ~60% of tokens
                saved = int(block.token_estimate * 0.6)
                saved_so_far += saved
                actions.append(
                    CompactionAction(
                        strategy=CompactionStrategy.SUMMARIZE,
                        tokens_before=current_tokens,
                        tokens_after=current_tokens - saved_so_far,
                        tokens_saved=saved,
                        blocks_summarized=1,
                        fidelity_score=0.85,
                        reason=f"Summarized normal-priority block: {block.name}",
                    )
                )

        # Phase 3: DEFER if we have enough savings
        if saved_so_far < tokens_to_save:
            actions.append(
                CompactionAction(
                    strategy=CompactionStrategy.DEFER,
                    tokens_before=current_tokens,
                    tokens_after=current_tokens,
                    tokens_saved=0,
                    fidelity_score=1.0,
                    reason="Insufficient low-priority content to meet target",
                )
            )

        self._plan_history.append({
            "timestamp": time.time(),
            "current_tokens": current_tokens,
            "target_tokens": target_tokens,
            "actions_planned": len(actions),
            "expected_tokens_saved": saved_so_far,
        })

        return actions

    @property
    def plan_history(self) -> list[dict[str, Any]]:
        """Get plan history."""
        return list(self._plan_history)
