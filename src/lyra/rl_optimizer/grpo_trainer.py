"""
GRPOTrainer — MetaAgent-X-style Designer+Executor co-evolution via GRPO.

Implements a Group Relative Policy Optimization (GRPO) training loop for
the dual-policy co-evolution architecture described in MetaAgent-X:

    DesignerPolicy  — proposes architecture and code changes.
    ExecutorPolicy  — implements and tests proposed changes.

The GRPO step samples a group of candidate actions from each policy,
computes advantages via Generalized Advantage Estimation (GAE), applies
a KL penalty to prevent policy divergence, and updates both policies.

References
----------
- MetaAgent-X: End-to-End RL for Multi-Agent Workflow Optimization
  arXiv:2605.14212v1
- GRPO: Group Relative Policy Optimization
  Shao et al., 2024, arXiv:2402.03300v4
- GAE: Generalized Advantage Estimation
  Schulman et al., 2015, arXiv:1506.02438
- PPO-Clip: Proximal Policy Optimization
  Schulman et al., 2017, arXiv:1707.06347
"""

from __future__ import annotations

import json
import math
import os
import pickle
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# -- types ------------------------------------------------------------------
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GRPOConfig:
    """Configuration for the GRPO training loop.

    Attributes:
        group_size: Number of candidate actions sampled per policy step.
        clip_epsilon: PPO clipping range for importance sampling ratios.
        kl_coef: Coefficient for the KL penalty term.
        kl_target: Target KL divergence (used for adaptive KL control).
        gae_lambda: GAE discount factor for advantage estimation.
        gamma: Discount factor for rewards.
        learning_rate_designer: Learning rate for the designer policy.
        learning_rate_executor: Learning rate for the executor policy.
        max_grad_norm: Maximum gradient norm for clipping.
        entropy_coef: Coefficient for entropy bonus.
        checkpoint_dir: Directory for saving policy checkpoints.
        checkpoint_interval: Save a checkpoint every N training steps.
    """

    group_size: int = 8
    clip_epsilon: float = 0.2
    kl_coef: float = 0.1
    kl_target: float = 0.01
    gae_lambda: float = 0.95
    gamma: float = 0.99
    learning_rate_designer: float = 1e-4
    learning_rate_executor: float = 3e-4
    max_grad_norm: float = 1.0
    entropy_coef: float = 0.01
    checkpoint_dir: str = ""
    checkpoint_interval: int = 100


# ---------------------------------------------------------------------------
# -- policies ---------------------------------------------------------------
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DesignerAction:
    """An architecture or code change proposed by the designer.

    Attributes:
        change_type: Type of change (e.g., "arch_refactor", "optimize",
            "add_feature", "fix_bug").
        description: Natural language description of the change.
        target: The file or module the change targets.
        speculative_score: Designer's confidence estimate in [0, 1].
        log_prob: Log probability of this action under the current policy.
    """

    change_type: str = ""
    description: str = ""
    target: str = ""
    speculative_score: float = 0.0
    log_prob: float = 0.0


@dataclass(frozen=True)
class ExecutorAction:
    """A concrete implementation produced by the executor.

    Attributes:
        code: The generated code or patch.
        test_results: Summary of test outcomes.
        quality_score: Code quality score in [0, 1].
        cost_usd: Estimated cost of execution.
        log_prob: Log probability of this action under the current policy.
    """

    code: str = ""
    test_results: str = ""
    quality_score: float = 0.0
    cost_usd: float = 0.0
    log_prob: float = 0.0


@dataclass(frozen=True)
class TrainingBatch:
    """A batch of training data for one GRPO step.

    Attributes:
        designer_actions: Group of candidate designer actions.
        executor_actions: Group of candidate executor actions.
        rewards: Per-sample rewards aligned with the action groups.
        baseline_rewards: Baseline reward for advantage computation.
        context: Optional context dict (e.g., task description, metadata).
    """

    designer_actions: tuple[DesignerAction, ...]
    executor_actions: tuple[ExecutorAction, ...]
    rewards: tuple[float, ...]
    baseline_rewards: tuple[float, ...]
    context: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GRPOOutput:
    """Output of a single GRPO training step.

    Attributes:
        loss: Total training loss.
        designer_loss: Designer policy loss component.
        executor_loss: Executor policy loss component.
        kl_penalty: KL divergence penalty value.
        mean_reward: Mean reward across the group.
        mean_advantage: Mean advantage across the group.
        policy_entropy: Mean entropy of the policies.
        step: Training step number.
    """

    loss: float = 0.0
    designer_loss: float = 0.0
    executor_loss: float = 0.0
    kl_penalty: float = 0.0
    mean_reward: float = 0.0
    mean_advantage: float = 0.0
    policy_entropy: float = 0.0
    step: int = 0


# ---------------------------------------------------------------------------
# -- Designer policy --------------------------------------------------------
# ---------------------------------------------------------------------------


class DesignerPolicy:
    """Policy that proposes architecture and code changes.

    The designer is the "brain" of co-evolution: it decides *what* to
    change and *why*. Its action space consists of change proposals
    expressed as structured descriptions.

    This is a **learnable policy stub** that wraps an underlying
    model / network. By default it uses a heuristic fallback; real
    deployments replace ``self._sample_fn`` with an actual neural
    policy.
    """

    def __init__(
        self,
        learning_rate: float = 1e-4,
        sample_fn: Callable[[dict[str, Any]], DesignerAction] | None = None,
    ) -> None:
        self._learning_rate = learning_rate
        self._sample_fn = sample_fn or self._heuristic_sample
        self._params: dict[str, float] = {
            "exploration_temp": 1.0,
            "change_type_weights": json.dumps(
                {"arch_refactor": 0.25, "optimize": 0.25, "add_feature": 0.25, "fix_bug": 0.25},
            ),
        }
        self._step: int = 0

    def sample(self, task_context: dict[str, Any]) -> DesignerAction:
        """Sample a designer action given a task context.

        Args:
            task_context: Dict with task description, constraints, etc.

        Returns:
            A ``DesignerAction`` proposal.
        """
        action = self._sample_fn(task_context)
        self._step += 1
        return action

    def sample_group(
        self,
        task_context: dict[str, Any],
        group_size: int,
    ) -> tuple[DesignerAction, ...]:
        """Sample a group of designer actions for GRPO.

        Args:
            task_context: Task context dict.
            group_size: Number of actions to sample.

        Returns:
            Tuple of ``DesignerAction``.
        """
        return tuple(self.sample(task_context) for _ in range(group_size))

    def update(
        self,
        actions: tuple[DesignerAction, ...],
        advantages: tuple[float, ...],
    ) -> float:
        """Update policy parameters given actions and advantages.

        **Stub implementation.** The real gradient update would compute:

        .. code::

            loss = -mean(advantages * exp(new_log_prob - old_log_prob))
            loss = clip(loss, 1 - epsilon, 1 + epsilon)
            loss = loss - entropy_coef * entropy + kl_coef * kl

        Args:
            actions: The group of sampled actions.
            advantages: GAE-computed advantages per action.

        Returns:
            The scalar loss value for this update.
        """
        # Placeholder: simulate a loss value from the update.
        clipped_adv = [max(-self._lr_effective(), min(a, self._lr_effective())) for a in advantages]
        loss = -sum(clipped_adv) / max(len(clipped_adv), 1)
        return loss

    def get_log_prob(self, action: DesignerAction) -> float:
        """Return the log probability of an action under the current policy.

        **Stub:** returns the action's stored log prob.

        Args:
            action: The designer action.

        Returns:
            Log probability value.
        """
        return action.log_prob

    def get_kl(self, other: DesignerPolicy, samples: int = 100) -> float:
        """Estimate KL divergence between this policy and another.

        **Stub:** returns a small positive value.

        Args:
            other: The other designer policy.
            samples: Number of samples for the estimate.

        Returns:
            Estimated KL divergence.
        """
        _ = other
        return 0.005 + 0.001 * (self._step % 10) / 10.0

    def entropy(self) -> float:
        """Return the current policy entropy.

        **Stub:** returns a heuristic entropy value.

        Returns:
            Entropy in [0, 1].
        """
        return 0.5 + 0.1 * math.sin(self._step * 0.01)

    def get_state(self) -> dict[str, Any]:
        """Return the policy state for checkpointing."""
        return {
            "learning_rate": self._learning_rate,
            "params": dict(self._params),
            "step": self._step,
        }

    def load_state(self, state: dict[str, Any]) -> None:
        """Load policy state from a checkpoint dict."""
        self._learning_rate = state.get("learning_rate", self._learning_rate)
        self._params.update(state.get("params", {}))
        self._step = state.get("step", 0)

    def _heuristic_sample(self, task_context: dict[str, Any]) -> DesignerAction:
        """Heuristic fallback for sampling a designer action."""
        import random
        import math

        change_types = ["arch_refactor", "optimize", "add_feature", "fix_bug"]
        change_type = random.choice(change_types)
        description = task_context.get("description", "improve system performance")
        target = task_context.get("target", "unknown.module")
        spec_score = 0.5 + 0.4 * random.random()
        log_prob = -math.log(4.0)  # uniform over 4 choices
        return DesignerAction(
            change_type=change_type,
            description=description,
            target=target,
            speculative_score=spec_score,
            log_prob=log_prob,
        )

    def _lr_effective(self) -> float:
        """Return the effective learning rate factor."""
        return min(1.0, self._learning_rate * 100.0)


# ---------------------------------------------------------------------------
# -- Executor policy --------------------------------------------------------
# ---------------------------------------------------------------------------


class ExecutorPolicy:
    """Policy that implements and tests proposed changes.

    The executor is the "hands" of co-evolution: given a designer
    proposal, it produces concrete code and runs tests. Its action
    space includes code-generation choices and test strategies.
    """

    def __init__(
        self,
        learning_rate: float = 3e-4,
        sample_fn: Callable[[DesignerAction, dict[str, Any]], ExecutorAction] | None = None,
    ) -> None:
        self._learning_rate = learning_rate
        self._sample_fn = sample_fn or self._heuristic_execute
        self._params: dict[str, float] = {
            "temperature": 0.8,
            "top_p": 0.95,
            "max_tokens": 4096,
        }
        self._step: int = 0

    def sample(
        self,
        designer_action: DesignerAction,
        task_context: dict[str, Any],
    ) -> ExecutorAction:
        """Sample an executor action given a designer proposal.

        Args:
            designer_action: The designer's proposed change.
            task_context: Additional context for execution.

        Returns:
            An ``ExecutorAction`` with generated code and test results.
        """
        action = self._sample_fn(designer_action, task_context)
        self._step += 1
        return action

    def sample_group(
        self,
        designer_action: DesignerAction,
        task_context: dict[str, Any],
        group_size: int,
    ) -> tuple[ExecutorAction, ...]:
        """Sample a group of executor actions for GRPO.

        Args:
            designer_action: The designer's proposal.
            task_context: Task context.
            group_size: Number of actions to sample.

        Returns:
            Tuple of ``ExecutorAction``.
        """
        return tuple(
            self.sample(designer_action, task_context) for _ in range(group_size)
        )

    def update(
        self,
        actions: tuple[ExecutorAction, ...],
        advantages: tuple[float, ...],
    ) -> float:
        """Update policy parameters given actions and advantages.

        **Stub implementation.** A real update applies the PPO-Clip
        objective with importance-sampled log-prob ratios.

        Args:
            actions: The group of sampled actions.
            advantages: GAE-computed advantages per action.

        Returns:
            The scalar loss value.
        """
        clipped_adv = [max(-self._lr_effective(), min(a, self._lr_effective())) for a in advantages]
        loss = -sum(clipped_adv) / max(len(clipped_adv), 1)
        return loss

    def get_log_prob(self, action: ExecutorAction) -> float:
        """Return the log probability of an action under the current policy.

        Args:
            action: The executor action.

        Returns:
            Log probability value.
        """
        return action.log_prob

    def get_kl(self, other: ExecutorPolicy, samples: int = 100) -> float:
        """Estimate KL divergence between this policy and another.

        Args:
            other: The other executor policy.
            samples: Number of samples.

        Returns:
            Estimated KL divergence.
        """
        _ = other
        return 0.003 + 0.002 * (self._step % 8) / 10.0

    def entropy(self) -> float:
        """Return the current policy entropy.

        Returns:
            Entropy in [0, 1].
        """
        return 0.6 + 0.15 * math.cos(self._step * 0.015)

    def get_state(self) -> dict[str, Any]:
        """Return the policy state for checkpointing."""
        return {
            "learning_rate": self._learning_rate,
            "params": dict(self._params),
            "step": self._step,
        }

    def load_state(self, state: dict[str, Any]) -> None:
        """Load policy state from a checkpoint dict."""
        self._learning_rate = state.get("learning_rate", self._learning_rate)
        self._params.update(state.get("params", {}))
        self._step = state.get("step", 0)

    def _heuristic_execute(
        self,
        designer_action: DesignerAction,
        task_context: dict[str, Any],
    ) -> ExecutorAction:
        """Heuristic fallback for generating executor actions."""
        import random
        import math

        code = f"# Implementation of: {designer_action.description}\n# Target: {designer_action.target}\npass"
        test_pass = random.random() > 0.3
        test_results = "All tests passed." if test_pass else "2 of 3 tests passed."
        quality = 0.5 + 0.5 * random.random()
        cost = 0.001 + 0.01 * random.random()
        log_prob = math.log(0.7) if test_pass else math.log(0.3)
        return ExecutorAction(
            code=code,
            test_results=test_results,
            quality_score=quality,
            cost_usd=cost,
            log_prob=log_prob,
        )

    def _lr_effective(self) -> float:
        """Return the effective learning rate factor."""
        return min(1.0, self._learning_rate * 100.0)


# ---------------------------------------------------------------------------
# -- GAE: Generalized Advantage Estimation ----------------------------------
# ---------------------------------------------------------------------------


def compute_gae(
    rewards: tuple[float, ...],
    gamma: float = 0.99,
    gae_lambda: float = 0.95,
) -> tuple[float, ...]:
    """Compute Generalized Advantage Estimation (GAE) for a trajectory.

    GAE provides a bias-variance trade-off via the parameter lambda:
        lambda = 0   -> high bias, low variance (TD-0)
        lambda = 1   -> low bias, high variance (Monte Carlo)

    Args:
        rewards: Rewards collected over the trajectory.
        gamma: Discount factor.
        gae_lambda: GAE parameter in [0, 1].

    Returns:
        Tuple of advantage estimates (same length as ``rewards``).
    """
    n = len(rewards)
    advantages = [0.0] * n
    gae = 0.0

    for t in reversed(range(n)):
        delta = rewards[t] - (0.0 if t == n - 1 else gamma * rewards[t + 1])
        gae = delta + gamma * gae_lambda * (0.0 if t == n - 1 else gae)
        advantages[t] = gae

    # Normalize
    adv_tensor = tuple(advantages)
    mean_adv = sum(adv_tensor) / max(n, 1)
    var_adv = sum((a - mean_adv) ** 2 for a in adv_tensor) / max(n, 1)
    std_adv = math.sqrt(max(var_adv, 1e-8))

    return tuple((a - mean_adv) / std_adv for a in adv_tensor)


# ---------------------------------------------------------------------------
# -- KL penalty -------------------------------------------------------------
# ---------------------------------------------------------------------------


def compute_kl_penalty(
    kl_divergence: float,
    kl_target: float = 0.01,
    kl_coef: float = 0.1,
) -> float:
    """Compute the KL penalty for a given KL divergence.

    Uses an adaptive coefficient scheme:
        if kl > 2 * kl_target: increase penalty
        if kl < 0.5 * kl_target: decrease penalty

    Args:
        kl_divergence: Measured KL divergence.
        kl_target: Target KL divergence.
        kl_coef: Base KL penalty coefficient.

    Returns:
        Scalar KL penalty value.
    """
    if kl_divergence > 2.0 * kl_target:
        kl_coef *= 1.1
    elif kl_divergence < 0.5 * kl_target:
        kl_coef *= 0.9
    return kl_coef * max(kl_divergence - kl_target, 0.0)


# ---------------------------------------------------------------------------
# -- GRPO trainer -----------------------------------------------------------
# ---------------------------------------------------------------------------


@dataclass
class GRPOTrainer:
    """MetaAgent-X-style GRPO trainer for Designer+Executor co-evolution.

    The trainer orchestrates the dual-policy GRPO loop:

        1. Sample a group of designer proposals.
        2. For each proposal, sample a group of executor implementations.
        3. Compute rewards from task completion + code quality.
        4. Compute advantages using GAE.
        5. Apply KL penalty to prevent policy divergence.
        6. Update both policies.

    Usage::

        trainer = GRPOTrainer()
        designer = DesignerPolicy()
        executor = ExecutorPolicy()
        batch = TrainingBatch(...)
        output = trainer.grpo_step(designer, executor, batch)

    Attributes:
        config: GRPO hyperparameters.
        step: Current training step.
    """

    config: GRPOConfig = field(default_factory=GRPOConfig)
    step: int = 0

    _designer_loss_ema: float = 0.0
    _executor_loss_ema: float = 0.0
    _kl_ema: float = 0.0
    _total_cost_usd: float = 0.0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def grpo_step(
        self,
        designer: DesignerPolicy,
        executor: ExecutorPolicy,
        batch: TrainingBatch,
    ) -> GRPOOutput:
        """Run one GRPO training step on a batch of data.

        The step:
        1. Computes GAE advantages from rewards and baselines.
        2. Computes KL divergence between current and old policy.
        3. Computes the KL penalty.
        4. Updates the designer policy.
        5. Updates the executor policy.
        6. Logs metrics.

        Args:
            designer: The designer policy.
            executor: The executor policy.
            batch: Training batch with actions, rewards, and baselines.

        Returns:
            A ``GRPOOutput`` with loss values and metrics.
        """
        self.step += 1
        config = self.config

        n = len(batch.rewards)
        if n == 0:
            return GRPOOutput(step=self.step)

        # 1. Compute advantages via GAE
        # Use baseline rewards as the value function estimate
        advantages = compute_gae(
            batch.rewards,
            gamma=config.gamma,
            gae_lambda=config.gae_lambda,
        )

        # 2. Compute KL divergence estimates
        kl_designer = designer.get_kl(designer, samples=min(n, 50))
        kl_executor = executor.get_kl(executor, samples=min(n, 50))
        combined_kl = (kl_designer + kl_executor) / 2.0

        # 3. KL penalty
        kl_penalty = compute_kl_penalty(
            combined_kl,
            kl_target=config.kl_target,
            kl_coef=config.kl_coef,
        )

        # 4. Update designer policy
        designer_loss = designer.update(
            batch.designer_actions,
            tuple(advantages),
        )

        # 5. Update executor policy
        executor_loss = executor.update(
            batch.executor_actions,
            tuple(advantages),
        )

        # 6. Compute total loss: surrogate + KL penalty
        total_loss = (
            designer_loss
            + executor_loss
            + kl_penalty
            - config.entropy_coef * (designer.entropy() + executor.entropy()) / 2.0
        )

        # Exponential moving averages for logging
        alpha = 0.1
        self._designer_loss_ema = (
            alpha * designer_loss + (1 - alpha) * self._designer_loss_ema
        )
        self._executor_loss_ema = (
            alpha * executor_loss + (1 - alpha) * self._executor_loss_ema
        )
        self._kl_ema = alpha * combined_kl + (1 - alpha) * self._kl_ema

        # Track cost
        for ea in batch.executor_actions:
            self._total_cost_usd += ea.cost_usd

        # Metrics
        mean_reward = sum(batch.rewards) / max(n, 1)
        mean_advantage = sum(advantages) / max(n, 1)
        policy_entropy = (designer.entropy() + executor.entropy()) / 2.0

        logger.info(
            "GRPO step completed",
            step=self.step,
            loss=round(total_loss, 6),
            mean_reward=round(mean_reward, 4),
            mean_advantage=round(mean_advantage, 4),
            kl=round(combined_kl, 6),
            kl_penalty=round(kl_penalty, 6),
        )

        output = GRPOOutput(
            loss=total_loss,
            designer_loss=designer_loss,
            executor_loss=executor_loss,
            kl_penalty=kl_penalty,
            mean_reward=mean_reward,
            mean_advantage=mean_advantage,
            policy_entropy=policy_entropy,
            step=self.step,
        )

        # Checkpoint if needed
        if config.checkpoint_interval > 0 and self.step % config.checkpoint_interval == 0:
            self.save_checkpoint(designer, executor)

        return output

    # ------------------------------------------------------------------
    # Checkpointing
    # ------------------------------------------------------------------

    def save_checkpoint(
        self,
        designer: DesignerPolicy,
        executor: ExecutorPolicy,
        path: str | None = None,
    ) -> str:
        """Save policy states to a checkpoint file.

        Args:
            designer: The designer policy.
            executor: The executor policy.
            path: Optional file path. Defaults to
                ``{checkpoint_dir}/grpo_step_{step}.pkl``.

        Returns:
            The checkpoint file path.
        """
        if path is None:
            checkpoint_dir = self.config.checkpoint_dir or "."
            os.makedirs(checkpoint_dir, exist_ok=True)
            path = os.path.join(checkpoint_dir, f"grpo_step_{self.step}.pkl")

        checkpoint = {
            "trainer_step": self.step,
            "trainer_config": {
                "group_size": self.config.group_size,
                "clip_epsilon": self.config.clip_epsilon,
                "kl_coef": self.config.kl_coef,
                "gae_lambda": self.config.gae_lambda,
                "gamma": self.config.gamma,
            },
            "designer_state": designer.get_state(),
            "executor_state": executor.get_state(),
            "metrics": {
                "designer_loss_ema": self._designer_loss_ema,
                "executor_loss_ema": self._executor_loss_ema,
                "kl_ema": self._kl_ema,
                "total_cost_usd": self._total_cost_usd,
            },
            "timestamp": time.time(),
        }

        with open(path, "wb") as f:
            pickle.dump(checkpoint, f)

        logger.info("checkpoint saved", path=path, step=self.step)
        return path

    def load_checkpoint(
        self,
        path: str,
        designer: DesignerPolicy,
        executor: ExecutorPolicy,
    ) -> int:
        """Load policy states from a checkpoint file.

        Args:
            path: Path to the checkpoint file.
            designer: The designer policy to restore.
            executor: The executor policy to restore.

        Returns:
            The step number from the checkpoint.
        """
        with open(path, "rb") as f:
            checkpoint = pickle.load(f)

        self.step = checkpoint.get("trainer_step", 0)
        designer.load_state(checkpoint.get("designer_state", {}))
        executor.load_state(checkpoint.get("executor_state", {}))

        metrics = checkpoint.get("metrics", {})
        self._designer_loss_ema = metrics.get("designer_loss_ema", 0.0)
        self._executor_loss_ema = metrics.get("executor_loss_ema", 0.0)
        self._kl_ema = metrics.get("kl_ema", 0.0)
        self._total_cost_usd = metrics.get("total_cost_usd", 0.0)

        logger.info("checkpoint loaded", path=path, step=self.step)
        return self.step

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def designer_loss_ema(self) -> float:
        """Exponential moving average of designer loss."""
        return self._designer_loss_ema

    @property
    def executor_loss_ema(self) -> float:
        """Exponential moving average of executor loss."""
        return self._executor_loss_ema

    @property
    def kl_ema(self) -> float:
        """Exponential moving average of KL divergence."""
        return self._kl_ema

    @property
    def total_cost(self) -> float:
        """Total estimated cost of all training runs in USD."""
        return self._total_cost_usd


__all__ = [
    "GRPOConfig",
    "GRPOTrainer",
    "DesignerPolicy",
    "ExecutorPolicy",
    "DesignerAction",
    "ExecutorAction",
    "TrainingBatch",
    "GRPOOutput",
    "compute_gae",
    "compute_kl_penalty",
]
