"""L38-2 — SkillTelemetryStore + decayed-rate contract tests."""
from __future__ import annotations

import math
import time
from pathlib import Path

import pytest

from lyra_core.skills.registry import Skill, SkillRegistry
from lyra_core.skills.telemetry import (
    DecayedRate,
    SkillTelemetryStore,
    TelemetryEvent,
)


@pytest.fixture
def store(tmp_path: Path) -> SkillTelemetryStore:
    return SkillTelemetryStore(tmp_path / "telemetry.sqlite")


# ----- raw ledger -----------------------------------------------------


def test_store_records_and_returns_events_in_order(store: SkillTelemetryStore) -> None:
    store.record_success("edit", ts_unix=100.0)
    store.record_miss("edit", ts_unix=200.0)
    store.record_success("edit", ts_unix=300.0)

    events = store.events("edit")
    assert [e.ts_unix for e in events] == [100.0, 200.0, 300.0]
    assert [e.kind for e in events] == ["success", "miss", "success"]


def test_counts_returns_lifetime_aggregates(store: SkillTelemetryStore) -> None:
    for ts in (100.0, 200.0, 300.0):
        store.record_success("edit", ts_unix=ts)
    store.record_miss("edit", ts_unix=400.0)

    s, m = store.counts("edit")
    assert s == 3
    assert m == 1


def test_unknown_skill_has_empty_counts(store: SkillTelemetryStore) -> None:
    assert store.counts("never-seen") == (0, 0)
    assert store.events("never-seen") == []


def test_record_rejects_invalid_kind(store: SkillTelemetryStore) -> None:
    with pytest.raises(ValueError):
        store.record("edit", "exploded")  # type: ignore[arg-type]


# ----- decayed rate ---------------------------------------------------


def test_decayed_rate_cold_skill_returns_zero(store: SkillTelemetryStore) -> None:
    rate = store.decayed_rate("never-seen")
    assert rate.is_cold
    assert rate.rate == 0.0


def test_decayed_rate_recent_success_dominates(store: SkillTelemetryStore) -> None:
    """Recent success should outweigh an ancient miss past one half-life."""
    now = 1_000_000.0
    one_day = 86_400.0
    # Old miss (60 days ago, ~4 half-lives @ 14d → weight ≈ 1/16) and a
    # fresh success (now). Decayed rate should sit close to 1.0.
    store.record_miss("edit", ts_unix=now - 60 * one_day)
    store.record_success("edit", ts_unix=now)

    rate = store.decayed_rate("edit", half_life_days=14.0, now_unix=now)
    assert not rate.is_cold
    assert rate.rate > 0.9, f"expected ~1.0, got {rate.rate:.3f}"


def test_decayed_rate_old_skill_drifts_toward_zero_signal(
    store: SkillTelemetryStore,
) -> None:
    """An old success and an old miss at the same age should yield 0.5."""
    now = 1_000_000.0
    one_day = 86_400.0
    store.record_success("edit", ts_unix=now - 30 * one_day)
    store.record_miss("edit", ts_unix=now - 30 * one_day)

    rate = store.decayed_rate("edit", half_life_days=14.0, now_unix=now)
    assert rate.rate == pytest.approx(0.5, abs=1e-9)


def test_decayed_rate_rejects_nonpositive_half_life(
    store: SkillTelemetryStore,
) -> None:
    store.record_success("edit", ts_unix=100.0)
    with pytest.raises(ValueError):
        store.decayed_rate("edit", half_life_days=0.0)


def test_prune_before_drops_old_events(store: SkillTelemetryStore) -> None:
    store.record_success("edit", ts_unix=100.0)
    store.record_success("edit", ts_unix=500.0)
    dropped = store.prune_before(ts_unix=300.0)
    assert dropped == 1
    assert [e.ts_unix for e in store.events("edit")] == [500.0]


# ----- registry integration ------------------------------------------


def _make_skill(skill_id: str, triggers: tuple[str, ...] = ("foo",)) -> Skill:
    return Skill(id=skill_id, description=skill_id, triggers=triggers)


def test_registry_with_store_persists_records(tmp_path: Path) -> None:
    db = tmp_path / "telemetry.sqlite"
    store_a = SkillTelemetryStore(db)
    reg_a = SkillRegistry(telemetry_store=store_a)
    reg_a.register(_make_skill("edit"))
    reg_a.record_success("edit")
    reg_a.record_success("edit")
    reg_a.record_miss("edit")
    store_a.close()

    # Fresh process — counts should be restored from the ledger.
    store_b = SkillTelemetryStore(db)
    reg_b = SkillRegistry(telemetry_store=store_b)
    reg_b.register(_make_skill("edit"))
    skill = reg_b.get("edit")
    assert skill.success_count == 2
    assert skill.miss_count == 1


def test_registry_decayed_rate_returns_none_without_store() -> None:
    reg = SkillRegistry()
    reg.register(_make_skill("edit"))
    assert reg.decayed_rate("edit") is None


def test_registry_decayed_rate_uses_attached_store(tmp_path: Path) -> None:
    store = SkillTelemetryStore(tmp_path / "t.sqlite")
    reg = SkillRegistry(telemetry_store=store)
    reg.register(_make_skill("edit"))
    reg.record_success("edit")
    rate = reg.decayed_rate("edit")
    assert isinstance(rate, DecayedRate)
    assert rate.rate > 0.0
