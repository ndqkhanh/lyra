"""
NeuralUCB contextual bandit for intelligent model selection.

Implements the Neural Upper Confidence Bound algorithm for online
model routing with exploration-exploitation trade-off and cost-aware rewards.

Based on "Neural Contextual Bandits with UCB Exploration" (Zhou et al., 2020).
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass
from typing import Any

import numpy as np

# Cost estimates per model tier (USD per task)
_MODEL_COST_ESTIMATES: dict[str, float] = {
    "local_slm": 0.00003,
    "haiku": 0.001,
    "fast": 0.0005,
    "standard": 0.01,
    "premium": 0.05,
    "agentic": 0.10,
}


@dataclass(frozen=True)
class UCBConfig:
    """Configuration for the NeuralUCB algorithm.

    Attributes:
        hidden_dim: Number of hidden units in the 2-layer MLP.
        learning_rate: SGD learning rate for neural network updates.
        exploration_bonus: UCB exploration coefficient ``c``.
            Higher values encourage more exploration.
        window_size: Maximum size of the replay buffer (sliding window).
        min_samples: Minimum samples before using neural predictions
            (otherwise falls back to uniform exploration).
        cost_sensitivity: Weight for cost penalty in reward computation.
            ``cost_penalty = cost / max_cost * cost_sensitivity``.
        quality_weight: Weight for task success in reward computation.
    """

    hidden_dim: int = 64
    learning_rate: float = 0.001
    exploration_bonus: float = 0.1
    window_size: int = 1000
    min_samples: int = 10
    cost_sensitivity: float = 0.5
    quality_weight: float = 1.0


class NeuralUCB:
    """Neural Upper Confidence Bound for contextual bandit model routing.

    Uses a 2-layer MLP (input -> hidden -> n_models) to predict rewards
    from task features. Model selection uses the UCB criterion:

        model = argmax(predicted_reward + c * sqrt(log(t) / n_i))

    where ``c`` is the exploration bonus, ``t`` is total pulls, and
    ``n_i`` is the number of times model ``i`` was selected.

    Cost-aware reward::

        reward = success * quality_weight - cost_penalty
        cost_penalty = actual_cost / max_cost * cost_sensitivity
    """

    _INPUT_DIM = 10  # Matches NeuralTier feature extraction

    def __init__(self, config: UCBConfig, n_models: int) -> None:
        self.config = config
        self._n_models = n_models

        # Model ID <-> index mapping
        self._model_indices: dict[str, int] = {}
        self._index_to_model: dict[int, str] = {}
        self._next_idx: int = 0

        # Neural network weights (He initialization for ReLU)
        self._W1: np.ndarray = np.random.randn(self._INPUT_DIM, config.hidden_dim) * math.sqrt(
            2.0 / self._INPUT_DIM
        )
        self._b1: np.ndarray = np.zeros((1, config.hidden_dim))
        self._W2: np.ndarray = np.random.randn(config.hidden_dim, n_models) * math.sqrt(
            2.0 / config.hidden_dim
        )
        self._b2: np.ndarray = np.zeros((1, n_models))

        # Per-model statistics
        self.counts: dict[str, int] = {}
        self.rewards: dict[str, list[float]] = {}

        # Training buffer
        self.replay_buffer: deque = deque(maxlen=config.window_size)
        self._total_pulls: int = 0
        self._update_counter: int = 0

    # ── Model ID management ────────────────────────────────────────────

    def _resolve_idx(self, model_id: str) -> int:
        """Get or create an output index for a model ID."""
        if model_id not in self._model_indices:
            idx = self._next_idx
            if idx >= self._n_models:
                raise ValueError(
                    f"Cannot register model '{model_id}': "
                    f"max {self._n_models} models already allocated"
                )
            self._model_indices[model_id] = idx
            self._index_to_model[idx] = model_id
            self._next_idx = idx + 1
        return self._model_indices[model_id]

    # ── Neural network ─────────────────────────────────────────────────

    def _forward(self, X: np.ndarray) -> np.ndarray:
        """Forward pass through the 2-layer MLP.

        Args:
            X: Input features, shape ``(batch, input_dim)``.

        Returns:
            Predicted rewards, shape ``(batch, n_models)``.
        """
        hidden = np.maximum(0, X @ self._W1 + self._b1)  # ReLU
        return hidden @ self._W2 + self._b2

    def _train_step(self) -> None:
        """Single SGD training step on a random batch from the replay buffer."""
        buffer_len = len(self.replay_buffer)
        if buffer_len == 0:
            return

        batch_size = min(32, buffer_len)
        indices = np.random.choice(buffer_len, batch_size, replace=False)

        for idx in indices:
            features, model_idx, reward = self.replay_buffer[idx]
            X = features.reshape(1, -1)  # (1, input_dim)

            # Forward pass
            z1 = X @ self._W1 + self._b1          # (1, hidden_dim)
            h = np.maximum(0, z1)                  # (1, hidden_dim)
            z2 = h @ self._W2 + self._b2           # (1, n_models)
            pred = z2[0, model_idx]                # scalar

            # MSE loss gradient (dL/d_pred = pred - reward)
            error = pred - reward

            # Output layer gradient for the selected model column
            dL_dW2_col = error * h.T               # (hidden_dim, 1)
            dL_db2 = error                         # scalar

            # Hidden layer gradient (backprop through ReLU)
            dL_dh = error * self._W2[:, model_idx:model_idx + 1].T   # (1, hidden_dim)
            dL_dz1 = dL_dh * (z1 > 0).astype(float)                  # (1, hidden_dim)
            dL_dW1 = X.T @ dL_dz1                                    # (input_dim, hidden_dim)
            dL_db1 = dL_dz1                                          # (1, hidden_dim)

            # SGD update
            lr = self.config.learning_rate
            self._W2[:, model_idx] -= lr * dL_dW2_col.flatten()
            self._b2[0, model_idx] -= lr * dL_db2
            self._W1 -= lr * dL_dW1
            self._b1 -= lr * dL_db1

    # ── Public API ─────────────────────────────────────────────────────

    def select_model(
        self,
        task_features: np.ndarray,
        candidate_models: list[str],
        budget_constraint: float | None = None,
    ) -> tuple[str, float]:
        """Select the best model using UCB criterion.

        Args:
            task_features: Feature vector of shape ``(input_dim,)``.
            candidate_models: List of model IDs to consider.
            budget_constraint: Optional maximum allowed cost per task.
                Models exceeding this budget are filtered out. Falls back
                to all candidates when all are over budget.

        Returns:
            Tuple of ``(model_id, confidence)`` where confidence is the
            sigmoid-transformed predicted reward in ``[0, 1]``.
        """
        features = task_features.reshape(1, -1)
        predictions = self._forward(features).flatten()
        total_pulls = max(self._total_pulls, 1)

        # Filter by budget constraint
        if budget_constraint is not None:
            filtered = [
                m for m in candidate_models
                if _MODEL_COST_ESTIMATES.get(m, 0.0) <= budget_constraint
            ]
            if filtered:
                candidate_models = filtered

        best_model: str | None = None
        best_score = -float("inf")
        best_predicted = 0.0

        for model_id in candidate_models:
            try:
                idx = self._resolve_idx(model_id)
            except ValueError:
                continue  # Skip models beyond allocation

            predicted_reward = float(predictions[idx])

            # Exploration bonus: UCB = c * sqrt(log(t) / n_i)
            n = self.counts.get(model_id, 0)
            if n < self.config.min_samples:
                # Bootstrap exploration before min_samples
                bonus = 1.0 + (self.config.min_samples - n) / self.config.min_samples
                exploration = self.config.exploration_bonus * bonus
            elif n > 0:
                exploration = self.config.exploration_bonus * math.sqrt(
                    math.log(total_pulls) / n
                )
            else:
                # Never selected — maximum exploration
                exploration = self.config.exploration_bonus * math.sqrt(
                    math.log(total_pulls) + 1.0
                )

            score = predicted_reward + exploration

            if score > best_score:
                best_score = score
                best_model = model_id
                best_predicted = predicted_reward

        assert best_model is not None, "No valid model selected"
        confidence = 1.0 / (1.0 + math.exp(-best_predicted))
        return best_model, confidence

    def update(
        self,
        model_id: str,
        task_features: np.ndarray,
        success: bool,
        latency_ms: float,
        cost: float,
    ) -> None:
        """Record an outcome and update the model online.

        Args:
            model_id: The model that was used.
            task_features: Feature vector of shape ``(input_dim,)``.
            success: Whether the task completed successfully.
            latency_ms: Actual task latency in milliseconds.
            cost: Actual USD cost of the task.
        """
        idx = self._resolve_idx(model_id)

        # Compute cost-aware reward
        # cost_penalty = actual_cost * cost_sensitivity (absolute cost penalty)
        cost_penalty = cost * self.config.cost_sensitivity
        reward = float(success) * self.config.quality_weight - cost_penalty

        # Update per-model statistics
        self.counts[model_id] = self.counts.get(model_id, 0) + 1
        if model_id not in self.rewards:
            self.rewards[model_id] = []
        self.rewards[model_id].append(reward)
        self._total_pulls += 1

        # Store in replay buffer
        self.replay_buffer.append((task_features.copy(), idx, reward))

        # Periodic retraining
        self._update_counter += 1
        if self._update_counter % 5 == 0 and len(self.replay_buffer) >= self.config.min_samples:
            self._train_step()

    def get_model_stats(self) -> dict[str, dict[str, Any]]:
        """Return per-model statistics.

        Returns:
            Dict keyed by model ID with ``pulls``, ``mean_reward``,
            ``ucb_value``, ``total_reward``, and ``reward_history``.
        """
        total_pulls = max(self._total_pulls, 1)
        stats: dict[str, dict[str, Any]] = {}

        for model_id in list(self._model_indices.keys()):
            pulls = self.counts.get(model_id, 0)
            model_rewards = self.rewards.get(model_id, [])
            mean_reward = sum(model_rewards) / len(model_rewards) if model_rewards else 0.0

            # Current UCB exploration value
            if pulls > 0:
                ucb_val = self.config.exploration_bonus * math.sqrt(
                    math.log(total_pulls) / pulls
                )
            else:
                ucb_val = self.config.exploration_bonus * math.sqrt(
                    math.log(total_pulls) + 1.0
                )

            stats[model_id] = {
                "pulls": pulls,
                "mean_reward": round(mean_reward, 4),
                "ucb_value": round(ucb_val, 4),
                "total_reward": round(sum(model_rewards), 4),
                "reward_history": model_rewards[-10:],
            }

        return stats
