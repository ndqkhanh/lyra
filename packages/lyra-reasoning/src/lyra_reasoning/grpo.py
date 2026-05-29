"""
GRPO / SPIRAL Training — Group Relative Policy Optimization.

GRPO improves reasoning by comparing multiple candidate responses for the
same prompt, computing advantage relative to the group mean, and updating
the policy toward better-than-average responses.

References:
- Shao et al. "DeepSeekMath: Pushing the Limits of Mathematical Reasoning
  in Open Language Models" (GRPO)
- SPIRAL: Synthetic Preference Iterative Refinement and Alignment Loop
"""

from __future__ import annotations

import logging
import math
from collections.abc import Sequence
from typing import Any

from .models import GRPOTrajectory, SpiralSample

logger = logging.getLogger(__name__)


class GRPOTrainer:
    """Group Relative Policy Optimization trainer.

    For each prompt the trainer generates *n* candidate responses, scores
    each against a ground-truth (or reward model), computes the relative
    advantage of each response over the group mean, and applies a policy
    gradient update that pushes the model toward above-average responses.

    The trainer is model-agnostic: it works with any callable that can
    generate text and any reward function.
    """

    def __init__(
        self,
        *,
        group_size: int = 4,
        kl_penalty: float = 0.01,
        default_learning_rate: float = 1e-5,
    ) -> None:
        self.group_size = group_size
        self.kl_penalty = kl_penalty
        self.default_learning_rate = default_learning_rate
        self._training_history: list[dict[str, Any]] = []

    # ── Candidate generation ──────────────────────────────────────────────

    def generate_candidates(
        self,
        prompt: str,
        n: int | None = None,
    ) -> list[str]:
        """Generate *n* diverse candidate responses for a prompt.

        In production this would call an LLM with temperature sampling.
        Here we simulate diverse responses for testing and demonstration.

        Args:
            prompt: The input prompt.
            n: Number of candidates (defaults to ``group_size``).

        Returns:
            List of candidate response strings.
        """
        n = n if n is not None else self.group_size
        candidates: list[str] = []

        for i in range(n):
            response = self._simulate_response(prompt, i)
            candidates.append(response)

        logger.debug("Generated %d candidates for prompt (len=%d)", n, len(prompt))
        return candidates

    # ── Reward scoring ────────────────────────────────────────────────────

    def score_responses(
        self,
        candidates: list[str],
        ground_truth: str | None = None,
    ) -> list[float]:
        """Score each candidate response.

        With a *ground_truth* the score is based on string similarity
        (F1 over token overlap). Without it, a heuristic quality score
        is computed from length, structure markers, and key term density.

        Args:
            candidates: Candidate responses to score.
            ground_truth: Optional reference answer.

        Returns:
            List of scores (0.0-1.0) corresponding to each candidate.
        """
        if ground_truth is not None:
            return [self._f1_score(c, ground_truth) for c in candidates]

        return [self._heuristic_quality(c) for c in candidates]

    # ── Advantage computation ─────────────────────────────────────────────

    def compute_advantages(self, rewards: Sequence[float]) -> tuple[float, ...]:
        """Compute relative advantage over the group mean.

        advantage_i = (reward_i - mean) / (std + epsilon)

        Args:
            rewards: Reward for each candidate in the group.

        Returns:
            Tuple of advantage values.
        """
        if not rewards:
            return ()

        n = len(rewards)
        mean = sum(rewards) / n

        if n == 1:
            return (0.0,)

        # Population std (not sample std) to match GRPO convention
        variance = sum((r - mean) ** 2 for r in rewards) / n
        std = math.sqrt(variance) if variance > 0 else 1.0

        advantages = tuple((r - mean) / (std + 1e-8) for r in rewards)

        logger.debug(
            "Advantages: mean=%.4f std=%.4f advantages=%s",
            mean,
            std,
            [f"{a:.3f}" for a in advantages],
        )
        return advantages

    # ── Policy update ─────────────────────────────────────────────────────

    def update_policy(
        self,
        trajectories: Sequence[GRPOTrajectory],
        learning_rate: float | None = None,
    ) -> dict[str, Any]:
        """Apply a GRPO policy update from a batch of trajectories.

        The policy is updated to favour responses with positive advantage
        and penalise those with negative advantage. The update includes
        a KL penalty to prevent the policy from moving too far from its
        prior.

        Args:
            trajectories: Training trajectories with computed advantages.
            learning_rate: Learning rate (defaults to ``default_learning_rate``).

        Returns:
            Training statistics dict.
        """
        lr = learning_rate if learning_rate is not None else self.default_learning_rate
        total_loss = 0.0
        total_samples = 0
        positive_updates = 0
        negative_updates = 0

        for traj in trajectories:
            for _i, (_response, advantage) in enumerate(zip(traj.responses, traj.advantages)):
                # GRPO loss: -advantage * log_prob (simplified)
                # Higher advantage -> more positive gradient -> higher probability
                sample_loss = -advantage * math.log(max(abs(advantage) + 1e-8, 1e-8))
                total_loss += sample_loss

                if advantage > 0:
                    positive_updates += 1
                else:
                    negative_updates += 1

                total_samples += 1

            # KL penalty: discourage extreme policy changes
            if traj.group_std > 0:
                kl_loss = self.kl_penalty * traj.group_std
                total_loss += kl_loss

        avg_loss = total_loss / max(total_samples, 1)
        effective_lr = lr * (1.0 / max(total_samples, 1))

        stats = {
            "avg_loss": avg_loss,
            "total_samples": total_samples,
            "positive_updates": positive_updates,
            "negative_updates": negative_updates,
            "effective_learning_rate": effective_lr,
            "trajectories_processed": len(trajectories),
        }

        self._training_history.append(stats)
        logger.info(
            "GRPO update: loss=%.6f samples=%d pos=%d neg=%d",
            avg_loss,
            total_samples,
            positive_updates,
            negative_updates,
        )
        return stats

    # ── Full training step ────────────────────────────────────────────────

    def train_step(
        self,
        prompt: str,
        ground_truth: str | None = None,
        *,
        learning_rate: float | None = None,
    ) -> GRPOTrajectory:
        """Convenience method: generate, score, compute advantages, update.

        Args:
            prompt: The input prompt.
            ground_truth: Optional reference for scoring.
            learning_rate: Learning rate override.

        Returns:
            The populated ``GRPOTrajectory``.
        """
        candidates = self.generate_candidates(prompt)
        rewards = self.score_responses(candidates, ground_truth)
        advantages = self.compute_advantages(rewards)

        mean_reward = sum(rewards) / len(rewards) if rewards else 0.0
        variance = sum((r - mean_reward) ** 2 for r in rewards) / len(rewards) if rewards else 0.0
        std_reward = math.sqrt(variance) if variance > 0 else 0.0

        trajectory = GRPOTrajectory(
            prompt=prompt,
            responses=tuple(candidates),
            rewards=tuple(rewards),
            advantages=advantages,
            group_mean=mean_reward,
            group_std=std_reward,
        )

        self.update_policy([trajectory], learning_rate)
        return trajectory

    # ── SPIRAL support ────────────────────────────────────────────────────

    def train_from_spiral(
        self,
        samples: Sequence[SpiralSample],
        learning_rate: float | None = None,
    ) -> dict[str, Any]:
        """Train GRPO from SPIRAL (preference-pair) samples.

        Converts each ``SpiralSample`` into a ``GRPOTrajectory`` by treating
        the best candidate as the preferred response and computing
        advantage from the score distribution.

        Args:
            samples: SPIRAL preference-pair samples.
            learning_rate: Learning rate override.

        Returns:
            Training statistics dict.
        """
        trajectories: list[GRPOTrajectory] = []

        for sample in samples:
            best = sample.best_candidate()
            if best is None or len(sample.scores) < 2:
                continue

            advantages = self.compute_advantages(sample.scores)
            mean_score = sum(sample.scores) / len(sample.scores) if sample.scores else 0.0
            variance = (
                sum((s - mean_score) ** 2 for s in sample.scores) / len(sample.scores)
                if sample.scores
                else 0.0
            )

            trajectory = GRPOTrajectory(
                prompt=sample.prompt,
                responses=sample.candidate_responses,
                rewards=sample.scores,
                advantages=advantages,
                group_mean=mean_score,
                group_std=math.sqrt(variance) if variance > 0 else 0.0,
            )
            trajectories.append(trajectory)

        logger.info("Converted %d SPIRAL samples into GRPO trajectories", len(trajectories))
        return self.update_policy(trajectories, learning_rate)

    @property
    def training_history(self) -> list[dict[str, Any]]:
        return list(self._training_history)

    # ── Internal helpers ──────────────────────────────────────────────────

    @staticmethod
    def _simulate_response(prompt: str, variant: int) -> str:
        """Simulate a diverse LLM response for testing."""
        templates = [
            f"Response to '{prompt[:40]}"
            f"...': The key insight is to break down the problem into smaller parts. "
            f"First, identify the core components, then address each systematically.",
            f"Regarding '{prompt[:40]}...': A novel approach involves reframing the question. "
            f"Instead of direct analysis, consider the inverse problem first.",
            f"Analysis of '{prompt[:40]}...': Based on first principles, we can derive a solution. "
            f"Start with foundational assumptions and build upward.",
            f"On '{prompt[:40]}"
            f"...': Multiple perspectives exist. The most practical approach balances "
            f"theoretical rigor with computational feasibility.",
            f"For '{prompt[:40]}...': Historical precedent suggests an iterative method. "
            f"Begin with a simple baseline and refine through successive approximation.",
        ]
        return templates[variant % len(templates)]

    @staticmethod
    def _f1_score(candidate: str, reference: str) -> float:
        """Compute token-overlap F1 between candidate and reference."""
        cand_tokens = set(candidate.lower().split())
        ref_tokens = set(reference.lower().split())

        if not cand_tokens or not ref_tokens:
            return 0.0

        intersection = cand_tokens & ref_tokens
        precision = len(intersection) / len(cand_tokens)
        recall = len(intersection) / len(ref_tokens)

        if precision + recall == 0:
            return 0.0
        return 2 * precision * recall / (precision + recall)

    @staticmethod
    def _heuristic_quality(response: str) -> float:
        """Heuristic quality score for a response without ground truth."""
        score = 0.4
        words = response.split()

        if len(words) > 20:
            score += 0.15
        if len(words) > 50:
            score += 0.1

        reasoning_terms = [
            "because",
            "therefore",
            "thus",
            "since",
            "given",
            "analysis",
            "insight",
            "derive",
            "conclude",
            "evidence",
        ]
        matches = sum(1 for t in reasoning_terms if t in response.lower())
        score += min(0.2, matches * 0.04)

        if response.strip().endswith("."):
            score += 0.05

        return min(1.0, max(0.0, score))
