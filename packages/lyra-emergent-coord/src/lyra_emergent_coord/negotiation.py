"""Agent negotiation with Contract Net Protocol, multi-round bargaining, and conflict resolution."""

from __future__ import annotations

import asyncio
import logging
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


class NegotiationError(Exception):
    """Base exception for negotiation errors."""


class NegotiationTimeoutError(NegotiationError):
    """Raised when negotiation exceeds its deadline."""


class DeadlockError(NegotiationError):
    """Raised when negotiation reaches an unresolvable deadlock."""


class AgreementViolationError(NegotiationError):
    """Raised when an agent violates a formalized agreement."""


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class NegotiationState(Enum):
    """State of a negotiation session."""

    OPEN = auto()
    BIDDING = auto()
    EVALUATING = auto()
    COUNTER_OFFER = auto()
    AGREED = auto()
    REJECTED = auto()
    EXPIRED = auto()
    DEADLOCKED = auto()


class ConflictResolutionStrategy(Enum):
    """How to resolve conflicts between agents."""

    MAJORITY_VOTE = auto()
    AUTHORITY_OVERRIDE = auto()
    MEDIATION = auto()
    RANDOM_SELECTION = auto()
    RANKED_CHOICE = auto()


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
class Offer:
    """An offer made during negotiation.

    Attributes:
        offer_id: Unique offer identifier.
        session_id: The negotiation session this belongs to.
        proposer_id: Agent making the offer.
        terms: Key-value terms of the offer.
        value: Estimated value of the offer to the proposer.
        round_number: Which negotiation round this is in.
        expires_at: When the offer expires.
        accepted: Whether it has been accepted.
        accepted_by: Which agent accepted, if any.
    """

    offer_id: str = field(default_factory=_new_id)
    session_id: str = ""
    proposer_id: str = ""
    terms: dict[str, Any] = field(default_factory=dict)
    value: float = 0.5
    round_number: int = 0
    expires_at: float | None = None
    accepted: bool = False
    accepted_by: str | None = None

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return _now() > self.expires_at


@dataclass(frozen=True)
class Contract:
    """A formalized agreement between agents.

    Attributes:
        contract_id: Unique contract identifier.
        parties: Agent IDs that are party to this contract.
        terms: Agreed-upon terms.
        formed_at: When the contract was formed.
        expires_at: When the contract expires.
        metadata: Additional contract metadata.
    """

    contract_id: str = field(default_factory=_new_id)
    parties: tuple[str, ...] = ()
    terms: dict[str, Any] = field(default_factory=dict)
    formed_at: float = field(default_factory=_now)
    expires_at: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return _now() > self.expires_at

    @property
    def party_count(self) -> int:
        return len(self.parties)


@dataclass
class NegotiationSession:
    """Tracks the state and history of a negotiation session.

    Attributes:
        session_id: Unique session identifier.
        task_id: The task being negotiated over.
        participants: Agent IDs involved in the negotiation.
        state: Current negotiation state.
        offers: All offers made during the session.
        contracts: Contract(s) resulting from this session.
        deadline: Maximum time for negotiation.
        started_at: When negotiations began.
        max_rounds: Maximum negotiation rounds allowed.
        current_round: Current round number.
    """

    session_id: str = field(default_factory=_new_id)
    task_id: str = ""
    participants: list[str] = field(default_factory=list)
    state: NegotiationState = NegotiationState.OPEN
    offers: list[Offer] = field(default_factory=list)
    contracts: list[Contract] = field(default_factory=list)
    deadline: float | None = None
    started_at: float = field(default_factory=_now)
    max_rounds: int = 10
    current_round: int = 0

    def is_expired(self) -> bool:
        if self.deadline is None:
            return False
        return _now() > self.deadline


# ---------------------------------------------------------------------------
# Contract Net Protocol
# ---------------------------------------------------------------------------


class ContractNetProtocol:
    """Implements the Contract Net Protocol for agent task negotiation.

    The protocol:
    1. Manager announces a task (advertisement)
    2. Agents submit bids (offers)
    3. Manager evaluates bids and awards the contract
    4. Awardee acknowledges and executes
    """

    def __init__(self, *, bid_timeout: float = 5.0) -> None:
        self._bid_timeout = bid_timeout
        self._pending_tasks: dict[str, NegotiationSession] = {}
        self._contracts: dict[str, Contract] = {}

    async def announce_task(
        self,
        task_id: str,
        task_spec: dict[str, Any],
        eligible_agents: Sequence[str],
        *,
        deadline: float | None = None,
    ) -> NegotiationSession:
        """Announce a task and open bidding.

        Returns a NegotiationSession tracking the process.
        """
        session = NegotiationSession(
            task_id=task_id,
            participants=list(eligible_agents),
            state=NegotiationState.OPEN,
            deadline=deadline,
            started_at=_now(),
        )
        self._pending_tasks[task_id] = session
        self._pending_tasks[session.session_id] = session  # also index by session_id
        logger.info("CNP announced task %s (%d eligible agents)", task_id, len(eligible_agents))
        return session

    def submit_bid(
        self,
        session_id: str,
        proposer_id: str,
        terms: dict[str, Any],
        value: float = 0.5,
    ) -> Offer:
        """Submit a bid for a pending task announcement."""
        session = self._pending_tasks.get(session_id)
        if session is None:
            raise NegotiationError(f"No session {session_id}")

        if session.is_expired():
            session.state = NegotiationState.EXPIRED
            raise NegotiationTimeoutError(f"Session {session_id} expired")

        if proposer_id not in session.participants:
            raise NegotiationError(f"Agent {proposer_id} not eligible for session {session_id}")

        offer = Offer(
            session_id=session_id,
            proposer_id=proposer_id,
            terms=terms,
            value=value,
            round_number=session.current_round,
            expires_at=_now() + self._bid_timeout,
        )
        session.offers.append(offer)
        session.state = NegotiationState.BIDDING
        logger.debug("Agent %s bid %.2f on session %s", proposer_id, value, session_id)
        return offer

    def evaluate_and_award(self, session_id: str) -> Contract | None:
        """Evaluate all valid bids and award contract to the best bidder."""
        session = self._pending_tasks.get(session_id)
        if session is None:
            return None

        session.state = NegotiationState.EVALUATING

        # Filter valid, non-expired offers
        valid_offers = [o for o in session.offers if not o.is_expired() and not o.accepted]
        if not valid_offers:
            session.state = NegotiationState.REJECTED
            return None

        # Award to highest-value offer
        best_offer = max(valid_offers, key=lambda o: o.value)
        contract = Contract(
            parties=(best_offer.proposer_id,),
            terms=best_offer.terms,
            metadata={
                "session_id": session_id,
                "task_id": session.task_id,
                "award_value": best_offer.value,
            },
        )
        session.contracts.append(contract)
        session.state = NegotiationState.AGREED
        self._contracts[contract.contract_id] = contract

        logger.info("Awarded contract %s to %s (value=%.2f)", contract.contract_id, best_offer.proposer_id, best_offer.value)
        return contract

    def get_contract(self, contract_id: str) -> Contract | None:
        """Retrieve a contract by ID."""
        return self._contracts.get(contract_id)


# ---------------------------------------------------------------------------
# Multi-round Negotiator
# ---------------------------------------------------------------------------


class MultiRoundNegotiator:
    """Handles multi-round negotiation with offer/counter-offer strategies.

    Agents can make offers, respond with counter-offers, and converge
    toward an agreement over multiple rounds, with deadline enforcement.
    """

    def __init__(
        self,
        *,
        default_max_rounds: int = 10,
        concession_rate: float = 0.1,
    ) -> None:
        self._default_max_rounds = default_max_rounds
        self._concession_rate = concession_rate
        self._sessions: dict[str, NegotiationSession] = {}
        self._agreements: dict[str, Contract] = {}
        self._agent_strategies: dict[str, str] = {}

    def set_strategy(self, agent_id: str, strategy: str) -> None:
        """Set a negotiation strategy for an agent.

        Strategies: 'aggressive', 'cooperative', 'tit_for_tat', 'random'
        """
        self._agent_strategies[agent_id] = strategy

    async def start_negotiation(
        self,
        participants: Sequence[str],
        topic: str,
        *,
        max_rounds: int | None = None,
        deadline: float | None = None,
    ) -> NegotiationSession:
        """Open a multi-round negotiation session."""
        rounds = max_rounds or self._default_max_rounds
        session = NegotiationSession(
            task_id=topic,
            participants=list(participants),
            state=NegotiationState.OPEN,
            max_rounds=rounds,
            deadline=deadline or _now() + (rounds * 5.0),
        )
        self._sessions[session.session_id] = session
        logger.info("Started negotiation %s: %d participants", session.session_id, len(participants))
        return session

    def make_offer(
        self,
        session_id: str,
        proposer_id: str,
        terms: dict[str, Any],
        initial_value: float = 0.7,
    ) -> Offer:
        """Make an offer in a negotiation session."""
        session = self._sessions.get(session_id)
        if session is None:
            raise NegotiationError(f"No session {session_id}")

        if session.state in (NegotiationState.AGREED, NegotiationState.REJECTED, NegotiationState.EXPIRED):
            raise NegotiationError(f"Session {session_id} is {session.state.name}")

        if session.is_expired():
            session.state = NegotiationState.EXPIRED
            raise NegotiationTimeoutError(f"Session {session_id} expired")

        if session.current_round >= session.max_rounds:
            session.state = NegotiationState.REJECTED
            raise NegotiationError(f"Max rounds ({session.max_rounds}) reached")

        strategy = self._agent_strategies.get(proposer_id, "cooperative")
        adjusted_value = self._apply_strategy(strategy, initial_value, session.current_round)

        offer = Offer(
            session_id=session_id,
            proposer_id=proposer_id,
            terms=terms,
            value=adjusted_value,
            round_number=session.current_round,
            expires_at=_now() + 30.0,
        )
        session.offers.append(offer)
        return offer

    def counter_offer(
        self,
        session_id: str,
        original_offer_id: str,
        counter_proposer_id: str,
        terms: dict[str, Any],
        value: float,
    ) -> Offer:
        """Respond with a counter-offer."""
        session = self._sessions.get(session_id)
        if session is None:
            raise NegotiationError(f"No session {session_id}")

        session.state = NegotiationState.COUNTER_OFFER
        session.current_round += 1

        strategy = self._agent_strategies.get(counter_proposer_id, "cooperative")
        adjusted_value = self._apply_strategy(strategy, value, session.current_round)

        offer = Offer(
            session_id=session_id,
            proposer_id=counter_proposer_id,
            terms=terms,
            value=adjusted_value,
            round_number=session.current_round,
        )
        session.offers.append(offer)
        logger.debug("Counter-offer by %s in round %d of %s", counter_proposer_id, session.current_round, session_id)
        return offer

    def accept_offer(self, session_id: str, offer_id: str, acceptor_id: str) -> Contract:
        """Accept an offer and formalize the agreement."""
        session = self._sessions.get(session_id)
        if session is None:
            raise NegotiationError(f"No session {session_id}")

        # Find the offer
        target: Offer | None = None
        for o in session.offers:
            if o.offer_id == offer_id:
                target = o
                break

        if target is None:
            raise NegotiationError(f"Offer {offer_id} not found in session {session_id}")

        # Immutable dataclass: create new accepted version
        accepted_offer = Offer(
            offer_id=target.offer_id,
            session_id=target.session_id,
            proposer_id=target.proposer_id,
            terms=target.terms,
            value=target.value,
            round_number=target.round_number,
            accepted=True,
            accepted_by=acceptor_id,
        )
        # Replace in list
        for i, o in enumerate(session.offers):
            if o.offer_id == offer_id:
                session.offers[i] = accepted_offer
                break

        contract = Contract(
            parties=(target.proposer_id, acceptor_id),
            terms=target.terms,
            metadata={
                "session_id": session_id,
                "offer_id": offer_id,
                "round": target.round_number,
            },
        )
        session.contracts.append(contract)
        session.state = NegotiationState.AGREED
        self._agreements[contract.contract_id] = contract

        logger.info("Agreement reached in %s: %s accepted %s's offer", session_id, acceptor_id, target.proposer_id)
        return contract

    def reject_session(self, session_id: str) -> None:
        """Mark a negotiation session as rejected."""
        session = self._sessions.get(session_id)
        if session:
            session.state = NegotiationState.REJECTED

    def _apply_strategy(self, strategy: str, value: float, round_num: int) -> float:
        """Adjust offer value based on the agent's negotiation strategy."""
        if strategy == "aggressive":
            # Start high, make small concessions
            return max(0.1, value - self._concession_rate * 0.5 * round_num)
        elif strategy == "cooperative":
            # Make steady concessions
            return max(0.1, value - self._concession_rate * round_num)
        elif strategy == "tit_for_tat":
            # Mirror opponent's behavior (simplified: moderate concessions)
            return max(0.1, value - self._concession_rate * 0.75 * round_num)
        elif strategy == "random":
            import random
            return max(0.1, value + random.uniform(-0.2, 0.2))
        return value

    def get_session(self, session_id: str) -> NegotiationSession | None:
        """Get a negotiation session by ID."""
        return self._sessions.get(session_id)

    def get_agreement(self, contract_id: str) -> Contract | None:
        """Get a formalized agreement by ID."""
        return self._agreements.get(contract_id)

    def snapshot(self) -> dict[str, Any]:
        """Return current state snapshot."""
        return {
            "active_sessions": len(self._sessions),
            "agreements": len(self._agreements),
            "sessions": [
                {
                    "id": s.session_id,
                    "state": s.state.name,
                    "participants": len(s.participants),
                    "round": s.current_round,
                    "offers": len(s.offers),
                }
                for s in self._sessions.values()
            ],
        }


# ---------------------------------------------------------------------------
# Conflict Resolver
# ---------------------------------------------------------------------------


class ConflictResolver:
    """Resolves conflicts between agents using various strategies.

    Supports majority vote, authority override, mediation, random
    selection, and ranked-choice resolution.
    """

    def __init__(
        self,
        default_strategy: ConflictResolutionStrategy = ConflictResolutionStrategy.MAJORITY_VOTE,
    ) -> None:
        self._default_strategy = default_strategy
        self._conflicts: dict[str, dict[str, Any]] = {}
        self._resolutions: dict[str, dict[str, Any]] = []

    def register_conflict(
        self,
        conflict_id: str,
        description: str,
        parties: list[str],
        positions: dict[str, str],
        *,
        authority: str | None = None,
    ) -> None:
        """Register a conflict for resolution."""
        self._conflicts[conflict_id] = {
            "description": description,
            "parties": parties,
            "positions": positions,
            "authority": authority,
            "resolved": False,
            "resolution": None,
            "strategy": None,
        }
        logger.info("Conflict %s: %s (%d parties)", conflict_id, description, len(parties))

    def resolve(
        self,
        conflict_id: str,
        strategy: ConflictResolutionStrategy | None = None,
    ) -> dict[str, Any]:
        """Resolve a conflict using the specified or default strategy."""
        conflict = self._conflicts.get(conflict_id)
        if conflict is None:
            raise NegotiationError(f"Conflict {conflict_id} not found")

        if conflict["resolved"]:
            return conflict

        strat = strategy or self._default_strategy
        resolution: dict[str, Any]

        if strat == ConflictResolutionStrategy.MAJORITY_VOTE:
            resolution = self._resolve_majority(conflict)
        elif strat == ConflictResolutionStrategy.AUTHORITY_OVERRIDE:
            resolution = self._resolve_authority(conflict)
        elif strat == ConflictResolutionStrategy.MEDIATION:
            resolution = self._resolve_mediation(conflict)
        elif strat == ConflictResolutionStrategy.RANDOM_SELECTION:
            resolution = self._resolve_random(conflict)
        elif strat == ConflictResolutionStrategy.RANKED_CHOICE:
            resolution = self._resolve_ranked_choice(conflict)
        else:
            resolution = self._resolve_majority(conflict)

        conflict["resolved"] = True
        conflict["resolution"] = resolution
        conflict["strategy"] = strat.name
        self._resolutions.append(
            {"conflict_id": conflict_id, "resolution": resolution, "strategy": strat.name}
        )

        logger.info("Resolved conflict %s via %s: %s", conflict_id, strat.name, resolution["winner"])
        return resolution

    def _resolve_majority(self, conflict: dict[str, Any]) -> dict[str, Any]:
        """Resolve by majority vote."""
        positions: dict[str, str] = conflict["positions"]
        vote_counts: dict[str, int] = defaultdict(int)
        for pos in positions.values():
            vote_counts[pos] += 1

        winner = max(vote_counts, key=vote_counts.get)  # type: ignore[arg-type]
        total = len(positions)
        return {
            "winner": winner,
            "votes": vote_counts[winner],
            "total_votes": total,
            "method": "majority_vote",
        }

    def _resolve_authority(self, conflict: dict[str, Any]) -> dict[str, Any]:
        """Resolve by authority override."""
        authority = conflict.get("authority")
        positions: dict[str, str] = conflict["positions"]
        if authority and authority in positions:
            return {
                "winner": positions[authority],
                "method": "authority_override",
                "authority": authority,
            }
        # Fallback to majority if authority not in parties
        return self._resolve_majority(conflict)

    def _resolve_mediation(self, conflict: dict[str, Any]) -> dict[str, Any]:
        """Resolve by mediation: find middle ground or most centrist position."""
        positions: dict[str, str] = conflict["positions"]
        unique = list(set(positions.values()))
        # Pick the first unique position (simplified mediation)
        winner = unique[0] if unique else "unresolved"
        return {
            "winner": winner,
            "method": "mediation",
            "candidates": unique,
        }

    def _resolve_random(self, conflict: dict[str, Any]) -> dict[str, Any]:
        """Resolve by random selection."""
        import random
        positions: dict[str, str] = conflict["positions"]
        unique = list(set(positions.values()))
        winner = random.choice(unique) if unique else "unresolved"
        return {
            "winner": winner,
            "method": "random_selection",
        }

    def _resolve_ranked_choice(self, conflict: dict[str, Any]) -> dict[str, Any]:
        """Resolve by ranked-choice: eliminate least popular until majority."""
        positions: dict[str, str] = conflict["positions"]
        votes = list(positions.values())
        vote_counts: dict[str, int] = defaultdict(int)
        for v in votes:
            vote_counts[v] += 1

        winner = max(vote_counts, key=vote_counts.get) if vote_counts else "unresolved"  # type: ignore[arg-type]
        return {
            "winner": winner,
            "method": "ranked_choice",
            "rounds": 1,
        }

    def is_resolved(self, conflict_id: str) -> bool:
        """Check if a conflict has been resolved."""
        return self._conflicts.get(conflict_id, {}).get("resolved", False)

    def get_resolution(self, conflict_id: str) -> dict[str, Any] | None:
        """Get the resolution of a conflict."""
        return self._conflicts.get(conflict_id, {}).get("resolution")
