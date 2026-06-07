"""
Preference learning — learn user preferences from feedback over time.

Provides PreferenceLearner for modelling user preferences from implicit
and explicit feedback, ProactiveElicitation for requesting guidance when
preferences are ambiguous, DecoupledRewind for checkpoint-based session
rewind without context loss, and IdentityAnonymizedSteering for steering
decisions with anonymised user identity.
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Feedback models
# ---------------------------------------------------------------------------


@dataclass
class FeedbackEvent:
    """A single feedback event from the user.

    Attributes:
        session_id: Session identifier.
        action_type: Type of action the feedback applies to
            (e.g. "tool_call", "response", "approval").
        action_details: Details of the action.
        rating: User rating (-1 = negative, 0 = neutral, 1 = positive).
        timestamp: When the feedback was given.
        context: Additional context (e.g. reason, tags).
    """

    session_id: str
    action_type: str
    action_details: dict[str, Any] = field(default_factory=dict)
    rating: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class UserPreference:
    """Learnt user preference for a specific action type or context.

    Attributes:
        preference_id: Unique identifier.
        action_type: The action type this preference applies to.
        pattern: Descriptive pattern string (e.g. "always ask before write").
        score: Preference score in [0, 1] (higher = more preferred).
        confidence: Confidence in this preference in [0, 1].
        sample_count: Number of feedback events supporting this preference.
        tags: Free-form tags for categorisation.
    """

    preference_id: str
    action_type: str
    pattern: str
    score: float = 0.5
    confidence: float = 0.5
    sample_count: int = 0
    tags: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# PreferenceLearner
# ---------------------------------------------------------------------------


class PreferenceLearner:
    """Learns user preferences from feedback over time.

    Maintains a preference model that evolves with each feedback event.
    Preferences are stored as scored patterns per action type.
    """

    def __init__(self, persistence_path: str | None = None):
        """Initialize PreferenceLearner.

        Args:
            persistence_path: Optional file path to persist preferences.
        """
        self._preferences: dict[str, list[UserPreference]] = {}
        self._feedback_history: list[FeedbackEvent] = []
        self._persistence_path = Path(persistence_path) if persistence_path else None

        if self._persistence_path and self._persistence_path.exists():
            self._load()

    def record_feedback(self, event: FeedbackEvent) -> None:
        """Record a feedback event and update preferences.

        Args:
            event: The feedback event to record.
        """
        self._feedback_history.append(event)
        self._update_preferences(event)

    def record_feedback_simple(
        self,
        session_id: str,
        action_type: str,
        rating: int,
        details: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Record feedback with simple parameters.

        Args:
            session_id: Session identifier.
            action_type: Type of action.
            rating: User rating (-1, 0, or 1).
            details: Optional action details.
            context: Optional context.
        """
        self.record_feedback(
            FeedbackEvent(
                session_id=session_id,
                action_type=action_type,
                action_details=details or {},
                rating=rating,
                context=context or {},
            )
        )

    def get_preference(
        self, action_type: str, tags: list[str] | None = None
    ) -> UserPreference | None:
        """Get the strongest preference for an action type.

        Args:
            action_type: Action type to query.
            tags: Optional tags to filter by.

        Returns:
            Highest-confidence UserPreference, or None.
        """
        prefs = self._preferences.get(action_type, [])
        if tags:
            prefs = [p for p in prefs if any(t in p.tags for t in tags)]
        if not prefs:
            return None
        return max(prefs, key=lambda p: p.confidence)

    def get_all_preferences(self, action_type: str | None = None) -> list[UserPreference]:
        """Get all known preferences.

        Args:
            action_type: Optional filter by action type.

        Returns:
            List of UserPreference instances.
        """
        if action_type:
            return list(self._preferences.get(action_type, []))
        result: list[UserPreference] = []
        for prefs in self._preferences.values():
            result.extend(prefs)
        return result

    def predict_preference(self, action_type: str, details: dict[str, Any] | None = None) -> float:
        """Predict user preference score for an action.

        Returns a score in [0, 1] where >0.5 means likely preferred,
        <0.5 means likely not preferred.

        Args:
            action_type: Action type to evaluate.
            details: Optional action details for finer-grained matching.

        Returns:
            Predicted preference score.
        """
        pref = self.get_preference(action_type)
        if pref is None:
            return 0.5  # Neutral for unknown actions

        # If details are provided, try to find a more specific match
        if details:
            specific_prefs = [
                p
                for p in self._preferences.get(action_type, [])
                if any(kw in p.pattern.lower() for kw in self._details_keywords(details))
            ]
            if specific_prefs:
                best = max(specific_prefs, key=lambda p: p.confidence)
                return best.score

        return pref.score

    def _update_preferences(self, event: FeedbackEvent) -> None:
        """Update preference model from a feedback event."""
        action_type = event.action_type
        if action_type not in self._preferences:
            self._preferences[action_type] = []

        # Generate a pattern from the action details
        pattern = self._pattern_from_event(event)

        # Find existing preference with matching pattern
        existing = None
        for pref in self._preferences[action_type]:
            if pref.pattern == pattern:
                existing = pref
                break

        if existing is not None:
            # Update existing preference
            n = existing.sample_count
            updated_score = (existing.score * n + (event.rating + 1) / 2) / (n + 1)
            existing.score = max(0.0, min(1.0, updated_score))
            existing.sample_count += 1
            existing.confidence = min(1.0, existing.sample_count / 20.0)
        else:
            # Create new preference
            pref_id = f"{action_type}_{len(self._preferences[action_type])}"
            score = max(0.0, min(1.0, (event.rating + 1) / 2))
            self._preferences[action_type].append(
                UserPreference(
                    preference_id=pref_id,
                    action_type=action_type,
                    pattern=pattern,
                    score=score,
                    confidence=0.5,
                    sample_count=1,
                )
            )

        self._persist()

    def _pattern_from_event(self, event: FeedbackEvent) -> str:
        """Generate a descriptive pattern from a feedback event."""
        parts = [event.action_type]
        for key in ("tool", "command", "path", "provider"):
            val = event.action_details.get(key)
            if val:
                parts.append(str(val))
        return "/".join(parts)

    @staticmethod
    def _details_keywords(details: dict[str, Any]) -> list[str]:
        """Extract keywords from action details."""
        keywords: list[str] = []
        for val in details.values():
            if isinstance(val, str):
                keywords.extend(val.lower().split())
            elif isinstance(val, (list, tuple)):
                for item in val:
                    if isinstance(item, str):
                        keywords.extend(item.lower().split())
        return keywords

    def get_feedback_history(
        self,
        action_type: str | None = None,
        limit: int = 100,
    ) -> list[FeedbackEvent]:
        """Get feedback history, optionally filtered.

        Args:
            action_type: Optional filter.
            limit: Maximum events to return.

        Returns:
            List of recent FeedbackEvent instances.
        """
        if action_type:
            filtered = [e for e in self._feedback_history if e.action_type == action_type]
        else:
            filtered = list(self._feedback_history)
        return filtered[-limit:]

    # ---- persistence --------------------------------------------------------

    def _persist(self) -> None:
        """Save preferences to disk if persistence path is set."""
        if not self._persistence_path:
            return
        data = {
            "preferences": {
                at: [
                    {
                        "preference_id": p.preference_id,
                        "action_type": p.action_type,
                        "pattern": p.pattern,
                        "score": p.score,
                        "confidence": p.confidence,
                        "sample_count": p.sample_count,
                        "tags": p.tags,
                    }
                    for p in prefs
                ]
                for at, prefs in self._preferences.items()
            },
            "feedback_count": len(self._feedback_history),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self._persistence_path.parent.mkdir(parents=True, exist_ok=True)
        self._persistence_path.write_text(
            json.dumps(data, indent=2), encoding="utf-8"
        )

    def _load(self) -> None:
        """Load preferences from disk."""
        if not self._persistence_path or not self._persistence_path.exists():
            return
        try:
            data = json.loads(self._persistence_path.read_text(encoding="utf-8"))
            for at, prefs in data.get("preferences", {}).items():
                self._preferences[at] = [
                    UserPreference(**p) for p in prefs
                ]
        except Exception:
            pass


# ---------------------------------------------------------------------------
# ProactiveElicitation
# ---------------------------------------------------------------------------


@dataclass
class ElicitationQuery:
    """A proactive query to the user for guidance.

    Attributes:
        query_id: Unique query identifier.
        question: The question to ask the user.
        context: Context about why this question is being asked.
        options: Optional list of suggested options.
        answered: Whether the user has answered.
        answer: The user's answer (None if not yet answered).
    """

    query_id: str
    question: str
    context: str = ""
    options: list[str] = field(default_factory=list)
    answered: bool = False
    answer: str | None = None


class ProactiveElicitation:
    """Proactively asks the user for guidance when preferences are ambiguous.

    Tracks which situations have been clarified and learns from the
    user's answers to reduce future interruptions.
    """

    def __init__(
        self,
        preference_learner: PreferenceLearner,
        uncertainty_threshold: float = 0.4,
    ):
        """Initialize ProactiveElicitation.

        Args:
            preference_learner: Shared PreferenceLearner instance.
            uncertainty_threshold: Preference confidence below this
                triggers a query.
        """
        self._preference_learner = preference_learner
        self._uncertainty_threshold = uncertainty_threshold
        self._queries: dict[str, ElicitationQuery] = {}

    def should_ask(self, action_type: str, details: dict[str, Any] | None = None) -> bool:
        """Determine whether to proactively ask the user.

        Asks when:
          - No preference exists for this action type.
          - Preference confidence is below threshold.

        Args:
            action_type: Action to evaluate.
            details: Optional action details.

        Returns:
            True if the system should ask the user.
        """
        pref = self._preference_learner.get_preference(action_type)
        if pref is None:
            return True
        return pref.confidence < self._uncertainty_threshold

    def ask(
        self,
        action_type: str,
        context: str = "",
        options: list[str] | None = None,
        force: bool = False,
    ) -> ElicitationQuery | None:
        """Create an elicitation query for the user.

        Args:
            action_type: The action type needing clarification.
            context: Context description.
            options: Optional suggested options.
            force: If True, ask even if preference is known.

        Returns:
            ElicitationQuery if a question should be posed, None otherwise.
        """
        if not force and not self.should_ask(action_type):
            return None

        query_id = f"elicit_{len(self._queries)}_{action_type}"
        question = self._build_question(action_type, options)

        query = ElicitationQuery(
            query_id=query_id,
            question=question,
            context=context,
            options=options or [],
        )
        self._queries[query_id] = query
        return query

    def answer_query(self, query_id: str, answer: str) -> bool:
        """Record the user's answer to an elicitation query.

        Also updates the preference model with the answer.

        Args:
            query_id: Query identifier.
            answer: The user's answer.

        Returns:
            True if the query was found and answered.
        """
        query = self._queries.get(query_id)
        if query is None or query.answered:
            return False

        query.answer = answer
        query.answered = True

        # Derive a feedback event from the answer
        action_type = query_id.split("_", 2)[-1] if "_" in query_id else "unknown"
        rating = 1  # Assuming user-provided guidance is positive feedback
        self._preference_learner.record_feedback_simple(
            session_id="_elicitation_",
            action_type=action_type,
            rating=rating,
            details={"elicited_answer": answer, "question": query.question},
        )

        return True

    def pending_queries(self) -> list[ElicitationQuery]:
        """Return unanswered queries."""
        return [q for q in self._queries.values() if not q.answered]

    def _build_question(self, action_type: str, options: list[str] | None) -> str:
        """Build a natural-language question for the user."""
        base = f"How should I handle '{action_type}' actions?"
        if options:
            base += f" Options: {', '.join(options)}"
        return base


# ---------------------------------------------------------------------------
# DecoupledRewind
# ---------------------------------------------------------------------------


@dataclass
class RewindCheckpoint:
    """A checkpoint that can be rewound to without losing context.

    Attributes:
        checkpoint_id: Unique checkpoint identifier.
        timestamp: When the checkpoint was created.
        session_state: Snapshot of session state (tokens, context, etc.).
        metadata: User-facing metadata describing this point.
        context_blob: Preserved context that survives rewind.
    """

    checkpoint_id: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    session_state: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    context_blob: dict[str, Any] = field(default_factory=dict)


class DecoupledRewind:
    """Rewinds a session to a checkpoint while preserving accumulated context.

    Unlike a hard rollback, the rewind keeps context_blob intact so
    the agent does not lose what it learned up to that point.
    """

    def __init__(self):
        """Initialize DecoupledRewind."""
        self._checkpoints: dict[str, RewindCheckpoint] = {}
        self._checkpoint_counter: int = 0

    def save_checkpoint(
        self,
        session_state: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        context_blob: dict[str, Any] | None = None,
    ) -> str:
        """Save a checkpoint for potential rewind.

        Args:
            session_state: Snapshot of session variables.
            metadata: User-facing metadata (e.g. action description).
            context_blob: Context that should survive rewind.

        Returns:
            Checkpoint ID.
        """
        self._checkpoint_counter += 1
        ckpt_id = f"rewind_{self._checkpoint_counter}"

        checkpoint = RewindCheckpoint(
            checkpoint_id=ckpt_id,
            session_state=copy.deepcopy(session_state or {}),
            metadata=metadata or {},
            context_blob=copy.deepcopy(context_blob or {}),
        )
        self._checkpoints[ckpt_id] = checkpoint
        return ckpt_id

    def rewind(self, checkpoint_id: str) -> RewindCheckpoint | None:
        """Rewind to a checkpoint, returning the restored state.

        The context_blob from the checkpoint is preserved.

        Args:
            checkpoint_id: Checkpoint to rewind to.

        Returns:
            RewindCheckpoint if found, None otherwise.
        """
        checkpoint = self._checkpoints.get(checkpoint_id)
        if checkpoint is None:
            return None

        # Remove all checkpoints after this one
        to_remove: list[str] = []
        for ckpt_id in self._checkpoints:
            if ckpt_id == checkpoint_id:
                break
            to_remove.append(ckpt_id)
        for ckpt_id in to_remove:
            self._checkpoints.pop(ckpt_id, None)

        return RewindCheckpoint(
            checkpoint_id=checkpoint.checkpoint_id,
            timestamp=checkpoint.timestamp,
            session_state=copy.deepcopy(checkpoint.session_state),
            metadata=copy.deepcopy(checkpoint.metadata),
            context_blob=copy.deepcopy(checkpoint.context_blob),
        )

    def list_checkpoints(self) -> list[RewindCheckpoint]:
        """Return all saved checkpoints in order."""
        return list(self._checkpoints.values())

    def latest_checkpoint(self) -> RewindCheckpoint | None:
        """Return the most recent checkpoint."""
        if not self._checkpoints:
            return None
        return max(self._checkpoints.values(), key=lambda c: c.timestamp)

    def clear(self) -> None:
        """Remove all checkpoints."""
        self._checkpoints.clear()
        self._checkpoint_counter = 0


# ---------------------------------------------------------------------------
# IdentityAnonymizedSteering
# ---------------------------------------------------------------------------


@dataclass
class AnonymizedSteeringDecision:
    """A steering decision made with anonymised identity.

    Attributes:
        decision_id: Unique decision identifier.
        action: The steering action taken.
        session_anonymized_id: Anonymised session identifier.
        reason: Reason for the decision.
        confident: Whether the system was confident in this decision.
        timestamp: When the decision was made.
    """

    decision_id: str
    action: str
    session_anonymized_id: str = ""
    reason: str = ""
    confident: bool = True
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class IdentityAnonymizedSteering:
    """Makes steering decisions with anonymised user identity.

    Strips personally identifiable information from session data before
    making steering decisions, enabling privacy-preserving steering.
    """

    def __init__(self, salt: str = "lyra-anon"):
        """Initialize IdentityAnonymizedSteering.

        Args:
            salt: Salt for hashing session IDs.
        """
        import hashlib
        self._salt = salt
        self._hasher = hashlib.sha256  # Use sha256 for readability
        self._decisions: list[AnonymizedSteeringDecision] = []

    def anonymize(self, session_id: str) -> str:
        """Produce an anonymised identifier from a session ID.

        Args:
            session_id: Original session identifier.

        Returns:
            Anonymised session identifier (first 16 hex chars).
        """
        raw = (session_id + self._salt).encode()
        return self._hasher(raw).hexdigest()[:16]

    def record_decision(
        self,
        action: str,
        session_id: str,
        reason: str = "",
        confident: bool = True,
    ) -> AnonymizedSteeringDecision:
        """Record a steering decision with anonymised identity.

        Args:
            action: The steering action taken.
            session_id: Original session ID (will be anonymised).
            reason: Reason for the decision.
            confident: Whether confident in the decision.

        Returns:
            The recorded AnonymizedSteeringDecision.
        """
        decision = AnonymizedSteeringDecision(
            decision_id=f"anon_decision_{len(self._decisions)}",
            action=action,
            session_anonymized_id=self.anonymize(session_id),
            reason=reason,
            confident=confident,
        )
        self._decisions.append(decision)
        return decision

    def get_decisions(
        self, session_id: str | None = None
    ) -> list[AnonymizedSteeringDecision]:
        """Get steering decisions, optionally filtered by session.

        Args:
            session_id: If provided, matched against anonymised ID.

        Returns:
            List of AnonymizedSteeringDecision instances.
        """
        if session_id is None:
            return list(self._decisions)
        anon_id = self.anonymize(session_id)
        return [d for d in self._decisions if d.session_anonymized_id == anon_id]

    def get_decision_count(self) -> int:
        """Return total number of recorded decisions."""
        return len(self._decisions)


__all__ = [
    "FeedbackEvent",
    "UserPreference",
    "PreferenceLearner",
    "ElicitationQuery",
    "ProactiveElicitation",
    "RewindCheckpoint",
    "DecoupledRewind",
    "AnonymizedSteeringDecision",
    "IdentityAnonymizedSteering",
]
