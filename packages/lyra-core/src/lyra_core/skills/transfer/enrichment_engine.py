"""Enrichment Engine - Enriches target skills with transferred patterns.

Applies extracted patterns to target skill implementations, adapting them
to the target domain and validating the enrichment results.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class EnrichmentStatus(StrEnum):
    """Status of a skill enrichment operation."""

    ENRICHED = "enriched"
    UNCHANGED = "unchanged"
    REJECTED = "rejected"
    PARTIAL = "partial"


class AdaptationLevel(StrEnum):
    """How much adaptation was needed for the enrichment."""

    NONE = "none"          # Direct copy
    MINIMAL = "minimal"     # Rename/refactor
    MODERATE = "moderate"   # Restructure
    SIGNIFICANT = "significant"  # Major rewrite needed


@dataclass(frozen=True)
class EnrichmentAction:
    """A single enrichment action to apply to a skill."""

    action_type: str  # "add_import", "add_function", "add_class", "add_decorator"
    target_skill: str
    content: str
    position: str  # "top", "bottom", "before_pattern", "after_pattern"
    adaptation_level: AdaptationLevel
    confidence: float  # 0.0-1.0


@dataclass(frozen=True)
class EnrichmentResult:
    """Result of enriching a target skill with transferred patterns."""

    target_skill: str
    source_skills: tuple[str, ...]
    actions_applied: tuple[EnrichmentAction, ...]
    status: EnrichmentStatus
    original_lines: int
    enriched_lines: int
    added_patterns: int
    rejected_patterns: int
    enrichment_score: float  # 0.0-1.0
    message: str = ""


@dataclass(frozen=True)
class EnrichmentReport:
    """Aggregate report on skill enrichment operations."""

    total_enrichments: int
    successful: int
    rejected: int
    partial: int
    avg_patterns_added: float
    top_added_pattern_types: tuple[tuple[str, int], ...]
    timestamp: str


class EnrichmentEngine:
    """Enriches target skills with transferred patterns from source skills.

    Adapts extracted patterns to target domain context and applies
    them to skill implementations with validation.

    Features:
    - Pattern adaptation to target domain (rename, restructure)
    - Multi-level adaptation (none through significant)
    - Enrichment action generation and application
    - Enrichment quality scoring
    - Aggregate enrichment reporting
    """

    def __init__(self, max_patterns_per_enrichment: int = 10):
        self.max_patterns_per_enrichment = max_patterns_per_enrichment
        self._history: list[EnrichmentResult] = []

    def build_actions(
        self,
        target_skill: str,
        source_patterns: list[dict],
        target_domain: str,
    ) -> list[EnrichmentAction]:
        """Build enrichment actions from source patterns for a target skill.

        Args:
            target_skill: Name of the skill to enrich
            source_patterns: List of pattern dicts from PatternExtractor
            target_domain: Target domain to adapt patterns for

        Returns:
            List of EnrichmentAction
        """
        actions: list[EnrichmentAction] = []
        seen_content: set[str] = set()

        for pattern in source_patterns[: self.max_patterns_per_enrichment]:
            pattern_type = pattern.get("pattern_type", "structure")
            content = pattern.get("content", "")
            name = pattern.get("name", "")

            # Skip duplicates
            content_hash = f"{pattern_type}:{content}"
            if content_hash in seen_content:
                continue
            seen_content.add(content_hash)

            adaptation = self._determine_adaptation(
                pattern.get("source_skill", ""), target_domain
            )

            action_type_map = {
                "import": "add_import",
                "function": "add_function",
                "class": "add_class",
                "decorator": "add_decorator",
                "error_handling": "add_function",
                "validation": "add_function",
            }

            action = EnrichmentAction(
                action_type=action_type_map.get(pattern_type, "add_function"),
                target_skill=target_skill,
                content=f"# Enriched from {pattern.get('source_skill', 'unknown')}: {name}\n{content}",
                position="bottom" if pattern_type in ("import",) else "before_pattern",
                adaptation_level=adaptation,
                confidence=pattern.get("reusability_score", 0.5),
            )
            actions.append(action)

        return actions

    def enrich(
        self,
        target_skill: str,
        source_code: str,
        actions: list[EnrichmentAction],
        target_domain: str = "",
    ) -> EnrichmentResult:
        """Apply enrichment actions to skill source code.

        Args:
            target_skill: Name of the skill to enrich
            source_code: Current source code of the target skill
            actions: Enrichment actions to apply
            target_domain: Target domain for adaptation

        Returns:
            EnrichmentResult with enriched skill and metadata
        """
        original_lines = len(source_code.splitlines())
        applied: list[EnrichmentAction] = []
        rejected: list[EnrichmentAction] = []
        enriched = source_code

        for action in actions:
            # Check if actual code content (not comment prefix) already exists
            actual_code = action.content.split("\n", 1)[-1] if "\n" in action.content else action.content
            if actual_code.strip() in enriched:
                rejected.append(action)
                continue

            # Check adaptation level threshold
            if action.adaptation_level == AdaptationLevel.SIGNIFICANT and action.confidence < 0.5:
                rejected.append(action)
                continue

            if action.position == "top":
                enriched = action.content + "\n" + enriched
            else:
                enriched = enriched + "\n" + action.content

            applied.append(action)

        enriched_lines = len(enriched.splitlines())

        # Determine status
        if not applied and not rejected:
            status = EnrichmentStatus.UNCHANGED
        elif applied and not rejected:
            status = EnrichmentStatus.ENRICHED
        elif applied:
            status = EnrichmentStatus.PARTIAL
        else:
            status = EnrichmentStatus.REJECTED

        enrichment_score = (
            len(applied) / len(actions) if actions else 0.0
        )

        sources = tuple(set(a.target_skill for a in applied))

        result = EnrichmentResult(
            target_skill=target_skill,
            source_skills=sources,
            actions_applied=tuple(applied),
            status=status,
            original_lines=original_lines,
            enriched_lines=enriched_lines,
            added_patterns=len(applied),
            rejected_patterns=len(rejected),
            enrichment_score=enrichment_score,
            message=f"Enriched with {len(applied)} patterns from {len(sources)} sources",
        )
        self._history.append(result)
        return result

    def get_report(self) -> EnrichmentReport:
        """Generate an enrichment report.

        Returns:
            EnrichmentReport with aggregate statistics
        """
        total = len(self._history)
        successful = sum(1 for r in self._history if r.status == EnrichmentStatus.ENRICHED)
        rejected = sum(1 for r in self._history if r.status == EnrichmentStatus.REJECTED)
        partial = sum(1 for r in self._history if r.status == EnrichmentStatus.PARTIAL)
        avg_patterns = (
            sum(r.added_patterns for r in self._history) / total
            if total > 0 else 0.0
        )

        # Count top pattern types
        type_counts: dict[str, int] = {}
        for r in self._history:
            for action in r.actions_applied:
                type_counts[action.action_type] = type_counts.get(action.action_type, 0) + 1

        top_types = tuple(
            sorted(type_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        )

        return EnrichmentReport(
            total_enrichments=total,
            successful=successful,
            rejected=rejected,
            partial=partial,
            avg_patterns_added=avg_patterns,
            top_added_pattern_types=top_types,
            timestamp="",
        )

    def _determine_adaptation(
        self, source_skill: str, target_domain: str
    ) -> AdaptationLevel:
        """Determine how much adaptation is needed for a pattern."""
        # Simple heuristic: domain similarity
        if source_skill == target_domain:
            return AdaptationLevel.NONE
        if any(kw in source_skill.lower() for kw in target_domain.lower().split()):
            return AdaptationLevel.MINIMAL
        if len(source_skill) > 0 and len(target_domain) > 0:
            return AdaptationLevel.MODERATE
        return AdaptationLevel.SIGNIFICANT

    def clear(self) -> None:
        """Clear enrichment history."""
        self._history.clear()
