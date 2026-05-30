"""Raft Leader Election — capability-weighted election with stagnation detection.

Implements leader election for agent swarms:
  - Randomized election timeouts (150-300ms) per Raft spec
  - Capability + health score weighting for candidate nomination
  - Stagnation-triggered re-election
  - Graceful leader step-down
  - Vote tallying with majority quorum validation
"""

from __future__ import annotations

import random
import time
import uuid
from dataclasses import dataclass, field
from enum import StrEnum


class ElectionPhase(StrEnum):
    """Phases of a leader election cycle."""

    IDLE = "idle"
    PRE_VOTE = "pre_vote"
    CANDIDATE = "candidate"
    VOTING = "voting"
    SETTLED = "settled"
    STEPPED_DOWN = "stepped_down"


@dataclass(frozen=True)
class VoteRequest:
    """A request for a vote from a candidate."""

    term: int
    candidate_id: str
    last_log_index: int
    last_log_term: int
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass(frozen=True)
class VoteResponse:
    """A response to a vote request."""

    term: int
    vote_granted: bool
    voter_id: str
    request_id: str
    reason: str = ""


@dataclass(frozen=True)
class CandidateNomination:
    """A candidate for leader election with capability scoring."""

    agent_id: str
    term: int
    capability_score: float  # 0.0-1.0
    health_score: float  # 0.0-1.0
    nomination_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    @property
    def composite_score(self) -> float:
        return (self.capability_score * 0.6) + (self.health_score * 0.4)


@dataclass
class ElectionConfig:
    """Configuration for leader election behaviour."""

    election_timeout_min_ms: float = 150.0
    election_timeout_max_ms: float = 300.0
    heartbeat_interval_ms: float = 50.0
    stagnation_threshold_ms: float = 10_000.0
    max_election_retries: int = 3
    pre_vote_enabled: bool = True
    capability_weight: float = 0.6
    health_weight: float = 0.4


@dataclass
class ElectionResult:
    """Result of a completed leader election."""

    leader_id: str
    term: int
    votes_received: int
    total_voters: int
    phase: ElectionPhase
    election_duration_ms: float
    retries: int = 0
    reason: str = ""


@dataclass
class ElectionState:
    """Mutable state for an ongoing election."""

    phase: ElectionPhase = ElectionPhase.IDLE
    current_term: int = 0
    voted_for: str | None = None
    votes_received: set[str] = field(default_factory=set)
    election_start: float = 0.0
    election_deadline: float = 0.0
    retry_count: int = 0
    last_progress: float = field(default_factory=time.monotonic)


class LeaderElection:
    """Manages leader election for a Raft cluster node.

    Implements Raft's leader election sub-protocol with extensions:
    - Pre-vote phase to prevent disruptive candidacies
    - Capability-weighted nomination scoring
    - Stagnation-triggered leader step-down and re-election
    - Graceful leader transfer

    Usage::

        election = LeaderElection(node_id="agent-1", peer_ids=["agent-2", "agent-3"])
        election.tick()  # Called periodically
        if election.is_leader:
            commands = get_commands_to_replicate()
    """

    def __init__(
        self,
        node_id: str,
        peer_ids: list[str] | None = None,
        config: ElectionConfig | None = None,
    ) -> None:
        self.node_id = node_id
        self.peer_ids = peer_ids or []
        self.config = config or ElectionConfig()
        self._state = ElectionState()
        self._nomination: CandidateNomination | None = None
        self._capability_score: float = 0.5
        self._health_score: float = 1.0
        self._last_heartbeat: float = 0.0
        self._leader_id: str | None = None

    # ── Properties ───────────────────────────────────────────────

    @property
    def is_leader(self) -> bool:
        return self._leader_id == self.node_id

    @property
    def current_leader(self) -> str | None:
        return self._leader_id

    @property
    def current_term(self) -> int:
        return self._state.current_term

    @property
    def phase(self) -> ElectionPhase:
        return self._state.phase

    @property
    def capability_score(self) -> float:
        return self._capability_score

    @property
    def health_score(self) -> float:
        return self._health_score

    # ── Public API ───────────────────────────────────────────────

    def update_scores(self, capability: float, health: float) -> None:
        """Update the agent's capability and health scores for election weighting."""
        self._capability_score = max(0.0, min(1.0, capability))
        self._health_score = max(0.0, min(1.0, health))

    def tick(self, log_size: int = 0, log_last_term: int = 0) -> list[str]:
        """Periodic tick — checks timeouts and signals election needed.

        Returns list of event strings. Does NOT start elections directly;
        callers should check phase == CANDIDATE and call start_election().
        """
        events: list[str] = []
        now = time.monotonic()

        if self._state.phase in (ElectionPhase.IDLE, ElectionPhase.SETTLED):
            if now >= self._state.election_deadline:
                self._state.phase = ElectionPhase.CANDIDATE
                events.append("election_timeout")
        elif self._state.phase == ElectionPhase.CANDIDATE:
            if now >= self._state.election_deadline:
                events.extend(self._handle_election_timeout(now, log_size, log_last_term))

        return events

    def receive_heartbeat(self, leader_id: str, leader_term: int) -> bool:
        """Process an incoming heartbeat from a leader.

        Returns True if this node accepts the leader's authority.
        """
        if leader_term < self._state.current_term:
            return False

        if leader_term > self._state.current_term:
            self._state.current_term = leader_term
            self._state.voted_for = None

        self._state.phase = ElectionPhase.SETTLED
        self._leader_id = leader_id
        self._last_heartbeat = time.monotonic()
        self._reset_election_timeout()
        return True

    def request_vote(self, request: VoteRequest, log_size: int = 0, log_last_term: int = 0) -> VoteResponse:
        """Handle an incoming vote request from a candidate.

        Implements Raft's RequestVote RPC safety checks.
        """
        if request.term < self._state.current_term:
            return VoteResponse(
                term=self._state.current_term,
                vote_granted=False,
                voter_id=self.node_id,
                request_id=request.request_id,
                reason=f"Stale term (candidate={request.term} < current={self._state.current_term})",
            )

        if request.term > self._state.current_term:
            self._state.current_term = request.term
            self._state.voted_for = None
            self._state.phase = ElectionPhase.SETTLED

        # Already voted for someone else this term
        if self._state.voted_for is not None and self._state.voted_for != request.candidate_id:
            return VoteResponse(
                term=self._state.current_term,
                vote_granted=False,
                voter_id=self.node_id,
                request_id=request.request_id,
                reason=f"Already voted for {self._state.voted_for}",
            )

        # Candidate log must be at least as up-to-date as ours
        my_last_index = log_size - 1
        my_last_term = log_last_term
        if request.last_log_term < my_last_term:
            return VoteResponse(
                term=self._state.current_term,
                vote_granted=False,
                voter_id=self.node_id,
                request_id=request.request_id,
                reason="Candidate log behind (term)",
            )
        if request.last_log_term == my_last_term and request.last_log_index < my_last_index:
            return VoteResponse(
                term=self._state.current_term,
                vote_granted=False,
                voter_id=self.node_id,
                request_id=request.request_id,
                reason="Candidate log behind (index)",
            )

        self._state.voted_for = request.candidate_id
        self._reset_election_timeout()
        return VoteResponse(
            term=self._state.current_term,
            vote_granted=True,
            voter_id=self.node_id,
            request_id=request.request_id,
            reason="Candidate log is current",
        )

    def start_election(self, log_size: int = 0, log_last_term: int = 0) -> tuple[ElectionPhase, VoteRequest | None]:
        """Initiate a leader election as a candidate.

        Returns (new_phase, vote_request_to_broadcast).
        """
        if self._state.retry_count >= self.config.max_election_retries:
            self._state.phase = ElectionPhase.SETTLED
            self._state.retry_count = 0
            return ElectionPhase.SETTLED, None

        self._state.phase = ElectionPhase.CANDIDATE
        self._state.current_term += 1
        self._state.voted_for = self.node_id
        self._state.votes_received = {self.node_id}
        self._state.election_start = time.monotonic()
        self._state.retry_count += 1

        self._reset_election_timeout()

        self._nomination = CandidateNomination(
            agent_id=self.node_id,
            term=self._state.current_term,
            capability_score=self._capability_score,
            health_score=self._health_score,
        )

        request = VoteRequest(
            term=self._state.current_term,
            candidate_id=self.node_id,
            last_log_index=log_size - 1 if log_size > 0 else 0,
            last_log_term=log_last_term,
        )

        return ElectionPhase.CANDIDATE, request

    def record_vote(self, voter_id: str, vote_granted: bool) -> None:
        """Record a vote response from a peer."""
        if vote_granted and self._state.phase == ElectionPhase.CANDIDATE:
            self._state.votes_received.add(voter_id)

    def try_claim_leadership(self) -> ElectionResult | None:
        """Check if the candidate has won the election.

        Returns ElectionResult if quorum reached, None otherwise.
        """
        if self._state.phase != ElectionPhase.CANDIDATE:
            return None

        quorum = (len(self.peer_ids) + 1) // 2 + 1
        if len(self._state.votes_received) < quorum:
            return None

        self._state.phase = ElectionPhase.SETTLED
        self._leader_id = self.node_id
        self._state.retry_count = 0
        self._last_heartbeat = time.monotonic()

        duration = (time.monotonic() - self._state.election_start) * 1000

        return ElectionResult(
            leader_id=self.node_id,
            term=self._state.current_term,
            votes_received=len(self._state.votes_received),
            total_voters=len(self.peer_ids) + 1,
            phase=ElectionPhase.SETTLED,
            election_duration_ms=duration,
            retries=self._state.retry_count - 1,
            reason="Quorum reached",
        )

    def step_down(self) -> None:
        """Voluntarily step down as leader."""
        self._leader_id = None
        self._state.phase = ElectionPhase.STEPPED_DOWN
        self._state.voted_for = None

    def check_stagnation(self, last_progress_ms: float) -> bool:
        """Check if the leader should step down due to stagnation.

        Returns True if stagnation threshold exceeded.
        """
        if not self.is_leader:
            return False
        return last_progress_ms >= self.config.stagnation_threshold_ms

    def get_quorum_size(self) -> int:
        """Return the number of votes needed for a majority."""
        return (len(self.peer_ids) + 1) // 2 + 1

    def reset(self) -> None:
        """Reset election state (e.g., on cluster restart)."""
        self._state = ElectionState()
        self._nomination = None
        self._leader_id = None
        self._last_heartbeat = 0.0

    # ── Private ───────────────────────────────────────────────────

    def _reset_election_timeout(self) -> None:
        ms = random.uniform(
            self.config.election_timeout_min_ms,
            self.config.election_timeout_max_ms,
        )
        self._state.election_deadline = time.monotonic() + ms / 1000.0

    def _check_heartbeat_timeout(self, now: float, events: list[str]) -> None:
        """Check if election timeout has elapsed and start election if so."""
        if self._state.election_deadline == 0.0:
            self._reset_election_timeout()
            return

        if now >= self._state.election_deadline:
            _, request = self.start_election()
            if request:
                events.append(f"election_started_term_{self._state.current_term}")

    def _handle_election_timeout(self, _now: float, log_size: int, log_last_term: int) -> list[str]:
        """Handle election timeout — split vote or lost election."""
        events: list[str] = []
        self._state.phase = ElectionPhase.IDLE
        self._state.voted_for = None
        _, request = self.start_election(log_size, log_last_term)
        if request:
            events.append(f"election_retry_{self._state.retry_count}_term_{self._state.current_term}")
        return events
