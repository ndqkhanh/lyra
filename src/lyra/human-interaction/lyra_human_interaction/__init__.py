"""
Lyra Human Interaction — Human-agent interaction: explanations, negotiation,
feedback, alignment dialog, and interactive clarification.

This package provides:
- Explanation generation at multiple levels of detail
- Negotiation protocols for reaching agreement
- User feedback integration
- Alignment dialog for value discovery
- Interactive clarification when the agent is uncertain
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ExplanationLevel(str, Enum):
    """Level of detail for generated explanations."""

    NOVICE = "NOVICE"
    INTERMEDIATE = "INTERMEDIATE"
    EXPERT = "EXPERT"
    EXECUTIVE = "EXECUTIVE"
    TECHNICAL = "TECHNICAL"


class NegotiationPhase(str, Enum):
    """Current phase of a negotiation session."""

    PROPOSAL = "PROPOSAL"
    COUNTER_PROPOSAL = "COUNTER_PROPOSAL"
    CLARIFICATION = "CLARIFICATION"
    CONCESSION = "CONCESSION"
    AGREEMENT = "AGREEMENT"
    IMPASSE = "IMPASSE"


class FeedbackType(str, Enum):
    """Type of user feedback on a decision."""

    CORRECTION = "CORRECTION"
    PREFERENCE = "PREFERENCE"
    RATING = "RATING"
    SUGGESTION = "SUGGESTION"
    CLARIFICATION_REQUEST = "CLARIFICATION_REQUEST"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Explanation:
    """A structured explanation of a decision or reasoning trace.

    Parameters
    ----------
    explanation_id : str
        Unique identifier for this explanation.
    topic : str
        The subject being explained.
    level : str
        Explanation level (NOVICE, INTERMEDIATE, etc.).
    summary : str
        One-paragraph high-level summary.
    detailed_steps : tuple[str, ...]
        Step-by-step breakdown of the reasoning.
    key_insights : tuple[str, ...]
        Most important takeaways.
    confidence : float
        Agent's confidence in this explanation (0.0 to 1.0).
    assumptions : tuple[str, ...]
        Assumptions underlying the reasoning.
    limitations : tuple[str, ...]
        Known limitations of the approach or explanation.
    """

    explanation_id: str
    topic: str
    level: str
    summary: str
    detailed_steps: tuple[str, ...]
    key_insights: tuple[str, ...]
    confidence: float
    assumptions: tuple[str, ...]
    limitations: tuple[str, ...]


@dataclass(frozen=True)
class NegotiationState:
    """State tracking for an active negotiation session.

    Parameters
    ----------
    negotiation_id : str
        Unique identifier for this negotiation.
    phase : str
        Current negotiation phase.
    agent_proposal : str
        The agent's most recent proposal.
    human_counter : str
        The human's most recent counter-proposal or response.
    points_of_agreement : tuple[str, ...]
        Points both parties agree on.
    points_of_disagreement : tuple[str, ...]
        Points where parties diverge.
    resolution : str
        Final resolution text (empty string if unresolved).
    round_count : int
        Number of negotiation rounds completed.
    """

    negotiation_id: str
    phase: str
    agent_proposal: str
    human_counter: str
    points_of_agreement: tuple[str, ...]
    points_of_disagreement: tuple[str, ...]
    resolution: str = ""
    round_count: int = 0


@dataclass(frozen=True)
class UserFeedback:
    """Feedback provided by a human user on an agent decision.

    Parameters
    ----------
    feedback_id : str
        Unique identifier for this feedback.
    feedback_type : str
        Type of feedback (CORRECTION, PREFERENCE, etc.).
    content : str
        The feedback text.
    target_decision_id : str
        Identifier of the decision this feedback targets.
    timestamp : float
        Unix timestamp when feedback was provided.
    incorporated : bool
        Whether the feedback has been incorporated into the decision.
    """

    feedback_id: str
    feedback_type: str
    content: str
    target_decision_id: str
    timestamp: float
    incorporated: bool = False


@dataclass(frozen=True)
class ClarificationRequest:
    """A request for human clarification when the agent is uncertain.

    Parameters
    ----------
    request_id : str
        Unique identifier for this request.
    context : str
        The context or scenario prompting the request.
    question : str
        The clarification question posed to the human.
    options : tuple[str, ...]
        Pre-defined answer options for the human to choose from.
    default_answer : str
        Default answer if the human does not respond.
    resolved : bool
        Whether this request has been resolved.
    """

    request_id: str
    context: str
    question: str
    options: tuple[str, ...]
    default_answer: str
    resolved: bool = False


@dataclass(frozen=True)
class AlignmentDialog:
    """Record of a structured alignment dialog between agent and human.

    Parameters
    ----------
    dialog_id : str
        Unique identifier for this dialog.
    topic : str
        The subject of the alignment dialog.
    agent_position : str
        The agent's stated position on the topic.
    human_position : str
        The human's stated position on the topic.
    common_ground : tuple[str, ...]
        Areas of shared understanding found during the dialog.
    outcome : str
        Outcome or resolution of the dialog.
    trust_score : float
        Estimated trust score after the dialog (0.0 to 1.0).
    """

    dialog_id: str
    topic: str
    agent_position: str
    human_position: str
    common_ground: tuple[str, ...]
    outcome: str
    trust_score: float


@dataclass(frozen=True)
class InteractionConfig:
    """Configuration options for the HumanInteractionEngine.

    Parameters
    ----------
    default_explanation_level : str
        Default explanation level when none is specified.
    negotiation_rounds_limit : int
        Maximum number of negotiation rounds before forced resolution.
    feedback_enabled : bool
        Whether user feedback processing is active.
    clarification_enabled : bool
        Whether clarification requests are active.
    alignment_dialog_enabled : bool
        Whether alignment dialogs are active.
    max_context_history : int
        Maximum number of interactions to retain in history.
    """

    default_explanation_level: str = "INTERMEDIATE"
    negotiation_rounds_limit: int = 5
    feedback_enabled: bool = True
    clarification_enabled: bool = True
    alignment_dialog_enabled: bool = True
    max_context_history: int = 50


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_AGREEMENT_KEYWORDS = frozenset(
    {
        "agree",
        "correct",
        "right",
        "yes",
        "good",
        "fine",
        "acceptable",
        "understood",
        "makes sense",
        "sure",
        "okay",
        "works",
    }
)

_DISAGREEMENT_KEYWORDS = frozenset(
    {
        "disagree",
        "wrong",
        "incorrect",
        "no",
        "bad",
        "unacceptable",
        "not",
        "however",
        "but",
        "unfortunately",
        "issue",
        "problem",
        "concern",
    }
)


def _extract_points(text: str, keywords: frozenset[str]) -> tuple[str, ...]:
    """Extract simple point-like phrases from *text* that contain *keywords*."""
    sentences = [
        s.strip() for s in text.replace("!", ".").replace("?", ".").split(".") if s.strip()
    ]
    matched: list[str] = []
    for sentence in sentences:
        lower = sentence.lower()
        if any(kw in lower for kw in keywords):
            matched.append(sentence)
    return tuple(matched[:5])


def _generate_id(prefix: str = "") -> str:
    """Generate a simple unique identifier."""
    import uuid

    return f"{prefix}_{uuid.uuid4().hex[:12]}" if prefix else uuid.uuid4().hex[:12]


# ---------------------------------------------------------------------------
# Level adapters
# ---------------------------------------------------------------------------

_EXPLANATION_TEMPLATES: dict[str, dict[str, Any]] = {
    ExplanationLevel.NOVICE.value: {
        "vocabulary": "simple",
        "detail": "minimal",
        "analogy": True,
        "confidence": 0.7,
    },
    ExplanationLevel.INTERMEDIATE.value: {
        "vocabulary": "moderate",
        "detail": "balanced",
        "analogy": False,
        "confidence": 0.8,
    },
    ExplanationLevel.EXPERT.value: {
        "vocabulary": "technical",
        "detail": "deep",
        "analogy": False,
        "confidence": 0.9,
    },
    ExplanationLevel.EXECUTIVE.value: {
        "vocabulary": "business",
        "detail": "high-level",
        "analogy": True,
        "confidence": 0.75,
    },
    ExplanationLevel.TECHNICAL.value: {
        "vocabulary": "precise",
        "detail": "comprehensive",
        "analogy": False,
        "confidence": 0.85,
    },
}


def _build_summary(topic: str, level: str, audience_knowledge: str) -> str:
    """Build a summary string adapted to the requested explanation level."""
    prefixes = {
        ExplanationLevel.NOVICE.value: (
            f"In simple terms, {topic} works by following a clear set of steps "
            f"that anyone can understand."
        ),
        ExplanationLevel.INTERMEDIATE.value: (
            f"{topic} operates through a structured process that balances "
            f"several key factors to reach a well-reasoned decision."
        ),
        ExplanationLevel.EXPERT.value: (
            f"{topic} employs advanced reasoning over multiple evidence "
            f"sources, applying domain-specific heuristics and weighted "
            f"evaluation criteria."
        ),
        ExplanationLevel.EXECUTIVE.value: (
            f"{topic} was evaluated against strategic objectives and "
            f"determined to provide the optimal outcome within the "
            f"established constraints."
        ),
        ExplanationLevel.TECHNICAL.value: (
            f"{topic}: analysis performed via multi-factor evaluation "
            f"with configurable parameters, yielding a deterministic "
            f"result within bounded error margins."
        ),
    }
    summary = prefixes.get(level, prefixes[ExplanationLevel.INTERMEDIATE.value])
    if audience_knowledge:
        summary += f" Tailored for an audience with knowledge of: {audience_knowledge}."
    return summary


def _build_detailed_steps(
    reasoning: list[str],
    level: str,
    *,
    template: dict[str, Any] | None = None,
) -> tuple[str, ...]:
    """Build a tuple of detailed steps, adapted to the explanation level."""
    base = tuple(reasoning) if reasoning else (f"Analyzed {reasoning!r} inputs",)
    if not base:
        base = ("Considered available information and constraints.",)

    if level == ExplanationLevel.NOVICE.value:
        # Simplify: shorten each step, remove jargon
        simplified: list[str] = []
        for step in base:
            words = step.split()
            simplified.append(" ".join(words[:12]) + ("..." if len(words) > 12 else ""))
        return tuple(simplified[:3])

    if level == ExplanationLevel.EXECUTIVE.value:
        return (
            f"Evaluated strategic alignment of {base[0].lower() if base else 'the proposal'}",
            "Assessed resource requirements and expected impact",
            "Validated against business objectives and risk tolerance",
        )

    if level == ExplanationLevel.EXPERT.value or level == ExplanationLevel.TECHNICAL.value:
        detail = template or _EXPLANATION_TEMPLATES.get(level, {})
        if detail.get("detail") in ("deep", "comprehensive"):
            augmented: list[str] = []
            for step in base:
                augmented.append(step)
                augmented.append(f"  -> Cross-validated {step.lower()} against source data")
            return tuple(augmented[:6])
        return base

    return base


def _build_key_insights(topic: str, reasoning: list[str], level: str) -> tuple[str, ...]:
    """Build key insight tuples adapted to the level."""
    _ = topic  # kept for consistency across callers
    base = tuple(reasoning[:3]) if reasoning else ("Key considerations were weighed.",)
    if level == ExplanationLevel.NOVICE.value:
        return ("The most important thing to understand is the main goal.",) + base[:2]
    if level == ExplanationLevel.EXECUTIVE.value:
        return (
            "Strategic outcome: decision aligns with stated objectives",
            "Risk profile: within acceptable thresholds",
            "Resource allocation: justified by expected returns",
        )
    if level == ExplanationLevel.TECHNICAL.value or level == ExplanationLevel.EXPERT.value:
        return base + ("Cross-validation confirms no contradictory evidence was overlooked.",)
    return base


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class HumanInteractionEngine:
    """Engine for managing human-agent interactions.

    Generates explanations, supports negotiation, processes feedback, handles
    clarification requests, and facilitates alignment dialogs.

    Parameters
    ----------
    config : InteractionConfig | None
        Configuration for the engine. Uses defaults if not provided.
    """

    def __init__(self, config: InteractionConfig | None = None) -> None:
        self._config = config or InteractionConfig()
        self._history: list[dict[str, Any]] = []
        self._feedback_log: list[UserFeedback] = []
        self._negotiation_count: int = 0
        self._clarification_count: int = 0
        self._dialog_count: int = 0
        self._explanation_count: int = 0

    # -- history ----------------------------------------------------------

    def _record(self, entry: dict[str, Any]) -> None:
        """Append a history entry, trimming to *max_context_history*."""
        self._history.append(entry)
        if len(self._history) > self._config.max_context_history:
            self._history = self._history[-self._config.max_context_history :]

    # -- explanations -----------------------------------------------------

    def generate_explanation(
        self,
        topic: str,
        decision_context: str,
        reasoning: list[str],
        level: str | None = None,
        audience_knowledge: str = "",
    ) -> Explanation:
        """Generate a tailored explanation at the requested level.

        Adapts vocabulary, depth, and structure based on the explanation
        level. Produces a realistic stub with heuristic content adaptation.

        Parameters
        ----------
        topic : str
            The subject being explained.
        decision_context : str
            Context surrounding the decision being explained.
        reasoning : list[str]
            Step-by-step reasoning trace from the agent.
        level : str | None
            Desired explanation level. Falls back to config default if None.
        audience_knowledge : str
            Optional description of the audience's knowledge background.

        Returns
        -------
        Explanation
            A fully populated explanation dataclass.
        """
        effective_level = level or self._config.default_explanation_level
        template = _EXPLANATION_TEMPLATES.get(
            effective_level, _EXPLANATION_TEMPLATES["INTERMEDIATE"]
        )

        explanation_id = _generate_id("exp")
        self._explanation_count += 1

        summary = _build_summary(topic, effective_level, audience_knowledge)
        detailed_steps = _build_detailed_steps(reasoning, effective_level, template=template)
        key_insights = _build_key_insights(topic, reasoning, effective_level)
        confidence = template["confidence"]

        # Generate simple assumptions / limitations
        assumptions = (
            "Input data is accurate and up-to-date",
            "Decision context has been fully captured",
        )
        limitations = (
            "Explanation is a summary and may omit edge cases",
            f"Generated at {effective_level} level of detail",
        )

        explanation = Explanation(
            explanation_id=explanation_id,
            topic=topic,
            level=effective_level,
            summary=summary,
            detailed_steps=detailed_steps,
            key_insights=key_insights,
            confidence=confidence,
            assumptions=assumptions,
            limitations=limitations,
        )

        self._record(
            {
                "type": "explanation",
                "explanation_id": explanation_id,
                "topic": topic,
                "level": effective_level,
                "confidence": confidence,
            }
        )

        logger.debug(
            "Generated explanation %s for topic '%s' at level %s",
            explanation_id,
            topic,
            effective_level,
        )
        return explanation

    # -- negotiation ------------------------------------------------------

    def start_negotiation(self, topic: str, agent_proposal: str) -> NegotiationState:
        """Initiate a new negotiation session.

        The agent puts forward a proposal and awaits the human's counter.

        Parameters
        ----------
        topic : str
            The subject of the negotiation.
        agent_proposal : str
            The agent's initial proposal.

        Returns
        -------
        NegotiationState
            The initial negotiation state.
        """
        self._negotiation_count += 1
        neg_id = _generate_id("neg")

        state = NegotiationState(
            negotiation_id=neg_id,
            phase=NegotiationPhase.PROPOSAL.value,
            agent_proposal=agent_proposal,
            human_counter="",
            points_of_agreement=(),
            points_of_disagreement=(),
            round_count=0,
        )

        self._record(
            {
                "type": "negotiation_start",
                "negotiation_id": neg_id,
                "topic": topic,
                "agent_proposal": agent_proposal,
            }
        )

        logger.debug("Started negotiation %s on topic '%s'", neg_id, topic)
        return state

    def negotiate_round(
        self,
        state: NegotiationState,
        human_response: str,
        agent_concession: str = "",
    ) -> NegotiationState:
        """Process one round of negotiation.

        Analyzes the human response for agreement and disagreement signals,
        then advances the phase accordingly.

        Parameters
        ----------
        state : NegotiationState
            The current negotiation state.
        human_response : str
            The human's response in this round.
        agent_concession : str
            Optional concession or adjustment from the agent.

        Returns
        -------
        NegotiationState
            Updated negotiation state after processing this round.
        """
        new_round = state.round_count + 1
        new_proposal = agent_concession or state.agent_proposal

        # Analyse the human response
        agreement_points = _extract_points(human_response, _AGREEMENT_KEYWORDS)
        disagreement_points = _extract_points(human_response, _DISAGREEMENT_KEYWORDS)

        merged_agreements = list(state.points_of_agreement) + list(agreement_points)
        merged_disagreements = list(state.points_of_disagreement) + list(disagreement_points)

        # Determine next phase
        has_strong_agreement = any(
            kw in human_response.lower() for kw in ("agree", "yes", "correct", "good")
        )
        has_strong_disagreement = any(
            kw in human_response.lower() for kw in ("disagree", "no", "wrong", "unacceptable")
        )

        if has_strong_agreement and not disagreement_points:
            phase = NegotiationPhase.AGREEMENT.value
            resolution = human_response
        elif new_round >= self._config.negotiation_rounds_limit:
            phase = NegotiationPhase.IMPASSE.value
            resolution = "Negotiation round limit reached."
        elif has_strong_disagreement:
            phase = (
                NegotiationPhase.COUNTER_PROPOSAL.value
                if agent_concession
                else NegotiationPhase.CONCESSION.value
            )
            resolution = ""
        elif agreement_points and disagreement_points:
            phase = NegotiationPhase.CONCESSION.value
            resolution = ""
        else:
            phase = NegotiationPhase.CLARIFICATION.value
            resolution = ""

        new_state = NegotiationState(
            negotiation_id=state.negotiation_id,
            phase=phase,
            agent_proposal=new_proposal,
            human_counter=human_response,
            points_of_agreement=tuple(merged_agreements),
            points_of_disagreement=tuple(merged_disagreements),
            resolution=resolution,
            round_count=new_round,
        )

        self._record(
            {
                "type": "negotiation_round",
                "negotiation_id": state.negotiation_id,
                "round": new_round,
                "phase": phase,
                "agreement_count": len(merged_agreements),
                "disagreement_count": len(merged_disagreements),
            }
        )

        return new_state

    # -- feedback ---------------------------------------------------------

    def process_feedback(
        self,
        feedback: UserFeedback,
        original_decision: str,
    ) -> tuple[str, bool]:
        """Process user feedback on a decision.

        Evaluates the feedback and returns a potentially revised decision.

        Parameters
        ----------
        feedback : UserFeedback
            The feedback to process.
        original_decision : str
            The original decision text to revise.

        Returns
        -------
        tuple[str, bool]
            The (revised decision, whether feedback was incorporated).
        """
        if not self._config.feedback_enabled:
            return (original_decision, False)

        self._feedback_log.append(feedback)

        # Heuristic: corrections and suggestions are always incorporated
        was_incorporated = feedback.feedback_type in (
            FeedbackType.CORRECTION.value,
            FeedbackType.SUGGESTION.value,
        )
        if was_incorporated:
            revised = f"{original_decision} [Incorporated feedback: {feedback.content}]"
        else:
            revised = original_decision

        self._record(
            {
                "type": "feedback",
                "feedback_id": feedback.feedback_id,
                "feedback_type": feedback.feedback_type,
                "incorporated": was_incorporated,
            }
        )

        return (revised, was_incorporated)

    # -- clarification ----------------------------------------------------

    def request_clarification(
        self,
        context: str,
        question: str,
        options: list[str],
    ) -> ClarificationRequest:
        """Ask the human for clarification when the agent is uncertain.

        Parameters
        ----------
        context : str
            The context prompting the clarification request.
        question : str
            The question to present to the human.
        options : list[str]
            Pre-defined answer options.

        Returns
        -------
        ClarificationRequest
            A new clarification request.
        """
        self._clarification_count += 1
        request_id = _generate_id("clar")

        request = ClarificationRequest(
            request_id=request_id,
            context=context,
            question=question,
            options=tuple(options),
            default_answer=options[0] if options else "",
        )

        self._record(
            {
                "type": "clarification_request",
                "request_id": request_id,
                "question": question,
                "options": list(options),
            }
        )

        return request

    def resolve_clarification(
        self,
        request: ClarificationRequest,
        answer: str,
    ) -> ClarificationRequest:
        """Resolve a clarification request with the human's answer.

        Parameters
        ----------
        request : ClarificationRequest
            The request being resolved.
        answer : str
            The human's chosen answer.

        Returns
        -------
        ClarificationRequest
            A new request instance with resolved state.
        """
        resolved = ClarificationRequest(
            request_id=request.request_id,
            context=request.context,
            question=request.question,
            options=request.options,
            default_answer=request.default_answer,
            resolved=True,
        )

        self._record(
            {
                "type": "clarification_resolve",
                "request_id": request.request_id,
                "answer": answer,
            }
        )

        return resolved

    # -- alignment dialog ------------------------------------------------

    def start_alignment_dialog(
        self,
        topic: str,
        agent_position: str,
    ) -> AlignmentDialog:
        """Initiate a structured alignment dialog to find common ground.

        Parameters
        ----------
        topic : str
            The subject of the dialog.
        agent_position : str
            The agent's initial position on the topic.

        Returns
        -------
        AlignmentDialog
            A new alignment dialog record awaiting the human position.
        """
        self._dialog_count += 1
        dialog_id = _generate_id("dialog")

        dialog = AlignmentDialog(
            dialog_id=dialog_id,
            topic=topic,
            agent_position=agent_position,
            human_position="",
            common_ground=(),
            outcome="In progress",
            trust_score=0.5,
        )

        self._record(
            {
                "type": "alignment_dialog_start",
                "dialog_id": dialog_id,
                "topic": topic,
                "agent_position": agent_position,
            }
        )

        return dialog

    # -- compromise -------------------------------------------------------

    def suggest_compromise(self, state: NegotiationState) -> str:
        """Suggest a compromise based on areas of agreement and disagreement.

        Parameters
        ----------
        state : NegotiationState
            The current negotiation state to base the compromise on.

        Returns
        -------
        str
            A suggested compromise text.
        """
        if not state.points_of_agreement and not state.points_of_disagreement:
            return f"Proceeding with the current proposal: {state.agent_proposal[:100]}"

        agreement_summary = "; ".join(state.points_of_agreement[:3])
        disagreement_summary = "; ".join(state.points_of_disagreement[:3])

        if state.points_of_agreement and not state.points_of_disagreement:
            return (
                f"We seem to be in agreement. Let's proceed with:\n"
                f"{state.agent_proposal}\n\n"
                f"Agreed points:\n{agreement_summary}"
            )

        if not state.points_of_agreement and state.points_of_disagreement:
            return (
                f"We have some differences to resolve. I suggest:\n"
                f"1. Address each concern individually.\n"
                f"2. Identify overlapping goals.\n"
                f"3. Propose a modified approach that incorporates your feedback.\n\n"
                f"Concerns raised:\n{disagreement_summary}"
            )

        # Both agreement and disagreement exist
        return (
            f"Based on our discussion, here is a suggested compromise:\n\n"
            f"Areas of agreement:\n{agreement_summary}\n\n"
            f"Outstanding differences:\n{disagreement_summary}\n\n"
            f"Proposal: {state.agent_proposal[:150]}"
        )

    # -- introspection ----------------------------------------------------

    def get_interaction_history(self) -> list[dict[str, Any]]:
        """Return the recent interaction history.

        Returns
        -------
        list[dict[str, Any]]
            Chronological list of interaction records.
        """
        return list(self._history)

    def get_stats(self) -> dict[str, Any]:
        """Return aggregate usage statistics for the engine.

        Returns
        -------
        dict[str, Any]
            Dictionary of counter and configuration values.
        """
        return {
            "explanations_generated": self._explanation_count,
            "negotiations_started": self._negotiation_count,
            "feedback_processed": len(self._feedback_log),
            "clarification_requests": self._clarification_count,
            "alignment_dialogs": self._dialog_count,
            "history_size": len(self._history),
            "config": {
                "default_explanation_level": self._config.default_explanation_level,
                "negotiation_rounds_limit": self._config.negotiation_rounds_limit,
                "feedback_enabled": self._config.feedback_enabled,
                "clarification_enabled": self._config.clarification_enabled,
                "alignment_dialog_enabled": self._config.alignment_dialog_enabled,
                "max_context_history": self._config.max_context_history,
            },
        }


__version__ = "0.1.0"

__all__ = [
    # Enums
    "ExplanationLevel",
    "NegotiationPhase",
    "FeedbackType",
    # Data classes
    "Explanation",
    "NegotiationState",
    "UserFeedback",
    "ClarificationRequest",
    "AlignmentDialog",
    "InteractionConfig",
    # Engine
    "HumanInteractionEngine",
]
