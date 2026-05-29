"""Lightweight policy network for RL-based routing.

A simple 2-layer feedforward network with softmax output that maps
state vectors to action probabilities. No heavy ML framework required
— pure Python with manual backprop for transparency and zero-dependency
deployment.

Architecture:
  Input(12) → Hidden(24, ReLU) → Output(3, Softmax)
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

from .state_encoder import FEATURE_DIM

ACTION_SPACE = ("fast", "reasoning", "advisor")
NUM_ACTIONS = len(ACTION_SPACE)
HIDDEN_DIM = 24


@dataclass
class PolicyWeights:
    """Weights and biases for the 2-layer policy network."""

    w1: list[list[float]]   # [FEATURE_DIM x HIDDEN_DIM]
    b1: list[float]          # [HIDDEN_DIM]
    w2: list[list[float]]   # [HIDDEN_DIM x NUM_ACTIONS]
    b2: list[float]          # [NUM_ACTIONS]

    @classmethod
    def random(cls, seed: int | None = None) -> PolicyWeights:
        """Initialize with Xavier-uniform-like scaling."""
        rng = random.Random(seed)

        def _xavier_scale(fan_in: int, fan_out: int) -> float:
            return math.sqrt(6.0 / (fan_in + fan_out))

        s1 = _xavier_scale(FEATURE_DIM, HIDDEN_DIM)
        w1 = [[rng.uniform(-s1, s1) for _ in range(HIDDEN_DIM)] for _ in range(FEATURE_DIM)]
        b1 = [0.0] * HIDDEN_DIM

        s2 = _xavier_scale(HIDDEN_DIM, NUM_ACTIONS)
        w2 = [[rng.uniform(-s2, s2) for _ in range(NUM_ACTIONS)] for _ in range(HIDDEN_DIM)]
        b2 = [0.0] * NUM_ACTIONS

        return cls(w1=w1, b1=b1, w2=w2, b2=b2)

    @classmethod
    def zeros(cls) -> PolicyWeights:
        w1 = [[0.0] * HIDDEN_DIM for _ in range(FEATURE_DIM)]
        b1 = [0.0] * HIDDEN_DIM
        w2 = [[0.0] * NUM_ACTIONS for _ in range(HIDDEN_DIM)]
        b2 = [0.0] * NUM_ACTIONS
        return cls(w1=w1, b1=b1, w2=w2, b2=b2)


def _relu(x: float) -> float:
    return max(0.0, x)


def _softmax(logits: list[float]) -> list[float]:
    max_logit = max(logits)
    exps = [math.exp(v - max_logit) for v in logits]
    total = sum(exps)
    return [e / total for e in exps]


def _dot(a: list[float], b: list[float]) -> float:
    return sum(ai * bi for ai, bi in zip(a, b, strict=False))


def _vec_scale(s: float, v: list[float]) -> list[float]:
    return [s * vi for vi in v]


class PolicyNetwork:
    """2-layer feedforward policy network for routing decisions.

    Usage::

        net = PolicyNetwork()
        probs = net.forward(state_features)          # inference
        loss = net.train_step(state, action, reward)  # online SGD
    """

    def __init__(self, weights: PolicyWeights | None = None, learning_rate: float = 0.01) -> None:
        self.weights = weights or PolicyWeights.random()
        self.lr = learning_rate
        self._train_steps: int = 0
        self._total_loss: float = 0.0

    def forward(self, features: list[float]) -> tuple[list[float], list[float], list[float]]:
        """Forward pass. Returns (probs, hidden, logits)."""
        # Hidden layer
        hidden = [_relu(_dot(features, [self.weights.w1[j][i] for j in range(FEATURE_DIM)])
                          + self.weights.b1[i])
                   for i in range(HIDDEN_DIM)]

        # Output layer
        logits = [_dot(hidden, [self.weights.w2[j][i] for j in range(HIDDEN_DIM)])
                  + self.weights.b2[i]
                  for i in range(NUM_ACTIONS)]

        probs = _softmax(logits)
        return probs, hidden, logits

    def select_action(self, features: list[float], *, exploit: bool = False) -> tuple[str, int]:
        """Select an action using epsilon-greedy over the policy.

        Returns (action_name, action_index).
        """
        probs, _, _ = self.forward(features)

        if exploit:
            idx = max(range(NUM_ACTIONS), key=lambda i: probs[i])
        else:
            idx = random.choices(range(NUM_ACTIONS), weights=probs, k=1)[0]

        return ACTION_SPACE[idx], idx

    def train_step(
        self, features: list[float], action_idx: int, reward: float
    ) -> float:
        """Single SGD step with policy gradient (REINFORCE).

        Returns the loss for this step.
        """
        probs, hidden, _ = self.forward(features)

        # Cross-entropy loss weighted by reward (policy gradient)
        log_prob = math.log(max(probs[action_idx], 1e-12))
        loss = -log_prob * reward

        # Gradient of loss w.r.t. output logits
        d_logits = [0.0] * NUM_ACTIONS
        for i in range(NUM_ACTIONS):
            d_logits[i] = probs[i]
        d_logits[action_idx] -= 1.0
        d_logits = _vec_scale(reward, d_logits)

        # Gradient w.r.t. hidden
        d_hidden = [0.0] * HIDDEN_DIM
        for j in range(HIDDEN_DIM):
            for k in range(NUM_ACTIONS):
                d_hidden[j] += d_logits[k] * self.weights.w2[j][k]

        # ReLU gradient
        for j in range(HIDDEN_DIM):
            if hidden[j] <= 0:
                d_hidden[j] = 0.0

        # Update W2, B2
        for j in range(HIDDEN_DIM):
            for k in range(NUM_ACTIONS):
                self.weights.w2[j][k] -= self.lr * d_logits[k] * hidden[j]
        for k in range(NUM_ACTIONS):
            self.weights.b2[k] -= self.lr * d_logits[k]

        # Update W1, B1
        for i in range(FEATURE_DIM):
            for j in range(HIDDEN_DIM):
                self.weights.w1[i][j] -= self.lr * d_hidden[j] * features[i]
        for j in range(HIDDEN_DIM):
            self.weights.b1[j] -= self.lr * d_hidden[j]

        self._train_steps += 1
        self._total_loss += abs(loss)
        return loss

    def get_weights_vector(self) -> list[float]:
        """Flatten all weights into a single vector (for persistence)."""
        flat: list[float] = []
        for row in self.weights.w1:
            flat.extend(row)
        flat.extend(self.weights.b1)
        for row in self.weights.w2:
            flat.extend(row)
        flat.extend(self.weights.b2)
        return flat

    def set_weights_vector(self, flat: list[float]) -> None:
        """Restore weights from a flat vector."""
        idx = 0
        for i in range(FEATURE_DIM):
            for j in range(HIDDEN_DIM):
                self.weights.w1[i][j] = flat[idx]
                idx += 1
        for j in range(HIDDEN_DIM):
            self.weights.b1[j] = flat[idx]
            idx += 1
        for j in range(HIDDEN_DIM):
            for k in range(NUM_ACTIONS):
                self.weights.w2[j][k] = flat[idx]
                idx += 1
        for k in range(NUM_ACTIONS):
            self.weights.b2[k] = flat[idx]
            idx += 1

    @property
    def train_steps(self) -> int:
        return self._train_steps

    @property
    def avg_loss(self) -> float:
        if self._train_steps == 0:
            return 0.0
        return self._total_loss / self._train_steps

    def clone_weights(self) -> PolicyWeights:
        w1 = [row[:] for row in self.weights.w1]
        b1 = self.weights.b1[:]
        w2 = [row[:] for row in self.weights.w2]
        b2 = self.weights.b2[:]
        return PolicyWeights(w1=w1, b1=b1, w2=w2, b2=b2)


__all__ = ["ACTION_SPACE", "HIDDEN_DIM", "NUM_ACTIONS", "PolicyNetwork", "PolicyWeights"]
