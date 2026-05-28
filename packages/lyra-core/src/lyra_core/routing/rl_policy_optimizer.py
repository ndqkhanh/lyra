"""RL-Based Policy Optimizer for intelligent model routing.

Integrates state encoding, policy network, reward calculation, and
experience replay into a complete RL training loop.

Shadow Mode: The RL policy runs alongside the deterministic router,
observing decisions and learning from outcomes without affecting
production traffic. Once the policy achieves sufficient performance
on held-out validation, it can be promoted to active routing.

Key metrics tracked:
  - Cumulative reward per episode
  - Cost savings vs. always-use-advisor baseline
  - Action distribution entropy (exploration indicator)
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from .dynamic_pricing import DynamicPricingEngine
from .experience_buffer import Experience, ExperienceBuffer
from .policy_network import ACTION_SPACE, PolicyNetwork
from .reward_calculator import RewardCalculator
from .state_encoder import StateEncoder, StateVector


@dataclass(frozen=True)
class TrainingMetrics:
    """Aggregated metrics for one training epoch."""

    epoch: int
    avg_loss: float
    avg_reward: float
    cumulative_reward: float
    episodes_completed: int
    steps_completed: int
    action_distribution: dict[str, float]
    cost_savings_pct: float
    timestamp: float


@dataclass
class RLRouterConfig:
    """Configuration for the RL-based routing optimizer."""

    learning_rate: float = 0.01
    discount_factor: float = 0.95        # gamma for future reward discounting
    batch_size: int = 32
    replay_capacity: int = 10000
    target_update_frequency: int = 100    # steps between target network syncs
    min_replay_size: int = 128            # min experiences before training starts
    shadow_mode: bool = True              # True = observe only, don't affect routing
    promotion_threshold: float = 0.15     # avg reward > this to exit shadow mode
    save_path: str = "~/.lyra/route-policy.json"


@dataclass
class RLRoutingDecision:
    """Decision from the RL router with metadata."""

    tier: str
    action_idx: int
    confidence: float
    state_vector: StateVector
    shadow_mode: bool
    reason: str


@dataclass
class RLPriorityOptimizer:
    """RL-based routing policy optimizer with shadow-mode deployment.

    Usage::

        optimizer = RLPriorityOptimizer()
        optimizer.start_episode("task-001")

        state = encoder.encode_from_signals(signals)
        decision = optimizer.select_tier(state)

        # ... execute model call, observe outcome ...
        reward = optimizer.record_outcome(
            decision, quality=0.9, cost_usd=0.02, latency_ms=450.0
        )

        metrics = optimizer.end_episode()
    """

    config: RLRouterConfig = field(default_factory=RLRouterConfig)
    _policy: PolicyNetwork = field(default_factory=PolicyNetwork)
    _target_policy: PolicyNetwork | None = None
    _encoder: StateEncoder = field(default_factory=StateEncoder)
    _reward_calc: RewardCalculator = field(default_factory=RewardCalculator)
    _buffer: ExperienceBuffer = field(default_factory=ExperienceBuffer)
    _pricing: DynamicPricingEngine = field(default_factory=DynamicPricingEngine)

    _current_episode: str | None = None
    _episode_rewards: list[float] = field(default_factory=list)
    _episode_states: list[StateVector] = field(default_factory=list)
    _episode_actions: list[int] = field(default_factory=list)
    _last_state: StateVector | None = None
    _last_action_idx: int | None = None

    _total_steps: int = 0
    _total_episodes: int = 0
    _cumulative_reward: float = 0.0
    _action_counts: dict[str, int] = field(default_factory=lambda: {a: 0 for a in ACTION_SPACE})
    _cost_history: list[float] = field(default_factory=list)

    def start_episode(self, episode_id: str | None = None) -> str:
        self._current_episode = episode_id or f"ep-{uuid.uuid4().hex[:12]}"
        self._episode_rewards.clear()
        self._episode_states.clear()
        self._episode_actions.clear()
        self._last_state = None
        self._last_action_idx = None
        return self._current_episode

    def select_tier(self, state: StateVector, *, exploit: bool = False) -> RLRoutingDecision:
        features = state.as_list()
        tier, action_idx = self._policy.select_action(features, exploit=exploit)
        probs, _, _ = self._policy.forward(features)

        self._last_state = state
        self._last_action_idx = action_idx
        self._episode_states.append(state)
        self._episode_actions.append(action_idx)
        self._action_counts[tier] = self._action_counts.get(tier, 0) + 1

        return RLRoutingDecision(
            tier=tier,
            action_idx=action_idx,
            confidence=probs[action_idx],
            state_vector=state,
            shadow_mode=self.config.shadow_mode,
            reason=(
                f"RL policy selected '{tier}' (confidence={probs[action_idx]:.3f})"
                f"{' [SHADOW]' if self.config.shadow_mode else ''}"
            ),
        )

    def record_outcome(
        self,
        decision: RLRoutingDecision,
        *,
        quality: float = 1.0,
        cost_usd: float = 0.0,
        latency_ms: float = 0.0,
        safety_flagged: bool = False,
        next_state: StateVector | None = None,
        done: bool = False,
    ) -> float:
        reward_components = self._reward_calc.compute(
            quality=quality,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
            safety_flagged=safety_flagged,
            tier=decision.tier,
        )
        reward = reward_components.total
        self._episode_rewards.append(reward)
        self._cost_history.append(cost_usd)

        if self._last_state is not None and self._last_action_idx is not None:
            next_features = next_state.features if next_state else self._last_state.features
            experience = Experience(
                state_features=self._last_state.features,
                action=decision.tier,
                reward=reward,
                next_state_features=next_features,
                done=done,
                priority=abs(reward),
                timestamp=time.time(),
                episode_id=self._current_episode or "unknown",
            )
            self._buffer.push(experience)

        self._train_if_ready()
        return reward

    def _train_if_ready(self) -> None:
        if self._buffer.size < self.config.min_replay_size:
            return

        batch = self._buffer.sample(self.config.batch_size, stratified=True)
        if not batch:
            return

        for exp in batch:
            action_idx = ACTION_SPACE.index(exp.action)
            self._policy.train_step(
                list(exp.state_features), action_idx, exp.reward
            )

        self._total_steps += 1
        self._cumulative_reward += sum(exp.reward for exp in batch) / len(batch)

        if self._total_steps % self.config.target_update_frequency == 0:
            self._sync_target_network()

    def _sync_target_network(self) -> None:
        if self._target_policy is None:
            self._target_policy = PolicyNetwork()
        self._target_policy.weights = self._policy.clone_weights()

    def end_episode(self) -> TrainingMetrics:
        self._total_episodes += 1

        avg_reward = (
            sum(self._episode_rewards) / len(self._episode_rewards)
            if self._episode_rewards else 0.0
        )

        total_actions = sum(self._action_counts.values()) or 1
        action_dist = {
            a: self._action_counts.get(a, 0) / total_actions
            for a in ACTION_SPACE
        }

        # Cost savings vs. always using advisor
        advisor_cost = self._pricing.cost_for_tier("advisor")
        avg_cost = sum(self._cost_history) / max(len(self._cost_history), 1.0)
        cost_savings = max(0.0, (advisor_cost - avg_cost) / max(advisor_cost, 0.0001)) * 100

        return TrainingMetrics(
            epoch=self._total_episodes,
            avg_loss=self._policy.avg_loss,
            avg_reward=round(avg_reward, 6),
            cumulative_reward=round(self._cumulative_reward, 4),
            episodes_completed=self._total_episodes,
            steps_completed=self._total_steps,
            action_distribution=action_dist,
            cost_savings_pct=round(cost_savings, 1),
            timestamp=time.time(),
        )

    def should_promote(self) -> bool:
        """Check if the RL policy is ready to exit shadow mode."""
        if not self.config.shadow_mode:
            return True
        if self._total_episodes < 10:
            return False
        recent_rewards = self._episode_rewards[-10:]
        avg = sum(recent_rewards) / len(recent_rewards) if recent_rewards else 0.0
        return avg >= self.config.promotion_threshold

    def promote(self) -> None:
        self.config.shadow_mode = False

    def save_policy(self, path: str | Path | None = None) -> Path:
        save_path = Path(path or self.config.save_path).expanduser().resolve()
        save_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "weights": self._policy.get_weights_vector(),
            "train_steps": self._total_steps,
            "episodes": self._total_episodes,
            "cumulative_reward": self._cumulative_reward,
            "action_distribution": {
                a: self._action_counts.get(a, 0) for a in ACTION_SPACE
            },
            "shadow_mode": self.config.shadow_mode,
            "saved_at": time.time(),
        }
        save_path.write_text(json.dumps(data, indent=2))
        return save_path

    def load_policy(self, path: str | Path | None = None) -> bool:
        load_path = Path(path or self.config.save_path).expanduser().resolve()
        if not load_path.exists():
            return False

        data = json.loads(load_path.read_text())
        if "weights" in data:
            self._policy.set_weights_vector(data["weights"])
        self._total_steps = data.get("train_steps", 0)
        self._total_episodes = data.get("episodes", 0)
        self._cumulative_reward = data.get("cumulative_reward", 0.0)
        self.config.shadow_mode = data.get("shadow_mode", True)
        return True

    def reset(self) -> None:
        self._policy = PolicyNetwork()
        self._target_policy = None
        self._buffer.clear()
        self._total_steps = 0
        self._total_episodes = 0
        self._cumulative_reward = 0.0
        self._action_counts = {a: 0 for a in ACTION_SPACE}
        self._cost_history.clear()
        self._episode_rewards.clear()
        self._episode_states.clear()
        self._episode_actions.clear()
        self._current_episode = None
        self._last_state = None
        self._last_action_idx = None

    @property
    def buffer_size(self) -> int:
        return self._buffer.size

    @property
    def total_steps(self) -> int:
        return self._total_steps

    @property
    def episodes(self) -> int:
        return self._total_episodes

    @property
    def action_distribution(self) -> dict[str, int]:
        return dict(self._action_counts)


__all__ = [
    "RLPriorityOptimizer",
    "RLRouterConfig",
    "RLRoutingDecision",
    "TrainingMetrics",
]
