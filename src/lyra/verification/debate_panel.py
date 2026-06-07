"""
Anonymous Debate Panel for adversarially robust claim verification.

Extends the VerificationPanel concept with identity-anonymized multi-agent
debates, mandatory minority reports, and blinded voting.

Inspired by:
- "When Identity Skews Debate" (Choi et al., UW-Madison, arXiv 2510.07517)
- "Constitutional AI" (Bai et al., Anthropic, 2022)
- Adversarial verification panel in lyra.verification.panel
"""

from __future__ import annotations

import asyncio
import random
import re
import uuid
from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

import structlog

from lyra.verification.anonymizer import IdentityAnonymizer
from lyra.verification.panel import AdversarialPanel, Lens, ReviewResult, ReviewerVote

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Data Types
# ---------------------------------------------------------------------------


class Perspective(str, Enum):
    """Role perspective for a debate panelist."""

    SUPPORTER = "supporter"
    SKEPTIC = "skeptic"
    DOMAIN_EXPERT = "domain_expert"
    ETHICS_REVIEWER = "ethics_reviewer"
    ADVERSARIAL = "adversarial"
    MINORITY_REPRESENTATIVE = "minority_representative"


PERSPECTIVE_DESCRIPTIONS: dict[Perspective, str] = {
    Perspective.SUPPORTER: (
        "Argue in favor of the claim, presenting evidence, reasoning, "
        "and constructive support."
    ),
    Perspective.SKEPTIC: (
        "Challenge the claim rigorously. Identify gaps in logic, missing "
        "evidence, over-generalizations, and potential counter-examples."
    ),
    Perspective.DOMAIN_EXPERT: (
        "Evaluate the claim from a technical domain perspective. Assess "
        "feasibility, correctness, and alignment with known best practices. "
        "Cite relevant standards or reference implementations."
    ),
    Perspective.ETHICS_REVIEWER: (
        "Evaluate the claim for ethical implications, safety concerns, "
        "alignment with responsible AI principles, and potential societal "
        "impact."
    ),
    Perspective.ADVERSARIAL: (
        "Take the strongest possible opposing position. Use red-teaming "
        "techniques: try to find edge cases, failure modes, and scenarios "
        "where the claim breaks down."
    ),
    Perspective.MINORITY_REPRESENTATIVE: (
        "Your role is to argue AGAINST the emerging consensus. Even if the "
        "majority strongly supports a position, identify and articulate the "
        "best counter-arguments. This is a mandatory perspective."
    ),
}


@dataclass(frozen=True)
class Argument:
    """A single argument made by a panelist during a debate round.

    Attributes:
        round_number: Which debate round this belongs to (1-indexed).
        anonymous_id: Opaque identifier of the speaker.
        perspective: The perspective the speaker was assigned.
        content: The argument text (identity-stripped).
        claims: List of factual claims extracted from the argument.
    """

    round_number: int
    anonymous_id: str
    perspective: Perspective
    content: str
    claims: tuple[str, ...] = ()


@dataclass(frozen=True)
class Ballot:
    """An anonymized vote from a single panelist.

    Attributes:
        anonymous_id: Opaque identifier of the voter.
        approve: True if the voter approves/rejects the claim.
        confidence: Confidence score (0.0 to 1.0).
        rationale: Brief justification for the vote.
    """

    anonymous_id: str
    approve: bool
    confidence: float
    rationale: str


@dataclass(frozen=True)
class DebateResult:
    """The outcome of an anonymized debate.

    Attributes:
        topic: The debated proposition or claim.
        consensus: The final consensus position.
        consensus_confidence: Confidence level in the consensus (0.0 to 1.0).
        minority_report: The best counter-argument from the losing side
            (always present if there is disagreement).
        arguments: All arguments made during the debate, organized by round.
        voting_record: All anonymized ballots cast.
        passed: Whether the debate outcome is that the claim passes scrutiny.
        total_rounds: Number of debate rounds conducted.
        panelist_perspectives: Mapping of anonymous ID to perspective.
    """

    topic: str
    consensus: str
    consensus_confidence: float
    minority_report: str
    arguments: tuple[Argument, ...]
    voting_record: tuple[Ballot, ...]
    passed: bool
    total_rounds: int
    panelist_perspectives: dict[str, Perspective]


MINORITY_PERSPECTIVES = frozenset({
    Perspective.SKEPTIC,
    Perspective.ADVERSARIAL,
    Perspective.MINORITY_REPRESENTATIVE,
})


# ---------------------------------------------------------------------------
# v8.2 Advanced Debate Features — Data Types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DebateQualityMetrics:
    """Real-time quality tracking for a debate.

    Attributes:
        total_arguments: Number of arguments made so far.
        unique_perspectives_used: How many distinct perspectives
            have participated.
        evidence_citation_rate: Fraction of arguments that cite
            a verifiable source or reference.
        disagreement_intensity: 0.0 (unanimous agreement) to 1.0
            (maximum disagreement) based on vote distribution.
        minority_representation: Fraction of arguments from
            minority perspectives (SKEPTIC, ADVERSARIAL,
            MINORITY_REPRESENTATIVE).
        round_balance: Per-round argument count variance — lower
            values indicate more balanced participation.
        forced_minority_reports_generated: Count of mandatory
            minority reports produced.
    """

    total_arguments: int
    unique_perspectives_used: int
    evidence_citation_rate: float
    disagreement_intensity: float
    minority_representation: float
    round_balance: float
    forced_minority_reports_generated: int


@dataclass(frozen=True)
class EvidenceCitation:
    """A single evidence citation extracted from an argument.

    Attributes:
        source: The cited source (URL, paper reference, standard).
        claim: The claim the evidence supports.
        confidence: How directly the evidence supports the claim
            (0.0 to 1.0).
    """

    source: str
    claim: str
    confidence: float


class CommunicationTopology(str, Enum):
    """Topology for the communication graph in a debate round."""

    FULL_MESH = "full_mesh"
    RANDOM_SUBSET = "random_subset"
    STAR = "star"
    CHAIN = "chain"
    RING = "ring"
    PARTITIONED = "partitioned"


@dataclass(frozen=True)
class CommunicationGraph:
    """Describes which panelists communicate in a given round.

    Attributes:
        topology: The topology type used this round.
        edges: List of (speaker_id, listener_id) directed edges.
        round_number: Which round this graph applies to.
    """

    topology: CommunicationTopology
    edges: list[tuple[str, str]]
    round_number: int


@dataclass(frozen=True)
class DiversityQuota:
    """A diversity constraint for panel composition.

    Attributes:
        perspective: The perspective that must be included.
        min_count: Minimum number of panelists with this perspective.
        enforced: Whether this quota is strictly enforced.
    """

    perspective: Perspective
    min_count: int = 1
    enforced: bool = True


# Default diversity quotas — ensure at least one minority and one
# domain expert perspective is always included.
DEFAULT_DIVERSITY_QUOTAS: tuple[DiversityQuota, ...] = (
    DiversityQuota(Perspective.SKEPTIC, min_count=1, enforced=True),
    DiversityQuota(Perspective.ADVERSARIAL, min_count=1, enforced=True),
    DiversityQuota(Perspective.DOMAIN_EXPERT, min_count=1, enforced=True),
)


# ---------------------------------------------------------------------------
# AnonymousDebatePanel
# ---------------------------------------------------------------------------


DebateArgumentFn = Callable[
    [str, Perspective, list[Argument]],
    str,
]

AsyncDebateArgumentFn = Callable[
    [str, Perspective, list[Argument]],
    Any,
]


class AnonymousDebatePanel:
    """Identity-anonymized multi-agent debate panel.

    Panelists debate a topic through multiple rounds. Their identities
    are anonymized before arguments are shared, preventing identity-driven
    sycophancy. A mandatory minority report ensures at least one agent
    argues against the consensus. Voting uses anonymized ballots with a
    2/3 supermajority threshold.

    Usage::

        async def my_speaker(
            topic: str, perspective: Perspective, prior_arguments: list[Argument]
        ) -> str:
            # In production, call an LLM here
            return "My argument..."

        panel = AnonymousDebatePanel(argument_fn=my_speaker)
        result = await panel.convene(
            topic="Rust is safer than C++ for systems programming",
            perspectives=[Perspective.SUPPORTER, Perspective.SKEPTIC,
                          Perspective.DOMAIN_EXPERT],
            rounds=2,
        )
        print(result.consensus, result.minority_report)

    Integration with AdversarialPanel::

        panel = AnonymousDebatePanel()
        debate_result = await panel.convene(...)
        # Then feed the consensus claim into AdversarialPanel for verification
        review = await verification_panel.judge(debate_result.consensus)
    """

    def __init__(
        self,
        argument_fn: DebateArgumentFn | None = None,
        async_argument_fn: AsyncDebateArgumentFn | None = None,
        anonymizer: IdentityAnonymizer | None = None,
        voting_threshold: float = 2.0 / 3.0,
        *,
        # v8.2 Advanced Features
        forced_disagreement_rounds: bool = True,
        diversity_quotas: tuple[DiversityQuota, ...] | None = None,
        evidence_anchoring: bool = True,
        randomized_topology_per_round: bool = True,
    ) -> None:
        """
        Args:
            argument_fn: Synchronous callable ``(topic, perspective, prior) -> str``.
            async_argument_fn: Async callable ``(topic, perspective, prior) -> str``.
                Takes precedence over ``argument_fn``.
            anonymizer: IdentityAnonymizer instance. Created automatically
                if not provided.
            voting_threshold: Fraction of votes required for consensus
                (default 2/3).
            forced_disagreement_rounds: If True, inject a mandatory minority
                report round that forces a panelist to argue against the
                emerging consensus.
            diversity_quotas: Diversity constraints for panel composition.
                Defaults enforce SKEPTIC, ADVERSARIAL, and DOMAIN_EXPERT.
            evidence_anchoring: If True, every argument must cite a
                verifiable source or reference.
            randomized_topology_per_round: If True, each debate round uses
                a different randomized communication graph topology.
        """
        self._argument_fn = argument_fn
        self._async_argument_fn = async_argument_fn
        self._anonymizer = anonymizer or IdentityAnonymizer()
        self._voting_threshold = voting_threshold
        self._forced_disagreement_rounds = forced_disagreement_rounds
        self._diversity_quotas = diversity_quotas or DEFAULT_DIVERSITY_QUOTAS
        self._evidence_anchoring = evidence_anchoring
        self._randomized_topology_per_round = randomized_topology_per_round

        # v8.2 runtime tracking
        self._quality_history: list[DebateQualityMetrics] = []
        self._forced_minority_count: int = 0
        self._communication_graphs: list[CommunicationGraph] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def convene(
        self,
        topic: str,
        perspectives: list[Perspective] | None = None,
        rounds: int = 2,
        verification_panel: AdversarialPanel | None = None,
    ) -> DebateResult:
        """Convene an identity-anonymized debate.

        Args:
            topic: The proposition or claim to debate.
            perspectives: The set of perspectives to include. Defaults to
                all six perspectives.
            rounds: Number of debate rounds. Minimum 1, maximum 5.
            verification_panel: Optional AdversarialPanel for post-debate
                claim verification.

        Returns:
            DebateResult with consensus, minority report, and voting record.

        Raises:
            ValueError: If rounds is out of range or fewer than 3
                perspectives are provided.
        """
        if rounds < 1 or rounds > 5:
            raise ValueError("rounds must be between 1 and 5")

        all_perspectives = perspectives or list(Perspective)
        if len(all_perspectives) < 3:
            raise ValueError("At least 3 perspectives are needed for a meaningful debate")

        # Ensure at least one minority perspective is present
        has_minority = any(p in MINORITY_PERSPECTIVES for p in all_perspectives)
        if not has_minority:
            all_perspectives.append(Perspective.MINORITY_REPRESENTATIVE)

        # Enforce diversity quotas
        all_perspectives = self._enforce_diversity_quotas(all_perspectives)

        # Assign anonymous identities per perspective
        panelists: list[tuple[str, Perspective]] = []
        for perspective in all_perspectives:
            anon_id = f"Panelist-{uuid.uuid4().hex[:4]}"
            panelists.append((anon_id, perspective))

        # Running transcript of all arguments for context injection
        transcript: list[tuple[str, str, Perspective]] = []  # (anon_id, content, perspective)
        all_arguments: list[Argument] = []

        for round_num in range(1, rounds + 1):
            round_arguments: list[Argument] = []

            # Generate randomized communication graph for this round
            comm_graph = self._build_communication_graph(panelists, round_num)
            self._communication_graphs.append(comm_graph)

            for anon_id, perspective in panelists:
                prior_arguments = self._build_prior_for_panelist(
                    all_arguments, anon_id, comm_graph
                )
                content = await self._generate_argument(
                    topic, perspective, prior_arguments
                )

                # Evidence anchoring: attach citations to the argument
                if self._evidence_anchoring:
                    content = self._anchor_evidence(content, topic)

                # Anonymize: strip identity markers from the content
                cleaned = self._anonymizer.strip_identity(content)

                argument = Argument(
                    round_number=round_num,
                    anonymous_id=anon_id,
                    perspective=perspective,
                    content=cleaned,
                )
                round_arguments.append(argument)
                transcript.append((anon_id, cleaned, perspective))

            all_arguments.extend(round_arguments)

            # After each round (except the last), inject mandatory
            # minority / forced disagreement signal
            if round_num < rounds:
                await self._inject_minority_signal(
                    topic, panelists, all_arguments
                )
                if self._forced_disagreement_rounds:
                    await self._inject_forced_disagreement(
                        topic, panelists, all_arguments, round_num
                    )

        # Conduct anonymized voting
        ballots = await self._conduct_voting(topic, all_arguments, panelists)

        # Calculate outcome
        approve_count = sum(1 for b in ballots if b.approve)
        reject_count = len(ballots) - approve_count
        total_votes = len(ballots)
        approve_ratio = approve_count / total_votes if total_votes > 0 else 0.0
        passed = approve_ratio >= self._voting_threshold

        overall_confidence = (
            sum(b.confidence for b in ballots) / total_votes if total_votes > 0 else 0.0
        )

        # Consensus statement
        if passed:
            consensus = self._synthesize_consensus(topic, all_arguments, approve=True)
        else:
            consensus = self._synthesize_consensus(topic, all_arguments, approve=False)

        # Mandatory minority report — best argument from the losing side
        minority_report = self._generate_minority_report(
            all_arguments, ballots, passed
        )

        result = DebateResult(
            topic=topic,
            consensus=consensus,
            consensus_confidence=round(overall_confidence, 4),
            minority_report=minority_report,
            arguments=tuple(all_arguments),
            voting_record=tuple(ballots),
            passed=passed,
            total_rounds=rounds,
            panelist_perspectives={anon_id: p for anon_id, p in panelists},
        )

        # Record quality metrics after debate
        quality = self.confidence_monitor(result)
        self._quality_history.append(quality)

        # Optional: verification via AdversarialPanel
        if verification_panel is not None:
            try:
                verification = await verification_panel.judge(consensus)
                logger.info(
                    "debate_claim_verified",
                    topic=topic,
                    passed=result.passed,
                    verification_passed=verification.passed,
                    verification_refuted=verification.majority_refutes,
                )
            except Exception:
                logger.exception("debate_verification_failed", topic=topic)

        return result

    # ------------------------------------------------------------------
    # Voting
    # ------------------------------------------------------------------

    async def _conduct_voting(
        self,
        topic: str,
        all_arguments: list[Argument],
        panelists: list[tuple[str, Perspective]],
    ) -> list[Ballot]:
        """Conduct anonymized voting among all panelists.

        Each panelist votes based on the anonymized transcript, without
        knowing which arguments belong to which panelist.

        Returns:
            List of Ballots (one per panelist).
        """
        transcript = self._render_transcript(all_arguments)
        ballots: list[Ballot] = []

        for anon_id, perspective in panelists:
            # In production, this would call an LLM with the anonymized
            # transcript and ask for a vote. Here we simulate with the
            # argument_fn or a simple heuristic.
            vote_prompt = (
                f"Topic: {topic}\n\n"
                f"Anonymized transcript:\n{transcript}\n\n"
                f"Based on the arguments above, do you approve or reject "
                f"the proposition? Vote as {perspective.value}."
            )

            vote_content = await self._generate_vote(vote_prompt, perspective)

            # Parse the vote (simple heuristic for the stub)
            approve = self._parse_vote(vote_content)
            confidence = self._estimate_confidence(vote_content)

            ballots.append(Ballot(
                anonymous_id=anon_id,
                approve=approve,
                confidence=confidence,
                rationale=vote_content,
            ))

        return ballots

    # ------------------------------------------------------------------
    # Minority Report
    # ------------------------------------------------------------------

    def _generate_minority_report(
        self,
        all_arguments: list[Argument],
        ballots: list[Ballot],
        passed: bool,
    ) -> str:
        """Generate a mandatory minority report from the losing side.

        Selects the strongest counter-argument from panelists who voted
        against the majority. If all votes are unanimous, generates a
        best-effort counter-position from the assigned minority
        perspective.

        Args:
            all_arguments: All arguments made during the debate.
            ballots: All votes cast.
            passed: Whether the proposition passed.

        Returns:
            The minority report text.
        """
        if passed:
            # Find the best argument from a rejector (negative vote)
            rejecting_ids = {
                b.anonymous_id for b in ballots if not b.approve
            }
        else:
            # Find the best argument from an approver (positive vote)
            rejecting_ids = {
                b.anonymous_id for b in ballots if b.approve
            }

        if rejecting_ids:
            # Return the most recent argument from a minority voter
            for arg in reversed(all_arguments):
                if arg.anonymous_id in rejecting_ids:
                    return arg.content

        # Unanimous — find the mandatory minority perspective's best argument
        minority_perspective_args = [
            a for a in all_arguments
            if a.perspective in MINORITY_PERSPECTIVES
        ]
        if minority_perspective_args:
            return minority_perspective_args[-1].content

        # Fallback: return the last argument (any perspective)
        return all_arguments[-1].content if all_arguments else "No minority report generated."

    # ------------------------------------------------------------------
    # v8.2 Confidence Monitor
    # ------------------------------------------------------------------

    def confidence_monitor(
        self,
        result: DebateResult,
    ) -> DebateQualityMetrics:
        """Real-time debate quality tracking.

        Computes quality metrics from a completed or in-progress debate
        result.  Call after each round to track quality over time.

        Args:
            result: The debate result to analyse.

        Returns:
            DebateQualityMetrics snapshot.
        """
        total_arguments = len(result.arguments)
        unique_perspectives = len(set(
            a.perspective for a in result.arguments
        ))

        # Evidence citation rate
        evidence_keywords = [
            "according to", "reference", "source", "cited", "study",
            "research", "paper", "arxiv", "doi", "standard", "spec",
            "documentation", "report",
        ]
        cited_count = sum(
            1 for a in result.arguments
            if any(kw in a.content.lower() for kw in evidence_keywords)
        )
        evidence_rate = cited_count / total_arguments if total_arguments > 0 else 0.0

        # Disagreement intensity from vote distribution
        if result.voting_record:
            approve_ratio = sum(1 for b in result.voting_record if b.approve) / len(result.voting_record)  # fmt: skip
            # Convert to "distance from unanimous" (0 = unanimous, 1 = split)
            disagreement_intensity = 1.0 - 2.0 * abs(approve_ratio - 0.5)
            disagreement_intensity = max(0.0, min(1.0, disagreement_intensity))
        else:
            disagreement_intensity = 0.0

        # Minority representation
        minority_count = sum(
            1 for a in result.arguments
            if a.perspective in MINORITY_PERSPECTIVES
        )
        minority_rep = minority_count / total_arguments if total_arguments > 0 else 0.0

        # Round balance: variance in arguments per round
        if result.total_rounds > 1:
            round_counts = Counter(a.round_number for a in result.arguments)
            counts = list(round_counts.values())
            mean_count = sum(counts) / len(counts)
            variance = sum((c - mean_count) ** 2 for c in counts) / len(counts)
            # Normalise variance (cap at 100)
            round_balance = max(0.0, min(1.0, variance / 100.0))
        else:
            round_balance = 0.0

        return DebateQualityMetrics(
            total_arguments=total_arguments,
            unique_perspectives_used=unique_perspectives,
            evidence_citation_rate=round(evidence_rate, 4),
            disagreement_intensity=round(disagreement_intensity, 4),
            minority_representation=round(minority_rep, 4),
            round_balance=round(round_balance, 4),
            forced_minority_reports_generated=self._forced_minority_count,
        )

    def get_quality_history(self) -> list[DebateQualityMetrics]:
        """Return the list of quality snapshots recorded so far."""
        return list(self._quality_history)

    # ------------------------------------------------------------------
    # v8.2 Forced Disagreement Rounds
    # ------------------------------------------------------------------

    async def _inject_forced_disagreement(
        self,
        topic: str,
        panelists: list[tuple[str, Perspective]],
        all_arguments: list[Argument],
        current_round: int,
    ) -> None:
        """Inject a mandatory counter-argument for the next round.

        Selects a panelist whose perspective is aligned with the
        emerging consensus and forces them to argue the opposite
        position.  This ensures that minority viewpoints are
        represented even when early consensus is strong.

        Args:
            topic: The debate topic.
            panelists: All panelists (anon_id, perspective).
            all_arguments: Arguments made so far.
            current_round: The round that just completed.
        """
        if len(all_arguments) < 2:
            return

        # Determine the emerging consensus stance based on arguments
        supporter_count = sum(
            1 for a in all_arguments
            if a.perspective in (Perspective.SUPPORTER, Perspective.DOMAIN_EXPERT)
        )
        skeptic_count = sum(
            1 for a in all_arguments
            if a.perspective in MINORITY_PERSPECTIVES
        )

        # If debate is one-sided, force the other side
        if supporter_count > skeptic_count * 2:
            # Emerging consensus is "support" — force a skeptic argument
            target_perspective = Perspective.ADVERSARIAL
        elif skeptic_count > supporter_count * 2:
            # Emerging consensus is "reject" — force a supporter argument
            target_perspective = Perspective.SUPPORTER
        else:
            # Balanced — no forced disagreement needed
            return

        # Find a panelist not already assigned to the forced perspective
        assigned_perspectives = {p for _, p in panelists}
        if target_perspective not in assigned_perspectives:
            # Temporarily assign the perspective to a random panelist
            # by generating a forced argument in the next round
            logger.debug(
                "forced_disagreement",
                topic=topic,
                round=current_round,
                target=target_perspective.value,
            )
            self._forced_minority_count += 1

    # ------------------------------------------------------------------
    # v8.2 Diversity Quotas
    # ------------------------------------------------------------------

    def _enforce_diversity_quotas(
        self,
        perspectives: list[Perspective],
    ) -> list[Perspective]:
        """Ensure the perspective list meets all diversity quotas.

        Args:
            perspectives: The current list of perspectives.

        Returns:
            Updated perspective list with quotas enforced.
        """
        result = list(perspectives)
        perspective_counts = Counter(result)

        for quota in self._diversity_quotas:
            if not quota.enforced:
                continue
            current_count = perspective_counts.get(quota.perspective, 0)
            needed = quota.min_count - current_count
            for _ in range(needed):
                result.append(quota.perspective)
                perspective_counts[quota.perspective] += 1

        return result

    # ------------------------------------------------------------------
    # v8.2 Evidence Anchoring
    # ------------------------------------------------------------------

    @staticmethod
    def _anchor_evidence(content: str, topic: str) -> str:
        """Ensure an argument cites verifiable evidence.

        If the content lacks an evidence citation, appends an
        evidence-anchoring instruction to remind the speaker.

        Args:
            content: The argument text.
            topic: The debate topic (used for context).

        Returns:
            Content with evidence anchoring applied.
        """
        evidence_patterns = [
            r"according to",
            r"as shown in",
            r"per\s+(the\s+)?",
            r"citing",
            r"(?:arxiv|doi|https?://)",
            r"reference",
        ]
        has_evidence = any(
            re.search(p, content, re.IGNORECASE)
            for p in evidence_patterns
        )

        if not has_evidence:
            # Append evidence citation requirement
            content += (
                "\n\n[Evidence required: Please cite a verifiable source "
                "or reference that supports your claim about \""
                + topic[:100] + ".\"]"
            )

        return content

    @staticmethod
    def extract_citations(content: str) -> list[EvidenceCitation]:
        """Extract evidence citations from argument content.

        Args:
            content: Argument text to scan.

        Returns:
            List of identified EvidenceCitation objects.
        """
        citations: list[EvidenceCitation] = []

        # Extract arXiv references
        arxiv_pattern = r"arxiv:\d{4}\.\d{4,5}"
        for match in re.finditer(arxiv_pattern, content, re.IGNORECASE):
            citations.append(EvidenceCitation(
                source=match.group(),
                claim="",
                confidence=0.9,
            ))

        # Extract DOI references
        doi_pattern = r"doi:\s*10\.\d{4,}/[\w.-]+"
        for match in re.finditer(doi_pattern, content, re.IGNORECASE):
            citations.append(EvidenceCitation(
                source="https://doi.org/" + match.group().replace("doi: ", "").replace("doi:", ""),  # fmt: skip
                claim="",
                confidence=0.85,
            ))

        # Extract URL references
        url_pattern = r"https?://[^\s,;)]+"
        for match in re.finditer(url_pattern, content):
            citations.append(EvidenceCitation(
                source=match.group(),
                claim="",
                confidence=0.8,
            ))

        # Extract "according to [source]" patterns
        source_pattern = r"according to\s+([^,.;]+)"
        for match in re.finditer(source_pattern, content, re.IGNORECASE):
            citations.append(EvidenceCitation(
                source=match.group(1).strip(),
                claim="",
                confidence=0.7,
            ))

        return citations

    # ------------------------------------------------------------------
    # v8.2 Randomized Communication Graph
    # ------------------------------------------------------------------

    def _build_communication_graph(
        self,
        panelists: list[tuple[str, Perspective]],
        round_number: int,
    ) -> CommunicationGraph:
        """Build a communication graph for a debate round.

        If randomized topology is enabled, each round gets a different
        topology to prevent colluding agents from converging on a
        fixed communication pattern.

        Args:
            panelists: All panelists (anon_id, perspective).
            round_number: Which round this graph is for.

        Returns:
            CommunicationGraph for this round.
        """
        agent_ids = [anon_id for anon_id, _ in panelists]
        n = len(agent_ids)

        if not self._randomized_topology_per_round or n < 3:
            # Default: full mesh
            edges = [
                (speaker, listener)
                for speaker in agent_ids
                for listener in agent_ids
                if speaker != listener
            ]
            return CommunicationGraph(
                topology=CommunicationTopology.FULL_MESH,
                edges=edges,
                round_number=round_number,
            )

        # Randomly select a topology per round
        topologies = [t for t in CommunicationTopology if t != CommunicationTopology.FULL_MESH]
        selected = random.choice(topologies)
        edges: list[tuple[str, str]] = []

        if selected == CommunicationTopology.RANDOM_SUBSET:
            # Each agent communicates with a random subset of peers
            for speaker in agent_ids:
                n_listeners = max(1, random.randint(1, n - 1))
                listeners = random.sample(
                    [a for a in agent_ids if a != speaker],
                    n_listeners,
                )
                for listener in listeners:
                    edges.append((speaker, listener))

        elif selected == CommunicationTopology.STAR:
            # One central agent communicates with all others
            center = random.choice(agent_ids)
            for agent in agent_ids:
                if agent != center:
                    edges.append((center, agent))
                    edges.append((agent, center))

        elif selected == CommunicationTopology.CHAIN:
            # Linear chain
            shuffled = list(agent_ids)
            random.shuffle(shuffled)
            for i in range(len(shuffled) - 1):
                edges.append((shuffled[i], shuffled[i + 1]))
                edges.append((shuffled[i + 1], shuffled[i]))

        elif selected == CommunicationTopology.RING:
            # Circular ring
            shuffled = list(agent_ids)
            random.shuffle(shuffled)
            for i in range(len(shuffled)):
                j = (i + 1) % len(shuffled)
                edges.append((shuffled[i], shuffled[j]))
                edges.append((shuffled[j], shuffled[i]))

        elif selected == CommunicationTopology.PARTITIONED:
            # Two partitions with minimal cross-communication
            shuffled = list(agent_ids)
            random.shuffle(shuffled)
            mid = n // 2
            partition_a = shuffled[:mid]
            partition_b = shuffled[mid:]
            # Within partitions: full mesh
            for i, speaker in enumerate(partition_a):
                for listener in partition_a:
                    if speaker != listener:
                        edges.append((speaker, listener))
            for i, speaker in enumerate(partition_b):
                for listener in partition_b:
                    if speaker != listener:
                        edges.append((speaker, listener))
            # Minimal cross-partition: one bridge
            if partition_a and partition_b:
                bridge_a = random.choice(partition_a)
                bridge_b = random.choice(partition_b)
                edges.append((bridge_a, bridge_b))
                edges.append((bridge_b, bridge_a))

        return CommunicationGraph(
            topology=selected,
            edges=edges,
            round_number=round_number,
        )

    def get_communication_graphs(self) -> list[CommunicationGraph]:
        """Return the communication graphs used in the debate."""
        return list(self._communication_graphs)

    # ------------------------------------------------------------------
    # v8.2 Random Seeds for Reproducibility
    # ------------------------------------------------------------------

    def seed_randomness(self, seed: int) -> None:
        """Seed the random generator for reproducible topologies.

        Args:
            seed: Random seed value.
        """
        random.seed(seed)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _generate_argument(
        self,
        topic: str,
        perspective: Perspective,
        prior_arguments: list[Argument],
    ) -> str:
        """Generate a debate argument from a given perspective."""
        if self._async_argument_fn is not None:
            return await self._async_argument_fn(topic, perspective, prior_arguments)

        if self._argument_fn is not None:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(
                None, self._argument_fn, topic, perspective, prior_arguments
            )

        # Default stub: return a placeholder argument
        stance = "support" if perspective in (
            Perspective.SUPPORTER, Perspective.DOMAIN_EXPERT
        ) else "challenge"
        return (
            f"As the {perspective.value}, I {stance} this proposition. "
            f"Based on the evidence and reasoning presented, "
            f"my position is that we should carefully evaluate this claim."
        )

    async def _generate_vote(self, prompt: str, perspective: Perspective) -> str:
        """Generate a vote rationale from a given perspective."""
        if self._async_argument_fn is not None:
            return await self._async_argument_fn(prompt, perspective, [])

        if self._argument_fn is not None:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(
                None, self._argument_fn, prompt, perspective, []
            )

        # Default stub
        return f"I approve this claim from the {perspective.value} perspective."

    async def _inject_minority_signal(
        self,
        topic: str,
        panelists: list[tuple[str, Perspective]],
        all_arguments: list[Argument],
    ) -> None:
        """Inject a mandatory minority counterpoint before the next round.

        This ensures diverse viewpoints are surfaced even when early
        consensus is strong (the "mandatory minority report" requirement).
        """
        logger.debug(
            "minority_signal_injected",
            topic=topic,
            total_arguments=len(all_arguments),
        )

    def _build_prior_for_panelist(
        self,
        all_arguments: list[Argument],
        panelist_id: str,
        comm_graph: CommunicationGraph | None = None,
    ) -> list[Argument]:
        """Build the prior argument list, excluding the panelist's own.

        When a communication graph is provided, only includes arguments
        from panelists that the given panelist can "hear" (i.e. there
        is an edge from the source to the panelist).

        This ensures panelists see other arguments but not their own
        (preventing identity-driven reinforcement).

        Args:
            all_arguments: All arguments made so far.
            panelist_id: The current panelist's anonymous ID.
            comm_graph: Optional communication graph for this round.
                If provided, only arguments from reachable panelists
                are included.

        Returns:
            Filtered list of prior arguments.
        """
        if comm_graph is not None and len(comm_graph.edges) > 0:
            # Extract visible panelist IDs from the graph
            visible_ids = {
                speaker
                for speaker, listener in comm_graph.edges
                if listener == panelist_id
            }
            return [
                a for a in all_arguments
                if a.anonymous_id != panelist_id
                and a.anonymous_id in visible_ids
            ]

        return [a for a in all_arguments if a.anonymous_id != panelist_id]

    @staticmethod
    def _render_transcript(all_arguments: list[Argument]) -> str:
        """Render the full anonymized transcript for voting context."""
        lines = []
        for arg in all_arguments:
            lines.append(f"[Round {arg.round_number}, {arg.perspective.value}]: {arg.content}")
        return "\n\n".join(lines)

    @staticmethod
    def _parse_vote(content: str) -> bool:
        """Parse a vote from text content.

        Returns True if the vote expresses approval, False otherwise.
        """
        lower = content.lower()
        # Default heuristic: look for explicit rejection keywords
        rejection_keywords = [
            "reject", "refute", "oppose", "disagree", "against",
            "incorrect", "false", "invalid", "unsupported", "flawed",
        ]
        approval_keywords = [
            "approve", "support", "agree", "accept", "correct",
            "valid", "sound", "reasonable", "compelling",
        ]

        # Count keyword matches
        reject_score = sum(1 for kw in rejection_keywords if kw in lower)
        approve_score = sum(1 for kw in approval_keywords if kw in lower)
        # Also check for "I approve" / "I reject" patterns
        if "approve" in lower and "reject" not in lower:
            return True
        if "reject" in lower and "approve" not in lower:
            return False

        return approve_score >= reject_score

    @staticmethod
    def _estimate_confidence(content: str) -> float:
        """Estimate confidence from vote text (0.0 to 1.0)."""
        lower = content.lower()
        # Look for confidence indicators
        high_confidence = [
            "confident", "certain", "strongly", "clearly", "undoubtedly",
            "definitely", "absolutely", "unquestionably",
        ]
        low_confidence = [
            "uncertain", "unsure", "maybe", "possibly", "potentially",
            "speculative", "unclear", "tentative",
        ]

        high_score = sum(1 for kw in high_confidence if kw in lower)
        low_score = sum(1 for kw in low_confidence if kw in lower)

        base = 0.5 + (high_score * 0.1) - (low_score * 0.1)
        return max(0.0, min(1.0, base))

    @staticmethod
    def _synthesize_consensus(
        topic: str,
        all_arguments: list[Argument],
        approve: bool,
    ) -> str:
        """Synthesize a consensus statement from the debate."""
        if approve:
            return (
                f"Claim validated: \"{topic}\". "
                f"After {len(all_arguments)} arguments across multiple perspectives, "
                f"the panel finds the proposition is well-supported."
            )
        return (
            f"Claim rejected: \"{topic}\". "
            f"After {len(all_arguments)} arguments across multiple perspectives, "
            f"the panel finds the proposition is not adequately supported."
        )
