"""Phase 4c — SkillCurator tier rules + report rendering."""
from __future__ import annotations

import time
from pathlib import Path

import pytest

from lyra_skills.curator import (
    TIER_KEEP,
    TIER_PROMOTE,
    TIER_RETIRE,
    TIER_REWRITE,
    TIER_WATCH,
    VALID_TIERS,
    curate,
    render_report_markdown,
)
from lyra_skills.ledger import (
    SkillLedger,
    SkillStats,
)

# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _write_skill(root: Path, skill_id: str, body_lines: int = 30) -> Path:
    """Write a minimal SKILL.md file with frontmatter and `body_lines` body lines."""
    sk_dir = root / skill_id
    sk_dir.mkdir(parents=True, exist_ok=True)
    skill_md = sk_dir / "SKILL.md"
    body = "\n".join(f"line {i} body" for i in range(body_lines))
    skill_md.write_text(
        f"""---
id: {skill_id}
name: {skill_id.title()}
description: A test skill named {skill_id}.
version: "1.0.0"
---

{body}
""",
        encoding="utf-8",
    )
    return skill_md


def _ledger_with(stats_list: list[SkillStats]) -> SkillLedger:
    """Build a ledger with pre-populated stats (no I/O)."""
    led = SkillLedger()
    for s in stats_list:
        led.skills[s.skill_id] = s
    return led


def _make_stats(
    skill_id: str,
    *,
    successes: int = 0,
    failures: int = 0,
    last_used_at: float = 0.0,
) -> SkillStats:
    """Build a SkillStats instance directly (no record path)."""
    s = SkillStats(skill_id=skill_id)
    s.successes = successes
    s.failures = failures
    s.last_used_at = last_used_at
    return s


# ---------------------------------------------------------------------------
# Per-tier tier-rule tests
# ---------------------------------------------------------------------------


def test_curator_promotes_high_utility_skill(tmp_path: Path) -> None:
    """A skill with 20 wins, 0 fails, recent — gets `promote`."""
    now = time.time()
    _write_skill(tmp_path, "tdd-discipline")
    led = _ledger_with([
        _make_stats("tdd-discipline", successes=20, failures=0, last_used_at=now - 3600),
    ])

    report = curate(skill_roots=[tmp_path], ledger=led, now_ts=now)

    assert len(report.skills) == 1
    assert report.skills[0].tier == TIER_PROMOTE
    assert report.skills[0].activations == 20
    assert "feature in /help" in report.skills[0].suggested_action.lower()


def test_curator_keeps_solid_skill(tmp_path: Path) -> None:
    """Solid utility, recent, but not promote-quality — `keep`.

    Note: the ledger's `utility_score` uses (s - f) / (s + f), so we
    need a high success ratio to clear `keep_min_utility = 0.65`.
    9w/1f → base 0.8, +recency ≈ 0.88 → above keep, below promote
    (because activations < 10).
    """
    now = time.time()
    _write_skill(tmp_path, "ok-skill")
    led = _ledger_with([
        _make_stats("ok-skill", successes=9, failures=1, last_used_at=now - 3600),
    ])

    # The 9w/1f setup actually clears the PROMOTE bar (10 activations
    # exactly = promote_min_activations and utility 0.88 > 0.85). To
    # exercise the KEEP tier we need a strong utility but
    # activations < promote_min_activations.
    _ = curate(skill_roots=[tmp_path], ledger=led, now_ts=now)
    led_keep = _ledger_with([
        _make_stats("ok-skill", successes=6, failures=0, last_used_at=now - 3600),
    ])
    report_keep = curate(skill_roots=[tmp_path], ledger=led_keep, now_ts=now)
    assert report_keep.skills[0].tier == TIER_KEEP


def test_curator_marks_low_utility_short_skill_for_rewrite(tmp_path: Path) -> None:
    """utility < 0.40, file < 250 lines — `rewrite` (suggest reflect)."""
    now = time.time()
    _write_skill(tmp_path, "low-util", body_lines=10)
    led = _ledger_with([
        _make_stats("low-util", successes=2, failures=8, last_used_at=now - 3600),
    ])

    report = curate(skill_roots=[tmp_path], ledger=led, now_ts=now)
    r = report.skills[0]
    assert r.tier == TIER_REWRITE
    assert "lyra skill reflect low-util" in r.suggested_action


def test_curator_retires_stale_zero_utility_skill(tmp_path: Path) -> None:
    """utility < 0.20, ≥5 activations, ≥90 days stale — `retire`."""
    now = time.time()
    _write_skill(tmp_path, "abandoned")
    led = _ledger_with([
        _make_stats("abandoned", successes=1, failures=9, last_used_at=now - 100 * 86400),
    ])

    report = curate(skill_roots=[tmp_path], ledger=led, now_ts=now)
    r = report.skills[0]
    assert r.tier == TIER_RETIRE
    assert "lyra skill rm abandoned" in r.suggested_action


def test_curator_watches_unactivated_skill(tmp_path: Path) -> None:
    """A skill with no ledger entry stays in `watch` for first-use signal."""
    _write_skill(tmp_path, "brand-new")
    # Empty ledger — no stats for this skill at all.
    report = curate(skill_roots=[tmp_path], ledger=SkillLedger(), now_ts=time.time())

    r = report.skills[0]
    assert r.tier == TIER_WATCH
    assert r.activations == 0


# ---------------------------------------------------------------------------
# Aggregate behaviour
# ---------------------------------------------------------------------------


def test_curator_summary_counts_each_tier(tmp_path: Path) -> None:
    now = time.time()
    _write_skill(tmp_path, "promo")
    _write_skill(tmp_path, "keep1")
    _write_skill(tmp_path, "watch1")
    _write_skill(tmp_path, "rewrite1")
    led = _ledger_with([
        _make_stats("promo",   successes=20, failures=0, last_used_at=now - 60),
        _make_stats("keep1",   successes=6,  failures=2, last_used_at=now - 60),
        _make_stats("watch1",  successes=3,  failures=2, last_used_at=now - 60),
        _make_stats("rewrite1", successes=1, failures=4, last_used_at=now - 60),
    ])

    report = curate(skill_roots=[tmp_path], ledger=led, now_ts=now)
    summary = report.summary()

    # Every tier key present (even if zero):
    for tier in VALID_TIERS:
        assert tier in summary
    # Sum of tier counts equals number of skills:
    assert sum(summary.values()) == 4


def test_curator_render_markdown_contains_tier_sections(tmp_path: Path) -> None:
    now = time.time()
    _write_skill(tmp_path, "promo")
    led = _ledger_with([
        _make_stats("promo", successes=20, failures=0, last_used_at=now - 60),
    ])
    report = curate(skill_roots=[tmp_path], ledger=led, now_ts=now)

    md = render_report_markdown(report)
    assert "# Skill Curator Report" in md
    assert "## Summary" in md
    assert "promote" in md.lower()
    assert "`promo`" in md  # backtick-rendered skill id


# ---------------------------------------------------------------------------
# by_tier guard
# ---------------------------------------------------------------------------


def test_by_tier_rejects_unknown_tier() -> None:
    from lyra_skills.curator import CuratorReport

    rep = CuratorReport()
    with pytest.raises(ValueError, match="unknown tier"):
        rep.by_tier("not-a-real-tier")
