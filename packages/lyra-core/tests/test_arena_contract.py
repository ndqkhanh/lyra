"""Wave-F Task 12 — harness arena contract."""
from __future__ import annotations

import pytest

from lyra_core.arena import (
    Arena,
    ArenaMatch,
    expected_score,
    update_elo,
)


# ---- primitives ----------------------------------------------------


def test_expected_score_is_symmetric() -> None:
    ea = expected_score(1500, 1200)
    eb = expected_score(1200, 1500)
    assert ea + eb == pytest.approx(1.0)


def test_expected_score_is_monotone_in_rating_gap() -> None:
    low_gap = expected_score(1200, 1250)
    big_gap = expected_score(1200, 1400)
    assert low_gap > big_gap


def test_update_elo_winner_gains_loser_drops() -> None:
    new_a, new_b = update_elo(rating_a=1200, rating_b=1200, outcome="a_wins")
    assert new_a > 1200
    assert new_b < 1200
    assert pytest.approx(new_a + new_b) == 2400


def test_update_elo_draw_moves_towards_expectation() -> None:
    new_a, new_b = update_elo(rating_a=1400, rating_b=1200, outcome="draw")
    # Higher-rated player loses rating in a draw (they were expected to win).
    assert new_a < 1400
    assert new_b > 1200


def test_update_elo_rejects_bad_outcome() -> None:
    with pytest.raises(ValueError):
        update_elo(rating_a=1200, rating_b=1200, outcome="both_lose")


def test_update_elo_rejects_non_positive_k() -> None:
    with pytest.raises(ValueError):
        update_elo(rating_a=1200, rating_b=1200, outcome="draw", k=0)


# ---- arena --------------------------------------------------------


def test_record_match_creates_ratings_on_demand() -> None:
    arena = Arena()
    update = arena.record_match(
        match=ArenaMatch(config_a="alpha", config_b="beta", task_id="t1"),
        outcome="a_wins",
    )
    assert update.rating_a_before == 1200.0
    assert update.rating_a_after > update.rating_a_before
    assert update.rating_b_after < update.rating_b_before


def test_self_match_is_rejected() -> None:
    arena = Arena()
    with pytest.raises(ValueError):
        arena.record_match(
            match=ArenaMatch(config_a="alpha", config_b="alpha", task_id="t1"),
            outcome="draw",
        )


def test_round_robin_plays_every_pair_per_task() -> None:
    outcomes = [
        ("alpha", "beta", "a_wins"),
        ("alpha", "gamma", "a_wins"),
        ("beta", "gamma", "b_wins"),
    ]

    def judge(a, b, task):
        for x, y, o in outcomes:
            if (a, b) == (x, y):
                return o
        return "draw"

    arena = Arena()
    report = arena.run_round_robin(
        configs=["alpha", "beta", "gamma"],
        tasks=["t1"],
        judge=judge,
    )
    # 3 pairs * 1 task = 3 matches.
    assert len(report.updates) == 3
    # alpha has the most wins; gamma has 2.
    leaderboard = report.leaderboard()
    names = [r.config_name for r in leaderboard]
    assert names[0] == "alpha"


def test_report_serialises() -> None:
    arena = Arena()
    arena.record_match(
        match=ArenaMatch(config_a="alpha", config_b="beta", task_id="t1"),
        outcome="draw",
    )
    data = arena.report().to_dict()
    assert "leaderboard" in data and isinstance(data["leaderboard"], list)
    assert "updates" in data and len(data["updates"]) == 1


def test_win_loss_counters_increment() -> None:
    arena = Arena()
    arena.record_match(
        match=ArenaMatch(config_a="alpha", config_b="beta", task_id="t1"),
        outcome="a_wins",
    )
    arena.record_match(
        match=ArenaMatch(config_a="alpha", config_b="beta", task_id="t2"),
        outcome="b_wins",
    )
    arena.record_match(
        match=ArenaMatch(config_a="alpha", config_b="beta", task_id="t3"),
        outcome="draw",
    )
    ratings = {r.config_name: r for r in arena.report().ratings}
    assert ratings["alpha"].wins == 1
    assert ratings["alpha"].losses == 1
    assert ratings["alpha"].draws == 1
    assert ratings["beta"].wins == 1
    assert ratings["beta"].losses == 1
    assert ratings["beta"].draws == 1
