"""Credit assignment — inner-outer loop gradient-based contribution scoring."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .exceptions import CreditAssignmentError
from .latent_encoder import LatentVector, similarity


@dataclass(frozen=True)
class CreditConfig:
    inner_iterations: int = 10
    outer_iterations: int = 3
    learning_rate: float = 0.1
    decay: float = 0.95


@dataclass(frozen=True)
class CreditScore:
    agent_id: str
    contribution_score: float
    confidence: float
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class ContributionRecord:
    agent_id: str
    action: str
    impact_score: float
    timestamp: float


@dataclass(frozen=True)
class InnerLoopResult:
    agent_scores: tuple[tuple[str, float], ...]
    convergence_metric: float
    iterations: int


class CreditAssignmentEngine:
    """Inner-outer loop gradient-based credit assignment engine."""

    def __init__(self, config: CreditConfig | None = None) -> None:
        self.config = config or CreditConfig()

    def assign_credit(
        self,
        trajectory: list[tuple[str, LatentVector]],
        outcome: LatentVector,
    ) -> list[CreditScore]:
        if not trajectory:
            raise CreditAssignmentError("Cannot assign credit to empty trajectory")

        scores: list[CreditScore] = []
        for agent_id, latent in trajectory:
            try:
                sim = similarity(latent, outcome)
            except ValueError:
                sim = 0.0

            conf = min(1.0, max(0.0, abs(sim)))
            score = CreditScore(
                agent_id=agent_id,
                contribution_score=float(sim),
                confidence=conf,
                evidence=(f"similarity_to_outcome={sim:.4f}",),
            )
            scores.append(score)

        return scores

    def inner_loop(
        self,
        agent_messages: list[tuple[str, LatentVector]],
        ground_truth: LatentVector,
    ) -> InnerLoopResult:
        if not agent_messages:
            raise CreditAssignmentError(
                "Cannot run inner loop on empty agent messages"
            )

        lr = self.config.learning_rate
        n = len(agent_messages)

        raw_scores = np.array(
            [
                similarity(lv, ground_truth)
                for _, lv in agent_messages
            ],
            dtype=np.float64,
        )

        normalized = raw_scores / (np.sum(np.abs(raw_scores)) + 1e-10)
        refined = normalized.copy()

        for iteration in range(self.config.inner_iterations):
            current_lr = lr * (self.config.decay**iteration)

            gradient = np.zeros_like(refined)
            for i in range(n):
                for j in range(n):
                    if i != j:
                        gradient[i] += refined[i] - refined[j]

            gradient = gradient / (np.std(gradient) + 1e-10)
            refined = refined + current_lr * gradient
            refined = refined / (np.sum(np.abs(refined)) + 1e-10)

        scores = tuple(
            (agent_messages[i][0], float(refined[i]))
            for i in range(n)
        )

        convergence = float(np.std(refined)) if n > 1 else 1.0

        return InnerLoopResult(
            agent_scores=scores,
            convergence_metric=convergence,
            iterations=self.config.inner_iterations,
        )


class CreditLedger:
    """Tracks credit scores over time across episodes."""

    def __init__(self) -> None:
        self._records: dict[str, list[CreditScore]] = {}
        self._episodes: dict[str, list[CreditScore]] = {}

    def record(self, episode_id: str, scores: list[CreditScore]) -> None:
        if not scores:
            raise CreditAssignmentError(
                "Cannot record empty scores list"
            )
        self._episodes[episode_id] = scores
        for score in scores:
            if score.agent_id not in self._records:
                self._records[score.agent_id] = []
            self._records[score.agent_id].append(score)

    def get_agent_history(self, agent_id: str) -> list[CreditScore]:
        return list(self._records.get(agent_id, []))

    def get_top_contributors(
        self, episode_id: str, top_k: int = 3
    ) -> list[CreditScore]:
        scores = self._episodes.get(episode_id)
        if not scores:
            return []
        sorted_scores = sorted(
            scores, key=lambda s: s.contribution_score, reverse=True
        )
        return sorted_scores[:top_k]

    def get_all_episodes(self) -> dict[str, list[CreditScore]]:
        return dict(self._episodes)

    def clear(self) -> None:
        self._records.clear()
        self._episodes.clear()
