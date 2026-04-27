"""Elo-style arena for pairwise harness / model / config comparisons.

Each match pits two configurations against a single task; the
caller produces a :class:`MatchOutcome` (``"a_wins"``, ``"b_wins"``,
or ``"draw"``) via whatever judge they prefer (``prm_score`` above
a threshold, a pairwise LLM, or a human panel). The arena tracks
Elo ratings per configuration so the leaderboard surfaces *relative*
strength rather than absolute pass rates.

Draws update both players' expected scores towards the midpoint;
wins/losses use the standard formula ``R' = R + K * (S - E)``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable, Mapping, Sequence


__all__ = [
    "Arena",
    "ArenaMatch",
    "ArenaReport",
    "EloRating",
    "MatchOutcome",
    "RatingUpdate",
    "expected_score",
    "update_elo",
]


DEFAULT_K = 32.0
DEFAULT_RATING = 1200.0


# ---- Elo primitives ------------------------------------------------


def expected_score(rating_a: float, rating_b: float) -> float:
    """Standard Elo expected-score for A vs B."""
    return 1.0 / (1.0 + 10 ** ((rating_b - rating_a) / 400.0))


MatchOutcome = str  # "a_wins" | "b_wins" | "draw"


_VALID_OUTCOMES = frozenset({"a_wins", "b_wins", "draw"})


def update_elo(
    *,
    rating_a: float,
    rating_b: float,
    outcome: MatchOutcome,
    k: float = DEFAULT_K,
) -> tuple[float, float]:
    if outcome not in _VALID_OUTCOMES:
        raise ValueError(f"outcome must be one of {_VALID_OUTCOMES}, got {outcome!r}")
    if k <= 0:
        raise ValueError(f"k must be > 0, got {k}")
    e_a = expected_score(rating_a, rating_b)
    e_b = 1.0 - e_a
    if outcome == "a_wins":
        s_a, s_b = 1.0, 0.0
    elif outcome == "b_wins":
        s_a, s_b = 0.0, 1.0
    else:
        s_a = s_b = 0.5
    return rating_a + k * (s_a - e_a), rating_b + k * (s_b - e_b)


# ---- arena model ---------------------------------------------------


@dataclass
class EloRating:
    config_name: str
    rating: float = DEFAULT_RATING
    wins: int = 0
    losses: int = 0
    draws: int = 0

    @property
    def games(self) -> int:
        return self.wins + self.losses + self.draws

    def to_dict(self) -> dict[str, object]:
        return {
            "config_name": self.config_name,
            "rating": self.rating,
            "wins": self.wins,
            "losses": self.losses,
            "draws": self.draws,
            "games": self.games,
        }


@dataclass(frozen=True)
class ArenaMatch:
    config_a: str
    config_b: str
    task_id: str


@dataclass(frozen=True)
class RatingUpdate:
    match: ArenaMatch
    outcome: MatchOutcome
    rating_a_before: float
    rating_a_after: float
    rating_b_before: float
    rating_b_after: float

    def to_dict(self) -> dict[str, object]:
        return {
            "match": {
                "config_a": self.match.config_a,
                "config_b": self.match.config_b,
                "task_id": self.match.task_id,
            },
            "outcome": self.outcome,
            "rating_a_before": self.rating_a_before,
            "rating_a_after": self.rating_a_after,
            "rating_b_before": self.rating_b_before,
            "rating_b_after": self.rating_b_after,
        }


@dataclass
class ArenaReport:
    ratings: tuple[EloRating, ...]
    updates: tuple[RatingUpdate, ...]

    def leaderboard(self) -> tuple[EloRating, ...]:
        return tuple(sorted(self.ratings, key=lambda r: r.rating, reverse=True))

    def to_dict(self) -> dict[str, object]:
        return {
            "leaderboard": [r.to_dict() for r in self.leaderboard()],
            "updates": [u.to_dict() for u in self.updates],
        }


@dataclass
class Arena:
    """Elo-style arena over a set of candidate configurations."""

    k: float = DEFAULT_K
    default_rating: float = DEFAULT_RATING
    _ratings: dict[str, EloRating] = field(default_factory=dict)
    _updates: list[RatingUpdate] = field(default_factory=list)

    def _get_or_create(self, name: str) -> EloRating:
        if name not in self._ratings:
            self._ratings[name] = EloRating(
                config_name=name, rating=self.default_rating
            )
        return self._ratings[name]

    def record_match(
        self,
        *,
        match: ArenaMatch,
        outcome: MatchOutcome,
    ) -> RatingUpdate:
        if match.config_a == match.config_b:
            raise ValueError(
                f"match configs must differ; got {match.config_a!r} twice"
            )
        a = self._get_or_create(match.config_a)
        b = self._get_or_create(match.config_b)
        before_a, before_b = a.rating, b.rating
        new_a, new_b = update_elo(
            rating_a=a.rating, rating_b=b.rating, outcome=outcome, k=self.k
        )
        a.rating, b.rating = new_a, new_b
        if outcome == "a_wins":
            a.wins += 1
            b.losses += 1
        elif outcome == "b_wins":
            b.wins += 1
            a.losses += 1
        else:
            a.draws += 1
            b.draws += 1
        rating_update = RatingUpdate(
            match=match,
            outcome=outcome,
            rating_a_before=before_a,
            rating_a_after=a.rating,
            rating_b_before=before_b,
            rating_b_after=b.rating,
        )
        self._updates.append(rating_update)
        return rating_update

    def run_round_robin(
        self,
        *,
        configs: Sequence[str],
        tasks: Sequence[str],
        judge: Callable[[str, str, str], MatchOutcome],
    ) -> ArenaReport:
        """Play every pair on every task once; collect updates."""
        for i, a_name in enumerate(configs):
            for b_name in configs[i + 1:]:
                for task in tasks:
                    outcome = judge(a_name, b_name, task)
                    self.record_match(
                        match=ArenaMatch(
                            config_a=a_name, config_b=b_name, task_id=task
                        ),
                        outcome=outcome,
                    )
        return self.report()

    def report(self) -> ArenaReport:
        return ArenaReport(
            ratings=tuple(self._ratings.values()),
            updates=tuple(self._updates),
        )
