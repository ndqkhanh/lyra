"""Context-Aware Trigger Matching — match task context to skill triggers with pre-compiled regex
patterns (sub-50ms)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum, auto

from lyra_skill_loader.exceptions import TriggerError
from lyra_skill_loader.tiered_loader import LoadTier, SkillMetadata


class TriggerType(Enum):
    """Classification of trigger match."""

    KEYWORD = auto()
    CONTEXT = auto()
    CAPABILITY = auto()
    INTENT = auto()
    EXPLICIT = auto()


@dataclass(frozen=True)
class Trigger:
    """A trigger pattern associated with a skill."""

    pattern: str
    keywords: tuple[str, ...] = ()
    context_patterns: tuple[str, ...] = ()
    priority: int = 0
    skill_id: str = ""


@dataclass(frozen=True)
class MatchResult:
    """Result of matching a task context against skill triggers."""

    skill_id: str
    score: float
    matched_triggers: tuple[str, ...]
    confidence: float
    load_tier: LoadTier
    trigger_type: TriggerType = TriggerType.KEYWORD


@dataclass(frozen=True)
class MatchConfig:
    """Configuration for trigger matching."""

    min_score: float = 0.3
    max_matches: int = 5
    exact_match_boost: float = 1.5


class TriggerMatcher:
    """Matches task context against registered skill triggers.

    Pre-compiles regex patterns for O(1) keyword matching and supports multiple trigger types
    (keyword, context, capability, intent, explicit).
    """

    def __init__(self, config: MatchConfig | None = None) -> None:
        self._config = config or MatchConfig()
        self._triggers: dict[str, Trigger] = {}
        self._compiled_patterns: dict[str, re.Pattern[str]] = {}
        self._context_patterns: dict[str, list[re.Pattern[str]]] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register_trigger(self, trigger: Trigger) -> None:
        """Register a trigger and pre-compile its regex patterns."""
        if trigger.skill_id in self._triggers:
            msg = f"Trigger already registered for skill: {trigger.skill_id}"
            raise TriggerError(msg)

        self._triggers[trigger.skill_id] = trigger
        self._precompile(trigger)

    def register_skill_triggers(self, skill_id: str, metadata: SkillMetadata) -> None:
        """Convenience: create and register a trigger from skill metadata."""
        keywords = metadata.triggers + metadata.tags
        trigger = Trigger(
            pattern=metadata.name,
            keywords=keywords,
            context_patterns=(),
            priority=len(metadata.triggers),
            skill_id=skill_id,
        )
        self.register_trigger(trigger)

    def unregister_trigger(self, skill_id: str) -> None:
        """Remove a trigger by skill id."""
        self._triggers.pop(skill_id, None)
        self._compiled_patterns.pop(skill_id, None)
        self._context_patterns.pop(skill_id, None)

    def list_triggers(self) -> tuple[str, ...]:
        """Return all registered trigger skill ids."""
        return tuple(self._triggers.keys())

    # ------------------------------------------------------------------
    # Matching
    # ------------------------------------------------------------------

    def match(self, task_context: str) -> list[MatchResult]:
        """Match task context against all registered triggers.

        Returns unsorted match results. Use :meth:`rank_matches` to sort and filter by score.
        """
        if not task_context:
            return []

        results: list[MatchResult] = []

        for skill_id, trigger in self._triggers.items():
            result = self._match_single(task_context, skill_id, trigger)
            if result is not None:
                results.append(result)

        return results

    def rank_matches(self, matches: list[MatchResult]) -> list[MatchResult]:
        """Sort matches by relevance (descending score) and apply config limits.

        Filters out matches below ``min_score``, caps at ``max_matches``, and sorts by descending
        score.
        """
        filtered = [m for m in matches if m.score >= self._config.min_score]
        filtered.sort(key=lambda m: (-m.score, -m.confidence))
        return filtered[: self._config.max_matches]

    def match_and_rank(self, task_context: str) -> list[MatchResult]:
        """Convenience: match then rank in one call."""
        matches = self.match(task_context)
        return self.rank_matches(matches)

    def best_match(self, task_context: str) -> MatchResult | None:
        """Return the single best match, or None if none qualifies."""
        ranked = self.match_and_rank(task_context)
        return ranked[0] if ranked else None

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _precompile(self, trigger: Trigger) -> None:
        """Build and store compiled regex patterns for a trigger."""
        skip_chars = re.compile(r"[^a-z0-9\s-]")

        def _clean(text: str) -> str:
            return skip_chars.sub("", text.lower().strip())

        # Compile keyword patterns with word boundaries
        patterns: list[re.Pattern[str]] = []
        for kw in trigger.keywords:
            cleaned = re.escape(_clean(kw))
            if cleaned:
                patterns.append(re.compile(r"\b" + cleaned + r"\b", re.IGNORECASE))
        self._compiled_patterns[trigger.skill_id] = (
            patterns[0]
            if len(patterns) == 1
            else (
                re.compile("|".join(p.pattern for p in patterns))
                if patterns
                else re.compile(r"(?!)")
            )
        )  # never-match pattern

        # Compile context regex patterns
        ctx_patterns: list[re.Pattern[str]] = []
        for cp in trigger.context_patterns:
            try:
                ctx_patterns.append(re.compile(cp, re.IGNORECASE))
            except re.error:
                pass
        self._context_patterns[trigger.skill_id] = ctx_patterns

    def _detect_trigger_type(
        self,
        task_context: str,
        trigger: Trigger,
    ) -> tuple[TriggerType, float, list[str]]:
        """Determine the trigger type, base score, and matched items."""
        lower_ctx = task_context.lower()

        # Check explicit match (context contains the skill pattern directly)
        if trigger.pattern.lower() in lower_ctx:
            return TriggerType.EXPLICIT, 1.0, [trigger.pattern]

        # Check keyword matching
        matched_kws: list[str] = []
        for kw in trigger.keywords:
            if kw.lower() in lower_ctx or self._word_in_context(kw, task_context):
                matched_kws.append(kw)
        if matched_kws:
            ratio = len(matched_kws) / max(len(trigger.keywords), 1)
            score = 0.4 + (ratio * 0.4)
            return TriggerType.KEYWORD, score, matched_kws

        # Check context pattern matching (regex)
        ctx_patterns = self._context_patterns.get(trigger.skill_id, [])
        matched_ctx: list[str] = []
        for pat in ctx_patterns:
            if pat.search(task_context):
                matched_ctx.append(pat.pattern)
        if matched_ctx:
            return TriggerType.CONTEXT, 0.5, matched_ctx

        return TriggerType.KEYWORD, 0.0, []

    @staticmethod
    def _word_in_context(word: str, context: str) -> bool:
        """Check if a word appears as a whole word in the context."""
        escaped = re.escape(word)
        return bool(re.search(r"\b" + escaped + r"\b", context, re.IGNORECASE))

    def _match_single(
        self,
        task_context: str,
        skill_id: str,
        trigger: Trigger,
    ) -> MatchResult | None:
        """Match a single trigger against the task context."""
        trigger_type, base_score, matched_items = self._detect_trigger_type(task_context, trigger)

        if base_score == 0.0:
            return None

        # Apply exact match boost
        score = base_score
        if base_score >= 0.9:
            score *= self._config.exact_match_boost

        # Apply priority scaling (priority range: 0-10, produces 1.0x-2.0x)
        priority_mult = 1.0 + (trigger.priority / 10.0)
        score *= priority_mult

        # Cap score at reasonable max
        score = min(score, 2.0)

        # Determine load tier based on score
        load_tier = LoadTier.TIER1_METADATA
        if score >= 1.5:
            load_tier = LoadTier.TIER3_REFERENCES
        elif score >= 0.8:
            load_tier = LoadTier.TIER2_CONTENT

        return MatchResult(
            skill_id=skill_id,
            score=score,
            matched_triggers=tuple(matched_items),
            confidence=min(score, 1.0),
            load_tier=load_tier,
            trigger_type=trigger_type,
        )
