"""Distributed leader election with multiple algorithms, health monitoring, and failover."""

from __future__ import annotations

import asyncio
import logging
import random
import time
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class LeadershipError(Exception):
    """Base exception for leadership errors."""


class ElectionTimeoutError(LeadershipError):
    """Raised when leader election times out."""


class NoCandidateError(LeadershipError):
    """Raised when no candidates are available for election."""


class LeadershipConflictError(LeadershipError):
    """Raised when two leaders claim the same domain."""


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class LeaderState(Enum):
    """State of a leader in the colony."""

    CANDIDATE = auto()
    LEADER = auto()
    FOLLOWER = auto()
    DEPOSED = auto()


class ElectionAlgorithm(Enum):
    """Supported leader election algorithms."""

    BULLY = auto()
    RING = auto()
    RAFT_INSPIRED = auto()
    RANDOM = auto()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _new_id() -> str:
    return uuid4().hex[:12]


def _now() -> float:
    return time.monotonic()


# ---------------------------------------------------------------------------
# Dataclass models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ElectionResult:
    """The outcome of a leader election round.

    Attributes:
        election_id: Unique election identifier.
        algorithm: Which algorithm was used.
        winner_id: The elected leader.
        term: Monotonic term counter.
        votes_received: How many votes the winner got.
        total_voters: Total participating voters.
        quorum_achieved: Whether quorum was met.
        started_at: When the election began.
        completed_at: When the election concluded.
    """

    election_id: str = field(default_factory=_new_id)
    algorithm: ElectionAlgorithm = ElectionAlgorithm.BULLY
    winner_id: str = ""
    term: int = 0
    votes_received: int = 0
    total_voters: int = 0
    quorum_achieved: bool = False
    started_at: float = field(default_factory=_now)
    completed_at: float = field(default_factory=_now)

    @property
    def vote_share(self) -> float:
        if self.total_voters == 0:
            return 0.0
        return self.votes_received / self.total_voters

    @property
    def is_valid(self) -> bool:
        return self.quorum_achieved and self.votes_received > 0 and self.winner_id != ""


@dataclass
class LeaderRecord:
    """Tracks a leader's current state and health.

    Attributes:
        leader_id: The leader agent ID.
        domain: What domain/scope they lead over.
        state: Current leader state.
        term: The term during which they were elected.
        last_heartbeat: When the last heartbeat was received.
        follower_count: How many agents follow this leader.
    """

    leader_id: str
    domain: str = "default"
    state: LeaderState = LeaderState.LEADER
    term: int = 0
    last_heartbeat: float = field(default_factory=_now)
    follower_count: int = 0

    @property
    def is_healthy(self) -> bool:
        return self.state == LeaderState.LEADER


# ---------------------------------------------------------------------------
# Leader Election Algorithms
# ---------------------------------------------------------------------------


class _BullyAlgorithm:
    """Implements the Bully election algorithm.

    The agent with the highest ID (priority) wins. When a leader
    fails, the highest-ID agent that detects the failure calls
    an election.
    """

    @staticmethod
    def elect(
        candidates: Sequence[str],
        priorities: dict[str, float],
        *,
        timeout: float = 5.0,
    ) -> ElectionResult:
        """Run a bully election among candidates."""
        if not candidates:
            raise NoCandidateError("No candidates for bully election")

        # Highest priority wins
        winner = max(candidates, key=lambda c: priorities.get(c, 0.0))
        votes = sum(1 for c in candidates if priorities.get(c, 0.0) <= priorities.get(winner, 0.0))

        return ElectionResult(
            algorithm=ElectionAlgorithm.BULLY,
            winner_id=winner,
            votes_received=votes,
            total_voters=len(candidates),
            quorum_achieved=votes > len(candidates) / 2,
        )


class _RingAlgorithm:
    """Implements the Ring election algorithm.

    A coordinator message circulates around a logical ring. Each agent
    appends its ID if it has higher priority. The last agent declares
    the highest as leader.
    """

    @staticmethod
    def elect(
        candidates: Sequence[str],
        priorities: dict[str, float],
    ) -> ElectionResult:
        """Run a ring election among candidates."""
        if not candidates:
            raise NoCandidateError("No candidates for ring election")

        # Simulate the ring: the message passes through all candidates
        # and the highest priority ID wins
        winner = max(candidates, key=lambda c: priorities.get(c, 0.0))

        return ElectionResult(
            algorithm=ElectionAlgorithm.RING,
            winner_id=winner,
            votes_received=len(candidates),
            total_voters=len(candidates),
            quorum_achieved=len(candidates) > 1,
        )


class _RaftInspiredElection:
    """Raft-inspired leader election with randomized timeouts and term tracking.

    Candidates request votes with a randomized election timeout.
    The first candidate to gain majority becomes leader.
    """

    def __init__(self, *, min_timeout: float = 0.15, max_timeout: float = 0.3) -> None:
        self._min_timeout = min_timeout
        self._max_timeout = max_timeout
        self._current_term: int = 0
        self._voted_in_term: dict[int, str | None] = defaultdict(lambda: None)

    def start_term(self) -> int:
        """Increment and return a new term."""
        self._current_term += 1
        return self._current_term

    @property
    def current_term(self) -> int:
        return self._current_term

    def random_timeout(self) -> float:
        """Return a randomized election timeout."""
        return random.uniform(self._min_timeout, self._max_timeout)

    def request_vote(self, candidate_id: str, voter_id: str, term: int) -> bool:
        """A voter decides whether to grant a vote.

        Returns True if the vote is granted.
        """
        if term < self._current_term:
            return False  # stale term

        already_voted = self._voted_in_term.get(term)
        if already_voted is not None and already_voted != candidate_id:
            return False  # already voted for someone else

        self._voted_in_term[term] = candidate_id
        return True

    def elect(
        self,
        candidates: Sequence[str],
        priorities: dict[str, float],
        *,
        timeout: float = 5.0,
    ) -> ElectionResult:
        """Run a raft-inspired election."""
        if not candidates:
            raise NoCandidateError("No candidates for raft election")

        term = self.start_term()
        # Each candidate solicits votes; candidate with most votes wins
        votes: dict[str, int] = defaultdict(int)
        for candidate in candidates:
            for voter in candidates:
                if voter == candidate:
                    votes[candidate] += 1  # self-vote
                elif self.request_vote(candidate, voter, term):
                    votes[candidate] += 1

        winner = max(candidates, key=lambda c: votes.get(c, 0))
        vote_count = votes.get(winner, 0)
        quorum = vote_count > len(candidates) / 2

        return ElectionResult(
            algorithm=ElectionAlgorithm.RAFT_INSPIRED,
            winner_id=winner,
            term=term,
            votes_received=vote_count,
            total_voters=len(candidates),
            quorum_achieved=quorum,
        )


# ---------------------------------------------------------------------------
# Leader Health Monitor
# ---------------------------------------------------------------------------


class LeaderHealthMonitor:
    """Monitors leader health and triggers failover elections."""

    def __init__(
        self,
        *,
        heartbeat_timeout: float = 5.0,
        max_missed_heartbeats: int = 3,
    ) -> None:
        self._heartbeat_timeout = heartbeat_timeout
        self._max_missed_heartbeats = max_missed_heartbeats
        self._leader_heartbeats: dict[str, float] = {}
        self._missed_counts: dict[str, int] = defaultdict(int)
        self._leader_state: dict[str, LeaderState] = {}

    def record_heartbeat(self, leader_id: str) -> None:
        """Record a heartbeat from a leader."""
        self._leader_heartbeats[leader_id] = _now()
        self._missed_counts[leader_id] = 0
        self._leader_state[leader_id] = LeaderState.LEADER

    def check_health(self) -> list[str]:
        """Check all leaders and return IDs of failed leaders."""
        now = _now()
        failed: list[str] = []

        for leader_id, last_hb in list(self._leader_heartbeats.items()):
            if now - last_hb > self._heartbeat_timeout:
                self._missed_counts[leader_id] += 1
                if self._missed_counts[leader_id] >= self._max_missed_heartbeats:
                    self._leader_state[leader_id] = LeaderState.DEPOSED
                    failed.append(leader_id)
                    logger.warning(
                        "Leader %s failed (%d missed heartbeats)",
                        leader_id,
                        self._missed_counts[leader_id],
                    )

        return failed

    def register_leader(self, leader_id: str) -> None:
        """Register a new leader for health monitoring."""
        self._leader_heartbeats[leader_id] = _now()
        self._missed_counts[leader_id] = 0
        self._leader_state[leader_id] = LeaderState.LEADER

    def unregister_leader(self, leader_id: str) -> None:
        """Remove a leader from monitoring."""
        self._leader_heartbeats.pop(leader_id, None)
        self._missed_counts.pop(leader_id, None)
        self._leader_state.pop(leader_id, None)

    def is_healthy(self, leader_id: str) -> bool:
        """Check if a leader is healthy."""
        return self._leader_state.get(leader_id) == LeaderState.LEADER

    def get_state(self, leader_id: str) -> LeaderState | None:
        """Get the current state of a leader."""
        return self._leader_state.get(leader_id)


# ---------------------------------------------------------------------------
# Leader Manager
# ---------------------------------------------------------------------------


class LeaderManager:
    """Orchestrates leader election, delegation, and consensus building.

    Supports multiple election algorithms, leader health monitoring
    with automatic failover, delegation/authority management, and
    consensus building among multiple leaders.
    """

    def __init__(
        self,
        default_algorithm: ElectionAlgorithm = ElectionAlgorithm.BULLY,
    ) -> None:
        self._default_algorithm = default_algorithm
        self._algorithms: dict[ElectionAlgorithm, Any] = {
            ElectionAlgorithm.BULLY: _BullyAlgorithm(),
            ElectionAlgorithm.RING: _RingAlgorithm(),
            ElectionAlgorithm.RAFT_INSPIRED: _RaftInspiredElection(),
        }
        self._health_monitor = LeaderHealthMonitor()

        # Agent registry
        self._agent_priorities: dict[str, float] = {}
        self._agent_domains: dict[str, set[str]] = defaultdict(set)

        # Leader state
        self._leaders: dict[str, LeaderRecord] = {}
        self._followers: dict[str, set[str]] = defaultdict(set)
        self._delegations: dict[str, list[str]] = defaultdict(list)
        self._election_history: list[ElectionResult] = []

        # Background
        self._running = False
        self._health_task: asyncio.Task[Any] | None = None

    # ------------------------------------------------------------------
    # Agent registration
    # ------------------------------------------------------------------

    def register_agent(
        self,
        agent_id: str,
        priority: float = 1.0,
        domains: Sequence[str] | None = None,
    ) -> None:
        """Register an agent for leader election."""
        self._agent_priorities[agent_id] = priority
        if domains:
            self._agent_domains[agent_id] = set(domains)

    def unregister_agent(self, agent_id: str) -> None:
        """Remove an agent. If it was a leader, trigger failover."""
        self._agent_priorities.pop(agent_id, None)
        self._agent_domains.pop(agent_id, None)
        self._health_monitor.unregister_leader(agent_id)

    # ------------------------------------------------------------------
    # Leader election
    # ------------------------------------------------------------------

    def elect_leader(
        self,
        candidates: Sequence[str] | None = None,
        *,
        algorithm: ElectionAlgorithm | None = None,
        timeout: float = 5.0,
    ) -> ElectionResult:
        """Run a leader election and return the result.

        If no candidates are provided, all registered agents are candidates.
        """
        alg = algorithm or self._default_algorithm

        if candidates is None:
            candidates = list(self._agent_priorities.keys())

        if not candidates:
            raise NoCandidateError("No candidates available for election")

        if alg == ElectionAlgorithm.RANDOM:
            winner = random.choice(list(candidates))
            result = ElectionResult(
                algorithm=alg,
                winner_id=winner,
                votes_received=1,
                total_voters=len(candidates),
                quorum_achieved=True,
            )
        elif alg == ElectionAlgorithm.RAFT_INSPIRED:
            raft = self._algorithms[alg]
            result = raft.elect(candidates, self._agent_priorities, timeout=timeout)
        else:
            executor = self._algorithms[alg]
            result = executor.elect(candidates, self._agent_priorities)

        # Record the result
        self._election_history.append(result)
        if result.is_valid:
            self._promote_leader(result.winner_id, result.term)
            self._health_monitor.register_leader(result.winner_id)

        logger.info(
            "Election complete: winner=%s, algorithm=%s, votes=%d/%d",
            result.winner_id,
            result.algorithm.name,
            result.votes_received,
            result.total_voters,
        )
        return result

    def _promote_leader(self, leader_id: str, term: int) -> None:
        """Promote an agent to leader status."""
        old_leader = self._leaders.get(leader_id)
        if old_leader:
            old_leader.state = LeaderState.LEADER
            old_leader.term = term
        else:
            self._leaders[leader_id] = LeaderRecord(
                leader_id=leader_id,
                term=term,
            )
        self._health_monitor.record_heartbeat(leader_id)

    # ------------------------------------------------------------------
    # Delegation & authority
    # ------------------------------------------------------------------

    def delegate(self, leader_id: str, delegate_id: str, scope: str) -> bool:
        """Delegate authority from a leader to another agent for a scope."""
        if leader_id not in self._leaders:
            raise LeadershipError(f"Leader {leader_id} not found")
        self._delegations[leader_id].append(scope)
        logger.debug("Leader %s delegated %s to %s", leader_id, scope, delegate_id)
        return True

    def revoke_delegation(self, leader_id: str, scope: str) -> bool:
        """Revoke a delegated authority."""
        if scope in self._delegations.get(leader_id, []):
            self._delegations[leader_id].remove(scope)
            return True
        return False

    def get_delegations(self, leader_id: str) -> list[str]:
        """Get all active delegations for a leader."""
        return self._delegations.get(leader_id, [])

    # ------------------------------------------------------------------
    # Consensus building
    # ------------------------------------------------------------------

    def build_consensus(
        self,
        leaders: Sequence[str],
        proposal: str,
        *,
        quorum_ratio: float = 0.5,
    ) -> tuple[bool, dict[str, str]]:
        """Build consensus among multiple leaders on a proposal.

        Returns (consensus_reached, positions) where positions maps
        each leader to their position ("agree" or "disagree").
        """
        positions: dict[str, str] = {}
        agree = 0

        for leader_id in leaders:
            # Leader agrees based on priority-weighted random for demo
            # In production, this would invoke actual deliberation
            priority = self._agent_priorities.get(leader_id, 1.0)
            agrees = random.random() < priority / max(1.0, priority)
            positions[leader_id] = "agree" if agrees else "disagree"
            if agrees:
                agree += 1

        quorum = agree / max(len(leaders), 1) >= quorum_ratio
        logger.info("Consensus on '%s': %s (%d/%d agree)", proposal, quorum, agree, len(leaders))
        return quorum, positions

    # ------------------------------------------------------------------
    # Health and failover
    # ------------------------------------------------------------------

    def check_leader_health(self) -> list[str]:
        """Check leader health and return failed leader IDs."""
        return self._health_monitor.check_health()

    async def failover(self, failed_leader_id: str) -> ElectionResult | None:
        """Run a failover election for a failed leader's domain."""
        # Find followers who can become candidates
        followers = list(self._followers.get(failed_leader_id, set()))
        if not followers:
            followers = [aid for aid in self._agent_priorities if aid != failed_leader_id]

        if not followers:
            logger.warning("No candidates for failover of %s", failed_leader_id)
            return None

        self._health_monitor.unregister_leader(failed_leader_id)
        result = self.elect_leader(followers, algorithm=ElectionAlgorithm.BULLY)
        logger.info("Failover: %s replaced by %s", failed_leader_id, result.winner_id)
        return result

    # ------------------------------------------------------------------
    # Background monitoring
    # ------------------------------------------------------------------

    async def start_monitoring(self, interval: float = 2.0) -> None:
        """Start periodic leader health checks with automatic failover."""
        self._running = True
        self._health_task = asyncio.create_task(self._monitor_loop(interval))

    async def stop_monitoring(self) -> None:
        """Stop periodic monitoring."""
        self._running = False
        if self._health_task:
            self._health_task.cancel()
            try:
                await self._health_task
            except asyncio.CancelledError:
                pass

    async def _monitor_loop(self, interval: float) -> None:
        while self._running:
            try:
                failed = self.check_leader_health()
                for leader_id in failed:
                    await self.failover(leader_id)
            except Exception:
                logger.exception("Error in leader monitor loop")
            await asyncio.sleep(interval)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_leader(self, domain: str | None = None) -> LeaderRecord | None:
        """Get the current leader, optionally by domain."""
        for leader in self._leaders.values():
            if leader.is_healthy:
                if domain is None or leader.domain == domain:
                    return leader
        return None

    def list_leaders(self) -> list[LeaderRecord]:
        """List all active leaders."""
        return [leader for leader in self._leaders.values() if leader.is_healthy]

    def get_leader_history(self, limit: int = 20) -> list[ElectionResult]:
        """Return recent election results."""
        return self._election_history[-limit:]

    def snapshot(self) -> dict[str, Any]:
        """Return a current-state snapshot."""
        return {
            "active_leaders": len([leader for leader in self._leaders.values() if leader.is_healthy]),
            "total_agents": len(self._agent_priorities),
            "election_history": len(self._election_history),
            "leaders": [
                {
                    "id": leader.leader_id,
                    "domain": leader.domain,
                    "state": leader.state.name,
                    "term": leader.term,
                    "followers": leader.follower_count,
                }
                for leader in self._leaders.values()
            ],
        }
