"""
Theater of Mind - Global Workspace for Lyra AGI Cognitive Architecture.

A central broadcast hub where agent modules publish observations and
subscribe to relevant signals. Implements the Baars-style global workspace
theory with attention selection and working memory management.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from re import Pattern
from typing import Any

from lyra_cognitive.models import (
    AttentionSignal,
    Thought,
)

logger = logging.getLogger(__name__)

# Type alias for subscription callbacks
Subscriber = Callable[[Thought], None]


class AttentionManager:
    """
    Priority-based attention mechanism for the global workspace.

    Selects which signals receive conscious attention based on
    urgency, relevance, and novelty, with exponential decay
    for unattended signals.
    """

    def __init__(
        self,
        capacity: int = 7,
        decay_rate: float = 0.1,
    ):
        """
        Args:
            capacity: Maximum number of signals to attend simultaneously
                      (Miller's Law: 7 +/- 2).
            decay_rate: Exponential decay rate per tick for unattended signals.
        """
        if capacity < 1:
            raise ValueError(f"Capacity must be >= 1, got {capacity}")
        if not 0.0 < decay_rate <= 1.0:
            raise ValueError(f"Decay rate must be in (0.0, 1.0], got {decay_rate}")

        self._capacity = capacity
        self._decay_rate = decay_rate
        self._signal_pool: dict[str, AttentionSignal] = {}
        self._attention_weights: dict[str, float] = {}  # signal_id -> weight

    def compute_priority(self, signal: AttentionSignal) -> float:
        """
        Compute composite priority: urgency * relevance * novelty.

        Args:
            signal: The attention signal to score.

        Returns:
            Priority score from 0.0-1.0.
        """
        return signal.priority

    def register_signal(self, signal: AttentionSignal) -> None:
        """
        Register a new signal in the attention pool.

        Args:
            signal: The signal to register.
        """
        self._signal_pool[signal.id] = signal
        self._attention_weights[signal.id] = self.compute_priority(signal)
        logger.debug(
            "Attention: registered signal %s from %s, priority=%.3f",
            signal.id[:8],
            signal.source,
            signal.priority,
        )

    def select_focus(
        self, signals: list[AttentionSignal] | None = None
    ) -> list[AttentionSignal]:
        """
        Select top-k signals by priority for conscious attention.

        Args:
            signals: Optional list of signals to select from.
                     If None, uses the internal signal pool.

        Returns:
            List of selected signals, sorted by priority descending.
        """
        if signals is not None:
            # External signal list: rank and return top-k
            scored = [(self.compute_priority(s), s) for s in signals]
            scored.sort(key=lambda x: x[0], reverse=True)
            return [s for _, s in scored[: self._capacity]]

        # Internal pool: use tracked weights
        ranked = sorted(
            self._attention_weights.items(),
            key=lambda x: x[1],
            reverse=True,
        )
        selected: list[AttentionSignal] = []
        for sig_id, _ in ranked[: self._capacity]:
            if sig_id in self._signal_pool:
                selected.append(self._signal_pool[sig_id])
        return selected

    def decay_attention(self) -> None:
        """
        Apply exponential decay to all unattended signals.

        Signals that are not currently in the focus set have their
        attention weights multiplied by (1 - decay_rate).
        """
        focus_ids = {
            sig_id for sig_id, _ in sorted(
                self._attention_weights.items(),
                key=lambda x: x[1],
                reverse=True,
            )[: self._capacity]
        }

        for sig_id in self._attention_weights:
            if sig_id not in focus_ids:
                old_weight = self._attention_weights[sig_id]
                self._attention_weights[sig_id] *= (1.0 - self._decay_rate)
                if self._attention_weights[sig_id] < 0.001:
                    # Remove signals that have decayed to negligible weight
                    self._remove_signal(sig_id)
                    logger.debug(
                        "Attention: pruned signal %s (weight %.4f -> negligible)",
                        sig_id[:8],
                        old_weight,
                    )

    def get_top_signals(self, k: int | None = None) -> list[AttentionSignal]:
        """
        Get the current top-k signals by attention weight.

        Args:
            k: Number of signals to return. Defaults to capacity.

        Returns:
            List of top signals.
        """
        return self.select_focus()[: (k or self._capacity)]

    def clear(self) -> None:
        """Clear all signals and weights."""
        self._signal_pool.clear()
        self._attention_weights.clear()

    def _remove_signal(self, signal_id: str) -> None:
        """Remove a signal from the pool."""
        self._signal_pool.pop(signal_id, None)
        self._attention_weights.pop(signal_id, None)


class TheaterOfMind:
    """
    Central broadcast hub implementing Baars' Global Workspace Theory.

    All agent modules publish observations (Thoughts) to the theater.
    Other modules subscribe to relevant thought patterns.
    An attention manager selects which thoughts receive conscious focus.

    Cognitive tick flow: Perceive -> Attend -> Reason -> Decide -> Act -> Observe
    """

    def __init__(
        self,
        capacity: int = 7,
        decay_rate: float = 0.1,
        working_memory_limit: int = 50,
    ):
        """
        Args:
            capacity: Max simultaneous attended thoughts.
            decay_rate: Attention decay rate per tick.
            working_memory_limit: Max items in working memory buffer.
        """
        self._attention = AttentionManager(capacity=capacity, decay_rate=decay_rate)
        self._subscribers: list[tuple[Pattern[str], Subscriber]] = []
        self._thought_history: list[Thought] = []
        self._working_memory: dict[str, Any] = {}
        self._working_memory_limit = working_memory_limit
        self._focused_thought: str | None = None
        self._thought_index: dict[str, Thought] = {}

    # ── Publishing ────────────────────────────────────────────────────────

    def publish(self, thought: Thought) -> None:
        """
        Broadcast a thought to all matching subscribers.

        Also registers it as an attention signal so the attention
        manager can evaluate it.

        Args:
            thought: The thought to publish.
        """
        self._thought_history.append(thought)
        self._thought_index[thought.id] = thought

        # Register as attention signal
        signal = AttentionSignal(
            id=thought.id,
            source=thought.source,
            content=thought.content,
            urgency=thought.metadata.get("urgency", 0.5),
            relevance=thought.metadata.get("relevance", 0.5),
            novelty=self._compute_novelty(thought),
            metadata=thought.metadata,
        )
        self._attention.register_signal(signal)

        # Notify matching subscribers
        match_count = 0
        for pattern, callback in self._subscribers:
            if pattern.search(thought.content) or any(
                pattern.search(tag) for tag in thought.tags
            ):
                try:
                    callback(thought)
                    match_count += 1
                except Exception:
                    logger.exception(
                        "Subscriber callback failed for thought %s",
                        thought.id[:8],
                    )

        logger.debug(
            "TheaterOfMind: published thought %s, matched %d subscribers",
            thought.id[:8],
            match_count,
        )

    # ── Subscribing ───────────────────────────────────────────────────────

    def subscribe(
        self,
        pattern: str,
        callback: Subscriber,
    ) -> None:
        """
        Subscribe to thoughts matching a regex pattern.

        Args:
            pattern: Regex pattern to match against thought content and tags.
            callback: Callable invoked with matching Thought objects.
        """
        compiled = re.compile(pattern)
        self._subscribers.append((compiled, callback))
        logger.debug("TheaterOfMind: new subscriber for pattern '%s'", pattern)

    def unsubscribe(self, callback: Subscriber) -> int:
        """
        Remove all subscriptions for a callback.

        Args:
            callback: The callback to unsubscribe.

        Returns:
            Number of subscriptions removed.
        """
        before = len(self._subscribers)
        self._subscribers = [
            (p, cb) for p, cb in self._subscribers if cb is not callback
        ]
        removed = before - len(self._subscribers)
        logger.debug("TheaterOfMind: removed %d subscriptions", removed)
        return removed

    # ── Attention ─────────────────────────────────────────────────────────

    def attend(self) -> list[Thought]:
        """
        Get currently attended thoughts (top-k by attention priority).

        Returns:
            List of Thoughts ordered by priority descending.
        """
        signals = self._attention.select_focus()
        thoughts: list[Thought] = []
        for signal in signals:
            if signal.id in self._thought_index:
                thoughts.append(self._thought_index[signal.id])
        return thoughts

    def focus(self, thought_id: str) -> None:
        """
        Bring a specific thought to foreground attention.

        Args:
            thought_id: The ID of the thought to focus on.

        Raises:
            KeyError: If the thought_id is not found.
        """
        if thought_id not in self._thought_index:
            raise KeyError(f"Thought not found: {thought_id}")
        self._focused_thought = thought_id
        # Update working memory with focused thought
        thought = self._thought_index[thought_id]
        self._write_to_working_memory("focused_thought", thought.content)
        logger.debug("TheaterOfMind: focused on thought %s", thought_id[:8])

    def get_focused_thought(self) -> Thought | None:
        """Return the currently focused thought, if any."""
        if self._focused_thought and self._focused_thought in self._thought_index:
            return self._thought_index[self._focused_thought]
        return None

    # ── Working Memory ────────────────────────────────────────────────────

    def _write_to_working_memory(self, key: str, value: Any) -> None:
        """Write a key-value pair to working memory with eviction."""
        if (
            len(self._working_memory) >= self._working_memory_limit
            and key not in self._working_memory
        ):
            # Evict oldest entry
            oldest = next(iter(self._working_memory))
            self._working_memory.pop(oldest)
        self._working_memory[key] = value

    def get_workspace_state(self) -> dict[str, Any]:
        """
        Get the current state of the global workspace.

        Returns:
            Dict with keys: 'active_thoughts', 'focused_thought',
            'working_memory', 'subscriber_count', 'thought_count', 'signal_count'.
        """
        active_thoughts = self.attend()
        return {
            "active_thoughts": [t.content for t in active_thoughts],
            "focused_thought": (
                self._thought_index[self._focused_thought].content
                if self._focused_thought and self._focused_thought in self._thought_index
                else None
            ),
            "working_memory": dict(self._working_memory),
            "subscriber_count": len(self._subscribers),
            "thought_count": len(self._thought_history),
            "signal_count": len(self._attention._signal_pool),
        }

    def get_thought_by_id(self, thought_id: str) -> Thought | None:
        """Retrieve a thought by its ID."""
        return self._thought_index.get(thought_id)

    def get_thought_history(self, limit: int = 100) -> list[Thought]:
        """
        Return recent thought history.

        Args:
            limit: Maximum number of thoughts to return.

        Returns:
            List of Thoughts, most recent last.
        """
        return self._thought_history[-limit:]

    # ── Tick Maintenance ──────────────────────────────────────────────────

    def tick_maintenance(self) -> None:
        """
        Perform per-tick maintenance: decay attention, prune old state.
        """
        self._attention.decay_attention()

        # Prune old thought history (keep last 1000)
        if len(self._thought_history) > 1000:
            excess = len(self._thought_history) - 1000
            removed = self._thought_history[:excess]
            self._thought_history = self._thought_history[excess:]
            for t in removed:
                self._thought_index.pop(t.id, None)

    # ── Helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _compute_novelty(thought: Thought) -> float:
        """Estimate novelty based on content length and tags (simple heuristic)."""
        novelty = 0.5
        if thought.tags:
            novelty += 0.1 * min(len(thought.tags), 5)
        content_len = len(thought.content)
        if content_len > 200:
            novelty += 0.15
        return min(1.0, novelty)
