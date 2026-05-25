"""Tests for Plan 7 Part 1.6: Skills Auto-Compaction."""

from __future__ import annotations

import time

import pytest

from lyra_skills.compaction import (
    COMPRESSION_TARGET,
    MERGE_SIMILARITY_THRESHOLD,
    MIN_USES_TO_KEEP,
    STALE_THRESHOLD_DAYS,
    CompactionAction,
    CompactionPlan,
    CompactionReport,
    MergeCandidate,
    SectionStatus,
    SectionTrimResult,
    SectionUsage,
    SectionUsageTracker,
    SkillCompactor,
    SkillUsageProfile,
)


class TestSectionUsage:
    def test_create(self):
        s = SectionUsage(section_id="examples", reference_count=5, last_referenced_at=1000.0, char_count=200)
        assert s.section_id == "examples"
        assert s.reference_count == 5
        assert s.char_count == 200

    def test_defaults(self):
        s = SectionUsage(section_id="patterns")
        assert s.reference_count == 0
        assert s.last_referenced_at == 0.0
        assert s.char_count == 0

    def test_is_frozen(self):
        s = SectionUsage(section_id="examples")
        with pytest.raises(Exception):
            s.reference_count = 10


class TestSkillUsageProfile:
    def test_compression_ratio(self):
        p = SkillUsageProfile(
            skill_id="test-skill",
            total_chars=1000,
            active_chars=300,
        )
        assert p.compression_ratio == pytest.approx(0.7)

    def test_compression_ratio_zero_chars(self):
        p = SkillUsageProfile(skill_id="empty")
        assert p.compression_ratio == 0.0

    def test_days_since_last_use(self):
        recent = time.time() - 86400  # 1 day ago
        p = SkillUsageProfile(skill_id="recent", last_used_at=recent)
        assert 0.9 < p.days_since_last_use < 1.1

    def test_days_since_last_use_never(self):
        p = SkillUsageProfile(skill_id="never")
        assert p.days_since_last_use == float("inf")

    def test_is_stale(self):
        old = time.time() - (STALE_THRESHOLD_DAYS + 10) * 86400
        p = SkillUsageProfile(skill_id="stale", last_used_at=old)
        assert p.is_stale

    def test_is_not_stale(self):
        recent = time.time() - 10 * 86400
        p = SkillUsageProfile(skill_id="recent", last_used_at=recent)
        assert not p.is_stale

    def test_is_cold(self):
        old = time.time() - 60 * 86400
        p = SkillUsageProfile(skill_id="cold", total_invocations=1, last_used_at=old)
        assert p.is_cold

    def test_is_not_cold_if_used_enough(self):
        p = SkillUsageProfile(skill_id="warm", total_invocations=10, last_used_at=time.time())
        assert not p.is_cold

    def test_is_frozen(self):
        p = SkillUsageProfile(skill_id="test")
        with pytest.raises(Exception):
            p.total_invocations = 100


class TestSectionUsageTracker:
    def test_record_reference_new_skill(self):
        t = SectionUsageTracker()
        t.record_reference("skill-a", "examples", char_count=150)
        assert t.tracked_skill_count == 1

    def test_record_reference_multiple_sections(self):
        t = SectionUsageTracker()
        t.record_reference("skill-a", "examples", char_count=100)
        t.record_reference("skill-a", "patterns", char_count=200)
        t.record_reference("skill-a", "examples", char_count=100)  # second ref
        profile = t.get_profile("skill-a", total_chars=500)
        assert profile is not None
        assert profile.total_invocations == 3
        assert len(profile.sections) == 2

    def test_record_invocation(self):
        t = SectionUsageTracker()
        t.record_invocation("skill-b")
        profile = t.get_profile("skill-b")
        assert profile is not None
        assert profile.total_invocations == 1

    def test_get_profile_nonexistent(self):
        t = SectionUsageTracker()
        assert t.get_profile("nonexistent") is None

    def test_get_unreferenced_sections(self):
        t = SectionUsageTracker()
        t.record_reference("skill-a", "hot-section", char_count=100)
        # Add a section with zero refs manually
        t._sections["skill-a"]["cold-section"] = SectionUsage(section_id="cold-section")
        unreferenced = t.get_unreferenced_sections("skill-a")
        assert "cold-section" in unreferenced
        assert "hot-section" not in unreferenced

    def test_get_unreferenced_nonexistent_skill(self):
        t = SectionUsageTracker()
        assert t.get_unreferenced_sections("nonexistent") == ()

    def test_get_all_profiles(self):
        t = SectionUsageTracker()
        t.record_invocation("a")
        t.record_invocation("b")
        profiles = t.get_all_profiles()
        assert len(profiles) == 2

    def test_remove_skill(self):
        t = SectionUsageTracker()
        t.record_invocation("removable")
        assert t.tracked_skill_count == 1
        assert t.remove_skill("removable")
        assert t.tracked_skill_count == 0

    def test_remove_nonexistent(self):
        t = SectionUsageTracker()
        assert not t.remove_skill("nonexistent")

    def test_first_used_timestamp(self):
        t = SectionUsageTracker()
        t.record_invocation("first")
        time.sleep(0.01)
        t.record_invocation("first")
        profile = t.get_profile("first")
        assert profile is not None
        assert profile.first_used_at < profile.last_used_at


class TestSkillCompactor:
    def test_find_trims_empty(self):
        c = SkillCompactor()
        assert c.find_trims() == ()

    def test_find_trims_with_unreferenced(self):
        t = SectionUsageTracker()
        t.record_reference("skill-x", "intro", char_count=50)
        t.record_reference("skill-x", "body", char_count=200)
        t._sections["skill-x"]["unused-appendix"] = SectionUsage(
            section_id="unused-appendix", char_count=100
        )

        c = SkillCompactor(tracker=t)
        trims = c.find_trims({"skill-x": 350})
        assert len(trims) == 1
        assert trims[0].skill_id == "skill-x"
        assert "unused-appendix" in trims[0].trimmed_sections
        assert trims[0].chars_before == 350
        assert trims[0].chars_after == 250

    def test_find_trims_no_unreferenced(self):
        t = SectionUsageTracker()
        t.record_reference("skill-x", "intro", char_count=100)
        c = SkillCompactor(tracker=t)
        assert c.find_trims() == ()

    def test_find_merges_similar_tags(self):
        t = SectionUsageTracker()
        c = SkillCompactor(tracker=t)
        c.register_skill_tags("python-patterns", ["python", "backend", "typing"])
        c.register_skill_tags("python-testing", ["python", "testing", "pytest"])

        merges = c.find_merges()
        # 1 shared out of 5 total = 0.2 < threshold, no merge
        assert len(merges) == 0

    def test_find_merges_high_similarity(self):
        t = SectionUsageTracker()
        c = SkillCompactor(tracker=t)
        c.register_skill_tags("python-patterns", ["python", "backend", "typing", "async"])
        c.register_skill_tags("python-async", ["python", "backend", "async", "await"])

        merges = c.find_merges()
        # 3 shared out of 5 total = 0.6 >= threshold
        assert len(merges) == 1
        assert merges[0].similarity >= MERGE_SIMILARITY_THRESHOLD

    def test_find_merges_no_tags(self):
        t = SectionUsageTracker()
        c = SkillCompactor(tracker=t)
        assert c.find_merges() == ()

    def test_find_archival_candidates(self):
        t = SectionUsageTracker()
        old = time.time() - (STALE_THRESHOLD_DAYS + 10) * 86400
        t.record_invocation("old-skill")
        t._skill_meta["old-skill"] = (1, old, old)

        c = SkillCompactor(tracker=t)
        archives = c.find_archival_candidates()
        assert "old-skill" in archives

    def test_find_archival_no_stale(self):
        t = SectionUsageTracker()
        t.record_invocation("fresh-skill")
        c = SkillCompactor(tracker=t)
        assert c.find_archival_candidates() == ()

    def test_find_delete_candidates(self):
        t = SectionUsageTracker()
        old = time.time() - 60 * 86400
        t.record_invocation("cold-skill")
        t._skill_meta["cold-skill"] = (1, old, old)

        c = SkillCompactor(tracker=t)
        deletes = c.find_delete_candidates()
        assert "cold-skill" in deletes

    def test_find_delete_no_cold(self):
        t = SectionUsageTracker()
        t.record_invocation("warm-skill")
        c = SkillCompactor(tracker=t)
        assert c.find_delete_candidates() == ()

    def test_build_plan(self):
        t = SectionUsageTracker()
        t.record_reference("skill-x", "intro", char_count=50)
        t._sections["skill-x"]["appendix"] = SectionUsage(section_id="appendix", char_count=100)

        c = SkillCompactor(tracker=t)
        c.register_skill_tags("skill-x", ["python", "testing"])
        c.register_skill_tags("skill-y", ["python", "typing"])

        plan = c.build_plan({"skill-x": 150})
        assert isinstance(plan, CompactionPlan)
        assert len(plan.trims) >= 0

    def test_execute_returns_report(self):
        c = SkillCompactor()
        report = c.execute()
        assert isinstance(report, CompactionReport)
        assert report.timestamp > 0

    def test_execute_with_trims(self):
        t = SectionUsageTracker()
        t.record_reference("skill-x", "intro", char_count=50)
        t._sections["skill-x"]["appendix"] = SectionUsage(section_id="appendix", char_count=100)

        c = SkillCompactor(tracker=t)
        plan = c.build_plan({"skill-x": 150})
        report = c.execute(plan)
        assert report.skills_trimmed >= 0

    def test_stats(self):
        t = SectionUsageTracker()
        t.record_reference("s1", "intro", char_count=100)
        c = SkillCompactor(tracker=t)
        stats = c.stats()
        assert "tracked_skills" in stats
        assert "total_chars" in stats
        assert "compression_ratio" in stats

    def test_merge_similarity_custom_threshold(self):
        t = SectionUsageTracker()
        c = SkillCompactor(tracker=t, merge_similarity=0.2)
        c.register_skill_tags("a", ["x", "y"])
        c.register_skill_tags("b", ["x", "z"])
        merges = c.find_merges()
        # 1 shared / 3 total = 0.33 >= 0.2
        assert len(merges) == 1

    def test_custom_stale_threshold(self):
        t = SectionUsageTracker()
        old = time.time() - 30 * 86400  # 30 days ago
        t.record_invocation("oldish")
        t._skill_meta["oldish"] = (1, old, old)

        c = SkillCompactor(tracker=t, stale_threshold_days=20)
        archives = c.find_archival_candidates()
        assert "oldish" in archives

        c2 = SkillCompactor(tracker=t, stale_threshold_days=60)
        archives2 = c2.find_archival_candidates()
        assert "oldish" not in archives2


class TestMergeCandidate:
    def test_create(self):
        m = MergeCandidate(
            skill_a="python-patterns",
            skill_b="python-async",
            similarity=0.75,
            shared_tags=("python", "async"),
            suggested_name="python-core",
        )
        assert m.similarity == 0.75
        assert len(m.shared_tags) == 2

    def test_is_frozen(self):
        m = MergeCandidate(skill_a="a", skill_b="b", similarity=0.5)
        with pytest.raises(Exception):
            m.similarity = 0.9


class TestCompactionPlan:
    def test_default(self):
        p = CompactionPlan()
        assert p.trims == ()
        assert p.merges == ()
        assert p.archives == ()
        assert p.deletes == ()
        assert p.estimated_savings_chars == 0

    def test_with_savings(self):
        p = CompactionPlan(estimated_savings_chars=5000)
        assert p.estimated_savings_chars == 5000

    def test_is_frozen(self):
        p = CompactionPlan()
        with pytest.raises(Exception):
            p.estimated_savings_chars = 100


class TestCompactionReport:
    def test_create(self):
        r = CompactionReport(
            skills_trimmed=3,
            skills_archived=1,
            total_chars_saved=2000,
            compression_ratio=0.4,
        )
        assert r.skills_trimmed == 3
        assert r.total_chars_saved == 2000

    def test_has_timestamp(self):
        r = CompactionReport()
        assert r.timestamp > 0

    def test_is_frozen(self):
        r = CompactionReport()
        with pytest.raises(Exception):
            r.skills_trimmed = 5


class TestEnums:
    def test_section_status_values(self):
        assert SectionStatus.ACTIVE.value == "active"
        assert SectionStatus.UNREFERENCED.value == "unreferenced"
        assert SectionStatus.TRIMMED.value == "trimmed"
        assert SectionStatus.ARCHIVED.value == "archived"

    def test_compaction_action_values(self):
        assert CompactionAction.KEEP.value == "keep"
        assert CompactionAction.TRIM.value == "trim"
        assert CompactionAction.MERGE.value == "merge"
        assert CompactionAction.ARCHIVE.value == "archive"
        assert CompactionAction.DELETE.value == "delete"


class TestConstants:
    def test_stale_threshold(self):
        assert STALE_THRESHOLD_DAYS == 90

    def test_min_uses_to_keep(self):
        assert MIN_USES_TO_KEEP == 3

    def test_merge_similarity(self):
        assert MERGE_SIMILARITY_THRESHOLD == 0.6

    def test_compression_target(self):
        assert COMPRESSION_TARGET == 0.60
