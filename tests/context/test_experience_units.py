"""Tests for src/lyra/context/experience_units.py — 85%+ coverage target."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from lyra.context.experience_units import (
    ExperienceUnitType,
    Scheduler,
    TypedExperienceUnit,
    UnitLibrary,
    UnitScoring,
    library_get_scoring,
    library_load_from_json,
    library_prune_by_usage_threshold,
    library_save_to_json,
)


# =========================================================================
# TypedExperienceUnit
# =========================================================================


class TestTypedExperienceUnit:
    def test_defaults(self):
        unit = TypedExperienceUnit(unit_id="u1", unit_type=ExperienceUnitType.MEMORY, content="hello")
        assert unit.source == "manual"
        assert unit.task_type == "general"
        assert unit.score == 0.0
        assert unit.use_count == 0
        assert isinstance(unit.created_at, datetime)
        assert isinstance(unit.last_used_at, datetime)

    def test_record_use_ema(self):
        unit = TypedExperienceUnit(
            unit_id="u1",
            unit_type=ExperienceUnitType.MEMORY,
            content="test",
            score=0.5,
            use_count=3,
        )
        # Verify EMA: new = (1-0.3)*0.5 + 0.3*0.8 = 0.35 + 0.24 = 0.59
        new_score = unit.record_use(feedback=0.8)
        assert unit.score == pytest.approx(0.59, abs=1e-3)
        assert unit.use_count == 4
        assert new_score is None  # record_use returns None

    def test_record_use_zero_feedback(self):
        unit = TypedExperienceUnit(
            unit_id="u1", unit_type=ExperienceUnitType.SKILL, content="x", score=1.0
        )
        unit.record_use(feedback=0.0)
        # (1-0.3)*1.0 + 0.3*0.0 = 0.7
        assert unit.score == pytest.approx(0.7)
        assert unit.use_count == 1

    def test_is_stale_all_conditions_met(self):
        unit = TypedExperienceUnit(
            unit_id="u1",
            unit_type=ExperienceUnitType.STRATEGY,
            content="x",
            score=0.05,
            use_count=0,
            last_used_at=datetime.now(timezone.utc) - timedelta(days=60),
        )
        assert unit.is_stale(max_age_days=30, min_uses=1, score_threshold=0.1) is True

    def test_is_stale_not_old_enough(self):
        unit = TypedExperienceUnit(
            unit_id="u1",
            unit_type=ExperienceUnitType.WORKFLOW,
            content="x",
            score=0.05,
            use_count=0,
            last_used_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        assert unit.is_stale(max_age_days=30, min_uses=1, score_threshold=0.1) is False

    def test_is_stale_used_enough(self):
        unit = TypedExperienceUnit(
            unit_id="u1",
            unit_type=ExperienceUnitType.MEMORY,
            content="x",
            score=0.05,
            use_count=5,
            last_used_at=datetime.now(timezone.utc) - timedelta(days=60),
        )
        assert unit.is_stale(max_age_days=30, min_uses=3, score_threshold=0.1) is False

    def test_is_stale_score_high_enough(self):
        unit = TypedExperienceUnit(
            unit_id="u1",
            unit_type=ExperienceUnitType.MEMORY,
            content="x",
            score=0.5,
            use_count=0,
            last_used_at=datetime.now(timezone.utc) - timedelta(days=60),
        )
        assert unit.is_stale(max_age_days=30, min_uses=1, score_threshold=0.1) is False

    def test_to_dict(self):
        created = datetime(2025, 1, 1, tzinfo=timezone.utc)
        used = datetime(2025, 6, 1, tzinfo=timezone.utc)
        unit = TypedExperienceUnit(
            unit_id="u1",
            unit_type=ExperienceUnitType.MEMORY,
            content="some content",
            source="compaction",
            task_type="debug",
            score=0.75,
            created_at=created,
            last_used_at=used,
            use_count=4,
        )
        d = unit.to_dict()
        assert d["unit_id"] == "u1"
        assert d["unit_type"] == "memory"
        assert d["content"] == "some content"
        assert d["source"] == "compaction"
        assert d["task_type"] == "debug"
        assert d["score"] == 0.75
        assert d["created_at"] == "2025-01-01T00:00:00+00:00"
        assert d["last_used_at"] == "2025-06-01T00:00:00+00:00"
        assert d["use_count"] == 4


# =========================================================================
# UnitLibrary
# =========================================================================


class TestUnitLibrary:
    def test_empty_library(self):
        lib = UnitLibrary()
        assert lib.total_units == 0
        assert lib.stats()["total_units"] == 0

    def test_add_and_get(self):
        lib = UnitLibrary()
        unit = TypedExperienceUnit(
            unit_id="u1", unit_type=ExperienceUnitType.MEMORY, content="data"
        )
        lib.add(unit)
        assert lib.total_units == 1
        assert lib.get("u1") is unit
        assert lib.get("nonexistent") is None

    def test_add_replaces_existing(self):
        lib = UnitLibrary()
        u1 = TypedExperienceUnit(
            unit_id="u1", unit_type=ExperienceUnitType.MEMORY, content="old"
        )
        u2 = TypedExperienceUnit(
            unit_id="u1", unit_type=ExperienceUnitType.STRATEGY, content="new"
        )
        lib.add(u1)
        lib.add(u2)
        assert lib.total_units == 1
        assert lib.get("u1").content == "new"
        # MEMORY type should no longer have u1
        assert len(lib.find_by_type(ExperienceUnitType.MEMORY)) == 0
        assert len(lib.find_by_type(ExperienceUnitType.STRATEGY)) == 1

    def test_find_by_task(self):
        lib = UnitLibrary()
        u1 = TypedExperienceUnit(
            unit_id="u1", unit_type=ExperienceUnitType.MEMORY, content="a",
            task_type="search", score=0.5,
        )
        u2 = TypedExperienceUnit(
            unit_id="u2", unit_type=ExperienceUnitType.MEMORY, content="b",
            task_type="search", score=0.9,
        )
        u3 = TypedExperienceUnit(
            unit_id="u3", unit_type=ExperienceUnitType.MEMORY, content="c",
            task_type="debug", score=0.7,
        )
        lib.add(u1)
        lib.add(u2)
        lib.add(u3)
        results = lib.find_by_task("search")
        assert len(results) == 2
        assert results[0].unit_id == "u2"  # highest score first
        assert results[1].unit_id == "u1"

    def test_find_by_task_empty(self):
        lib = UnitLibrary()
        assert lib.find_by_task("nonexistent") == []

    def test_find_by_type(self):
        lib = UnitLibrary()
        u1 = TypedExperienceUnit(
            unit_id="u1", unit_type=ExperienceUnitType.SKILL, content="a", score=0.3,
        )
        u2 = TypedExperienceUnit(
            unit_id="u2", unit_type=ExperienceUnitType.SKILL, content="b", score=0.8,
        )
        u3 = TypedExperienceUnit(
            unit_id="u3", unit_type=ExperienceUnitType.MEMORY, content="c",
        )
        lib.add(u1)
        lib.add(u2)
        lib.add(u3)
        results = lib.find_by_type(ExperienceUnitType.SKILL)
        assert len(results) == 2
        assert results[0].unit_id == "u2"

    def test_find_by_type_empty(self):
        lib = UnitLibrary()
        assert lib.find_by_type(ExperienceUnitType.WORKFLOW) == []

    def test_score_unit_found(self):
        lib = UnitLibrary()
        unit = TypedExperienceUnit(
            unit_id="u1", unit_type=ExperienceUnitType.MEMORY, content="x", score=0.5,
        )
        lib.add(unit)
        new_score = lib.score_unit("u1", feedback=0.9)
        assert new_score is not None
        assert new_score == pytest.approx(0.62, abs=1e-3)

    def test_score_unit_not_found(self):
        lib = UnitLibrary()
        assert lib.score_unit("nonexistent") is None

    def test_prune_stale_removes_some(self):
        lib = UnitLibrary()
        fresh = TypedExperienceUnit(
            unit_id="fresh", unit_type=ExperienceUnitType.MEMORY, content="x",
            use_count=10, score=0.9,
            last_used_at=datetime.now(timezone.utc),
        )
        stale = TypedExperienceUnit(
            unit_id="stale", unit_type=ExperienceUnitType.STRATEGY, content="y",
            use_count=0, score=0.05,
            last_used_at=datetime.now(timezone.utc) - timedelta(days=60),
        )
        lib.add(fresh)
        lib.add(stale)
        assert lib.prune_stale(max_age_days=30, min_uses=1, score_threshold=0.1) == 1
        assert lib.get("fresh") is not None
        assert lib.get("stale") is None

    def test_prune_stale_nothing_to_remove(self):
        lib = UnitLibrary()
        unit = TypedExperienceUnit(
            unit_id="u1", unit_type=ExperienceUnitType.MEMORY, content="x",
            use_count=5, score=0.8,
        )
        lib.add(unit)
        assert lib.prune_stale() == 0

    def test_stats(self):
        lib = UnitLibrary()
        u1 = TypedExperienceUnit(
            unit_id="u1", unit_type=ExperienceUnitType.MEMORY, content="a", score=0.5,
        )
        u2 = TypedExperienceUnit(
            unit_id="u2", unit_type=ExperienceUnitType.MEMORY, content="b", score=0.7,
        )
        u3 = TypedExperienceUnit(
            unit_id="u3", unit_type=ExperienceUnitType.STRATEGY, content="c", score=0.9,
        )
        lib.add(u1)
        lib.add(u2)
        lib.add(u3)
        stats = lib.stats()
        assert stats["total_units"] == 3
        assert stats["per_type"]["memory"]["count"] == 2
        assert stats["per_type"]["memory"]["avg_score"] == pytest.approx(0.6)
        assert stats["per_type"]["strategy"]["count"] == 1
        assert stats["per_type"]["strategy"]["avg_score"] == pytest.approx(0.9)
        assert stats["per_type"]["workflow"]["count"] == 0
        assert stats["per_type"]["workflow"]["avg_score"] == 0.0


# =========================================================================
# Scheduler
# =========================================================================


class TestScheduler:
    def test_allocate_budget_empty_library(self):
        lib = UnitLibrary()
        scheduler = Scheduler()
        budget = scheduler.allocate_budget(library=lib)
        # All types are empty, so each gets BASE + 0.25 = 0.4, normalized to 0.25
        assert sum(budget.values()) == pytest.approx(1.0)
        assert all(v == 0.25 for v in budget.values())

    def test_allocate_budget_with_varied_scores(self):
        lib = UnitLibrary()
        # MEMORY has avg score 0.8 (needs 0.2)
        lib.add(TypedExperienceUnit(
            unit_id="m1", unit_type=ExperienceUnitType.MEMORY, content="x", score=0.8,
        ))
        # STRATEGY has avg score 0.3 (needs 0.7)
        lib.add(TypedExperienceUnit(
            unit_id="s1", unit_type=ExperienceUnitType.STRATEGY, content="x", score=0.3,
        ))
        scheduler = Scheduler()
        budget = scheduler.allocate_budget(library=lib)
        assert sum(budget.values()) == pytest.approx(1.0, abs=0.01)
        # STRATEGY should get a larger slice than MEMORY
        assert budget["strategy"] > budget["memory"]
        # WORKFLOW and SKILL are empty — get base+0.25 = 0.4 raw
        assert budget["workflow"] > 0
        assert budget["skill"] > 0

    def test_allocate_budget_all_high_scores(self):
        lib = UnitLibrary()
        for t in ExperienceUnitType:
            lib.add(TypedExperienceUnit(
                unit_id=f"{t.value}-1", unit_type=t, content="x", score=1.0,
            ))
        scheduler = Scheduler()
        budget = scheduler.allocate_budget(library=lib)
        assert sum(budget.values()) == pytest.approx(1.0)
        # Each needs 0.0 raw, clamped to min 0.05
        for v in budget.values():
            assert v >= 0.05

    def test_allocate_budget_normalizes_correctly(self):
        """Ensure rounding fix is tested."""
        lib = UnitLibrary()
        # Only one type — straight to 1.0
        lib.add(TypedExperienceUnit(
            unit_id="x", unit_type=ExperienceUnitType.MEMORY, content="x", score=0.0,
        ))
        scheduler = Scheduler()
        budget = scheduler.allocate_budget(library=lib)
        # MEMORY needs 1.0, others get BASE+0.25=0.4 each ... normalized
        assert sum(budget.values()) == pytest.approx(1.0)


# =========================================================================
# UnitScoring
# =========================================================================


class TestUnitScoring:
    def test_defaults(self):
        sc = UnitScoring(unit_type=ExperienceUnitType.MEMORY)
        assert sc.successes == 0
        assert sc.failures == 0
        assert sc.total_score == 0.0
        assert sc.total_attempts == 0
        assert sc.success_rate == 0.0
        assert sc.avg_score == 0.0

    def test_record_use_success(self):
        sc = UnitScoring(unit_type=ExperienceUnitType.SKILL)
        sc.record_use(feedback=0.8, threshold=0.6)
        assert sc.successes == 1
        assert sc.failures == 0
        assert sc.total_score == 0.8
        assert sc.success_rate == 1.0
        assert sc.avg_score == 0.8

    def test_record_use_failure(self):
        sc = UnitScoring(unit_type=ExperienceUnitType.STRATEGY)
        sc.record_use(feedback=0.3, threshold=0.6)
        assert sc.successes == 0
        assert sc.failures == 1
        assert sc.success_rate == 0.0

    def test_record_use_threshold_boundary(self):
        sc = UnitScoring(unit_type=ExperienceUnitType.WORKFLOW)
        sc.record_use(feedback=0.6, threshold=0.6)  # exactly at threshold -> success
        assert sc.successes == 1
        sc.record_use(feedback=0.599, threshold=0.6)  # below -> failure
        assert sc.failures == 1

    def test_to_dict(self):
        sc = UnitScoring(
            unit_type=ExperienceUnitType.MEMORY,
            successes=3,
            failures=1,
            total_score=2.5,
        )
        d = sc.to_dict()
        assert d["unit_type"] == "memory"
        assert d["successes"] == 3
        assert d["failures"] == 1
        assert d["total_score"] == 2.5
        assert d["success_rate"] == 0.75
        assert d["avg_score"] == 0.625


# =========================================================================
# Module-level persistence helpers
# =========================================================================


class TestLibrarySaveLoadJson:
    def test_save_and_load(self, tmp_path):
        lib = UnitLibrary()
        lib.add(TypedExperienceUnit(
            unit_id="u1", unit_type=ExperienceUnitType.MEMORY, content="hello",
        ))
        lib.add(TypedExperienceUnit(
            unit_id="u2", unit_type=ExperienceUnitType.SKILL, content="world",
        ))

        path = str(tmp_path / "units.json")
        library_save_to_json(library=lib, path=path)

        loaded = UnitLibrary()
        count = library_load_from_json(library=loaded, path=path)
        assert count == 2
        assert loaded.get("u1") is not None
        assert loaded.get("u1").content == "hello"
        assert loaded.get("u2").unit_type == ExperienceUnitType.SKILL

    def test_load_nonexistent_file(self, tmp_path):
        lib = UnitLibrary()
        count = library_load_from_json(library=lib, path=str(tmp_path / "nope.json"))
        assert count == 0

    def test_load_invalid_json(self, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text("not json")
        lib = UnitLibrary()
        with pytest.raises(json.JSONDecodeError):
            library_load_from_json(library=lib, path=str(p))

    def test_load_non_list_json(self, tmp_path):
        p = tmp_path / "obj.json"
        p.write_text('{"a": 1}')
        lib = UnitLibrary()
        assert library_load_from_json(library=lib, path=str(p)) == 0

    def test_load_malformed_entries(self, tmp_path):
        """Entries missing required keys should be skipped."""
        p = tmp_path / "bad_entries.json"
        p.write_text(json.dumps([
            {"unit_id": "good", "unit_type": "memory", "content": "ok",
             "created_at": "2025-01-01T00:00:00+00:00",
             "last_used_at": "2025-01-01T00:00:00+00:00"},
            {"unit_id": "bad", "content": "missing type and timestamps"},
        ]))
        lib = UnitLibrary()
        count = library_load_from_json(library=lib, path=str(p))
        assert count == 1
        assert lib.get("good") is not None

    def test_save_creates_parent_dirs(self, tmp_path):
        lib = UnitLibrary()
        lib.add(TypedExperienceUnit(
            unit_id="u1", unit_type=ExperienceUnitType.MEMORY, content="x",
        ))
        path = str(tmp_path / "sub" / "deep" / "units.json")
        library_save_to_json(library=lib, path=path)
        assert Path(path).exists()

    def test_save_and_load_replaces_existing(self, tmp_path):
        lib = UnitLibrary()
        lib.add(TypedExperienceUnit(
            unit_id="u1", unit_type=ExperienceUnitType.MEMORY, content="original",
        ))
        path = str(tmp_path / "replace.json")
        library_save_to_json(library=lib, path=path)

        lib2 = UnitLibrary()
        lib2.add(TypedExperienceUnit(
            unit_id="u1", unit_type=ExperienceUnitType.MEMORY, content="replaced",
        ))
        library_save_to_json(library=lib2, path=path)

        loaded = UnitLibrary()
        library_load_from_json(library=loaded, path=path)
        assert loaded.get("u1").content == "replaced"


class TestLibraryPruneByUsageThreshold:
    def test_prune_below_threshold(self):
        lib = UnitLibrary()
        lib.add(TypedExperienceUnit(
            unit_id="used", unit_type=ExperienceUnitType.MEMORY, content="x",
            use_count=5,
        ))
        lib.add(TypedExperienceUnit(
            unit_id="unused", unit_type=ExperienceUnitType.STRATEGY, content="y",
            use_count=0,
        ))
        lib.add(TypedExperienceUnit(
            unit_id="low", unit_type=ExperienceUnitType.SKILL, content="z",
            use_count=1,
        ))
        pruned = library_prune_by_usage_threshold(library=lib, min_use_count=2)
        assert pruned == 2
        assert lib.get("used") is not None
        assert lib.get("unused") is None
        assert lib.get("low") is None

    def test_prune_by_task_type(self):
        lib = UnitLibrary()
        lib.add(TypedExperienceUnit(
            unit_id="search1", unit_type=ExperienceUnitType.MEMORY, content="x",
            task_type="search", use_count=0,
        ))
        lib.add(TypedExperienceUnit(
            unit_id="debug1", unit_type=ExperienceUnitType.MEMORY, content="y",
            task_type="debug", use_count=0,
        ))
        pruned = library_prune_by_usage_threshold(
            library=lib, min_use_count=1, task_type="search",
        )
        assert pruned == 1
        assert lib.get("search1") is None
        assert lib.get("debug1") is not None

    def test_prune_no_units_matching(self):
        lib = UnitLibrary()
        lib.add(TypedExperienceUnit(
            unit_id="u1", unit_type=ExperienceUnitType.MEMORY, content="x",
            use_count=10,
        ))
        pruned = library_prune_by_usage_threshold(library=lib, min_use_count=5)
        assert pruned == 0

    def test_prune_empty_library(self):
        lib = UnitLibrary()
        assert library_prune_by_usage_threshold(library=lib) == 0


class TestLibraryGetScoring:
    def test_empty_library(self):
        lib = UnitLibrary()
        scores = library_get_scoring(library=lib)
        assert len(scores) == 4
        for sc in scores.values():
            assert sc.total_attempts == 0

    def test_with_units(self):
        lib = UnitLibrary()
        lib.add(TypedExperienceUnit(
            unit_id="m1", unit_type=ExperienceUnitType.MEMORY, content="x",
            score=0.8, use_count=3,
        ))
        lib.add(TypedExperienceUnit(
            unit_id="m2", unit_type=ExperienceUnitType.MEMORY, content="y",
            score=0.4, use_count=1,
        ))
        lib.add(TypedExperienceUnit(
            unit_id="s1", unit_type=ExperienceUnitType.STRATEGY, content="z",
            score=0.9, use_count=5,
        ))
        scores = library_get_scoring(library=lib)
        # MEMORY: m1 -> total_score += 0.8, record_use(0.8/3=0.267) -> total_score += 0.267 => 1.067
        #         m2 -> total_score += 0.4, record_use(0.4/1=0.4) -> total_score += 0.4 => 1.867
        assert scores["memory"].total_score == pytest.approx(1.867, abs=0.001)
        # STRATEGY: s1 -> total_score += 0.9, record_use(0.9/5=0.18) -> total_score += 0.18 => 1.08
        assert scores["strategy"].total_score == pytest.approx(1.08, abs=0.001)
        assert scores["workflow"].total_score == 0.0
        assert scores["skill"].total_score == 0.0

    def test_unit_with_zero_use_count(self):
        """Units with use_count=0 should not trigger record_use."""
        lib = UnitLibrary()
        lib.add(TypedExperienceUnit(
            unit_id="u1", unit_type=ExperienceUnitType.MEMORY, content="x",
            score=0.5, use_count=0,
        ))
        scores = library_get_scoring(library=lib)
        # total_score added, but record_use only called if use_count > 0
        assert scores["memory"].total_score == 0.5
        assert scores["memory"].total_attempts == 0
