"""Policy evaluation and comparison utilities."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .exceptions import PolicyEvaluationError
from .policy_search import PolicyCandidate


@dataclass(frozen=True)
class EvalConfig:
    """Configuration for policy evaluation."""

    num_episodes: int = 100
    horizon: int = 50
    eval_metrics: tuple[str, ...] = ("reward", "success_rate", "avg_latency")


@dataclass(frozen=True)
class EpisodeResult:
    """Result from a single evaluation episode."""

    episode: int
    total_reward: float
    success: bool
    steps: int
    metrics: tuple[tuple[str, float], ...]


@dataclass(frozen=True)
class PolicyEvaluation:
    """Complete evaluation of a policy across multiple episodes."""

    policy: PolicyCandidate
    episodes: tuple[EpisodeResult, ...]
    avg_reward: float
    success_rate: float
    std_reward: float


@dataclass(frozen=True)
class PolicyComparison:
    """Comparison of multiple evaluated policies."""

    evaluations: tuple[PolicyEvaluation, ...]
    winner: PolicyCandidate | None
    confidence: float
    recommendation: str


class PolicyEvaluator:
    """Evaluator for running policy rollouts and comparing policies."""

    def _simulate_episode(
        self, episode: int, policy: PolicyCandidate, horizon: int
    ) -> EpisodeResult:
        """Simulate a single episode rollout given a policy."""
        param_map = dict(policy.parameters)
        learning_rate = param_map.get("learning_rate", 0.01)
        batch_size = param_map.get("batch_size", 32)

        total_reward = 0.0
        for step in range(horizon):
            step_reward = learning_rate * math.exp(-step / horizon)
            if step % max(1, int(batch_size)) == 0:
                step_reward += 0.1
            total_reward += step_reward

        steps_taken = horizon
        success = total_reward > horizon * 0.3

        metrics: tuple[tuple[str, float], ...] = (
            ("cumulative_reward", total_reward),
            ("success", 1.0 if success else 0.0),
            ("exploration_rate", learning_rate),
        )

        return EpisodeResult(
            episode=episode,
            total_reward=total_reward,
            success=success,
            steps=steps_taken,
            metrics=metrics,
        )

    async def evaluate_policy(
        self, policy: PolicyCandidate, config: EvalConfig
    ) -> PolicyEvaluation:
        """Evaluate a policy over multiple episodes."""
        if config.num_episodes < 1:
            raise PolicyEvaluationError("num_episodes must be >= 1")
        if config.horizon < 1:
            raise PolicyEvaluationError("horizon must be >= 1")

        episodes: list[EpisodeResult] = []
        for ep in range(config.num_episodes):
            episode = self._simulate_episode(ep, policy, config.horizon)
            episodes.append(episode)

        if not episodes:
            raise PolicyEvaluationError("no episodes generated")

        rewards = np.array([e.total_reward for e in episodes], dtype=np.float64)
        successes = np.array([1.0 if e.success else 0.0 for e in episodes])

        return PolicyEvaluation(
            policy=policy,
            episodes=tuple(episodes),
            avg_reward=float(np.mean(rewards)),
            success_rate=float(np.mean(successes)),
            std_reward=float(np.std(rewards)),
        )

    async def compare_policies(
        self, policies: tuple[PolicyCandidate, ...]
    ) -> PolicyComparison:
        """Compare multiple policies and determine the winner."""
        if not policies:
            raise PolicyEvaluationError("policies must not be empty")

        eval_config = EvalConfig(num_episodes=20)
        evaluations: list[PolicyEvaluation] = []
        for policy in policies:
            eval_result = await self.evaluate_policy(policy, eval_config)
            evaluations.append(eval_result)

        sorted_evals = sorted(
            evaluations, key=lambda e: e.avg_reward, reverse=True
        )

        if len(sorted_evals) >= 2:
            best_avg = sorted_evals[0].avg_reward
            second_avg = sorted_evals[1].avg_reward
            diff = best_avg - second_avg
            confidence = min(1.0, max(0.0, diff / (second_avg + 1e-8)))
        else:
            confidence = 1.0

        best = sorted_evals[0]
        recommendation = (
            f"Policy '{best.policy.candidate_id}' recommended "
            f"(avg_reward={best.avg_reward:.4f}, "
            f"success_rate={best.success_rate:.2%})"
        )

        return PolicyComparison(
            evaluations=tuple(sorted_evals),
            winner=best.policy,
            confidence=confidence,
            recommendation=recommendation,
        )

    async def ab_test(
        self, policy_a: PolicyCandidate, policy_b: PolicyCandidate
    ) -> PolicyComparison:
        """Run an A/B test comparing two policies."""
        return await self.compare_policies((policy_a, policy_b))
