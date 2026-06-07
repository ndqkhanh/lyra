"""Agent Arena — competitive tournaments, Elo ratings, match-running, leaderboards."""

from __future__ import annotations

import datetime
import itertools
import logging
import math
import random
from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

__all__ = [
    "ArenaDomain",
    "AgentArena",
    "AgentEntry",
    "LeaderboardEntry",
    "MatchOutcome",
    "MatchRecord",
    "MatchResult",
    "MatchStatus",
    "TournamentConfig",
    "TournamentFormat",
    "TournamentResult",
]


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class MatchStatus(str, Enum):
    """Status of a match in the arena."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    DISPUTED = "DISPUTED"


class MatchOutcome(str, Enum):
    """Outcome of a match for a single agent."""

    WIN = "WIN"
    LOSS = "LOSS"
    DRAW = "DRAW"
    DISQUALIFIED = "DISQUALIFIED"


class TournamentFormat(str, Enum):
    """Format of a tournament in the arena."""

    ROUND_ROBIN = "ROUND_ROBIN"
    SWISS = "SWISS"
    SINGLE_ELIMINATION = "SINGLE_ELIMINATION"
    DOUBLE_ELIMINATION = "DOUBLE_ELIMINATION"


class ArenaDomain(str, Enum):
    """Domain for agent competition."""

    CODE_GENERATION = "CODE_GENERATION"
    CODE_REPAIR = "CODE_REPAIR"
    REASONING = "REASONING"
    MATH = "MATH"
    PLANNING = "PLANNING"
    TOOL_USE = "TOOL_USE"
    GENERAL = "GENERAL"


# ---------------------------------------------------------------------------
# Frozen dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AgentEntry:
    """An agent registered in the arena.

    Parameters
    ----------
    agent_id : str
        Unique identifier for the agent.
    name : str
        Human-readable name of the agent.
    version : str
        Version string for the agent.
    elo_rating : float
        Current global Elo rating. Defaults to 1500.0.
    matches_played : int
        Total number of matches played.
    wins : int
        Number of wins.
    losses : int
        Number of losses.
    draws : int
        Number of draws.
    domain_ratings : dict[str, float]
        Domain-specific Elo ratings keyed by domain name.
    """

    agent_id: str
    name: str
    version: str
    elo_rating: float = 1500.0
    matches_played: int = 0
    wins: int = 0
    losses: int = 0
    draws: int = 0
    domain_ratings: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class MatchResult:
    """Result of a completed match between two agents.

    Parameters
    ----------
    match_id : str
        Unique identifier for the match.
    agent_a_id : str
        Identifier of agent A.
    agent_b_id : str
        Identifier of agent B.
    outcome_a : str
        Outcome for agent A (WIN, LOSS, DRAW, DISQUALIFIED).
    outcome_b : str
        Outcome for agent B.
    score_a : float
        Score achieved by agent A.
    score_b : float
        Score achieved by agent B.
    domain : str
        Domain in which the match was played.
    duration_seconds : float
        Duration of the match in seconds.
    challenge_id : str
        Identifier of the challenge used.
    timestamp : datetime.datetime
        When the match was completed.
    """

    match_id: str
    agent_a_id: str
    agent_b_id: str
    outcome_a: str
    outcome_b: str
    score_a: float
    score_b: float
    domain: str
    duration_seconds: float
    challenge_id: str
    timestamp: datetime.datetime


@dataclass(frozen=True)
class MatchRecord:
    """A scheduled or completed match record in the arena.

    Parameters
    ----------
    match_id : str
        Unique identifier for the match.
    agent_a : AgentEntry
        Agent A participating in the match.
    agent_b : AgentEntry
        Agent B participating in the match.
    domain : str
        Domain for the match.
    status : MatchStatus
        Current status of the match.
    scheduled_at : datetime.datetime
        When the match is scheduled.
    """

    match_id: str
    agent_a: AgentEntry
    agent_b: AgentEntry
    domain: str
    status: MatchStatus
    scheduled_at: datetime.datetime


@dataclass(frozen=True)
class TournamentConfig:
    """Configuration for a tournament.

    Parameters
    ----------
    tournament_id : str
        Unique identifier for the tournament.
    name : str
        Human-readable name for the tournament.
    format : TournamentFormat
        Tournament format to use.
    domains : tuple[str, ...]
        Domains to include in the tournament.
    agents : tuple[AgentEntry, ...]
        Agents participating in the tournament.
    matches_per_pair : int
        Number of matches per pair (for round-robin). Defaults to 1.
    k_factor : float
        K-factor for Elo rating updates. Defaults to 32.0.
    """

    tournament_id: str
    name: str
    format: TournamentFormat
    domains: tuple[str, ...]
    agents: tuple[AgentEntry, ...]
    matches_per_pair: int = 1
    k_factor: float = 32.0


@dataclass(frozen=True)
class TournamentResult:
    """Result of a completed tournament.

    Parameters
    ----------
    tournament_id : str
        Identifier of the tournament.
    winner_id : str
        Identifier of the winning agent.
    final_standings : tuple[AgentEntry, ...]
        Final standings sorted by Elo rating (descending).
    total_matches : int
        Total number of matches played.
    duration_seconds : float
        Duration of the tournament in seconds.
    """

    tournament_id: str
    winner_id: str
    final_standings: tuple[AgentEntry, ...]
    total_matches: int
    duration_seconds: float


@dataclass(frozen=True)
class LeaderboardEntry:
    """An entry in the arena leaderboard.

    Parameters
    ----------
    agent_id : str
        Identifier of the agent.
    name : str
        Name of the agent.
    elo_rating : float
        Current Elo rating.
    rank : int
        Rank position on the leaderboard.
    win_rate : float
        Win rate (wins / total matches).
    domain : str
        Domain for this leaderboard entry. Empty string for global.
    matches_played : int
        Total number of matches played.
    """

    agent_id: str
    name: str
    elo_rating: float
    rank: int
    win_rate: float
    domain: str
    matches_played: int


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class AgentArena:
    """Engine for competitive agent tournaments with Elo ratings.

    The AgentArena manages agent registrations, records match results,
    computes Elo rating updates, runs tournaments in various formats,
    and maintains leaderboards and statistics.
    """

    def __init__(self) -> None:
        self._agents: dict[str, AgentEntry] = {}
        self._match_results: list[MatchResult] = []
        self._match_records: list[MatchRecord] = []

    # -- Agent management ---------------------------------------------------

    def register_agent(
        self,
        agent_id: str,
        name: str = "",
        version: str = "1.0",
        initial_elo: float = 1500.0,
    ) -> AgentEntry:
        """Register a new agent in the arena.

        Parameters
        ----------
        agent_id : str
            Unique identifier for the agent.
        name : str, optional
            Human-readable name. Defaults to agent_id if empty.
        version : str, optional
            Version string. Defaults to "1.0".
        initial_elo : float, optional
            Initial Elo rating. Defaults to 1500.0.

        Returns
        -------
        AgentEntry
            The newly registered agent entry.

        Raises
        ------
        ValueError
            If an agent with the same agent_id is already registered.
        """
        if agent_id in self._agents:
            raise ValueError(f"Agent '{agent_id}' is already registered.")
        agent = AgentEntry(
            agent_id=agent_id,
            name=name or agent_id,
            version=version,
            elo_rating=initial_elo,
        )
        self._agents[agent_id] = agent
        logger.info("Registered agent '%s' with Elo %.1f", agent_id, initial_elo)
        return agent

    def get_agent(self, agent_id: str) -> AgentEntry | None:
        """Look up an agent by ID.

        Parameters
        ----------
        agent_id : str
            The agent identifier.

        Returns
        -------
        AgentEntry | None
            The agent entry, or None if not found.
        """
        return self._agents.get(agent_id)

    # -- Elo computation ----------------------------------------------------

    def compute_elo(
        self,
        rating_a: float,
        rating_b: float,
        outcome_a: str,
        k_factor: float = 32.0,
    ) -> tuple[float, float]:
        """Compute new Elo ratings for two agents after a match.

        Uses the standard Elo formula:
        - Expected score: E = 1 / (1 + 10^((R_b - R_a) / 400))
        - New rating: R' = R + K * (S - E)
        - WIN -> S = 1.0, LOSS -> S = 0.0, DRAW -> S = 0.5

        Parameters
        ----------
        rating_a : float
            Current rating of agent A.
        rating_b : float
            Current rating of agent B.
        outcome_a : str
            Outcome for agent A (WIN, LOSS, DRAW, DISQUALIFIED).
        k_factor : float, optional
            K-factor for Elo adjustment. Defaults to 32.0.

        Returns
        -------
        tuple[float, float]
            New ratings for (agent A, agent B).
        """
        expected_a = 1.0 / (1.0 + 10.0 ** ((rating_b - rating_a) / 400.0))
        expected_b = 1.0 - expected_a

        if outcome_a == "WIN":
            actual_a, actual_b = 1.0, 0.0
        elif outcome_a == "LOSS":
            actual_a, actual_b = 0.0, 1.0
        elif outcome_a == "DRAW":
            actual_a, actual_b = 0.5, 0.5
        elif outcome_a == "DISQUALIFIED":
            actual_a, actual_b = 0.0, 1.0
        else:
            actual_a, actual_b = 0.0, 0.0

        new_a = rating_a + k_factor * (actual_a - expected_a)
        new_b = rating_b + k_factor * (actual_b - expected_b)
        return (new_a, new_b)

    # -- Match recording ----------------------------------------------------

    def record_match(self, match: MatchResult) -> None:
        """Record a completed match and update Elo ratings for both agents.

        Both global and domain-specific Elo ratings are updated. Domain
        ratings use a reduced K-factor (K/2).

        Parameters
        ----------
        match : MatchResult
            The match result to record.

        Raises
        ------
        ValueError
            If either agent is not registered.
        """
        agent_a = self._agents.get(match.agent_a_id)
        agent_b = self._agents.get(match.agent_b_id)
        if agent_a is None:
            raise ValueError(f"Agent '{match.agent_a_id}' is not registered.")
        if agent_b is None:
            raise ValueError(f"Agent '{match.agent_b_id}' is not registered.")

        # Compute new global Elo ratings
        new_ra, new_rb = self.compute_elo(
            agent_a.elo_rating,
            agent_b.elo_rating,
            match.outcome_a,
        )

        # Compute new domain-specific Elo ratings (reduced K-factor)
        domain_ra = agent_a.domain_ratings.get(match.domain, agent_a.elo_rating)
        domain_rb = agent_b.domain_ratings.get(match.domain, agent_b.elo_rating)
        new_domain_ra, new_domain_rb = self.compute_elo(
            domain_ra,
            domain_rb,
            match.outcome_a,
            k_factor=16.0,
        )

        # Update domain ratings dicts
        updated_domain_a = dict(agent_a.domain_ratings)
        updated_domain_a[match.domain] = new_domain_ra
        updated_domain_b = dict(agent_b.domain_ratings)
        updated_domain_b[match.domain] = new_domain_rb

        # Update stats (DISQUALIFIED is counted as a loss)
        wins_a = agent_a.wins + (1 if match.outcome_a == "WIN" else 0)
        losses_a = agent_a.losses + (
            1 if match.outcome_a in ("LOSS", "DISQUALIFIED") else 0
        )
        draws_a = agent_a.draws + (1 if match.outcome_a == "DRAW" else 0)

        wins_b = agent_b.wins + (1 if match.outcome_b == "WIN" else 0)
        losses_b = agent_b.losses + (
            1 if match.outcome_b in ("LOSS", "DISQUALIFIED") else 0
        )
        draws_b = agent_b.draws + (1 if match.outcome_b == "DRAW" else 0)

        # Create updated frozen dataclass instances
        self._agents[match.agent_a_id] = replace(
            agent_a,
            elo_rating=new_ra,
            matches_played=agent_a.matches_played + 1,
            wins=wins_a,
            losses=losses_a,
            draws=draws_a,
            domain_ratings=updated_domain_a,
        )
        self._agents[match.agent_b_id] = replace(
            agent_b,
            elo_rating=new_rb,
            matches_played=agent_b.matches_played + 1,
            wins=wins_b,
            losses=losses_b,
            draws=draws_b,
            domain_ratings=updated_domain_b,
        )

        self._match_results.append(match)
        logger.info(
            "Recorded match '%s': %s vs %s (%s)",
            match.match_id,
            match.agent_a_id,
            match.agent_b_id,
            match.outcome_a,
        )

    # -- Tournament ---------------------------------------------------------

    def run_tournament(self, config: TournamentConfig) -> TournamentResult:
        """Run a full tournament simulation.

        Generates expected matches based on the tournament format, simulates
        outcomes using a probabilistic model based on Elo differences, and
        returns the tournament results.

        Parameters
        ----------
        config : TournamentConfig
            Configuration for the tournament.

        Returns
        -------
        TournamentResult
            The results of the tournament.

        Raises
        ------
        ValueError
            If the format is unsupported or agent constraints are not met.
        """
        # Use copies of agents so tournament simulation doesn't mutate arena
        # state until all results are recorded
        working_agents: dict[str, AgentEntry] = {}
        for agent in config.agents:
            working_agents[agent.agent_id] = agent
            # Ensure agent is in the arena registry too
            if agent.agent_id not in self._agents:
                self._agents[agent.agent_id] = agent

        start_time = datetime.datetime.now()
        total_matches = 0

        fmt = config.format
        if fmt == TournamentFormat.ROUND_ROBIN:
            total_matches, working_agents = self._run_round_robin(
                config, working_agents
            )
        elif fmt == TournamentFormat.SINGLE_ELIMINATION:
            total_matches, working_agents = self._run_single_elimination(
                config, working_agents
            )
        elif fmt == TournamentFormat.SWISS:
            total_matches, working_agents = self._run_swiss(
                config, working_agents
            )
        elif fmt == TournamentFormat.DOUBLE_ELIMINATION:
            total_matches, working_agents = self._run_double_elimination(
                config, working_agents
            )
        else:
            raise ValueError(f"Unsupported tournament format: {fmt}")

        duration = (datetime.datetime.now() - start_time).total_seconds()

        # Sync final ratings back to arena
        for agent_id, updated in working_agents.items():
            self._agents[agent_id] = updated

        # Stable sort: Elo descending, tie-break by agent_id
        sorted_agents = sorted(
            working_agents.values(),
            key=lambda a: (-a.elo_rating, a.agent_id),
        )

        winner_id = sorted_agents[0].agent_id if sorted_agents else ""

        return TournamentResult(
            tournament_id=config.tournament_id,
            winner_id=winner_id,
            final_standings=tuple(sorted_agents),
            total_matches=total_matches,
            duration_seconds=duration,
        )

    def _simulate_match(
        self,
        agents: dict[str, AgentEntry],
        a_id: str,
        b_id: str,
        domain: str,
        k_factor: float,
        match_id: str,
    ) -> tuple[MatchResult, dict[str, AgentEntry]]:
        """Simulate a single match between two agents based on Elo difference.

        Parameters
        ----------
        agents : dict[str, AgentEntry]
            Current agent state (mutated in place with updated entries).
        a_id : str
            Agent A identifier.
        b_id : str
            Agent B identifier.
        domain : str
            Domain for this match.
        k_factor : float
            K-factor for Elo computation.
        match_id : str
            Unique identifier for this match.

        Returns
        -------
        tuple[MatchResult, dict[str, AgentEntry]]
            The match result and updated agents dict.
        """
        agent_a = agents[a_id]
        agent_b = agents[b_id]

        # Use domain-specific rating if available, else global
        ra = agent_a.domain_ratings.get(domain, agent_a.elo_rating)
        rb = agent_b.domain_ratings.get(domain, agent_b.elo_rating)

        # Win probability based on Elo difference
        prob_a_wins = 1.0 / (1.0 + 10.0 ** ((rb - ra) / 400.0))

        if random.random() < prob_a_wins:
            outcome_a: str = "WIN"
            outcome_b: str = "LOSS"
            score_a, score_b = 1.0, 0.0
        else:
            outcome_a = "LOSS"
            outcome_b = "WIN"
            score_a, score_b = 0.0, 1.0

        # Compute new ratings
        new_ra, new_rb = self.compute_elo(ra, rb, outcome_a, k_factor)
        new_domain_ra, new_domain_rb = self.compute_elo(
            ra, rb, outcome_a, k_factor / 2.0
        )

        # Update domain ratings dicts
        domain_a = dict(agent_a.domain_ratings)
        domain_a[domain] = new_domain_ra
        domain_b = dict(agent_b.domain_ratings)
        domain_b[domain] = new_domain_rb

        # Update stats (DISQUALIFIED is counted as a loss)
        wins_a = agent_a.wins + (1 if outcome_a == "WIN" else 0)
        losses_a = agent_a.losses + (
            1 if outcome_a in ("LOSS", "DISQUALIFIED") else 0
        )
        draws_a = agent_a.draws + (1 if outcome_a == "DRAW" else 0)
        wins_b = agent_b.wins + (1 if outcome_b == "WIN" else 0)
        losses_b = agent_b.losses + (
            1 if outcome_b in ("LOSS", "DISQUALIFIED") else 0
        )
        draws_b = agent_b.draws + (1 if outcome_b == "DRAW" else 0)

        # Create updated agent entries
        updated_a = replace(
            agent_a,
            elo_rating=new_ra,
            matches_played=agent_a.matches_played + 1,
            wins=wins_a,
            losses=losses_a,
            draws=draws_a,
            domain_ratings=domain_a,
        )
        updated_b = replace(
            agent_b,
            elo_rating=new_rb,
            matches_played=agent_b.matches_played + 1,
            wins=wins_b,
            losses=losses_b,
            draws=draws_b,
            domain_ratings=domain_b,
        )

        match_result = MatchResult(
            match_id=match_id,
            agent_a_id=a_id,
            agent_b_id=b_id,
            outcome_a=outcome_a,
            outcome_b=outcome_b,
            score_a=score_a,
            score_b=score_b,
            domain=domain,
            duration_seconds=round(random.uniform(5.0, 300.0), 2),
            challenge_id=f"ch_{domain}",
            timestamp=datetime.datetime.now(),
        )

        agents[a_id] = updated_a
        agents[b_id] = updated_b
        self._match_results.append(match_result)
        return match_result, agents

    def _pick_domain(self, domains: tuple[str, ...]) -> str:
        """Pick a random domain from the available domains.

        Parameters
        ----------
        domains : tuple[str, ...]
            Available domains.

        Returns
        -------
        str
            A randomly selected domain.
        """
        return domains[random.randint(0, len(domains) - 1)]

    def _run_round_robin(
        self,
        config: TournamentConfig,
        agents: dict[str, AgentEntry],
    ) -> tuple[int, dict[str, AgentEntry]]:
        """Run a round-robin tournament.

        Every agent plays every other agent. Each pair plays
        ``config.matches_per_pair`` matches.

        Parameters
        ----------
        config : TournamentConfig
            Tournament configuration.
        agents : dict[str, AgentEntry]
            Current agent state (mutated in place).

        Returns
        -------
        tuple[int, dict[str, AgentEntry]]
            Total matches played and updated agents dict.
        """
        total = 0
        match_counter = 0
        agent_ids = list(agents.keys())

        for a_id, b_id in itertools.combinations(agent_ids, 2):
            for _ in range(config.matches_per_pair):
                match_counter += 1
                domain = self._pick_domain(config.domains)
                match_id = f"{config.tournament_id}_rr_m{match_counter}"
                _, agents = self._simulate_match(
                    agents, a_id, b_id, domain, config.k_factor, match_id
                )
                total += 1

        return total, agents

    def _run_single_elimination(
        self,
        config: TournamentConfig,
        agents: dict[str, AgentEntry],
    ) -> tuple[int, dict[str, AgentEntry]]:
        """Run a single-elimination bracket tournament.

        Agents are seeded by Elo rating. If the number of agents is not a
        power of 2, byes are automatically assigned to the top seeds.

        Parameters
        ----------
        config : TournamentConfig
            Tournament configuration.
        agents : dict[str, AgentEntry]
            Current agent state (mutated in place).

        Returns
        -------
        tuple[int, dict[str, AgentEntry]]
            Total matches played and updated agents dict.

        Raises
        ------
        ValueError
            If there are fewer than 2 agents.
        """
        if len(agents) < 2:
            raise ValueError(
                "Single-elimination tournament requires at least 2 agents."
            )

        # Seed by Elo (descending, stable)
        seeded = sorted(
            agents.keys(),
            key=lambda aid: (-agents[aid].elo_rating, aid),
        )

        # Pad to next power of 2 with None (byes)
        power = 1
        while power < len(seeded):
            power *= 2
        bracket: list[str | None] = list(seeded)
        while len(bracket) < power:
            bracket.append(None)

        total = 0
        match_counter = 0
        round_num = 0

        while len([s for s in bracket if s is not None]) > 1:
            round_num += 1
            next_round: list[str | None] = []

            for i in range(0, len(bracket), 2):
                a_id = bracket[i]
                b_id = bracket[i + 1] if i + 1 < len(bracket) else None

                # Byes
                if a_id is None and b_id is None:
                    next_round.append(None)
                    continue
                if a_id is None:
                    next_round.append(b_id)
                    continue
                if b_id is None:
                    next_round.append(a_id)
                    continue

                # Simulate match
                match_counter += 1
                domain = self._pick_domain(config.domains)
                match_id = (
                    f"{config.tournament_id}_se_r{round_num}_m{match_counter}"
                )
                match, agents = self._simulate_match(
                    agents, a_id, b_id, domain, config.k_factor, match_id
                )
                total += 1

                # Winner advances
                if match.outcome_a == "WIN":
                    next_round.append(a_id)
                else:
                    next_round.append(b_id)

            bracket = next_round

        return total, agents

    def _run_swiss(
        self,
        config: TournamentConfig,
        agents: dict[str, AgentEntry],
    ) -> tuple[int, dict[str, AgentEntry]]:
        """Run a Swiss-system tournament.

        Agents are paired against opponents with similar records. The number
        of rounds is approximately log2(N) + 1.

        Parameters
        ----------
        config : TournamentConfig
            Tournament configuration.
        agents : dict[str, AgentEntry]
            Current agent state (mutated in place).

        Returns
        -------
        tuple[int, dict[str, AgentEntry]]
            Total matches played and updated agents dict.
        """
        n = len(agents)
        if n < 2:
            return 0, agents

        rounds = max(3, int(math.log2(n)) + 1)
        total = 0
        match_counter = 0

        for _round in range(rounds):
            # Sort by wins descending (stable tie-break by agent_id)
            sorted_ids = sorted(
                agents.keys(),
                key=lambda aid: (-agents[aid].wins, agents[aid].elo_rating, aid),
            )

            # Pair adjacent agents
            for i in range(0, len(sorted_ids) - 1, 2):
                match_counter += 1
                domain = self._pick_domain(config.domains)
                match_id = (
                    f"{config.tournament_id}_sw_r{_round + 1}_m{match_counter}"
                )
                _, agents = self._simulate_match(
                    agents,
                    sorted_ids[i],
                    sorted_ids[i + 1],
                    domain,
                    config.k_factor,
                    match_id,
                )
                total += 1

        return total, agents

    def _run_double_elimination(
        self,
        config: TournamentConfig,
        agents: dict[str, AgentEntry],
    ) -> tuple[int, dict[str, AgentEntry]]:
        """Run a double-elimination tournament.

        Features a winners bracket and a losers bracket. Agents are seeded
        by Elo. The winners bracket champion and losers bracket champion
        meet in a grand final.

        Parameters
        ----------
        config : TournamentConfig
            Tournament configuration.
        agents : dict[str, AgentEntry]
            Current agent state (mutated in place).

        Returns
        -------
        tuple[int, dict[str, AgentEntry]]
            Total matches played and updated agents dict.

        Raises
        ------
        ValueError
            If there are fewer than 2 agents.
        """
        if len(agents) < 2:
            raise ValueError(
                "Double-elimination tournament requires at least 2 agents."
            )

        # Seed by Elo
        seeded = sorted(
            agents.keys(),
            key=lambda aid: (-agents[aid].elo_rating, aid),
        )

        # Pad to next power of 2
        power = 1
        while power < len(seeded):
            power *= 2
        wb: list[str | None] = list(seeded)
        while len(wb) < power:
            wb.append(None)

        wb_alive: set[str] = set(seeded)
        lb_alive: set[str] = set()

        total = 0
        match_counter = 0

        # --- Winners bracket rounds ---
        while len(wb) >= 2 and len([s for s in wb if s is not None]) > 1:
            next_wb: list[str | None] = []

            for i in range(0, len(wb), 2):
                a_id = wb[i]
                b_id = wb[i + 1] if i + 1 < len(wb) else None

                if a_id is None and b_id is None:
                    continue
                if a_id is None and b_id is not None:
                    next_wb.append(b_id)
                    continue
                if a_id is not None and b_id is None:
                    next_wb.append(a_id)
                    continue
                if a_id is not None and b_id is not None:
                    match_counter += 1
                    domain = self._pick_domain(config.domains)
                    match_id = (
                        f"{config.tournament_id}_de_wb_m{match_counter}"
                    )
                    match, agents = self._simulate_match(
                        agents,
                        a_id,
                        b_id,
                        domain,
                        config.k_factor,
                        match_id,
                    )
                    total += 1

                    if match.outcome_a == "WIN":
                        next_wb.append(a_id)
                        if b_id in wb_alive:
                            wb_alive.discard(b_id)
                            lb_alive.add(b_id)
                    else:
                        next_wb.append(b_id)
                        if a_id in wb_alive:
                            wb_alive.discard(a_id)
                            lb_alive.add(a_id)

            wb = next_wb

        # WB winner
        wb_winner: str | None = wb[0] if wb and wb[0] is not None else None

        # --- Losers bracket ---
        if not lb_alive:
            # No losers bracket needed (e.g., only 2 agents, one won both)
            pass
        else:
            # Sort losers by Elo
            lb_list = sorted(
                lb_alive,
                key=lambda aid: (-agents[aid].elo_rating, aid),
            )

            # Pad to power of 2
            lb_power = 1
            while lb_power < len(lb_list):
                lb_power *= 2
            lb_bracket: list[str | None] = list(lb_list)
            while len(lb_bracket) < lb_power:
                lb_bracket.append(None)

            rounds = 0
            while (
                len([s for s in lb_bracket if s is not None]) > 1
                and rounds < 20
            ):
                rounds += 1
                next_lb: list[str | None] = []

                for i in range(0, len(lb_bracket), 2):
                    a_id = lb_bracket[i]
                    b_id = lb_bracket[i + 1] if i + 1 < len(lb_bracket) else None

                    if a_id is None and b_id is None:
                        continue
                    if a_id is None and b_id is not None:
                        next_lb.append(b_id)
                        continue
                    if a_id is not None and b_id is None:
                        next_lb.append(a_id)
                        continue
                    if a_id is not None and b_id is not None:
                        match_counter += 1
                        domain = self._pick_domain(config.domains)
                        match_id = (
                            f"{config.tournament_id}_de_lb_m{match_counter}"
                        )
                        match, agents = self._simulate_match(
                            agents,
                            a_id,
                            b_id,
                            domain,
                            config.k_factor,
                            match_id,
                        )
                        total += 1

                        if match.outcome_a == "WIN":
                            next_lb.append(a_id)
                            lb_alive.discard(b_id)
                        else:
                            next_lb.append(b_id)
                            lb_alive.discard(a_id)

                lb_bracket = next_lb

        # LB winner (last remaining in lb_alive)
        lb_winner: str | None = None
        for aid in sorted(lb_alive, key=lambda x: -agents[x].elo_rating):
            lb_winner = aid
            break

        # --- Grand final ---
        if wb_winner is not None and lb_winner is not None and wb_winner != lb_winner:
            match_counter += 1
            domain = self._pick_domain(config.domains)
            match_id = f"{config.tournament_id}_de_final_m{match_counter}"
            match, agents = self._simulate_match(
                agents,
                wb_winner,
                lb_winner,
                domain,
                config.k_factor,
                match_id,
            )
            total += 1

        return total, agents

    # -- Queries ------------------------------------------------------------

    def get_leaderboard(
        self,
        domain: str | None = None,
        limit: int = 10,
    ) -> list[LeaderboardEntry]:
        """Get the current arena leaderboard.

        Parameters
        ----------
        domain : str | None, optional
            If provided, returns domain-specific leaderboard. If None,
            returns global leaderboard.
        limit : int, optional
            Maximum number of entries. Defaults to 10.

        Returns
        -------
        list[LeaderboardEntry]
            Leaderboard entries sorted by Elo rating (descending).
        """
        agents = list(self._agents.values())

        if domain:
            agents = [
                a
                for a in agents
                if domain in a.domain_ratings
            ]
            # Sort by domain-specific Elo, or global if not available
            agents_sorted = sorted(
                agents,
                key=lambda a: (
                    -a.domain_ratings.get(domain, a.elo_rating),
                    a.agent_id,
                ),
            )
        else:
            agents_sorted = sorted(
                agents,
                key=lambda a: (-a.elo_rating, a.agent_id),
            )

        result: list[LeaderboardEntry] = []
        for rank, agent in enumerate(agents_sorted[:limit], start=1):
            rating = (
                agent.domain_ratings.get(domain, agent.elo_rating)
                if domain
                else agent.elo_rating
            )
            win_rate = (
                agent.wins / agent.matches_played
                if agent.matches_played > 0
                else 0.0
            )
            result.append(
                LeaderboardEntry(
                    agent_id=agent.agent_id,
                    name=agent.name,
                    elo_rating=rating,
                    rank=rank,
                    win_rate=win_rate,
                    domain=domain or "",
                    matches_played=agent.matches_played,
                )
            )

        return result

    def get_head_to_head(
        self,
        agent_a: str,
        agent_b: str,
    ) -> dict[str, Any]:
        """Get head-to-head record between two agents.

        Parameters
        ----------
        agent_a : str
            Identifier of the first agent.
        agent_b : str
            Identifier of the second agent.

        Returns
        -------
        dict[str, Any]
            Dictionary with keys: agent_a, agent_b, agent_a_wins,
            agent_b_wins, draws, total_matches, agent_a_win_rate,
            agent_b_win_rate.
        """
        a_wins = 0
        b_wins = 0
        draws = 0
        total = 0

        for match in self._match_results:
            ids = {match.agent_a_id, match.agent_b_id}
            if {agent_a, agent_b} == ids:
                total += 1
                if match.outcome_a == "WIN":
                    if match.agent_a_id == agent_a:
                        a_wins += 1
                    else:
                        b_wins += 1
                elif match.outcome_a == "LOSS":
                    if match.agent_a_id == agent_a:
                        b_wins += 1
                    else:
                        a_wins += 1
                elif match.outcome_a == "DRAW":
                    draws += 1

        return {
            "agent_a": agent_a,
            "agent_b": agent_b,
            f"{agent_a}_wins": a_wins,
            f"{agent_b}_wins": b_wins,
            "draws": draws,
            "total_matches": total,
            f"{agent_a}_win_rate": a_wins / total if total > 0 else 0.0,
            f"{agent_b}_win_rate": b_wins / total if total > 0 else 0.0,
        }

    def get_stats(self) -> dict[str, Any]:
        """Get arena-wide statistics.

        Returns
        -------
        dict[str, Any]
            Dictionary with keys: total_agents, total_matches,
            average_elo, min_elo, max_elo, total_domains, domains.
        """
        agents = list(self._agents.values())
        n_agents = len(agents)
        n_matches = len(self._match_results)
        elos = [a.elo_rating for a in agents] if agents else [1500.0]

        all_domains: set[str] = set()
        for a in agents:
            all_domains.update(a.domain_ratings.keys())

        return {
            "total_agents": n_agents,
            "total_matches": n_matches,
            "average_elo": sum(elos) / len(elos),
            "min_elo": min(elos),
            "max_elo": max(elos),
            "total_domains": len(all_domains),
            "domains": sorted(all_domains),
        }

    def get_agent_history(
        self,
        agent_id: str,
        limit: int = 10,
    ) -> list[MatchResult]:
        """Get match history for a specific agent.

        Parameters
        ----------
        agent_id : str
            Identifier of the agent.
        limit : int, optional
            Maximum number of results. Defaults to 10.

        Returns
        -------
        list[MatchResult]
            Most recent matches for the agent, limited to `limit`.
        """
        history = [
            match
            for match in self._match_results
            if match.agent_a_id == agent_id or match.agent_b_id == agent_id
        ]
        # Return most recent first, limited
        return list(reversed(history))[:limit]

    # -- Utility ------------------------------------------------------------

    @property
    def agents(self) -> dict[str, AgentEntry]:
        """dict[str, AgentEntry]: Read-only view of registered agents."""
        return dict(self._agents)

    @property
    def match_results(self) -> list[MatchResult]:
        """list[MatchResult]: Read-only view of recorded match results."""
        return list(self._match_results)
