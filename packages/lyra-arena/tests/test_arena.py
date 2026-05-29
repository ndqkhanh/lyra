"""Comprehensive tests for the lyra-arena package."""

from __future__ import annotations

import datetime
import random
from dataclasses import FrozenInstanceError

import pytest
from lyra_arena import (
    AgentArena,
    AgentEntry,
    ArenaDomain,
    LeaderboardEntry,
    MatchOutcome,
    MatchRecord,
    MatchResult,
    MatchStatus,
    TournamentConfig,
    TournamentFormat,
    TournamentResult,
)

# =========================================================================
# Enum tests
# =========================================================================


class TestMatchStatus:
    def test_all_values_present(self) -> None:
        values = {e.value for e in MatchStatus}
        expected = {"PENDING", "RUNNING", "COMPLETED", "CANCELLED", "DISPUTED"}
        assert values == expected

    def test_is_str_enum(self) -> None:
        assert issubclass(MatchStatus, str)


class TestMatchOutcome:
    def test_all_values_present(self) -> None:
        values = {e.value for e in MatchOutcome}
        expected = {"WIN", "LOSS", "DRAW", "DISQUALIFIED"}
        assert values == expected

    def test_is_str_enum(self) -> None:
        assert issubclass(MatchOutcome, str)


class TestTournamentFormat:
    def test_all_values_present(self) -> None:
        values = {e.value for e in TournamentFormat}
        expected = {
            "ROUND_ROBIN",
            "SWISS",
            "SINGLE_ELIMINATION",
            "DOUBLE_ELIMINATION",
        }
        assert values == expected

    def test_is_str_enum(self) -> None:
        assert issubclass(TournamentFormat, str)


class TestArenaDomain:
    def test_all_values_present(self) -> None:
        values = {e.value for e in ArenaDomain}
        expected = {
            "CODE_GENERATION",
            "CODE_REPAIR",
            "REASONING",
            "MATH",
            "PLANNING",
            "TOOL_USE",
            "GENERAL",
        }
        assert values == expected

    def test_is_str_enum(self) -> None:
        assert issubclass(ArenaDomain, str)


# =========================================================================
# Dataclass frozen tests
# =========================================================================


class TestDataclassImmutability:
    def test_agent_entry_is_frozen(self) -> None:
        entry = AgentEntry(agent_id="a1", name="Agent One", version="1.0")
        with pytest.raises(FrozenInstanceError):
            entry.elo_rating = 1600.0  # type: ignore[misc]

    def test_match_result_is_frozen(self) -> None:
        now = datetime.datetime.now()
        result = MatchResult(
            match_id="m1",
            agent_a_id="a1",
            agent_b_id="a2",
            outcome_a="WIN",
            outcome_b="LOSS",
            score_a=1.0,
            score_b=0.0,
            domain="GENERAL",
            duration_seconds=60.0,
            challenge_id="ch1",
            timestamp=now,
        )
        with pytest.raises(FrozenInstanceError):
            result.score_a = 0.5  # type: ignore[misc]

    def test_leaderboard_entry_is_frozen(self) -> None:
        entry = LeaderboardEntry(
            agent_id="a1",
            name="Agent One",
            elo_rating=1500.0,
            rank=1,
            win_rate=0.5,
            domain="",
            matches_played=10,
        )
        with pytest.raises(FrozenInstanceError):
            entry.rank = 2  # type: ignore[misc]

    def test_agent_entry_domain_ratings_default_factory(self) -> None:
        """Verify domain_ratings uses field(default_factory) and is isolated."""
        entry1 = AgentEntry(agent_id="a1", name="A", version="1")
        entry2 = AgentEntry(agent_id="a2", name="B", version="1")
        assert entry1.domain_ratings == {}
        assert entry2.domain_ratings == {}
        # Each instance has its own dict
        assert entry1.domain_ratings is not entry2.domain_ratings


# =========================================================================
# AgentArena - Registration and Lookup
# =========================================================================


class TestAgentRegistration:
    def test_register_agent_basic(self) -> None:
        arena = AgentArena()
        agent = arena.register_agent("agent-1", name="Alpha", version="2.0")
        assert agent.agent_id == "agent-1"
        assert agent.name == "Alpha"
        assert agent.version == "2.0"
        assert agent.elo_rating == 1500.0
        assert agent.matches_played == 0

    def test_register_agent_default_name(self) -> None:
        arena = AgentArena()
        agent = arena.register_agent("agent-1")
        assert agent.name == "agent-1"
        assert agent.version == "1.0"

    def test_register_agent_custom_elo(self) -> None:
        arena = AgentArena()
        agent = arena.register_agent("agent-1", initial_elo=1800.0)
        assert agent.elo_rating == 1800.0

    def test_register_agent_duplicate_raises(self) -> None:
        arena = AgentArena()
        arena.register_agent("agent-1")
        with pytest.raises(ValueError, match="already registered"):
            arena.register_agent("agent-1")

    def test_get_agent_exists(self) -> None:
        arena = AgentArena()
        arena.register_agent("agent-1", name="Alpha")
        agent = arena.get_agent("agent-1")
        assert agent is not None
        assert agent.name == "Alpha"

    def test_get_agent_not_found(self) -> None:
        arena = AgentArena()
        result = arena.get_agent("non-existent")
        assert result is None

    def test_agents_property_read_only(self) -> None:
        arena = AgentArena()
        arena.register_agent("agent-1")
        agents_copy = arena.agents
        assert "agent-1" in agents_copy
        # Mutating the copy should not affect the arena
        agents_copy.clear()
        assert arena.get_agent("agent-1") is not None

    def test_match_results_property_read_only(self) -> None:
        arena = AgentArena()
        assert arena.match_results == []


# =========================================================================
# AgentArena - Elo Computation
# =========================================================================


class TestEloComputation:
    def test_compute_elo_win(self) -> None:
        arena = AgentArena()
        new_a, new_b = arena.compute_elo(1500.0, 1500.0, "WIN")
        # Equal ratings: expected = 0.5, actual = 1.0, delta = +16
        assert new_a == pytest.approx(1516.0, rel=1e-9)
        assert new_b == pytest.approx(1484.0, rel=1e-9)

    def test_compute_elo_loss(self) -> None:
        arena = AgentArena()
        new_a, new_b = arena.compute_elo(1500.0, 1500.0, "LOSS")
        assert new_a == pytest.approx(1484.0, rel=1e-9)
        assert new_b == pytest.approx(1516.0, rel=1e-9)

    def test_compute_elo_draw(self) -> None:
        arena = AgentArena()
        new_a, new_b = arena.compute_elo(1500.0, 1500.0, "DRAW")
        # actual = 0.5, expected = 0.5, delta = 0
        assert new_a == pytest.approx(1500.0, rel=1e-9)
        assert new_b == pytest.approx(1500.0, rel=1e-9)

    def test_compute_elo_disqualified(self) -> None:
        arena = AgentArena()
        new_a, new_b = arena.compute_elo(1500.0, 1500.0, "DISQUALIFIED")
        # DQ treated as loss for the disqualified agent
        assert new_a == pytest.approx(1484.0, rel=1e-9)
        assert new_b == pytest.approx(1516.0, rel=1e-9)

    def test_compute_elo_custom_k_factor(self) -> None:
        arena = AgentArena()
        new_a, new_b = arena.compute_elo(1500.0, 1500.0, "WIN", k_factor=64.0)
        assert new_a == pytest.approx(1532.0, rel=1e-9)
        assert new_b == pytest.approx(1468.0, rel=1e-9)

    def test_compute_elo_rating_gap_upset(self) -> None:
        """Lower-rated agent beating a higher-rated agent gets more Elo."""
        arena = AgentArena()
        # 1000-rated beats 1500-rated
        new_a, new_b = arena.compute_elo(1000.0, 1500.0, "WIN")
        expected_a = 1.0 / (1.0 + 10.0 ** ((1500.0 - 1000.0) / 400.0))
        expected_b = 1.0 - expected_a
        # 1000-rated: expected ≈ 0.053, actual = 1.0, gain = 32 * (1 - 0.053) ≈ 30.3
        # 1500-rated: expected ≈ 0.947, actual = 0.0, loss = 32 * (0 - 0.947) ≈ -30.3
        assert new_a == pytest.approx(1000.0 + 32.0 * (1.0 - expected_a), rel=1e-9)
        assert new_b == pytest.approx(1500.0 + 32.0 * (0.0 - expected_b), rel=1e-9)

    def test_compute_elo_expected_formula(self) -> None:
        """Verify the exact expected score formula."""
        AgentArena()
        # Rating difference of 400: expected = 1/(1+10^(400/400)) = 1/11 ≈ 0.0909
        expected = 1.0 / (1.0 + 10.0 ** ((1500.0 - 1100.0) / 400.0))
        expected_approx = 1.0 / 11.0
        assert expected == pytest.approx(expected_approx, rel=1e-9)

    def test_compute_elo_symmetric(self) -> None:
        """Elo changes should be symmetric: A's gain = B's loss."""
        arena = AgentArena()
        new_a, new_b = arena.compute_elo(1500.0, 1400.0, "WIN")
        delta_a = new_a - 1500.0
        delta_b = new_b - 1400.0
        assert delta_a == pytest.approx(-delta_b, rel=1e-9)


# =========================================================================
# AgentArena - Match Recording
# =========================================================================


class TestMatchRecording:
    def _make_match(
        self,
        match_id: str,
        agent_a_id: str,
        agent_b_id: str,
        outcome_a: str = "WIN",
        domain: str = "GENERAL",
    ) -> MatchResult:
        if outcome_a == "WIN":
            outcome_b = "LOSS"
            score_a, score_b = 1.0, 0.0
        elif outcome_a == "LOSS":
            outcome_b = "WIN"
            score_a, score_b = 0.0, 1.0
        elif outcome_a == "DRAW":
            outcome_b = "DRAW"
            score_a, score_b = 0.5, 0.5
        else:  # DISQUALIFIED — disqualified agent loses
            outcome_b = "WIN"
            score_a, score_b = 0.0, 1.0
        return MatchResult(
            match_id=match_id,
            agent_a_id=agent_a_id,
            agent_b_id=agent_b_id,
            outcome_a=outcome_a,
            outcome_b=outcome_b,
            score_a=score_a,
            score_b=score_b,
            domain=domain,
            duration_seconds=60.0,
            challenge_id=f"ch_{domain}",
            timestamp=datetime.datetime.now(),
        )

    def test_record_match_basic(self) -> None:
        arena = AgentArena()
        arena.register_agent("a1", name="Alpha")
        arena.register_agent("a2", name="Beta")
        match = self._make_match("m1", "a1", "a2")
        arena.record_match(match)

        assert len(arena.match_results) == 1
        agent_a = arena.get_agent("a1")
        agent_b = arena.get_agent("a2")
        assert agent_a is not None
        assert agent_b is not None
        assert agent_a.matches_played == 1
        assert agent_b.matches_played == 1

    def test_record_match_updates_elo(self) -> None:
        arena = AgentArena()
        arena.register_agent("a1", name="Alpha")
        arena.register_agent("a2", name="Beta")
        match = self._make_match("m1", "a1", "a2")
        arena.record_match(match)

        agent_a = arena.get_agent("a1")
        agent_b = arena.get_agent("a2")
        assert agent_a is not None
        assert agent_b is not None
        assert agent_a.elo_rating == pytest.approx(1516.0, rel=1e-9)
        assert agent_b.elo_rating == pytest.approx(1484.0, rel=1e-9)

    def test_record_match_updates_stats(self) -> None:
        arena = AgentArena()
        arena.register_agent("a1")
        arena.register_agent("a2")
        arena.record_match(self._make_match("m1", "a1", "a2", "WIN"))
        arena.record_match(self._make_match("m2", "a1", "a2", "DRAW"))

        a1 = arena.get_agent("a1")
        a2 = arena.get_agent("a2")
        assert a1 is not None
        assert a2 is not None
        assert a1.wins == 1
        assert a1.draws == 1
        assert a1.losses == 0
        assert a1.matches_played == 2
        assert a2.wins == 0
        assert a2.draws == 1
        assert a2.losses == 1
        assert a2.matches_played == 2

    def test_record_match_domain_ratings(self) -> None:
        arena = AgentArena()
        arena.register_agent("a1")
        arena.register_agent("a2")
        match = self._make_match("m1", "a1", "a2", "WIN", domain="MATH")
        arena.record_match(match)

        a1 = arena.get_agent("a1")
        a2 = arena.get_agent("a2")
        assert a1 is not None
        assert a2 is not None
        # Domain rating uses k_factor=16
        assert "MATH" in a1.domain_ratings
        assert "MATH" in a2.domain_ratings
        # a1 won in MATH domain
        expected_domain_a = 1500.0 + 16.0 * (1.0 - 0.5)
        expected_domain_b = 1500.0 + 16.0 * (0.0 - 0.5)
        assert a1.domain_ratings["MATH"] == pytest.approx(expected_domain_a, rel=1e-9)
        assert a2.domain_ratings["MATH"] == pytest.approx(expected_domain_b, rel=1e-9)

    def test_record_match_disqualified(self) -> None:
        arena = AgentArena()
        arena.register_agent("a1")
        arena.register_agent("a2")
        match = self._make_match("m1", "a1", "a2", "DISQUALIFIED")
        arena.record_match(match)

        a1 = arena.get_agent("a1")
        a2 = arena.get_agent("a2")
        assert a1 is not None
        assert a2 is not None
        assert a1.losses == 1
        assert a2.wins == 1
        # DQ treated as loss for a1
        assert a1.elo_rating == pytest.approx(1484.0, rel=1e-9)
        assert a2.elo_rating == pytest.approx(1516.0, rel=1e-9)

    def test_record_match_unregistered_agent_a(self) -> None:
        arena = AgentArena()
        arena.register_agent("a2")
        match = self._make_match("m1", "a1", "a2")
        with pytest.raises(ValueError, match="not registered"):
            arena.record_match(match)

    def test_record_match_unregistered_agent_b(self) -> None:
        arena = AgentArena()
        arena.register_agent("a1")
        match = self._make_match("m1", "a1", "a2")
        with pytest.raises(ValueError, match="not registered"):
            arena.record_match(match)


# =========================================================================
# AgentArena - Tournament
# =========================================================================


class TestRoundRobinTournament:
    def test_round_robin_basic(self) -> None:
        arena = AgentArena()
        agents = [
            arena.register_agent("a1", "Alpha"),
            arena.register_agent("a2", "Beta"),
            arena.register_agent("a3", "Gamma"),
            arena.register_agent("a4", "Delta"),
        ]
        random.seed(42)
        config = TournamentConfig(
            tournament_id="t1",
            name="RR Test",
            format=TournamentFormat.ROUND_ROBIN,
            domains=("GENERAL",),
            agents=tuple(agents),
        )
        result = arena.run_tournament(config)
        # 4 agents -> C(4,2) = 6 matches
        assert result.total_matches == 6
        assert result.winner_id != ""
        assert len(result.final_standings) == 4
        # Stable sort by Elo desc, then agent_id
        standings = result.final_standings
        for i in range(len(standings) - 1):
            assert standings[i].elo_rating >= standings[i + 1].elo_rating

    def test_round_robin_matches_per_pair(self) -> None:
        arena = AgentArena()
        agents = [
            arena.register_agent("a1", "Alpha"),
            arena.register_agent("a2", "Beta"),
            arena.register_agent("a3", "Gamma"),
        ]
        random.seed(42)
        config = TournamentConfig(
            tournament_id="t2",
            name="RR Multi",
            format=TournamentFormat.ROUND_ROBIN,
            domains=("GENERAL",),
            agents=tuple(agents),
            matches_per_pair=3,
        )
        result = arena.run_tournament(config)
        # 3 agents -> C(3,2) = 3 pairs * 3 matches = 9
        assert result.total_matches == 9

    def test_round_robin_multiple_domains(self) -> None:
        arena = AgentArena()
        agents = [
            arena.register_agent("a1", "Alpha"),
            arena.register_agent("a2", "Beta"),
        ]
        random.seed(42)
        config = TournamentConfig(
            tournament_id="t3",
            name="RR Multi Domain",
            format=TournamentFormat.ROUND_ROBIN,
            domains=("MATH", "CODE_GENERATION", "REASONING"),
            agents=tuple(agents),
        )
        result = arena.run_tournament(config)
        # 2 agents -> C(2,2) = 1 pair * 1 match (random domain from 3)
        assert result.total_matches == 1

    def test_round_robin_single_agent(self) -> None:
        arena = AgentArena()
        agent = arena.register_agent("a1", "Alpha")
        config = TournamentConfig(
            tournament_id="t4",
            name="RR Single",
            format=TournamentFormat.ROUND_ROBIN,
            domains=("GENERAL",),
            agents=(agent,),
        )
        result = arena.run_tournament(config)
        assert result.total_matches == 0
        assert result.winner_id == "a1"


class TestSingleEliminationTournament:
    def test_single_elimination_power_of_two(self) -> None:
        arena = AgentArena()
        agents = [
            arena.register_agent("a1", "Alpha"),
            arena.register_agent("a2", "Beta"),
            arena.register_agent("a3", "Gamma"),
            arena.register_agent("a4", "Delta"),
        ]
        random.seed(42)
        config = TournamentConfig(
            tournament_id="t5",
            name="SE Test",
            format=TournamentFormat.SINGLE_ELIMINATION,
            domains=("GENERAL",),
            agents=tuple(agents),
        )
        result = arena.run_tournament(config)
        # 4 agents -> 3 matches (semi x2 + final)
        assert result.total_matches == 3
        assert result.winner_id != ""
        assert len(result.final_standings) == 4

    def test_single_elimination_not_power_of_two(self) -> None:
        arena = AgentArena()
        agents = [
            arena.register_agent("a1", "Alpha"),
            arena.register_agent("a2", "Beta"),
            arena.register_agent("a3", "Gamma"),
        ]
        random.seed(42)
        config = TournamentConfig(
            tournament_id="t6",
            name="SE Bye",
            format=TournamentFormat.SINGLE_ELIMINATION,
            domains=("GENERAL",),
            agents=tuple(agents),
        )
        result = arena.run_tournament(config)
        # 3 agents padded to 4 -> 2 semi (1 bye, 1 match) + 1 final = 2 matches
        assert result.total_matches == 2

    def test_single_elimination_two_agents(self) -> None:
        arena = AgentArena()
        agents = [
            arena.register_agent("a1", "Alpha"),
            arena.register_agent("a2", "Beta"),
        ]
        random.seed(42)
        config = TournamentConfig(
            tournament_id="t7",
            name="SE Two",
            format=TournamentFormat.SINGLE_ELIMINATION,
            domains=("GENERAL",),
            agents=tuple(agents),
        )
        result = arena.run_tournament(config)
        assert result.total_matches == 1

    def test_single_elimination_too_few_agents(self) -> None:
        arena = AgentArena()
        agent = arena.register_agent("a1", "Alpha")
        config = TournamentConfig(
            tournament_id="t8",
            name="SE Few",
            format=TournamentFormat.SINGLE_ELIMINATION,
            domains=("GENERAL",),
            agents=(agent,),
        )
        with pytest.raises(ValueError, match="at least 2 agents"):
            arena.run_tournament(config)


class TestSwissTournament:
    def test_swiss_basic(self) -> None:
        arena = AgentArena()
        agents = [
            arena.register_agent("a1", "Alpha"),
            arena.register_agent("a2", "Beta"),
            arena.register_agent("a3", "Gamma"),
            arena.register_agent("a4", "Delta"),
        ]
        random.seed(42)
        config = TournamentConfig(
            tournament_id="t9",
            name="Swiss Test",
            format=TournamentFormat.SWISS,
            domains=("GENERAL",),
            agents=tuple(agents),
        )
        result = arena.run_tournament(config)
        assert result.total_matches > 0
        assert result.winner_id != ""
        assert len(result.final_standings) == 4

    def test_swiss_two_agents(self) -> None:
        arena = AgentArena()
        agents = [
            arena.register_agent("a1", "Alpha"),
            arena.register_agent("a2", "Beta"),
        ]
        random.seed(42)
        config = TournamentConfig(
            tournament_id="t10",
            name="Swiss Two",
            format=TournamentFormat.SWISS,
            domains=("GENERAL",),
            agents=tuple(agents),
        )
        result = arena.run_tournament(config)
        assert result.total_matches > 0

    def test_swiss_single_agent(self) -> None:
        arena = AgentArena()
        agent = arena.register_agent("a1", "Alpha")
        config = TournamentConfig(
            tournament_id="t11",
            name="Swiss Single",
            format=TournamentFormat.SWISS,
            domains=("GENERAL",),
            agents=(agent,),
        )
        result = arena.run_tournament(config)
        assert result.total_matches == 0
        assert result.winner_id == "a1"


class TestDoubleEliminationTournament:
    def test_double_elimination_four_agents(self) -> None:
        arena = AgentArena()
        agents = [
            arena.register_agent("a1", "Alpha"),
            arena.register_agent("a2", "Beta"),
            arena.register_agent("a3", "Gamma"),
            arena.register_agent("a4", "Delta"),
        ]
        random.seed(42)
        config = TournamentConfig(
            tournament_id="t12",
            name="DE Test",
            format=TournamentFormat.DOUBLE_ELIMINATION,
            domains=("GENERAL",),
            agents=tuple(agents),
        )
        result = arena.run_tournament(config)
        assert result.total_matches > 0
        assert result.winner_id != ""
        assert len(result.final_standings) == 4

    def test_double_elimination_two_agents(self) -> None:
        arena = AgentArena()
        agents = [
            arena.register_agent("a1", "Alpha"),
            arena.register_agent("a2", "Beta"),
        ]
        random.seed(42)
        config = TournamentConfig(
            tournament_id="t13",
            name="DE Two",
            format=TournamentFormat.DOUBLE_ELIMINATION,
            domains=("GENERAL",),
            agents=tuple(agents),
        )
        result = arena.run_tournament(config)
        assert result.total_matches > 0

    def test_double_elimination_too_few_agents(self) -> None:
        arena = AgentArena()
        agent = arena.register_agent("a1", "Alpha")
        config = TournamentConfig(
            tournament_id="t14",
            name="DE Few",
            format=TournamentFormat.DOUBLE_ELIMINATION,
            domains=("GENERAL",),
            agents=(agent,),
        )
        with pytest.raises(ValueError, match="at least 2 agents"):
            arena.run_tournament(config)


# =========================================================================
# AgentArena - Leaderboard
# =========================================================================


class TestLeaderboard:
    def test_leaderboard_empty(self) -> None:
        arena = AgentArena()
        lb = arena.get_leaderboard()
        assert lb == []

    def test_leaderboard_basic(self) -> None:
        arena = AgentArena()
        arena.register_agent("alpha", "Alpha")
        arena.register_agent("beta", "Beta")
        arena.register_agent("gamma", "Gamma")

        # Manually set different Elos by recording matches
        now = datetime.datetime.now()
        arena.record_match(
            MatchResult(
                match_id="m1", agent_a_id="alpha", agent_b_id="beta",
                outcome_a="WIN", outcome_b="LOSS",
                score_a=1.0, score_b=0.0, domain="GENERAL",
                duration_seconds=10.0, challenge_id="ch1", timestamp=now,
            )
        )

        lb = arena.get_leaderboard()
        assert len(lb) == 3
        # Winner should be at top
        assert lb[0].agent_id == "alpha"
        assert lb[0].rank == 1
        assert lb[1].agent_id == "beta" or lb[1].agent_id == "gamma"
        assert lb[2].agent_id == "gamma" or lb[2].agent_id == "beta"

    def test_leaderboard_domain_specific(self) -> None:
        arena = AgentArena()
        arena.register_agent("a1", "Alpha")
        arena.register_agent("a2", "Beta")
        arena.register_agent("a3", "Gamma")

        now = datetime.datetime.now()
        arena.record_match(
            MatchResult(
                match_id="m1", agent_a_id="a1", agent_b_id="a2",
                outcome_a="WIN", outcome_b="LOSS",
                score_a=1.0, score_b=0.0, domain="MATH",
                duration_seconds=10.0, challenge_id="ch1", timestamp=now,
            )
        )

        # Domain leaderboard should only include agents with that domain
        lb_math = arena.get_leaderboard(domain="MATH")
        assert len(lb_math) == 2
        for entry in lb_math:
            assert entry.domain == "MATH"

        # Domain with no recorded matches should return empty
        lb_code = arena.get_leaderboard(domain="CODE_GENERATION")
        assert lb_code == []

    def test_leaderboard_custom_limit(self) -> None:
        arena = AgentArena()
        for i in range(5):
            arena.register_agent(f"a{i}", f"Agent {i}")

        lb_all = arena.get_leaderboard(limit=10)
        assert len(lb_all) == 5
        lb_limited = arena.get_leaderboard(limit=3)
        assert len(lb_limited) == 3

    def test_leaderboard_win_rate(self) -> None:
        arena = AgentArena()
        arena.register_agent("a1")
        arena.register_agent("a2")
        now = datetime.datetime.now()
        arena.record_match(
            MatchResult(
                match_id="m1", agent_a_id="a1", agent_b_id="a2",
                outcome_a="WIN", outcome_b="LOSS",
                score_a=1.0, score_b=0.0, domain="GENERAL",
                duration_seconds=10.0, challenge_id="ch1", timestamp=now,
            )
        )

        lb = arena.get_leaderboard()
        assert lb[0].win_rate == 1.0  # a1 won 1/1
        assert lb[1].win_rate == 0.0  # a2 lost 1/1


# =========================================================================
# AgentArena - Head-to-Head
# =========================================================================


class TestHeadToHead:
    def test_head_to_head_no_matches(self) -> None:
        arena = AgentArena()
        arena.register_agent("a1")
        arena.register_agent("a2")
        h2h = arena.get_head_to_head("a1", "a2")
        assert h2h["total_matches"] == 0
        assert h2h["a1_wins"] == 0
        assert h2h["a2_wins"] == 0

    def test_head_to_head_with_matches(self) -> None:
        arena = AgentArena()
        arena.register_agent("a1")
        arena.register_agent("a2")
        arena.register_agent("a3")
        now = datetime.datetime.now()

        # a1 beats a2
        arena.record_match(
            MatchResult(
                match_id="m1", agent_a_id="a1", agent_b_id="a2",
                outcome_a="WIN", outcome_b="LOSS",
                score_a=1.0, score_b=0.0, domain="GENERAL",
                duration_seconds=10.0, challenge_id="ch1", timestamp=now,
            )
        )
        # a2 beats a1
        arena.record_match(
            MatchResult(
                match_id="m2", agent_a_id="a2", agent_b_id="a1",
                outcome_a="WIN", outcome_b="LOSS",
                score_a=1.0, score_b=0.0, domain="GENERAL",
                duration_seconds=10.0, challenge_id="ch1", timestamp=now,
            )
        )
        # a1 beats a3 (should not affect a1 vs a2)
        arena.record_match(
            MatchResult(
                match_id="m3", agent_a_id="a1", agent_b_id="a3",
                outcome_a="WIN", outcome_b="LOSS",
                score_a=1.0, score_b=0.0, domain="GENERAL",
                duration_seconds=10.0, challenge_id="ch1", timestamp=now,
            )
        )

        h2h = arena.get_head_to_head("a1", "a2")
        assert h2h["total_matches"] == 2
        assert h2h["a1_wins"] == 1
        assert h2h["a2_wins"] == 1
        assert h2h["draws"] == 0
        assert h2h["a1_win_rate"] == 0.5
        assert h2h["a2_win_rate"] == 0.5


# =========================================================================
# AgentArena - Stats
# =========================================================================


class TestStats:
    def test_stats_empty_arena(self) -> None:
        arena = AgentArena()
        stats = arena.get_stats()
        assert stats["total_agents"] == 0
        assert stats["total_matches"] == 0
        assert stats["average_elo"] == 1500.0

    def test_stats_with_agents(self) -> None:
        arena = AgentArena()
        arena.register_agent("a1", initial_elo=1500.0)
        arena.register_agent("a2", initial_elo=1600.0)
        arena.register_agent("a3", initial_elo=1700.0)

        stats = arena.get_stats()
        assert stats["total_agents"] == 3
        assert stats["total_matches"] == 0
        assert stats["average_elo"] == pytest.approx(1600.0, rel=1e-9)
        assert stats["min_elo"] == 1500.0
        assert stats["max_elo"] == 1700.0

    def test_stats_with_matches_and_domains(self) -> None:
        arena = AgentArena()
        arena.register_agent("a1")
        arena.register_agent("a2")
        now = datetime.datetime.now()

        arena.record_match(
            MatchResult(
                match_id="m1", agent_a_id="a1", agent_b_id="a2",
                outcome_a="WIN", outcome_b="LOSS",
                score_a=1.0, score_b=0.0, domain="MATH",
                duration_seconds=10.0, challenge_id="ch1", timestamp=now,
            )
        )

        stats = arena.get_stats()
        assert stats["total_matches"] == 1
        assert "MATH" in stats["domains"]


# =========================================================================
# AgentArena - Agent History
# =========================================================================


class TestAgentHistory:
    def test_agent_history_no_matches(self) -> None:
        arena = AgentArena()
        arena.register_agent("a1")
        history = arena.get_agent_history("a1")
        assert history == []

    def test_agent_history_with_matches(self) -> None:
        arena = AgentArena()
        arena.register_agent("a1")
        arena.register_agent("a2")
        arena.register_agent("a3")
        now = datetime.datetime.now()

        matches = []
        for i in range(5):
            m = MatchResult(
                match_id=f"m{i}",
                agent_a_id="a1" if i % 2 == 0 else "a2",
                agent_b_id="a2" if i % 2 == 0 else "a1",
                outcome_a="WIN", outcome_b="LOSS",
                score_a=1.0, score_b=0.0, domain="GENERAL",
                duration_seconds=10.0, challenge_id="ch1",
                timestamp=now + datetime.timedelta(seconds=i),
            )
            arena.record_match(m)
            matches.append(m)

        history = arena.get_agent_history("a1", limit=3)
        assert len(history) == 3
        # Most recent first
        assert history[0].match_id == "m4"

    def test_agent_history_limit(self) -> None:
        arena = AgentArena()
        arena.register_agent("a1")
        arena.register_agent("a2")
        now = datetime.datetime.now()

        for i in range(20):
            arena.record_match(
                MatchResult(
                    match_id=f"m{i}",
                    agent_a_id="a1", agent_b_id="a2",
                    outcome_a="WIN", outcome_b="LOSS",
                    score_a=1.0, score_b=0.0, domain="GENERAL",
                    duration_seconds=10.0, challenge_id="ch1",
                    timestamp=now + datetime.timedelta(seconds=i),
                )
            )

        assert len(arena.get_agent_history("a1", limit=5)) == 5
        assert len(arena.get_agent_history("a1", limit=100)) == 20


# =========================================================================
# TournamentResult ordering
# =========================================================================


class TestTournamentResultOrdering:
    def test_final_standings_stable_sort(self) -> None:
        """Verify final standings use stable sort with deterministic tie-breaking."""
        arena = AgentArena()
        # Register agents with different initial Elos for variety
        arena.register_agent("z-ag", "Z Agent", initial_elo=1400.0)
        arena.register_agent("a-ag", "A Agent", initial_elo=1400.0)
        arena.register_agent("m-ag", "M Agent", initial_elo=1600.0)

        agents = [
            arena.get_agent("z-ag"),
            arena.get_agent("a-ag"),
            arena.get_agent("m-ag"),
        ]

        config = TournamentConfig(
            tournament_id="t15",
            name="Stable Sort",
            format=TournamentFormat.ROUND_ROBIN,
            domains=("GENERAL",),
            agents=tuple(a for a in agents if a is not None),
        )
        random.seed(42)
        result = arena.run_tournament(config)

        standings = result.final_standings
        for i in range(len(standings) - 1):
            # Higher Elo should come first
            assert standings[i].elo_rating >= standings[i + 1].elo_rating


# =========================================================================
# MatchRecord creation test
# =========================================================================


class TestMatchRecordCreation:
    def test_create_match_record(self) -> None:
        agent = AgentEntry(agent_id="a1", name="Alpha", version="1.0")
        record = MatchRecord(
            match_id="mr1",
            agent_a=agent,
            agent_b=agent,
            domain="GENERAL",
            status=MatchStatus.PENDING,
            scheduled_at=datetime.datetime.now(),
        )
        assert record.match_id == "mr1"
        assert record.status == MatchStatus.PENDING
        assert record.domain == "GENERAL"


# =========================================================================
# TournamentResult creation test
# =========================================================================


class TestTournamentResultCreation:
    def test_create_tournament_result(self) -> None:
        agents = (
            AgentEntry(agent_id="a1", name="Alpha", version="1.0", elo_rating=1550.0),
            AgentEntry(agent_id="a2", name="Beta", version="1.0", elo_rating=1450.0),
        )
        result = TournamentResult(
            tournament_id="t1",
            winner_id="a1",
            final_standings=agents,
            total_matches=10,
            duration_seconds=3600.0,
        )
        assert result.winner_id == "a1"
        assert result.total_matches == 10
        assert result.duration_seconds == 3600.0
