"""Anti-pattern registry — detect and avoid known-bad patterns.

Feeds into safety monitoring (``SafetyMonitor``) and the agent loop's
pre-tool-call hooks (``SafetyHookPlugin``) to block known failure modes
before they execute.
"""

from __future__ import annotations

import time
from collections.abc import Sequence
from dataclasses import dataclass, field


@dataclass(frozen=True)
class AntiPattern:
    """A known-bad pattern to detect and avoid."""

    id: str
    name: str
    description: str
    severity: str  # "low", "medium", "high", "critical"
    pattern_source: str
    detection_rule: str = ""
    suggested_fix: str = ""
    occurrence_count: int = 0
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    tags: tuple[str, ...] = ()

    def with_occurrence(self) -> AntiPattern:
        """Return a new copy with incremented occurrence count."""
        return AntiPattern(
            id=self.id,
            name=self.name,
            description=self.description,
            severity=self.severity,
            pattern_source=self.pattern_source,
            detection_rule=self.detection_rule,
            suggested_fix=self.suggested_fix,
            occurrence_count=self.occurrence_count + 1,
            first_seen=self.first_seen,
            last_seen=time.time(),
            tags=self.tags,
        )


@dataclass(frozen=True)
class MatchResult:
    """Result of matching an anti-pattern against content."""

    anti_pattern: AntiPattern
    matched: bool
    confidence: float
    evidence: str = ""
    matched_location: str = ""


@dataclass
class AntiPatternRegistry:
    """Registry to add, query, and match anti-patterns against content.

    Usage::

        reg = AntiPatternRegistry()
        reg.register(AntiPattern(id="ap1", name="hardcoded_secret", ...))
        results = reg.match("const API_KEY = 'sk-abc123'")
    """

    max_patterns: int = 200
    _patterns: dict[str, AntiPattern] = field(default_factory=dict)

    def register(self, pattern: AntiPattern) -> None:
        if len(self._patterns) >= self.max_patterns:
            oldest = min(
                self._patterns.values(), key=lambda p: p.last_seen
            )
            del self._patterns[oldest.id]
        self._patterns[pattern.id] = pattern

    def unregister(self, pattern_id: str) -> bool:
        return self._patterns.pop(pattern_id, None) is not None

    def match(self, content: str, *, min_confidence: float = 0.5) -> tuple[MatchResult, ...]:
        """Match content against all registered anti-patterns."""
        results: list[MatchResult] = []
        content_lower = content.lower()
        for pattern in self._patterns.values():
            matched = False
            if pattern.detection_rule and pattern.detection_rule.lower() in content_lower:
                results.append(MatchResult(
                    anti_pattern=pattern.with_occurrence(),
                    matched=True,
                    confidence=0.8,
                    evidence=f"Matched rule: {pattern.detection_rule}",
                ))
                matched = True

            if not matched and pattern.name.lower() in content_lower:
                results.append(MatchResult(
                    anti_pattern=pattern,
                    matched=True,
                    confidence=0.5,
                    evidence=f"Name match: {pattern.name}",
                ))
        return tuple(r for r in results if r.confidence >= min_confidence)

    def match_all(self, contents: Sequence[str]) -> list[MatchResult]:
        """Match multiple content strings against all anti-patterns."""
        results: list[MatchResult] = []
        for content in contents:
            results.extend(self.match(content))
        return results

    def get_by_severity(self, severity: str) -> tuple[AntiPattern, ...]:
        return tuple(p for p in self._patterns.values() if p.severity == severity)

    def get_frequent(self, min_occurrences: int = 5) -> tuple[AntiPattern, ...]:
        return tuple(p for p in self._patterns.values()
                    if p.occurrence_count >= min_occurrences)

    def merge(self, other: AntiPatternRegistry) -> None:
        """Merge patterns from another registry, deduplicating by name."""
        for pattern in other._patterns.values():
            if not self._get_by_name(pattern.name):
                self.register(pattern)

    def _get_by_name(self, name: str) -> AntiPattern | None:
        for p in self._patterns.values():
            if p.name == name:
                return p
        return None

    def to_list(self) -> tuple[AntiPattern, ...]:
        return tuple(self._patterns.values())

    def by_tag(self, tag: str) -> tuple[AntiPattern, ...]:
        return tuple(p for p in self._patterns.values() if tag in p.tags)

    @property
    def count(self) -> int:
        return len(self._patterns)
