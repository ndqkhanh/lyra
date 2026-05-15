"""Pure-logic tests for the ``/skills`` picker.

The full ``run_skills_dialog`` requires a TTY (``Application(full_screen=True)``),
so these tests cover the headless slice: entry construction, source
classification, sort mode cycling, and the toggle/diff machinery used
by the Enter/Esc paths.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from lyra_cli.interactive.dialog_skills import (
    _classify_source,
    _matches,
    _sort_entries,
    build_entries,
    _Entry,
)
from lyra_skills.state import SkillsState, with_toggled


def _write_skill(root: Path, sid: str, body: str = "do work.\nmore body.\n") -> None:
    sdir = root / sid
    sdir.mkdir(parents=True, exist_ok=True)
    (sdir / "SKILL.md").write_text(
        f"---\nid: {sid}\nname: {sid}\ndescription: {sid} desc\n---\n{body}",
        encoding="utf-8",
    )


# ── _classify_source ─────────────────────────────────────────────


def test_classify_source_packaged(tmp_path: Path) -> None:
    pkg = tmp_path / "pkg"
    (pkg / "alpha").mkdir(parents=True)
    skill_md = pkg / "alpha" / "SKILL.md"
    skill_md.touch()
    assert _classify_source(str(skill_md), pkg) == "packaged"


def test_classify_source_unknown_when_no_packaged_root(tmp_path: Path) -> None:
    skill_md = tmp_path / "loose.md"
    skill_md.touch()
    # Not under .lyra/ and no packaged_root → "unknown"
    assert _classify_source(str(skill_md), None) == "unknown"


# ── _sort_entries ────────────────────────────────────────────────


def _entry(sid: str, *, tokens: int = 100, source: str = "user", utility: float = 0.0) -> _Entry:
    return _Entry(
        skill_id=sid,
        description="d",
        source=source,
        tokens=tokens,
        locked=False,
        utility=utility,
    )


def test_sort_entries_by_name() -> None:
    rows = [_entry("zeta"), _entry("alpha"), _entry("mu")]
    out = _sort_entries(rows, "name")
    assert [e.skill_id for e in out] == ["alpha", "mu", "zeta"]


def test_sort_entries_by_tokens_desc() -> None:
    rows = [
        _entry("a", tokens=10),
        _entry("b", tokens=300),
        _entry("c", tokens=120),
    ]
    out = _sort_entries(rows, "tokens")
    assert [e.skill_id for e in out] == ["b", "c", "a"]


def test_sort_entries_by_source_then_id() -> None:
    rows = [
        _entry("a", source="user"),
        _entry("b", source="packaged"),
        _entry("c", source="packaged"),
    ]
    out = _sort_entries(rows, "source")
    assert [e.skill_id for e in out] == ["b", "c", "a"]


def test_sort_entries_by_utility_desc() -> None:
    rows = [
        _entry("a", utility=0.1),
        _entry("b", utility=0.9),
        _entry("c", utility=0.5),
    ]
    out = _sort_entries(rows, "utility")
    assert [e.skill_id for e in out] == ["b", "c", "a"]


def test_sort_entries_unknown_mode_falls_back_to_name() -> None:
    rows = [_entry("zeta"), _entry("alpha")]
    out = _sort_entries(rows, "totally-not-a-mode")
    assert [e.skill_id for e in out] == ["alpha", "zeta"]


# ── _matches ─────────────────────────────────────────────────────


def test_matches_empty_query_passes_everything() -> None:
    assert _matches(_entry("foo"), "") is True


def test_matches_query_against_id_description_source() -> None:
    e = _Entry(
        skill_id="surgical-changes",
        description="minimal edits",
        source="packaged",
        tokens=10,
        locked=True,
    )
    assert _matches(e, "surgical") is True
    assert _matches(e, "edits") is True
    assert _matches(e, "PACKAGED") is True
    assert _matches(e, "nope") is False


# ── build_entries ────────────────────────────────────────────────


def test_build_entries_includes_all_discovered_skills(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    project_skills = tmp_path / ".lyra" / "skills"
    project_skills.mkdir(parents=True)
    _write_skill(project_skills, "alpha")
    _write_skill(project_skills, "beta")
    monkeypatch.setattr(
        "lyra_cli.interactive.skills_inject._packaged_pack_root",
        lambda: None,
    )
    monkeypatch.setattr(
        "lyra_cli.interactive.skills_inject._user_skill_root",
        lambda: None,
    )

    out = build_entries(tmp_path, state=SkillsState())
    ids = sorted(e.skill_id for e in out)
    assert ids == ["alpha", "beta"]
    for e in out:
        assert e.locked is False
        assert e.tokens > 0


def test_build_entries_marks_packaged_as_locked(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    _write_skill(pkg, "shipped")

    project_skills = tmp_path / ".lyra" / "skills"
    project_skills.mkdir(parents=True)
    _write_skill(project_skills, "userland")

    monkeypatch.setattr(
        "lyra_cli.interactive.skills_inject._packaged_pack_root",
        lambda: pkg,
    )
    monkeypatch.setattr(
        "lyra_cli.interactive.skills_inject._user_skill_root",
        lambda: None,
    )

    out = {e.skill_id: e for e in build_entries(tmp_path, state=SkillsState())}
    assert out["shipped"].locked is True
    assert out["shipped"].source == "packaged"
    assert out["userland"].locked is False


def test_build_entries_routes_utility_resolver(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    project_skills = tmp_path / ".lyra" / "skills"
    project_skills.mkdir(parents=True)
    _write_skill(project_skills, "tracked")
    monkeypatch.setattr(
        "lyra_cli.interactive.skills_inject._packaged_pack_root",
        lambda: None,
    )
    monkeypatch.setattr(
        "lyra_cli.interactive.skills_inject._user_skill_root",
        lambda: None,
    )

    def fake_resolver(sid: str) -> float:
        return {"tracked": 0.42}.get(sid, 0.0)

    out = build_entries(
        tmp_path, state=SkillsState(), utility_resolver=fake_resolver
    )
    assert out[0].utility == 0.42


# ── toggle/diff invariants used by Enter handler ────────────────


def test_with_toggled_round_trip_clears_disabled() -> None:
    s = SkillsState()
    once = with_toggled(s, "foo", currently_active=True)
    twice = with_toggled(once, "foo", currently_active=False)
    assert twice.disabled == frozenset()


def test_changed_ids_reflects_xor_of_disabled_sets() -> None:
    """The Enter handler diffs ``initial.disabled ^ final.disabled``.

    Pinning the invariant: a single toggle yields a single id; a
    toggle-then-untoggle yields none.
    """
    initial = SkillsState()
    flipped = with_toggled(initial, "foo", currently_active=True)
    assert sorted(initial.disabled ^ flipped.disabled) == ["foo"]

    bounced = with_toggled(flipped, "foo", currently_active=False)
    assert sorted(initial.disabled ^ bounced.disabled) == []
