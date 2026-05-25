"""Policy gradient optimization for RL-based policy refinement."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable

import numpy as np

from .exceptions import PolicyGradientError


@dataclass(frozen=True)
class GradientConfig:
    """Configuration for gradient-based optimization."""

    learning_rate: float = 0.01
    batch_size: int = 32
    entropy_coef: float = 0.01
    max_grad_norm: float = 1.0
    optimizer: str = "adam"


@dataclass(frozen=True)
class GradientStep:
    """A single step in gradient optimization."""

    step: int
    loss: float
    gradient_norm: float
    policy_params: tuple[tuple[str, float], ...]


@dataclass(frozen=True)
class GradientResult:
    """The result of a gradient optimization run."""

    steps: tuple[GradientStep, ...]
    final_loss: float
    converged: bool
    total_steps: int


class PolicyGradientOptimizer:
    """Policy gradient optimizer with configurable learning parameters."""

    async def compute_gradient(
        self,
        params: tuple[float, ...],
        rewards: tuple[float, ...],
        config: GradientConfig,
    ) -> tuple[float, ...]:
        """Compute policy gradient from parameters and rewards."""
        if not params:
            raise PolicyGradientError("params must not be empty")
        if not rewards:
            raise PolicyGradientError("rewards must not be empty")
        if len(params) != len(rewards):
            raise PolicyGradientError(
                "params and rewards must have the same length"
            )
        if config.learning_rate <= 0:
            raise PolicyGradientError("learning_rate must be positive")
        if config.batch_size < 1:
            raise PolicyGradientError("batch_size must be >= 1")

        arr_params = np.array(params, dtype=np.float64)
        arr_rewards = np.array(rewards, dtype=np.float64)

        mean_r = np.mean(arr_rewards)
        std_r = np.std(arr_rewards) + 1e-8
        advantages = (arr_rewards - mean_r) / std_r

        if config.optimizer == "adam":
            grad = arr_params * advantages * config.learning_rate
        elif config.optimizer == "sgd":
            grad = advantages * config.learning_rate
        else:
            raise PolicyGradientError(f"unknown optimizer: {config.optimizer}")

        grad_norm = np.linalg.norm(grad)
        if grad_norm > config.max_grad_norm:
            grad = grad * (config.max_grad_norm / grad_norm)

        return tuple(grad.tolist())

    async def apply_gradient_step(
        self,
        params: tuple[float, ...],
        grad: tuple[float, ...],
        lr: float,
    ) -> tuple[float, ...]:
        """Apply computed gradient to parameters."""
        if not params:
            raise PolicyGradientError("params must not be empty")
        if not grad:
            raise PolicyGradientError("grad must not be empty")
        if len(params) != len(grad):
            raise PolicyGradientError("params and grad must have the same length")
        if lr <= 0:
            raise PolicyGradientError("lr must be positive")

        arr_params = np.array(params, dtype=np.float64)
        arr_grad = np.array(grad, dtype=np.float64)

        updated = arr_params - lr * arr_grad
        return tuple(updated.tolist())

    async def optimize_policy(
        self,
        initial_params: tuple[float, ...],
        reward_fn: Callable[[tuple[float, ...]], float],
        config: GradientConfig,
    ) -> GradientResult:
        """Run a full optimization loop returning step history."""
        if not initial_params:
            raise PolicyGradientError("initial_params must not be empty")

        params = np.array(initial_params, dtype=np.float64)
        steps: list[GradientStep] = []

        for step in range(config.batch_size):
            reward = reward_fn(tuple(params.tolist()))
            loss = -reward

            flat_rewards = tuple(
                reward_fn(tuple(params.tolist()))
                for _ in range(config.batch_size)
            )
            rewards = np.array(flat_rewards, dtype=np.float64)

            mean_r = np.mean(rewards)
            std_r = np.std(rewards) + 1e-8
            advantages = (rewards - mean_r) / std_r

            if config.optimizer == "adam":
                grad = params * advantages[0] * config.learning_rate
            elif config.optimizer == "sgd":
                grad = np.full_like(params, advantages[0] * config.learning_rate)
            else:
                raise PolicyGradientError(f"unknown optimizer: {config.optimizer}")

            grad_norm = np.linalg.norm(grad)
            if grad_norm > config.max_grad_norm:
                grad = grad * (config.max_grad_norm / grad_norm)
            grad_norm_clipped = np.linalg.norm(grad)

            params = params - config.learning_rate * grad

            step_params = tuple(
                (f"param_{i}", float(v)) for i, v in enumerate(params)
            )
            steps.append(
                GradientStep(
                    step=step,
                    loss=float(loss),
                    gradient_norm=float(grad_norm_clipped),
                    policy_params=step_params,
                )
            )

            if len(steps) >= 3:
                recent_losses = [s.loss for s in steps[-3:]]
                if max(recent_losses) - min(recent_losses) < 1e-6:
                    break

        final_loss = steps[-1].loss if steps else 0.0
        converged = len(steps) < config.batch_size

        return GradientResult(
            steps=tuple(steps),
            final_loss=final_loss,
            converged=converged,
            total_steps=len(steps),
        )
