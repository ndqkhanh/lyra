"""InstinctEngine — detects recurring patterns from session traces and evolves skills.

Core innovation of ECC v2: instead of manual skill authoring, skills emerge
automatically from detected patterns in agent behavior across sessions.
"""

from time import time

from .models import (
    EvolvedSkill,
    PatternType,
    RecurringPattern,
    SessionTrace,
    SkillState,
)


class InstinctEngine:
    """Detects recurring patterns from session traces and evolves skills.

    Three-phase pipeline:
    1. Ingest — collect session traces with outcomes
    2. Detect — find recurring patterns (successes, failures, workarounds)
    3. Evolve — convert strong patterns into persistent skills
    """

    def __init__(self, min_frequency: int = 3, min_confidence: float = 0.6):
        self._traces: list[SessionTrace] = []
        self._patterns: dict[str, RecurringPattern] = {}
        self._skills: dict[str, EvolvedSkill] = {}
        self._min_frequency = min_frequency
        self._min_confidence = min_confidence

    def ingest(self, trace: SessionTrace) -> None:
        """Ingest a session trace for pattern analysis."""
        self._traces.append(trace)
        self._detect_patterns(trace)

    def _detect_patterns(self, trace: SessionTrace) -> list[RecurringPattern]:
        """Detect patterns from a session trace."""
        found: list[RecurringPattern] = []
        event_strs = [str(e) for e in trace.events]

        if trace.outcome == "success":
            found.extend(self._extract_patterns(trace, PatternType.SUCCESS, event_strs))
        elif trace.outcome == "failure":
            found.extend(self._extract_patterns(trace, PatternType.FAILURE, event_strs))

        for e in trace.events:
            if "workaround" in str(e).lower():
                found.extend(self._extract_patterns(trace, PatternType.WORKAROUND, [str(e)]))
            if "optimize" in str(e).lower() or "optimization" in str(e).lower():
                found.extend(self._extract_patterns(trace, PatternType.OPTIMIZATION, [str(e)]))

        for pattern in found:
            if pattern.id in self._patterns:
                existing = self._patterns[pattern.id]
                updated = RecurringPattern(
                    id=existing.id,
                    pattern_type=existing.pattern_type,
                    description=existing.description,
                    frequency=existing.frequency + 1,
                    sessions=existing.sessions + (trace.session_id,),
                    confidence=min(existing.confidence + 0.1, 1.0),
                    first_seen=existing.first_seen,
                    last_seen=time(),
                )
                self._patterns[pattern.id] = updated
            else:
                self._patterns[pattern.id] = pattern

        return found

    @staticmethod
    def _make_pattern_id(ptype: PatternType, description: str) -> str:
        """Deterministic pattern ID so the same pattern is recognized across ingestions."""
        import hashlib

        key = f"{ptype.value}:{description}"
        return hashlib.sha256(key.encode()).hexdigest()[:16]

    def _extract_patterns(
        self, trace: SessionTrace, ptype: PatternType, texts: list[str]
    ) -> list[RecurringPattern]:
        """Extract patterns from text snippets — simplified keyword-based extraction."""
        patterns: list[RecurringPattern] = []
        keywords = {
            PatternType.SUCCESS: ["completed", "passed", "succeeded", "solved", "fixed"],
            PatternType.FAILURE: ["failed", "error", "timeout", "exception", "crash"],
            PatternType.WORKAROUND: ["workaround", "bypass", "fallback", "alternative"],
            PatternType.OPTIMIZATION: ["optimize", "faster", "reduce", "cache", "batch"],
            PatternType.BUG: ["bug", "defect", "regression", "incorrect"],
        }

        relevant = keywords.get(ptype, [])
        now = time()
        for text in texts:
            text_lower = text.lower()
            for kw in relevant:
                if kw in text_lower:
                    desc = f"{ptype.value}: {text[:200]}"
                    pattern = RecurringPattern(
                        id=self._make_pattern_id(ptype, desc),
                        pattern_type=ptype,
                        description=desc,
                        frequency=1,
                        sessions=(trace.session_id,),
                        confidence=0.5,
                        first_seen=now,
                        last_seen=now,
                    )
                    patterns.append(pattern)
        return patterns

    def evolve_skills(self) -> list[EvolvedSkill]:
        """Convert strong recurring patterns into evolved skills."""
        import uuid

        already_converted = {
            pid
            for s in self._skills.values()
            for pid in (s.source_pattern_ids or ())
        }

        new_skills: list[EvolvedSkill] = []
        for pattern in self._patterns.values():
            strong = pattern.confidence >= self._min_confidence and pattern.frequency >= self._min_frequency
            if strong and pattern.id not in already_converted:
                skill = EvolvedSkill(
                    id=str(uuid.uuid4()),
                    name=f"auto-skill-{pattern.pattern_type.value}",
                    description=pattern.description,
                    source_pattern_ids=(pattern.id,),
                    state=SkillState.EMERGING,
                )
                self._skills[skill.id] = skill
                new_skills.append(skill)
        return new_skills

    def get_skill(self, skill_id: str) -> EvolvedSkill | None:
        return self._skills.get(skill_id)

    def retire_skill(self, skill_id: str) -> EvolvedSkill | None:
        skill = self._skills.get(skill_id)
        if skill is None:
            return None
        updated = EvolvedSkill(
            id=skill.id, name=skill.name, description=skill.description,
            source_pattern_ids=skill.source_pattern_ids, state=SkillState.RETIRED,
            version=skill.version, success_rate=skill.success_rate,
            usage_count=skill.usage_count, last_used=time(),
        )
        self._skills[skill_id] = updated
        return updated

    def active_skills(self) -> list[EvolvedSkill]:
        return [s for s in self._skills.values() if s.state == SkillState.EMERGING or s.state == SkillState.STABLE]

    @property
    def trace_count(self) -> int:
        return len(self._traces)

    @property
    def pattern_count(self) -> int:
        return len(self._patterns)

    @property
    def skill_count(self) -> int:
        return len(self._skills)
