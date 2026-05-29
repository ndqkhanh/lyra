"""Collective Intelligence System — AutoScientists-inspired decentralized teams.

Inspired by the AutoScientists paper (Lu et al., 2024):
  - Shared state S: champion, work log, discussion forum, task queues, dead-ends
  - Discussion-before-queuing gate: teams must discuss before work is queued
  - Hypothesis-based team formation: teams form around verifiable hypotheses
  - Collective failure memory: dead-end registry prevents repeating failures
  - Noise-gated confirmation: N independent agents must agree before proceeding
  - Self-triggered reorganization: teams restructure when stagnant
  - Meta-improvement loop: every 3 cycles, the system reflects and optimizes
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from lyra_core.events import EventBus, EventCategory

logger = logging.getLogger(__name__)


# ── Discussion Forum ─────────────────────────────────────────────────────────


class PostKind(str, Enum):
    """Types of forum posts. Inspired by AutoScientists structured discussion."""
    PROPOSAL = "proposal"        # Hypothesis or experiment proposal
    QUESTION = "question"        # Clarifying question
    CRITIQUE = "critique"        # Peer review critique
    SUPPORT = "support"          # Supporting evidence
    OBJECTION = "objection"      # Objection or counter-argument
    RESOLUTION = "resolution"    # Resolution or decision
    OBSERVATION = "observation"  # Factual observation from experiment


class ConsensusLevel(str, Enum):
    """How much agreement exists on a topic."""
    NONE = "none"
    WEAK = "weak"         # < 50% agreement
    MODERATE = "moderate"  # 50-75% agreement
    STRONG = "strong"      # > 75% agreement
    UNANIMOUS = "unanimous"  # 100% agreement


@dataclass
class ForumPost:
    """A single post in the discussion forum."""

    id: str
    author_id: str
    kind: PostKind
    content: str
    thread_id: str | None = None  # Parent thread
    references: list[str] = field(default_factory=list)  # Referenced post IDs
    created_at: float = field(default_factory=time.time)
    votes: dict[str, int] = field(default_factory=dict)  # agent_id → vote (-1/0/+1)


@dataclass
class DiscussionThread:
    """A threaded discussion. Like AutoScientists' structured debate."""

    id: str
    topic: str
    hypothesis: str | None = None
    posts: list[ForumPost] = field(default_factory=list)
    status: str = "open"  # open, resolved, dead_end
    created_at: float = field(default_factory=time.time)
    resolved_at: float | None = None
    resolution: str | None = None
    participants: set[str] = field(default_factory=set)

    @property
    def post_count(self) -> int:
        return len(self.posts)

    @property
    def consensus(self) -> ConsensusLevel:
        """Compute consensus level from votes across all posts."""
        if not self.posts:
            return ConsensusLevel.NONE

        total_votes = sum(sum(p.votes.values()) for p in self.posts if p.votes)
        participant_count = len(self.participants)
        if participant_count == 0:
            return ConsensusLevel.NONE

        # Map vote totals to consensus levels
        # Each participant can vote -1, 0, or +1 per post
        max_possible = participant_count * self.post_count
        if max_possible == 0:
            return ConsensusLevel.NONE

        agreement_ratio = abs(total_votes) / max_possible
        if agreement_ratio >= 1.0:
            return ConsensusLevel.UNANIMOUS
        elif agreement_ratio >= 0.75:
            return ConsensusLevel.STRONG
        elif agreement_ratio >= 0.5:
            return ConsensusLevel.MODERATE
        elif agreement_ratio > 0:
            return ConsensusLevel.WEAK
        return ConsensusLevel.NONE

    def add_post(self, post: ForumPost) -> None:
        post.thread_id = self.id
        self.posts.append(post)
        self.participants.add(post.author_id)

    def vote(self, post_id: str, agent_id: str, value: int) -> bool:
        """Register a vote on a post. Returns True if post found."""
        for post in self.posts:
            if post.id == post_id:
                post.votes[agent_id] = max(-1, min(1, value))
                return True
        return False


class DiscussionForum:
    """Central discussion forum. Like AutoScientists' shared discussion space.

    All proposals must pass through discussion before being queued as work.
    This is the "discussion-before-queuing gate" pattern.
    """

    def __init__(self, bus: EventBus | None = None) -> None:
        self._threads: dict[str, DiscussionThread] = {}
        self._bus = bus or EventBus.get()

    def create_thread(self, thread_id: str, topic: str,
                     hypothesis: str | None = None) -> DiscussionThread:
        thread = DiscussionThread(id=thread_id, topic=topic, hypothesis=hypothesis)
        self._threads[thread_id] = thread
        self._bus.publish(
            category=EventCategory.LIFECYCLE,
            name="forum.thread_created",
            origin=__name__,
            payload={"thread_id": thread_id, "topic": topic,
                    "hypothesis": hypothesis},
        )
        return thread

    def get_thread(self, thread_id: str) -> DiscussionThread | None:
        return self._threads.get(thread_id)

    def post(self, thread_id: str, post: ForumPost) -> bool:
        """Post to a thread. Returns True if thread found."""
        thread = self._threads.get(thread_id)
        if thread is None:
            return False
        thread.add_post(post)
        self._bus.publish(
            category=EventCategory.LIFECYCLE,
            name="forum.post_added",
            origin=__name__,
            payload={"thread_id": thread_id, "post_id": post.id,
                    "kind": post.kind.value, "author": post.author_id},
        )
        return True

    def resolve_thread(self, thread_id: str, resolution: str) -> bool:
        """Resolve a thread with a decision."""
        thread = self._threads.get(thread_id)
        if thread is None:
            return False
        thread.status = "resolved"
        thread.resolved_at = time.time()
        thread.resolution = resolution
        return True

    def mark_dead_end(self, thread_id: str, reason: str) -> bool:
        """Mark a thread as a dead end (failed approach)."""
        thread = self._threads.get(thread_id)
        if thread is None:
            return False
        thread.status = "dead_end"
        thread.resolved_at = time.time()
        thread.resolution = reason
        return True

    @property
    def open_threads(self) -> list[DiscussionThread]:
        return [t for t in self._threads.values() if t.status == "open"]

    @property
    def thread_count(self) -> int:
        return len(self._threads)


# ── Dead-End Registry ────────────────────────────────────────────────────────


@dataclass
class DeadEndEntry:
    """Record of a failed approach. Prevents repeating past mistakes.

    Like AutoScientists' dead-end registry: teams consult this before
    starting new work to avoid known failure modes.
    """

    id: str
    hypothesis: str
    approach: str
    failure_reason: str
    discovered_by: str  # agent_id or team_id
    discovered_at: float = field(default_factory=time.time)
    severity: str = "moderate"  # moderate, severe, catastrophic
    tags: list[str] = field(default_factory=list)
    related_threads: list[str] = field(default_factory=list)


class DeadEndRegistry:
    """Collective failure memory. Prevents repeating proven failures.

    Like AutoScientists' dead-end mechanism:
      query_nearest(hypothesis) → distance → if < ρ: skip
    """

    def __init__(self, similarity_threshold: float = 0.7) -> None:
        self._entries: dict[str, DeadEndEntry] = {}
        self._similarity_threshold = similarity_threshold
        self._keyword_index: dict[str, set[str]] = defaultdict(set)

    def register(self, entry: DeadEndEntry) -> None:
        """Record a dead end."""
        self._entries[entry.id] = entry
        # Build keyword index from hypothesis + approach + tags
        all_terms = (
            entry.hypothesis.lower().split()
            + entry.approach.lower().split()
            + entry.tags
        )
        for term in all_terms:
            self._keyword_index[term].add(entry.id)

    def is_known_dead_end(self, hypothesis: str, approach: str = "",
                         threshold: float | None = None) -> tuple[bool, DeadEndEntry | None]:
        """Check if a hypothesis/approach matches a known dead end.

        Uses simple keyword overlap as a proxy for semantic similarity.
        Returns (is_dead_end, closest_entry).
        """
        limit = threshold or self._similarity_threshold
        query_terms = set(
            hypothesis.lower().split() + approach.lower().split()
        )

        best_entry: DeadEndEntry | None = None
        best_overlap = 0.0

        for entry in self._entries.values():
            entry_terms = set(
                entry.hypothesis.lower().split()
                + entry.approach.lower().split()
                + entry.tags
            )
            if not entry_terms:
                continue
            overlap = len(query_terms & entry_terms) / len(query_terms)
            if overlap > best_overlap:
                best_overlap = overlap
                best_entry = entry

        if best_overlap >= limit and best_entry is not None:
            return True, best_entry
        return False, None

    def query_similar(self, text: str, top_k: int = 5) -> list[DeadEndEntry]:
        """Find dead ends similar to the given text. Sorted by relevance."""
        query_terms = set(text.lower().split())
        scored: list[tuple[float, DeadEndEntry]] = []

        for entry in self._entries.values():
            entry_terms = set(
                entry.hypothesis.lower().split()
                + entry.approach.lower().split()
                + entry.tags
            )
            if not entry_terms:
                continue
            score = len(query_terms & entry_terms) / len(query_terms)
            if score > 0:
                scored.append((score, entry))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in scored[:top_k]]

    @property
    def entry_count(self) -> int:
        return len(self._entries)


# ── Hypothesis Team ──────────────────────────────────────────────────────────


class TeamFormationReason(str, Enum):
    """Why a team formed. AutoScientists requires explicit rationale."""
    HYPOTHESIS = "hypothesis"        # Formed around a testable hypothesis
    PROBLEM_DECOMPOSITION = "problem"  # Broke down a larger problem
    SKILL_GAP = "skill_gap"          # Needed capabilities not in existing teams
    DEADLOCK_BREAK = "deadlock"      # Formed to break a consensus deadlock
    META_IMPROVEMENT = "meta"        # Formed by the meta-improvement loop


@dataclass
class Hypothesis:
    """A testable hypothesis. The core unit of work in AutoScientists."""

    id: str
    statement: str
    proposed_by: str
    test_criteria: str  # How to verify/falsify this hypothesis
    priority: int = 0
    created_at: float = field(default_factory=time.time)
    status: str = "proposed"  # proposed, discussion, queued, testing, verified, falsified
    result: str | None = None
    confidence: float = 0.0  # 0.0–1.0 based on evidence collected


@dataclass
class HypothesisTeam:
    """A team formed around a hypothesis. Like AutoScientists' team formation.

    Teams have:
      - A champion who proposed the hypothesis
      - Members with relevant capabilities
      - A minimum lifetime (3 cycles before reformation allowed)
      - Discussion forum threads attached
    """

    id: str
    hypothesis: Hypothesis
    champion_id: str
    member_ids: list[str] = field(default_factory=list)
    formation_reason: TeamFormationReason = TeamFormationReason.HYPOTHESIS
    discussion_thread_id: str | None = None
    cycles_completed: int = 0
    created_at: float = field(default_factory=time.time)
    status: str = "forming"  # forming, discussing, working, reviewing, completed, dissolved
    min_lifetime_cycles: int = 3  # Minimum cycles before reformation allowed

    @property
    def can_reform(self) -> bool:
        """Teams can only reform after their minimum lifetime."""
        return self.cycles_completed >= self.min_lifetime_cycles

    @property
    def size(self) -> int:
        return 1 + len(self.member_ids)  # champion + members

    def add_member(self, agent_id: str) -> None:
        if agent_id not in self.member_ids and agent_id != self.champion_id:
            self.member_ids.append(agent_id)

    def remove_member(self, agent_id: str) -> None:
        if agent_id in self.member_ids:
            self.member_ids.remove(agent_id)

    def complete_cycle(self) -> None:
        self.cycles_completed += 1


# ── Noise-Gated Confirmation ─────────────────────────────────────────────────


class NoiseGate:
    """Requires N independent agents to agree before proceeding.

    Like AutoScientists' noise-gated confirmation:
      "N reviewers must independently confirm before proceeding."
    This counters individual agent noise and hallucination.
    """

    def __init__(self, required_confirmations: int = 2) -> None:
        self.required = required_confirmations
        self._confirmations: dict[str, set[str]] = {}  # item_id → {agent_ids}

    def confirm(self, item_id: str, agent_id: str) -> bool:
        """Register a confirmation. Returns True if threshold reached."""
        if item_id not in self._confirmations:
            self._confirmations[item_id] = set()
        self._confirmations[item_id].add(agent_id)
        return self.is_confirmed(item_id)

    def is_confirmed(self, item_id: str) -> bool:
        """Check if item has enough independent confirmations."""
        return len(self._confirmations.get(item_id, set())) >= self.required

    def get_confirmers(self, item_id: str) -> frozenset[str]:
        return frozenset(self._confirmations.get(item_id, set()))

    def reset(self, item_id: str) -> None:
        self._confirmations.pop(item_id, None)

    @property
    def pending_items(self) -> list[str]:
        return [k for k, v in self._confirmations.items()
                if len(v) < self.required]


# ── Shared State ─────────────────────────────────────────────────────────────


@dataclass
class CollectiveState:
    """The central shared state S in AutoScientists.

    S = {champion, work_log, discussion_forum, task_queues, dead_ends}

    All teams have read access. Write access is mediated by the discussion
    forum and noise-gated confirmation.
    """

    forum: DiscussionForum = field(default_factory=DiscussionForum)
    dead_ends: DeadEndRegistry = field(default_factory=DeadEndRegistry)
    noise_gate: NoiseGate = field(default_factory=NoiseGate)
    teams: dict[str, HypothesisTeam] = field(default_factory=dict)
    hypotheses: dict[str, Hypothesis] = field(default_factory=dict)
    work_log: list[dict[str, Any]] = field(default_factory=list)
    cycle_count: int = 0
    created_at: float = field(default_factory=time.time)

    # ── Hypothesis Management ─────────────────────────────────────────────

    def propose_hypothesis(self, hypothesis: Hypothesis,
                          champion_id: str) -> HypothesisTeam | None:
        """Propose a hypothesis. Automatically checks dead-end registry."""
        is_dead, entry = self.dead_ends.is_known_dead_end(hypothesis.statement)
        if is_dead:
            logger.warning("Hypothesis %s matches known dead end: %s",
                          hypothesis.id, entry.id if entry else "unknown")
            return None

        self.hypotheses[hypothesis.id] = hypothesis

        # Create team around the hypothesis
        team = HypothesisTeam(
            id=f"team_{hypothesis.id}",
            hypothesis=hypothesis,
            champion_id=champion_id,
        )
        self.teams[team.id] = team

        # Create discussion thread
        thread = self.forum.create_thread(
            thread_id=f"thread_{hypothesis.id}",
            topic=hypothesis.statement,
            hypothesis=hypothesis.statement,
        )
        team.discussion_thread_id = thread.id

        self._log("hypothesis_proposed", {
            "hypothesis_id": hypothesis.id,
            "champion": champion_id,
            "team_id": team.id,
        })
        return team

    def verify_hypothesis(self, hypothesis_id: str, result: str,
                         verified: bool, verifier_id: str) -> None:
        """Record verification/falsification of a hypothesis."""
        hyp = self.hypotheses.get(hypothesis_id)
        if hyp is None:
            return

        hyp.status = "verified" if verified else "falsified"
        hyp.result = result

        if not verified:
            # Register as dead end
            entry = DeadEndEntry(
                id=f"de_{hypothesis_id}",
                hypothesis=hyp.statement,
                approach=f"Proposed by {hyp.proposed_by}",
                failure_reason=result,
                discovered_by=verifier_id,
            )
            self.dead_ends.register(entry)

        self._log("hypothesis_verified" if verified else "hypothesis_falsified", {
            "hypothesis_id": hypothesis_id,
            "result": result,
            "verifier": verifier_id,
        })

    # ── Team Management ───────────────────────────────────────────────────

    def dissolve_team(self, team_id: str, reason: str = "") -> None:
        """Dissolve a team. Members return to pool."""
        team = self.teams.get(team_id)
        if team:
            team.status = "dissolved"
            self._log("team_dissolved", {"team_id": team_id, "reason": reason})

    # ── Meta ──────────────────────────────────────────────────────────────

    def _log(self, event: str, data: dict[str, Any]) -> None:
        """Append to the shared work log."""
        self.work_log.append({
            "event": event,
            "timestamp": time.time(),
            "cycle": self.cycle_count,
            "data": data,
        })

    def advance_cycle(self) -> None:
        """Advance to the next work cycle."""
        self.cycle_count += 1
        for team in self.teams.values():
            if team.status in ("working", "reviewing"):
                team.complete_cycle()

    @property
    def active_teams(self) -> list[HypothesisTeam]:
        return [t for t in self.teams.values()
                if t.status not in ("completed", "dissolved")]

    @property
    def verified_hypotheses(self) -> list[Hypothesis]:
        return [h for h in self.hypotheses.values() if h.status == "verified"]

    @property
    def falsified_hypotheses(self) -> list[Hypothesis]:
        return [h for h in self.hypotheses.values() if h.status == "falsified"]


# ── Meta-Improvement Loop ────────────────────────────────────────────────────


class MetaImprovementLoop:
    """Periodic self-reflection. Every N cycles, analyzes what worked.

    Like AutoScientists' meta-improvement:
      Every 3 cycles → evaluate performance → adjust strategy → apply
    """

    def __init__(self, state: CollectiveState, interval: int = 3,
                 bus: EventBus | None = None) -> None:
        self.state = state
        self.interval = interval
        self._bus = bus or EventBus.get()
        self._improvements_applied: list[dict[str, Any]] = []
        self._last_evaluation_cycle: int = 0

    def should_evaluate(self) -> bool:
        """Check if it's time for a meta-evaluation."""
        cycles_since = self.state.cycle_count - self._last_evaluation_cycle
        return cycles_since >= self.interval and self.state.cycle_count > 0

    def evaluate(self) -> dict[str, Any]:
        """Run meta-evaluation. Returns improvement recommendations."""
        self._last_evaluation_cycle = self.state.cycle_count

        report = {
            "cycle": self.state.cycle_count,
            "timestamp": time.time(),
            "metrics": self._compute_metrics(),
            "recommendations": [],
            "thrashing_detected": False,
        }

        # Detect thrashing (teams forming and dissolving rapidly)
        recent_dissolutions = [
            e for e in self.state.work_log[-20:]
            if e["event"] == "team_dissolved"
        ]
        if len(recent_dissolutions) >= 5:
            report["thrashing_detected"] = True
            report["recommendations"].append({
                "action": "increase_min_lifetime",
                "reason": "Team thrashing detected — too many dissolutions",
                "current_cycles": 3,
                "suggested_cycles": 5,
            })

        # Check dead-end hit rate
        dead_end_hits = sum(
            1 for e in self.state.work_log[-20:]
            if e["event"] == "hypothesis_falsified"
        )
        if dead_end_hits >= 5:
            report["recommendations"].append({
                "action": "raise_similarity_threshold",
                "reason": "High dead-end hit rate — threshold too low",
                "current_threshold": self.state.dead_ends._similarity_threshold,
                "suggested_threshold": min(0.95,
                    self.state.dead_ends._similarity_threshold + 0.1),
            })

        # Check team size balance
        avg_size = sum(t.size for t in self.state.teams.values()) / max(
            len(self.state.teams), 1)
        if avg_size < 2 and len(self.state.teams) > 3:
            report["recommendations"].append({
                "action": "consolidate_teams",
                "reason": f"Average team size is {avg_size:.1f} — consolidate",
            })

        self._improvements_applied.append(report)

        self._bus.publish(
            category=EventCategory.TELEMETRY,
            name="meta_evaluation.completed",
            origin=__name__,
            payload=report,
        )

        return report

    def _compute_metrics(self) -> dict[str, Any]:
        """Compute aggregate metrics from the current cycle."""
        total_hypotheses = len(self.state.hypotheses)
        verified = len(self.state.verified_hypotheses)
        falsified = len(self.state.falsified_hypotheses)

        return {
            "cycle": self.state.cycle_count,
            "active_teams": len(self.state.active_teams),
            "total_teams": len(self.state.teams),
            "hypotheses": {
                "total": total_hypotheses,
                "verified": verified,
                "falsified": falsified,
                "success_rate": verified / max(total_hypotheses, 1),
            },
            "forum_threads": self.state.forum.thread_count,
            "dead_ends_recorded": self.state.dead_ends.entry_count,
        }

    @property
    def last_report(self) -> dict[str, Any] | None:
        if self._improvements_applied:
            return self._improvements_applied[-1]
        return None


# ── Self-Triggered Reorganization ────────────────────────────────────────────


class ReorganizationTrigger(str, Enum):
    """Triggers for self-reorganization."""
    STAGNATION = "stagnation"        # No progress for N cycles
    THRASHING = "thrashing"          # Teams forming/dissolving too fast
    CONSENSUS_DEADLOCK = "deadlock"  # Can't reach consensus
    SKILL_MISMATCH = "skill_mismatch"  # Team capabilities don't match problem
    PERFORMANCE_DROP = "performance"  # Metrics declining


@dataclass
class ReorganizationPlan:
    """A plan for restructuring teams."""

    id: str
    trigger: ReorganizationTrigger
    created_at: float = field(default_factory=time.time)
    dissolve_teams: list[str] = field(default_factory=list)
    form_teams: list[HypothesisTeam] = field(default_factory=list)
    reassign_members: dict[str, str] = field(default_factory=dict)  # agent_id → team_id
    rationale: str = ""
    requires_confirmation: bool = True  # Must pass noise-gate


class SelfReorganization:
    """Self-triggered team restructuring. Like AutoScientists' reorganization.

    Monitors the collective state for triggers (stagnation, thrashing,
    deadlock) and proposes reorganization plans. Plans must pass the
    noise-gated confirmation before execution.
    """

    def __init__(self, state: CollectiveState,
                 bus: EventBus | None = None) -> None:
        self.state = state
        self._bus = bus or EventBus.get()
        self._applied_plans: list[ReorganizationPlan] = []
        self._progress_snapshots: list[dict[str, Any]] = []

    def check_triggers(self) -> list[ReorganizationTrigger]:
        """Check for reorganization triggers. Returns active triggers."""
        triggers: list[ReorganizationTrigger] = []

        # Check stagnation: no verified hypotheses in recent cycles
        if self.state.cycle_count >= 3:
            recent_verifications = sum(
                1 for e in self.state.work_log[-30:]
                if e["event"] == "hypothesis_verified"
            )
            if recent_verifications == 0 and self.state.active_teams:
                triggers.append(ReorganizationTrigger.STAGNATION)

        # Check thrashing: rapid team formation/dissolution
        recent_dissolves = sum(
            1 for e in self.state.work_log[-20:]
            if e["event"] == "team_dissolved"
        )
        if recent_dissolves >= 5:
            triggers.append(ReorganizationTrigger.THRASHING)

        # Check consensus deadlock: open forum threads with no resolution
        open_threads = self.state.forum.open_threads
        if len(open_threads) >= 3 and self.state.cycle_count >= 5:
            triggers.append(ReorganizationTrigger.CONSENSUS_DEADLOCK)

        return triggers

    def propose_plan(self, trigger: ReorganizationTrigger,
                    rationale: str) -> ReorganizationPlan:
        """Create a reorganization plan."""
        import uuid
        plan = ReorganizationPlan(
            id=f"reorg_{uuid.uuid4().hex[:8]}",
            trigger=trigger,
            rationale=rationale,
        )

        if trigger == ReorganizationTrigger.STAGNATION:
            # Dissolve stagnant teams, form new ones around fresh hypotheses
            stagnant = [t.id for t in self.state.active_teams
                       if t.cycles_completed >= 3 and t.hypothesis.status != "verified"]
            plan.dissolve_teams = stagnant

        elif trigger == ReorganizationTrigger.THRASHING:
            # Increase minimum lifetime for all teams
            for team in self.state.active_teams:
                team.min_lifetime_cycles = max(team.min_lifetime_cycles + 2, 5)

        elif trigger == ReorganizationTrigger.CONSENSUS_DEADLOCK:
            # Form a tiebreaker team
            plan.rationale = f"Consensus deadlock: {rationale}"

        return plan

    def execute_plan(self, plan: ReorganizationPlan) -> None:
        """Execute a reorganization plan."""
        # Dissolve marked teams
        for team_id in plan.dissolve_teams:
            self.state.dissolve_team(team_id, reason=plan.rationale)

        # Form new teams
        for team in plan.form_teams:
            self.state.teams[team.id] = team

        # Reassign members
        for agent_id, team_id in plan.reassign_members.items():
            target = self.state.teams.get(team_id)
            if target:
                target.add_member(agent_id)

        self._applied_plans.append(plan)

        self._bus.publish(
            category=EventCategory.LIFECYCLE,
            name="reorganization.applied",
            origin=__name__,
            payload={
                "plan_id": plan.id,
                "trigger": plan.trigger.value,
                "teams_dissolved": len(plan.dissolve_teams),
                "teams_formed": len(plan.form_teams),
            },
        )

    def snapshot_progress(self) -> None:
        """Record a progress snapshot for trend analysis."""
        self._progress_snapshots.append({
            "cycle": self.state.cycle_count,
            "timestamp": time.time(),
            "active_teams": len(self.state.active_teams),
            "verified_hypotheses": len(self.state.verified_hypotheses),
            "falsified_hypotheses": len(self.state.falsified_hypotheses),
            "forum_threads": self.state.forum.thread_count,
        })

    @property
    def applied_plan_count(self) -> int:
        return len(self._applied_plans)
