"""Multi-objective fitness evaluation with Pareto front computation."""

from __future__ import annotations

from dataclasses import dataclass

from .exceptions import FitnessError
from .hyper_agent import HyperAgent


@dataclass(frozen=True)
class FitnessConfig:
    """Configuration for multi-objective fitness evaluation."""

    objectives: tuple[str, ...] = ("correctness", "efficiency", "elegance")
    weights: tuple[float, ...] = (0.5, 0.3, 0.2)
    thresholds: tuple[float, ...] = (0.7, 0.6, 0.5)


@dataclass(frozen=True)
class FitnessScore:
    """A multi-objective fitness score for a single agent."""

    agent_id: str
    scores: tuple[tuple[str, float], ...]
    weighted_total: float
    pareto_rank: int = 0


@dataclass(frozen=True)
class ParetoFront:
    """The Pareto-optimal frontier of a set of fitness scores."""

    front: tuple[FitnessScore, ...]
    dominated: tuple[FitnessScore, ...]
    size: int


class FitnessEvaluator:
    """Evaluates and compares HyperAgent fitness across multiple objectives."""

    async def evaluate(
        self, agent: HyperAgent, config: FitnessConfig
    ) -> FitnessScore:
        """Evaluate a single agent against multi-objective config."""
        if not agent.genome:
            return FitnessScore(
                agent_id=agent.agent_id,
                scores=tuple((obj, 0.0) for obj in config.objectives),
                weighted_total=0.0,
            )

        if len(config.objectives) != len(config.weights):
            raise FitnessError(
                f"Objectives count ({len(config.objectives)}) "
                f"must match weights count ({len(config.weights)})"
            )

        if len(config.objectives) != len(config.thresholds):
            raise FitnessError(
                f"Objectives count ({len(config.objectives)}) "
                f"must match thresholds count ({len(config.thresholds)})"
            )

        scores: list[tuple[str, float]] = []
        for i, obj in enumerate(config.objectives):
            raw = _compute_objective_score(agent, obj, i)
            threshold = config.thresholds[i]
            scaled = raw if raw >= threshold else raw * 0.5
            scores.append((obj, scaled))

        weighted_total = sum(
            score * config.weights[idx]
            for idx, (_, score) in enumerate(scores)
        )

        return FitnessScore(
            agent_id=agent.agent_id,
            scores=tuple(scores),
            weighted_total=weighted_total,
        )

    async def batch_evaluate(
        self,
        agents: tuple[HyperAgent, ...],
        config: FitnessConfig,
    ) -> tuple[FitnessScore, ...]:
        """Evaluate multiple agents and assign Pareto ranks."""
        scores_list: list[FitnessScore] = []
        for agent in agents:
            score = await self.evaluate(agent, config)
            scores_list.append(score)

        # Assign Pareto ranks
        ranked = self._assign_pareto_ranks(tuple(scores_list))
        return ranked

    def compute_pareto_front(
        self, scores: tuple[FitnessScore, ...]
    ) -> ParetoFront:
        """Compute the Pareto-optimal frontier from fitness scores."""
        if not scores:
            return ParetoFront(front=(), dominated=(), size=0)

        n = len(scores)
        dominated_flags: list[bool] = [False] * n

        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                if self._dominates(scores[i], scores[j]):
                    dominated_flags[j] = True

        front: list[FitnessScore] = []
        dominated: list[FitnessScore] = []
        for i, score in enumerate(scores):
            if not dominated_flags[i]:
                front.append(score)
            else:
                dominated.append(score)

        return ParetoFront(
            front=tuple(front),
            dominated=tuple(dominated),
            size=len(front),
        )

    async def compare_agents(
        self, a1: HyperAgent, a2: HyperAgent
    ) -> int:
        """Compare two agents by fitness. Returns -1, 0, or 1."""
        config = FitnessConfig()
        score1 = await self.evaluate(a1, config)
        score2 = await self.evaluate(a2, config)

        if score1.weighted_total > score2.weighted_total:
            return 1
        if score1.weighted_total < score2.weighted_total:
            return -1
        return 0

    def _assign_pareto_ranks(
        self, scores: tuple[FitnessScore, ...]
    ) -> tuple[FitnessScore, ...]:
        """Assign Pareto ranks via iterative front extraction."""
        remaining = list(scores)
        ranked: list[FitnessScore] = []
        rank = 1

        while remaining:
            front_result = self.compute_pareto_front(tuple(remaining))
            for score in front_result.front:
                ranked.append(FitnessScore(
                    agent_id=score.agent_id,
                    scores=score.scores,
                    weighted_total=score.weighted_total,
                    pareto_rank=rank,
                ))
            remaining = list(front_result.dominated)
            rank += 1

        return tuple(ranked)

    @staticmethod
    def _dominates(a: FitnessScore, b: FitnessScore) -> bool:
        """Check if score 'a' dominates score 'b'."""
        score_map_a = dict(a.scores)
        score_map_b = dict(b.scores)

        all_keys = set(score_map_a) | set(score_map_b)
        at_least_one_better = False
        for key in all_keys:
            va = score_map_a.get(key, 0.0)
            vb = score_map_b.get(key, 0.0)
            if va < vb:
                return False
            if va > vb:
                at_least_one_better = True
        return at_least_one_better


def _compute_objective_score(
    agent: HyperAgent, objective: str, index: int
) -> float:
    """Compute a raw score for a single objective based on genome."""
    if not agent.genome:
        return 0.0

    if index >= len(agent.genome):
        index = index % max(len(agent.genome), 1)

    gene = agent.genome[index]
    raw = gene.value * agent.fitness if agent.fitness > 0 else gene.value

    if objective == "correctness":
        return raw * 0.9 + 0.1
    if objective == "efficiency":
        return raw * 0.7 + 0.3
    if objective == "elegance":
        return raw * 0.5 + 0.5

    # Generic fallback for arbitrary objectives
    return abs(raw) % 1.0
