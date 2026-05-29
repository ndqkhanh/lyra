"""Leaderboard engine — multi-domain agent ranking and comparison."""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass(frozen=True)
class AgentScore:
    """An agent's scores across domains with overall rank."""

    agent_id: str
    domain_scores: tuple[tuple[str, float], ...]
    overall_score: float
    rank: int = 0
    previous_rank: int = 0
    trend: str = "stable"  # "improving", "declining", "stable"
    evaluated_at: float = field(default_factory=time.time)

    def get_domain_score(self, domain: str) -> float | None:
        for d, s in self.domain_scores:
            if d == domain:
                return s
        return None


@dataclass(frozen=True)
class RankingView:
    """A snapshot of the leaderboard for a specific domain or overall."""

    domain: str  # "overall" for cross-domain ranking
    scores: tuple[AgentScore, ...]
    timestamp: float = field(default_factory=time.time)
    total_agents: int = 0

    @property
    def top_3(self) -> tuple[AgentScore, ...]:
        return self.scores[:3]

    @property
    def bottom_3(self) -> tuple[AgentScore, ...]:
        return self.scores[-3:] if len(self.scores) >= 3 else ()


@dataclass
class LeaderboardEngine:
    """Multi-domain leaderboard with ranking and rank history.

    Usage::

        engine = LeaderboardEngine()
        engine.submit_score(AgentScore(
            agent_id="agent-1",
            domain_scores=(("safety", 0.95), ("skills", 0.88)),
            overall_score=0.915,
        ))
        view = engine.get_overall_ranking()
        print(view.top_3)
    """

    _scores: dict[str, list[AgentScore]] = field(default_factory=dict)
    rank_volatility_threshold: float = 3.0

    def submit_score(self, score: AgentScore) -> None:
        """Submit a new score snapshot for an agent."""
        self._scores.setdefault(score.agent_id, []).append(score)
        self._prune_history(score.agent_id)

    def _prune_history(self, agent_id: str, max_history: int = 50) -> None:
        scores = self._scores.get(agent_id)
        if scores and len(scores) > max_history:
            self._scores[agent_id] = scores[-max_history:]

    def rank_agents(
        self,
        domain: str | None = None,
        *,
        weights: dict[str, float] | None = None,
    ) -> tuple[AgentScore, ...]:
        """Rank all agents by domain or overall score.

        Args:
            domain: Domain to rank by. None for overall ranking.
            weights: Per-domain weights for cross-domain ranking.
        """
        latest_scores: list[AgentScore] = []

        for agent_id, history in self._scores.items():
            if not history:
                continue
            latest = history[-1]

            if domain is not None:
                domain_score = latest.get_domain_score(domain)
                if domain_score is None:
                    continue
                effective_score = domain_score
            else:
                effective_score = self._compute_weighted_score(latest, weights)

            latest_scores.append(AgentScore(
                agent_id=agent_id,
                domain_scores=latest.domain_scores,
                overall_score=effective_score,
                evaluated_at=latest.evaluated_at,
            ))

        sorted_scores = sorted(latest_scores, key=lambda s: s.overall_score, reverse=True)
        previous_ranks = self._get_previous_ranks()

        result: list[AgentScore] = []
        for i, score in enumerate(sorted_scores):
            rank = i + 1
            prev_rank = previous_ranks.get(score.agent_id, rank)
            trend = self._compute_trend(rank, prev_rank)

            ranked = AgentScore(
                agent_id=score.agent_id,
                domain_scores=score.domain_scores,
                overall_score=score.overall_score,
                rank=rank,
                previous_rank=prev_rank,
                trend=trend,
                evaluated_at=score.evaluated_at,
            )
            result.append(ranked)
            # Persist rank back into stored history
            history = self._scores.get(score.agent_id, [])
            if history:
                last = history[-1]
                history[-1] = AgentScore(
                    agent_id=last.agent_id,
                    domain_scores=last.domain_scores,
                    overall_score=last.overall_score,
                    rank=rank,
                    previous_rank=prev_rank,
                    trend=trend,
                    evaluated_at=last.evaluated_at,
                )

        return tuple(result)

    def _compute_weighted_score(
        self,
        score: AgentScore,
        weights: dict[str, float] | None,
    ) -> float:
        """Compute weighted overall score across domains."""
        if not weights:
            scores = [s for _, s in score.domain_scores]
            return sum(scores) / max(len(scores), 1)

        total_weight = 0.0
        weighted_sum = 0.0
        for domain, s in score.domain_scores:
            w = weights.get(domain, 1.0)
            weighted_sum += s * w
            total_weight += w
        return round(weighted_sum / max(total_weight, 0.001), 4)

    def _get_previous_ranks(self) -> dict[str, int]:
        """Get ranks from the previous evaluation for trend detection."""
        previous: dict[str, int] = {}
        for agent_id, history in self._scores.items():
            if len(history) >= 2:
                prev_score = history[-2]
                if prev_score.rank > 0:
                    previous[agent_id] = prev_score.rank
        return previous

    @staticmethod
    def _compute_trend(current_rank: int, previous_rank: int) -> str:
        if current_rank < previous_rank:
            return "improving"
        elif current_rank > previous_rank:
            return "declining"
        return "stable"

    def get_overall_ranking(self, weights: dict[str, float] | None = None) -> RankingView:
        """Get the overall ranking across all domains."""
        scores = self.rank_agents(domain=None, weights=weights)
        return RankingView(
            domain="overall",
            scores=scores,
            total_agents=len(scores),
        )

    def get_domain_ranking(self, domain: str) -> RankingView:
        """Get the ranking for a specific domain."""
        scores = self.rank_agents(domain=domain)
        return RankingView(
            domain=domain,
            scores=scores,
            total_agents=len(scores),
        )

    def get_agent_history(self, agent_id: str) -> tuple[AgentScore, ...]:
        """Get the full score history for an agent."""
        return tuple(self._scores.get(agent_id, []))

    def get_agent_rank_history(
        self,
        agent_id: str,
    ) -> tuple[tuple[int, float], ...]:
        """Get (rank, score) tuples over time for an agent."""
        history = self._scores.get(agent_id, [])
        return tuple((s.rank, s.overall_score) for s in history if s.rank > 0)

    def get_volatile_agents(self) -> tuple[str, ...]:
        """Find agents with large rank swings."""
        volatile: list[str] = []
        for agent_id, history in self._scores.items():
            ranks = [s.rank for s in history if s.rank > 0]
            if len(ranks) < 2:
                continue
            max_swing = max(abs(ranks[i] - ranks[i - 1]) for i in range(1, len(ranks)))
            if max_swing >= self.rank_volatility_threshold:
                volatile.append(agent_id)
        return tuple(volatile)

    def compare_agents(
        self,
        agent_id_a: str,
        agent_id_b: str,
    ) -> dict[str, tuple[float, float] | None]:
        """Compare the latest scores of two agents per domain."""
        history_a = self._scores.get(agent_id_a)
        history_b = self._scores.get(agent_id_b)
        if not history_a or not history_b:
            return {}

        score_a = history_a[-1]
        score_b = history_b[-1]

        all_domains: set[str] = set()
        for d, _ in score_a.domain_scores:
            all_domains.add(d)
        for d, _ in score_b.domain_scores:
            all_domains.add(d)

        result: dict[str, tuple[float, float] | None] = {}
        for domain in sorted(all_domains):
            sa = score_a.get_domain_score(domain)
            sb = score_b.get_domain_score(domain)
            if sa is not None and sb is not None:
                result[domain] = (sa, sb)
            else:
                result[domain] = None
        return result

    @property
    def agent_count(self) -> int:
        return len(self._scores)

    def clear(self) -> None:
        self._scores.clear()
