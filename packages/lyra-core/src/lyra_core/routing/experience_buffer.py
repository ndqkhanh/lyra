"""Experience replay buffer for RL-based routing policy optimization.

Stores (state, action, reward, next_state, done) tuples with:
- FIFO eviction when capacity is exceeded
- Prioritized sampling based on TD-error magnitude
- Stratified sampling to ensure all action types are represented
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Sequence


# Action space for routing: which tier was chosen
VALID_ACTIONS = ("fast", "reasoning", "advisor")


@dataclass(frozen=True)
class Experience:
    """A single transition tuple for RL training."""

    state_features: tuple[float, ...]
    action: str
    reward: float
    next_state_features: tuple[float, ...]
    done: bool
    priority: float
    timestamp: float
    episode_id: str

    def __post_init__(self) -> None:
        if self.action not in VALID_ACTIONS:
            raise ValueError(f"Invalid action: {self.action!r}, must be one of {VALID_ACTIONS}")
        if len(self.state_features) != len(self.next_state_features):
            raise ValueError("State and next_state must have the same dimensionality")


@dataclass
class ExperienceBuffer:
    """Prioritized experience replay buffer.

    Usage::

        buf = ExperienceBuffer(capacity=10000)
        buf.push(Experience(...))
        batch = buf.sample(batch_size=32)
    """

    capacity: int = 10000
    alpha: float = 0.6          # prioritization exponent (0 = uniform, 1 = full priority)
    beta: float = 0.4           # importance-sampling correction (annealed over time)
    epsilon: float = 1e-6       # small constant to ensure non-zero priority

    _buffer: list[Experience] = field(default_factory=list)
    _position: int = 0
    _total_pushed: int = 0
    _action_counts: dict[str, int] = field(default_factory=lambda: {a: 0 for a in VALID_ACTIONS})

    def push(self, experience: Experience) -> None:
        if len(self._buffer) < self.capacity:
            self._buffer.append(experience)
        else:
            self._buffer[self._position % self.capacity] = experience
        self._position = (self._position + 1) % self.capacity
        self._total_pushed += 1
        self._action_counts[experience.action] = self._action_counts.get(experience.action, 0) + 1

    def push_batch(self, experiences: Sequence[Experience]) -> None:
        for exp in experiences:
            self.push(exp)

    def sample(self, batch_size: int = 32, *, stratified: bool = True) -> list[Experience]:
        available = min(batch_size, len(self._buffer))
        if available == 0:
            return []

        if stratified and len(self._buffer) >= batch_size:
            return self._stratified_sample(available)

        priorities = self._compute_priorities()
        total_priority = sum(priorities)
        if total_priority <= 0:
            probs = None
        else:
            probs = [p / total_priority for p in priorities]

        indices = random.choices(range(len(self._buffer)), weights=probs, k=available)
        return [self._buffer[i] for i in indices]

    def _stratified_sample(self, batch_size: int) -> list[Experience]:
        action_groups: dict[str, list[int]] = {a: [] for a in VALID_ACTIONS}
        for i, exp in enumerate(self._buffer):
            action_groups[exp.action].append(i)

        per_action = max(1, batch_size // 3)
        chosen_indices: set[int] = set()

        for action in VALID_ACTIONS:
            indices = action_groups[action]
            if not indices:
                continue
            n = min(per_action, len(indices))
            chosen = random.sample(indices, n)
            chosen_indices.update(chosen)

        remaining = batch_size - len(chosen_indices)
        if remaining > 0:
            available = [i for i in range(len(self._buffer)) if i not in chosen_indices]
            extra = random.sample(available, min(remaining, len(available)))
            chosen_indices.update(extra)

        samples = [self._buffer[i] for i in chosen_indices]
        random.shuffle(samples)
        return samples[:batch_size]

    def _compute_priorities(self) -> list[float]:
        return [(abs(exp.priority) + self.epsilon) ** self.alpha for exp in self._buffer]

    def update_priorities(self, indices: Sequence[int], td_errors: Sequence[float]) -> None:
        for idx, td_error in zip(indices, td_errors):
            if 0 <= idx < len(self._buffer):
                # Frozen dataclass — replace with new instance
                old = self._buffer[idx]
                self._buffer[idx] = Experience(
                    state_features=old.state_features,
                    action=old.action,
                    reward=old.reward,
                    next_state_features=old.next_state_features,
                    done=old.done,
                    priority=abs(td_error),
                    timestamp=old.timestamp,
                    episode_id=old.episode_id,
                )

    def clear(self) -> None:
        self._buffer.clear()
        self._position = 0
        self._total_pushed = 0
        self._action_counts = {a: 0 for a in VALID_ACTIONS}

    @property
    def size(self) -> int:
        return len(self._buffer)

    @property
    def is_full(self) -> bool:
        return len(self._buffer) >= self.capacity

    @property
    def action_distribution(self) -> dict[str, int]:
        return dict(self._action_counts)

    def set_beta(self, beta: float) -> None:
        self.beta = max(0.0, min(1.0, beta))


__all__ = ["Experience", "ExperienceBuffer", "VALID_ACTIONS"]
