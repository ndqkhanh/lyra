"""Phase O.1 — Skill ledger tests.

The ledger is the bookkeeping half of Memento-style Read-Write
Reflective Learning. It records per-skill activation outcomes
(successes, failures, neutral activations) so the Write phase
(``lyra skill reflect``) and the recency-boosted utility score
have something to feed on.

Schema invariants exercised here:

* ``SkillStats.utility`` is always in ``[-1.0, +recency_cap]`` and
  ``0.0`` for an unused skill (so a brand-new skill doesn't get
  punished or rewarded before any data exists).
* ``record_outcome`` is RMW: load → mutate → atomic save. Subsequent
  ``load_ledger`` calls see the change.
* The history list is capped (``MAX_HISTORY``) so a long-lived ledger
  doesn't grow unboundedly.
* ``default_ledger_path`` honours ``LYRA_HOME`` for sandboxed/test
  setups.
* Corrupt JSON is renamed aside (``.corrupt``) so the next load
  starts fresh — losing the ledger is recoverable, locking up the
  CLI is not.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lyra_skills.ledger import (
    MAX_HISTORY,
    OUTCOME_FAILURE,
    OUTCOME_NEUTRAL,
    OUTCOME_SUCCESS,
    SkillLedger,
    SkillOutcome,
    SkillStats,
    default_ledger_path,
    load_ledger,
    record_outcome,
    save_ledger,
    top_n,
    utility_score,
)


# ── SkillStats / utility_score ────────────────────────────────────


def test_utility_zero_when_unused() -> None:
    s = SkillStats(skill_id="x")
    assert utility_score(s) == 0.0
    assert s.utility == 0.0


def test_utility_positive_one_when_only_successes() -> None:
    s = SkillStats(skill_id="x", successes=5)
    assert utility_score(s) == pytest.approx(1.0)


def test_utility_negative_one_when_only_failures() -> None:
    s = SkillStats(skill_id="x", failures=3)
    assert utility_score(s) == pytest.approx(-1.0)


def test_utility_balanced_signs_around_zero() -> None:
    s = SkillStats(skill_id="x", successes=2, failures=2)
    assert -0.05 <= utility_score(s) <= 0.05


def test_utility_recency_boost_prefers_fresh_use(tmp_path: Path) -> None:
    fresh = SkillStats(
        skill_id="fresh",
        successes=3,
        failures=1,
        last_used_at=_days_ago(0.5),
    )
    stale = SkillStats(
        skill_id="stale",
        successes=3,
        failures=1,
        last_used_at=_days_ago(60),
    )
    assert utility_score(fresh) > utility_score(stale)


# ── record_outcome / persistence ──────────────────────────────────


def test_record_outcome_increments_success(tmp_path: Path) -> None:
    p = tmp_path / "ledger.json"
    record_outcome(
        "tdd-discipline",
        SkillOutcome(
            ts=1.0,
            session_id="abc",
            turn=1,
            kind=OUTCOME_SUCCESS,
            detail="all green",
        ),
        path=p,
    )
    led = load_ledger(p)
    s = led.get("tdd-discipline")
    assert s.successes == 1
    assert s.failures == 0
    assert s.last_used_at == 1.0


def test_record_outcome_failure_keeps_last_reason(tmp_path: Path) -> None:
    p = tmp_path / "ledger.json"
    record_outcome(
        "atomic-skills",
        SkillOutcome(
            ts=2.0,
            session_id="s",
            turn=4,
            kind=OUTCOME_FAILURE,
            detail="tool returned non-zero",
            error_kind="execution_error",
        ),
        path=p,
    )
    s = load_ledger(p).get("atomic-skills")
    assert s.failures == 1
    assert s.last_failure_reason == "tool returned non-zero"
    assert s.history[-1].error_kind == "execution_error"


def test_record_outcome_neutral_does_not_change_counts(tmp_path: Path) -> None:
    p = tmp_path / "ledger.json"
    record_outcome(
        "skill-a",
        SkillOutcome(ts=1.0, session_id="s", turn=1, kind=OUTCOME_NEUTRAL),
        path=p,
    )
    s = load_ledger(p).get("skill-a")
    assert s.successes == 0
    assert s.failures == 0
    assert s.last_used_at == 1.0
    assert s.history[-1].kind == OUTCOME_NEUTRAL


def test_history_is_capped(tmp_path: Path) -> None:
    p = tmp_path / "ledger.json"
    for i in range(MAX_HISTORY + 25):
        record_outcome(
            "noisy",
            SkillOutcome(
                ts=float(i),
                session_id=f"s{i}",
                turn=i,
                kind=OUTCOME_SUCCESS,
            ),
            path=p,
        )
    s = load_ledger(p).get("noisy")
    assert s.successes == MAX_HISTORY + 25
    assert len(s.history) == MAX_HISTORY
    assert s.history[0].ts == float(25)


def test_outcome_rejects_unknown_kind() -> None:
    with pytest.raises(ValueError):
        SkillOutcome(ts=0.0, session_id="s", turn=0, kind="weird")


# ── load / save round-trip ────────────────────────────────────────


def test_load_missing_file_returns_empty(tmp_path: Path) -> None:
    led = load_ledger(tmp_path / "nope.json")
    assert isinstance(led, SkillLedger)
    assert led.skills == {}


def test_save_then_load_round_trips(tmp_path: Path) -> None:
    p = tmp_path / "ledger.json"
    led = SkillLedger()
    led.record(
        "x",
        SkillOutcome(ts=1.0, session_id="s", turn=1, kind=OUTCOME_SUCCESS),
    )
    save_ledger(led, p)

    loaded = load_ledger(p)
    assert "x" in loaded.skills
    assert loaded.get("x").successes == 1


def test_corrupt_ledger_is_renamed_aside(tmp_path: Path) -> None:
    p = tmp_path / "ledger.json"
    p.write_text("{not valid json", encoding="utf-8")
    led = load_ledger(p)
    assert led.skills == {}
    corrupt = p.with_suffix(p.suffix + ".corrupt")
    assert corrupt.exists()


def test_save_is_atomic_no_temp_litter(tmp_path: Path) -> None:
    p = tmp_path / "ledger.json"
    save_ledger(SkillLedger(), p)
    siblings = [child.name for child in tmp_path.iterdir()]
    leftover = [s for s in siblings if s.startswith(".ledger.")]
    assert leftover == []


# ── top_n / sorting ───────────────────────────────────────────────


def test_top_n_orders_by_utility_descending(tmp_path: Path) -> None:
    p = tmp_path / "l.json"
    record_outcome("hot", SkillOutcome(ts=1.0, session_id="s", turn=1, kind=OUTCOME_SUCCESS), path=p)
    record_outcome("hot", SkillOutcome(ts=2.0, session_id="s", turn=2, kind=OUTCOME_SUCCESS), path=p)
    record_outcome("cold", SkillOutcome(ts=3.0, session_id="s", turn=3, kind=OUTCOME_FAILURE), path=p)
    record_outcome("cold", SkillOutcome(ts=4.0, session_id="s", turn=4, kind=OUTCOME_FAILURE), path=p)
    record_outcome("mixed", SkillOutcome(ts=5.0, session_id="s", turn=5, kind=OUTCOME_SUCCESS), path=p)
    record_outcome("mixed", SkillOutcome(ts=6.0, session_id="s", turn=6, kind=OUTCOME_FAILURE), path=p)

    led = load_ledger(p)
    ids = [s.skill_id for s in top_n(led, n=10)]
    assert ids[0] == "hot"
    assert ids[-1] == "cold"


# ── default_ledger_path / LYRA_HOME ───────────────────────────────


def test_default_ledger_path_honours_lyra_home(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LYRA_HOME", str(tmp_path))
    p = default_ledger_path()
    assert p == tmp_path / "skill_ledger.json"


def test_default_ledger_path_falls_back_to_home(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("LYRA_HOME", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    p = default_ledger_path()
    assert p == tmp_path / ".lyra" / "skill_ledger.json"


# ── helpers ───────────────────────────────────────────────────────


def _days_ago(d: float) -> float:
    import time

    return time.time() - d * 24 * 3600


def test_ledger_dict_round_trip_through_json(tmp_path: Path) -> None:
    p = tmp_path / "ledger.json"
    record_outcome(
        "x",
        SkillOutcome(ts=1.0, session_id="s", turn=1, kind=OUTCOME_SUCCESS),
        path=p,
    )
    raw = json.loads(p.read_text(encoding="utf-8"))
    assert raw["version"] == 1
    assert "x" in raw["skills"]
    entry = raw["skills"]["x"]
    assert entry["successes"] == 1
    assert entry["history"][0]["kind"] == OUTCOME_SUCCESS
