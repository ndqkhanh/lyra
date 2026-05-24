"""HeuristicExtractor — deterministic preference extractor.

Detects four classes of durable preferences from edit patterns:

    1. **Length preference**: edits consistently shorten or lengthen.
    2. **Vocabulary substitution**: word A → word B across edits.
    3. **Tone preference**: emoji / exclamation removal or addition.
    4. **Structure preference**: bullet introduction / removal.

The extractor groups edits per user, then reports a preference per pattern
when at least ``min_supporting_edits`` of that user's edits agree. The
production path wires an LLM-backed extractor via the
:class:`PreferenceExtractor` Protocol (richer rules, free-form rationales).
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass

from .types import EditEvent, LearnedPreference


_EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F700-\U0001F77F"
    "\U0001F900-\U0001F9FF"
    "☀-➿"
    "]"
)


@dataclass
class HeuristicExtractor:
    """Deterministic, dependency-free preference extractor.

    Tunables:
        min_supporting_edits: a pattern requires at least this many supporting
            edits before it produces a :class:`LearnedPreference`.
        confidence_per_edit: each supporting edit raises confidence by this
            increment; capped at 1.0.
        length_delta_threshold: a length-preference fires when the average
            absolute length delta of all edits is at least this many chars.

    >>> extractor = HeuristicExtractor(min_supporting_edits=2)
    >>> extractor.min_supporting_edits
    2
    """

    min_supporting_edits: int = 3
    confidence_per_edit: float = 0.2
    length_delta_threshold: int = 20

    def __post_init__(self) -> None:
        if self.min_supporting_edits < 1:
            raise ValueError(
                f"min_supporting_edits must be >= 1, got {self.min_supporting_edits}"
            )
        if not 0.0 < self.confidence_per_edit <= 1.0:
            raise ValueError(
                f"confidence_per_edit must be in (0, 1], got {self.confidence_per_edit}"
            )

    def extract(self, edits: list[EditEvent]) -> list[LearnedPreference]:
        if not edits:
            return []
        per_user: dict[str, list[EditEvent]] = defaultdict(list)
        for e in edits:
            per_user[e.user_id].append(e)
        out: list[LearnedPreference] = []
        for user_id, user_edits in per_user.items():
            out.extend(self._extract_for_user(user_id, user_edits))
        return out

    # --- Per-user pattern detectors --------------------------------------

    def _extract_for_user(
        self,
        user_id: str,
        edits: list[EditEvent],
    ) -> list[LearnedPreference]:
        out: list[LearnedPreference] = []
        out.extend(self._length_preference(user_id, edits))
        out.extend(self._vocabulary_preference(user_id, edits))
        out.extend(self._emoji_preference(user_id, edits))
        out.extend(self._bullet_preference(user_id, edits))
        return out

    def _length_preference(
        self,
        user_id: str,
        edits: list[EditEvent],
    ) -> list[LearnedPreference]:
        if len(edits) < self.min_supporting_edits:
            return []
        n_shorter = sum(1 for e in edits if e.shortened)
        n_longer = sum(1 for e in edits if e.lengthened)
        if n_shorter >= self.min_supporting_edits and n_shorter >= 2 * n_longer:
            avg_delta = sum(e.length_delta_chars for e in edits if e.shortened) / n_shorter
            if abs(avg_delta) >= self.length_delta_threshold:
                conf = min(1.0, n_shorter * self.confidence_per_edit)
                return [LearnedPreference.create(
                    rule=(
                        f"User {user_id} prefers shorter outputs "
                        f"(avg {abs(avg_delta):.0f} chars removed)"
                    ),
                    user_id=user_id,
                    confidence=conf,
                    n_supporting_edits=n_shorter,
                    tags=("length", "tone"),
                    metadata={"direction": "shorter", "avg_delta": avg_delta},
                )]
        if n_longer >= self.min_supporting_edits and n_longer >= 2 * n_shorter:
            avg_delta = sum(e.length_delta_chars for e in edits if e.lengthened) / n_longer
            if abs(avg_delta) >= self.length_delta_threshold:
                conf = min(1.0, n_longer * self.confidence_per_edit)
                return [LearnedPreference.create(
                    rule=(
                        f"User {user_id} prefers more detailed outputs "
                        f"(avg {abs(avg_delta):.0f} chars added)"
                    ),
                    user_id=user_id,
                    confidence=conf,
                    n_supporting_edits=n_longer,
                    tags=("length", "tone"),
                    metadata={"direction": "longer", "avg_delta": avg_delta},
                )]
        return []

    def _vocabulary_preference(
        self,
        user_id: str,
        edits: list[EditEvent],
    ) -> list[LearnedPreference]:
        substitutions: Counter = Counter()
        for e in edits:
            for sub in self._diff_substitutions(e.agent_output, e.user_edit):
                substitutions[sub] += 1
        out: list[LearnedPreference] = []
        for (orig, repl), count in substitutions.items():
            if count >= self.min_supporting_edits:
                conf = min(1.0, count * self.confidence_per_edit)
                out.append(LearnedPreference.create(
                    rule=(
                        f"User {user_id} replaces '{orig}' with '{repl}'"
                    ),
                    user_id=user_id,
                    confidence=conf,
                    n_supporting_edits=count,
                    tags=("vocabulary",),
                    metadata={"original": orig, "replacement": repl},
                ))
        return out

    def _emoji_preference(
        self,
        user_id: str,
        edits: list[EditEvent],
    ) -> list[LearnedPreference]:
        n_removes = 0
        n_adds = 0
        for e in edits:
            agent_emojis = len(_EMOJI_PATTERN.findall(e.agent_output))
            edit_emojis = len(_EMOJI_PATTERN.findall(e.user_edit))
            if agent_emojis > edit_emojis:
                n_removes += 1
            elif edit_emojis > agent_emojis:
                n_adds += 1
        out: list[LearnedPreference] = []
        if n_removes >= self.min_supporting_edits and n_removes >= 2 * n_adds:
            conf = min(1.0, n_removes * self.confidence_per_edit)
            out.append(LearnedPreference.create(
                rule=f"User {user_id} removes emoji from outputs",
                user_id=user_id,
                confidence=conf,
                n_supporting_edits=n_removes,
                tags=("tone", "emoji"),
                metadata={"direction": "remove"},
            ))
        elif n_adds >= self.min_supporting_edits and n_adds >= 2 * n_removes:
            conf = min(1.0, n_adds * self.confidence_per_edit)
            out.append(LearnedPreference.create(
                rule=f"User {user_id} adds emoji to outputs",
                user_id=user_id,
                confidence=conf,
                n_supporting_edits=n_adds,
                tags=("tone", "emoji"),
                metadata={"direction": "add"},
            ))
        return out

    def _bullet_preference(
        self,
        user_id: str,
        edits: list[EditEvent],
    ) -> list[LearnedPreference]:
        n_to_bullets = 0
        n_from_bullets = 0
        for e in edits:
            agent_bullets = self._count_bullets(e.agent_output)
            edit_bullets = self._count_bullets(e.user_edit)
            if edit_bullets > agent_bullets:
                n_to_bullets += 1
            elif agent_bullets > edit_bullets:
                n_from_bullets += 1
        out: list[LearnedPreference] = []
        if (
            n_to_bullets >= self.min_supporting_edits
            and n_to_bullets >= 2 * n_from_bullets
        ):
            conf = min(1.0, n_to_bullets * self.confidence_per_edit)
            out.append(LearnedPreference.create(
                rule=f"User {user_id} prefers bullet-list formatting",
                user_id=user_id,
                confidence=conf,
                n_supporting_edits=n_to_bullets,
                tags=("structure", "format"),
                metadata={"direction": "to_bullets"},
            ))
        elif (
            n_from_bullets >= self.min_supporting_edits
            and n_from_bullets >= 2 * n_to_bullets
        ):
            conf = min(1.0, n_from_bullets * self.confidence_per_edit)
            out.append(LearnedPreference.create(
                rule=f"User {user_id} prefers prose over bullet lists",
                user_id=user_id,
                confidence=conf,
                n_supporting_edits=n_from_bullets,
                tags=("structure", "format"),
                metadata={"direction": "from_bullets"},
            ))
        return out

    # --- Helpers ---------------------------------------------------------

    @staticmethod
    def _diff_substitutions(
        agent: str,
        edit: str,
    ) -> list[tuple[str, str]]:
        """Detect single-word substitutions: words in agent absent from edit
        paired against words in edit absent from agent, when both lists have
        the same length and the structure is otherwise close."""
        agent_tokens = re.findall(r"\b\w+\b", agent.lower())
        edit_tokens = re.findall(r"\b\w+\b", edit.lower())
        agent_set = set(agent_tokens)
        edit_set = set(edit_tokens)
        only_agent = list(agent_set - edit_set)
        only_edit = list(edit_set - agent_set)
        # Only attempt substitution detection on simple symmetric edits.
        if len(only_agent) == 1 and len(only_edit) == 1:
            return [(only_agent[0], only_edit[0])]
        return []

    @staticmethod
    def _count_bullets(text: str) -> int:
        n = 0
        for line in text.splitlines():
            stripped = line.lstrip()
            if stripped.startswith(("- ", "* ", "• ")):
                n += 1
        return n


__all__ = ["HeuristicExtractor"]
