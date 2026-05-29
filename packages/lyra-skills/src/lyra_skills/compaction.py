"""Plan 7 Part 1.6: Skills Auto-Compaction.

Tracks per-section usage, trims unreferenced sections, merges related skills,
archives stale skills (90+ days unused), and computes compression ratios.
"""

from __future__ import annotations

import time
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import Enum

# ── Constants ──────────────────────────────────────────────────────────────

STALE_THRESHOLD_DAYS = 90
MIN_USES_TO_KEEP = 3
MERGE_SIMILARITY_THRESHOLD = 0.6
COMPRESSION_TARGET = 0.60  # 60% context reduction target


class SectionStatus(Enum):
    ACTIVE = "active"
    UNREFERENCED = "unreferenced"
    TRIMMED = "trimmed"
    ARCHIVED = "archived"


class CompactionAction(Enum):
    KEEP = "keep"
    TRIM = "trim"
    MERGE = "merge"
    ARCHIVE = "archive"
    DELETE = "delete"


# ── Data Models ───────────────────────────────────────────────────────────


@dataclass(frozen=True)
class SectionUsage:
    """Usage record for a single section within a skill.

    Attributes:
        section_id: Identifier for the section (e.g. 'examples', 'patterns').
        reference_count: How many times this section was referenced.
        last_referenced_at: Timestamp of last reference.
        char_count: Size of this section in characters.
    """

    section_id: str
    reference_count: int = 0
    last_referenced_at: float = 0.0
    char_count: int = 0


@dataclass(frozen=True)
class SkillUsageProfile:
    """Aggregated usage data for a single skill.

    Attributes:
        skill_id: The skill's identifier.
        total_invocations: Total number of times the skill was activated.
        last_used_at: When the skill was last used.
        first_used_at: When the skill was first used.
        sections: Per-section usage records.
        total_chars: Total character count of the full skill body.
        active_chars: Character count of actively referenced sections.
    """

    skill_id: str
    total_invocations: int = 0
    last_used_at: float = 0.0
    first_used_at: float = 0.0
    sections: tuple[SectionUsage, ...] = ()
    total_chars: int = 0
    active_chars: int = 0

    @property
    def compression_ratio(self) -> float:
        if self.total_chars == 0:
            return 0.0
        return 1.0 - (self.active_chars / self.total_chars)

    @property
    def days_since_last_use(self) -> float:
        if self.last_used_at == 0:
            return float("inf")
        return (time.time() - self.last_used_at) / 86400.0

    @property
    def is_stale(self) -> bool:
        return self.days_since_last_use > STALE_THRESHOLD_DAYS

    @property
    def is_cold(self) -> bool:
        return self.total_invocations < MIN_USES_TO_KEEP and self.days_since_last_use > 30


@dataclass(frozen=True)
class SectionTrimResult:
    """Result of trimming unreferenced sections from a skill.

    Attributes:
        skill_id: The skill that was trimmed.
        trimmed_sections: IDs of sections that were removed.
        chars_before: Character count before trimming.
        chars_after: Character count after trimming.
        compression_pct: Percentage reduction achieved.
    """

    skill_id: str
    trimmed_sections: tuple[str, ...]
    chars_before: int
    chars_after: int
    compression_pct: float = 0.0


@dataclass(frozen=True)
class MergeCandidate:
    """Two skills that could be merged into a composite pack.

    Attributes:
        skill_a: First skill ID.
        skill_b: Second skill ID.
        similarity: Overlap score 0-1.
        shared_tags: Tags common to both skills.
        suggested_name: Proposed name for the merged pack.
    """

    skill_a: str
    skill_b: str
    similarity: float = 0.0
    shared_tags: tuple[str, ...] = ()
    suggested_name: str = ""


@dataclass(frozen=True)
class CompactionPlan:
    """A plan of compaction actions to execute.

    Attributes:
        trims: Skills to trim unreferenced sections from.
        merges: Skill pairs to merge.
        archives: Skills to archive.
        deletes: Skills to delete entirely.
        estimated_savings_chars: Total characters that would be saved.
    """

    trims: tuple[SectionTrimResult, ...] = ()
    merges: tuple[MergeCandidate, ...] = ()
    archives: tuple[str, ...] = ()
    deletes: tuple[str, ...] = ()
    estimated_savings_chars: int = 0


@dataclass(frozen=True)
class CompactionReport:
    """Summary report after executing a compaction plan.

    Attributes:
        skills_trimmed: Number of skills that had sections trimmed.
        skills_merged: Number of merge operations performed.
        skills_archived: Number of skills archived.
        skills_deleted: Number of skills deleted.
        total_chars_saved: Total characters saved.
        compression_ratio: 0-1 fraction of context saved.
        timestamp: When the compaction was performed.
    """

    skills_trimmed: int = 0
    skills_merged: int = 0
    skills_archived: int = 0
    skills_deleted: int = 0
    total_chars_saved: int = 0
    compression_ratio: float = 0.0
    timestamp: float = field(default_factory=time.time)


# ── Section Usage Tracker ──────────────────────────────────────────────────


class SectionUsageTracker:
    """Tracks per-section reference counts for skills.

    Usage::

        tracker = SectionUsageTracker()
        tracker.record_reference("tdd-discipline", "examples")
        tracker.record_reference("tdd-discipline", "patterns")
        profile = tracker.get_profile("tdd-discipline")
    """

    def __init__(self) -> None:
        self._sections: dict[str, dict[str, SectionUsage]] = defaultdict(dict)
        self._skill_meta: dict[str, tuple[int, float, float]] = {}  # (invocations, last_used, first_used)

    def record_reference(self, skill_id: str, section_id: str, char_count: int = 0) -> None:
        """Record a reference to a specific section of a skill."""
        now = time.time()
        entry = self._sections[skill_id].get(section_id)

        if entry is None:
            entry = SectionUsage(
                section_id=section_id,
                reference_count=1,
                last_referenced_at=now,
                char_count=char_count,
            )
        else:
            entry = SectionUsage(
                section_id=section_id,
                reference_count=entry.reference_count + 1,
                last_referenced_at=now,
                char_count=max(entry.char_count, char_count),
            )

        self._sections[skill_id][section_id] = entry

        if skill_id in self._skill_meta:
            inv, _, first = self._skill_meta[skill_id]
            self._skill_meta[skill_id] = (inv + 1, now, first)
        else:
            self._skill_meta[skill_id] = (1, now, now)

    def record_invocation(self, skill_id: str) -> None:
        """Record a skill activation without section-level tracking."""
        now = time.time()
        if skill_id in self._skill_meta:
            inv, _, first = self._skill_meta[skill_id]
            self._skill_meta[skill_id] = (inv + 1, now, first)
        else:
            self._skill_meta[skill_id] = (1, now, now)

    def get_profile(self, skill_id: str, total_chars: int = 0) -> SkillUsageProfile | None:
        """Build a usage profile for a skill."""
        meta = self._skill_meta.get(skill_id)
        if meta is None:
            return None

        sections = tuple(self._sections[skill_id].values())
        active_chars = sum(s.char_count for s in sections if s.reference_count > 0)

        return SkillUsageProfile(
            skill_id=skill_id,
            total_invocations=meta[0],
            last_used_at=meta[1],
            first_used_at=meta[2],
            sections=sections,
            total_chars=total_chars,
            active_chars=active_chars,
        )

    def get_unreferenced_sections(self, skill_id: str) -> tuple[str, ...]:
        """Return section IDs with zero references."""
        sections = self._sections.get(skill_id, {})
        return tuple(sid for sid, s in sections.items() if s.reference_count == 0)

    def get_all_profiles(self, skill_total_chars: dict[str, int] | None = None) -> tuple[SkillUsageProfile, ...]:
        """Build usage profiles for all tracked skills."""
        char_map = skill_total_chars or {}
        profiles: list[SkillUsageProfile] = []
        for skill_id in self._skill_meta:
            profile = self.get_profile(skill_id, total_chars=char_map.get(skill_id, 0))
            if profile is not None:
                profiles.append(profile)
        return tuple(profiles)

    def remove_skill(self, skill_id: str) -> bool:
        """Remove all tracking data for a skill."""
        removed = False
        if skill_id in self._sections:
            del self._sections[skill_id]
            removed = True
        if skill_id in self._skill_meta:
            del self._skill_meta[skill_id]
            removed = True
        return removed

    @property
    def tracked_skill_count(self) -> int:
        return len(self._skill_meta)

    @property
    def tracked_skill_ids(self) -> tuple[str, ...]:
        return tuple(self._skill_meta.keys())

    def get_sections(self, skill_id: str) -> tuple[SectionUsage, ...]:
        return tuple(self._sections.get(skill_id, {}).values())


# ── Compactor ─────────────────────────────────────────────────────────────


class SkillCompactor:
    """Analyzes skill usage and generates compaction plans.

    Consumes data from SectionUsageTracker and/or SkillLedger to identify
    sections to trim, skills to merge, and stale skills to archive.
    """

    def __init__(
        self,
        tracker: SectionUsageTracker | None = None,
        stale_threshold_days: int = STALE_THRESHOLD_DAYS,
        min_uses_to_keep: int = MIN_USES_TO_KEEP,
        merge_similarity: float = MERGE_SIMILARITY_THRESHOLD,
        compression_target: float = COMPRESSION_TARGET,
    ) -> None:
        self._tracker = tracker or SectionUsageTracker()
        self._stale_threshold = stale_threshold_days
        self._min_uses = min_uses_to_keep
        self._merge_similarity = merge_similarity
        self._compression_target = compression_target
        self._skill_tags: dict[str, frozenset[str]] = {}

    def register_skill_tags(self, skill_id: str, tags: Iterable[str]) -> None:
        """Register tags for a skill (used for merge similarity)."""
        self._skill_tags[skill_id] = frozenset(tags)

    # ── Trim ──────────────────────────────────────────────────────────────

    def find_trims(self, skill_total_chars: dict[str, int] | None = None) -> tuple[SectionTrimResult, ...]:
        """Find all skills with unreferenced sections that can be trimmed."""
        results: list[SectionTrimResult] = []
        char_map = skill_total_chars or {}

        for skill_id in self._tracker.tracked_skill_ids:
            unreferenced = self._tracker.get_unreferenced_sections(skill_id)
            if not unreferenced:
                continue

            profile = self._tracker.get_profile(skill_id, total_chars=char_map.get(skill_id, 0))
            if profile is None:
                continue

            trimmed_chars = sum(
                s.char_count for s in profile.sections
                if s.section_id in unreferenced
            )
            chars_before = profile.total_chars
            chars_after = chars_before - trimmed_chars

            results.append(SectionTrimResult(
                skill_id=skill_id,
                trimmed_sections=unreferenced,
                chars_before=chars_before,
                chars_after=chars_after,
                compression_pct=(trimmed_chars / chars_before * 100) if chars_before > 0 else 0.0,
            ))

        return tuple(results)

    # ── Merge ──────────────────────────────────────────────────────────────

    def find_merges(self) -> tuple[MergeCandidate, ...]:
        """Find skill pairs with high tag overlap that could be merged."""
        candidates: list[MergeCandidate] = []
        skill_ids = list(self._skill_tags.keys())

        for i in range(len(skill_ids)):
            for j in range(i + 1, len(skill_ids)):
                a, b = skill_ids[i], skill_ids[j]
                tags_a = self._skill_tags.get(a, frozenset())
                tags_b = self._skill_tags.get(b, frozenset())

                if not tags_a or not tags_b:
                    continue

                union = tags_a | tags_b
                intersection = tags_a & tags_b

                if not union:
                    continue

                similarity = len(intersection) / len(union)

                if similarity >= self._merge_similarity:
                    shared = tuple(sorted(intersection))
                    candidates.append(MergeCandidate(
                        skill_a=a,
                        skill_b=b,
                        similarity=round(similarity, 3),
                        shared_tags=shared,
                        suggested_name=f"{a}+{b}",
                    ))

        candidates.sort(key=lambda c: c.similarity, reverse=True)
        return tuple(candidates)

    # ── Archive ────────────────────────────────────────────────────────────

    def find_archival_candidates(self) -> tuple[str, ...]:
        """Find stale skills (unused for 90+ days) for archival."""
        stale: list[str] = []

        for skill_id in self._tracker.tracked_skill_ids:
            profile = self._tracker.get_profile(skill_id)
            if profile is not None and profile.days_since_last_use > self._stale_threshold:
                stale.append(skill_id)

        return tuple(stale)

    def find_delete_candidates(self) -> tuple[str, ...]:
        """Find cold skills (rarely used, stale) for potential deletion."""
        cold: list[str] = []

        for skill_id in self._tracker.tracked_skill_ids:
            profile = self._tracker.get_profile(skill_id)
            if profile is not None and profile.is_cold:
                cold.append(skill_id)

        return tuple(cold)

    # ── Plan ───────────────────────────────────────────────────────────────

    def build_plan(self, skill_total_chars: dict[str, int] | None = None) -> CompactionPlan:
        """Build a comprehensive compaction plan."""
        trims = self.find_trims(skill_total_chars)
        merges = self.find_merges()
        archives = self.find_archival_candidates()
        deletes = self.find_delete_candidates()

        total_saved = sum(t.chars_before - t.chars_after for t in trims)

        return CompactionPlan(
            trims=trims,
            merges=merges,
            archives=archives,
            deletes=deletes,
            estimated_savings_chars=total_saved,
        )

    def execute(self, plan: CompactionPlan | None = None) -> CompactionReport:
        """Execute a compaction plan and return a report.

        In practice this updates the tracker state; actual file removal is
        delegated to the skill installer/loader.
        """
        if plan is None:
            plan = self.build_plan()

        for trim in plan.trims:
            for section_id in trim.trimmed_sections:
                if section_id in self._tracker._sections.get(trim.skill_id, {}):
                    self._tracker._sections[trim.skill_id][section_id] = SectionUsage(
                        section_id=section_id,
                        reference_count=0,
                        last_referenced_at=0.0,
                        char_count=0,
                    )

        for archive_id in plan.archives:
            self._skill_tags.pop(archive_id, None)

        for delete_id in plan.deletes:
            self._tracker.remove_skill(delete_id)
            self._skill_tags.pop(delete_id, None)

        # Merge updates — combine tags for merged pairs, remove originals
        for merge in plan.merges:
            combined = self._skill_tags.get(merge.skill_a, frozenset()) | self._skill_tags.get(merge.skill_b, frozenset())
            self._skill_tags[merge.suggested_name] = combined
            self._skill_tags.pop(merge.skill_a, None)
            self._skill_tags.pop(merge.skill_b, None)

        return CompactionReport(
            skills_trimmed=len(plan.trims),
            skills_merged=len(plan.merges),
            skills_archived=len(plan.archives),
            skills_deleted=len(plan.deletes),
            total_chars_saved=plan.estimated_savings_chars,
            compression_ratio=self._compute_overall_ratio(),
        )

    # ── Stats ──────────────────────────────────────────────────────────────

    def stats(self) -> dict:
        """Return compaction statistics."""
        profiles = self._tracker.get_all_profiles()
        total_chars = sum(p.total_chars for p in profiles)
        active_chars = sum(p.active_chars for p in profiles)

        return {
            "tracked_skills": self._tracker.tracked_skill_count,
            "total_chars": total_chars,
            "active_chars": active_chars,
            "compression_ratio": self._compute_overall_ratio(),
            "compression_target": self._compression_target,
            "stale_count": len(self.find_archival_candidates()),
            "cold_count": len(self.find_delete_candidates()),
            "merge_candidates": len(self.find_merges()),
            "trimmable_skills": len(self.find_trims()),
        }

    def _compute_overall_ratio(self) -> float:
        profiles = self._tracker.get_all_profiles()
        total = sum(p.total_chars for p in profiles)
        active = sum(p.active_chars for p in profiles)
        if total == 0:
            return 0.0
        return round(1.0 - (active / total), 3)
