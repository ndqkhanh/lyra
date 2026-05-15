"""Tests for ``lyra_skills.state`` — per-skill enable/disable overrides.

The picker stores user-driven overrides in ``~/.lyra/skills_state.json``;
the inject layer consults this state to filter the advertised skill block.
Locked skills (i.e. shipped/packaged packs) cannot be disabled — the
picker hides the toggle and the state module enforces the invariant
defensively in case a hand-edit slips through.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from lyra_skills.state import (
    SkillsState,
    is_active,
    load_state,
    save_state,
)


# ── pure logic ───────────────────────────────────────────────────


def test_default_state_is_empty() -> None:
    s = SkillsState()
    assert s.enabled == frozenset()
    assert s.disabled == frozenset()


def test_is_active_default_on_for_unknown_skill() -> None:
    """Lyra ships every discovered skill enabled by default; an empty
    state must not silently turn anything off."""
    assert is_active("any-skill", locked=False, state=SkillsState()) is True


def test_is_active_locked_skills_are_always_active() -> None:
    """Locked skills (packaged packs) cannot be disabled even if the
    state file lists them — defensive invariant."""
    state = SkillsState(disabled=frozenset({"surgical-changes"}))
    assert is_active("surgical-changes", locked=True, state=state) is True


def test_is_active_disabled_overrides_default_on() -> None:
    state = SkillsState(disabled=frozenset({"foo"}))
    assert is_active("foo", locked=False, state=state) is False


def test_is_active_enabled_set_redundant_for_default_on() -> None:
    """``enabled`` is reserved for future opt-in skills; today it's
    a no-op for default-on skills but must not break them."""
    state = SkillsState(enabled=frozenset({"foo"}))
    assert is_active("foo", locked=False, state=state) is True


# ── persistence ──────────────────────────────────────────────────


def test_load_state_missing_file_returns_empty(tmp_path: Path) -> None:
    state = load_state(tmp_path / "skills_state.json")
    assert state == SkillsState()


def test_load_state_malformed_json_returns_empty(tmp_path: Path) -> None:
    p = tmp_path / "skills_state.json"
    p.write_text("not json {")
    assert load_state(p) == SkillsState()
    # corrupt file is renamed for post-mortem (matches ledger contract)
    assert (tmp_path / "skills_state.json.corrupt").is_file()


def test_save_then_load_round_trip(tmp_path: Path) -> None:
    p = tmp_path / "skills_state.json"
    state = SkillsState(
        enabled=frozenset({"a", "b"}),
        disabled=frozenset({"c"}),
    )
    save_state(state, p)
    assert load_state(p) == state


def test_save_state_writes_atomically(tmp_path: Path) -> None:
    """The temp file must not survive a successful save."""
    p = tmp_path / "skills_state.json"
    save_state(SkillsState(disabled=frozenset({"x"})), p)
    leftover = list(tmp_path.glob(".skills_state.*"))
    assert leftover == []


def test_save_state_creates_parent_dir(tmp_path: Path) -> None:
    p = tmp_path / "nested" / "dir" / "skills_state.json"
    save_state(SkillsState(disabled=frozenset({"y"})), p)
    assert p.is_file()


def test_save_state_json_is_stable(tmp_path: Path) -> None:
    """Sorted keys + sorted lists so two saves of equal state hash
    identically — handy for diff tools and tests."""
    p = tmp_path / "skills_state.json"
    save_state(
        SkillsState(disabled=frozenset({"z", "a", "m"})),
        p,
    )
    raw = json.loads(p.read_text())
    assert raw["disabled"] == ["a", "m", "z"]
    assert raw["enabled"] == []


# ── helpers used by the picker ──────────────────────────────────


def test_state_with_toggled_disabled_returns_new_instance() -> None:
    """The picker uses ``with_toggled`` to flip a skill without
    mutating the original — keeps undo trivial."""
    from lyra_skills.state import with_toggled

    state = SkillsState()
    flipped = with_toggled(state, "foo", currently_active=True)
    assert state.disabled == frozenset()  # original untouched
    assert flipped.disabled == frozenset({"foo"})


def test_state_with_toggled_re_enables() -> None:
    from lyra_skills.state import with_toggled

    state = SkillsState(disabled=frozenset({"foo"}))
    flipped = with_toggled(state, "foo", currently_active=False)
    assert flipped.disabled == frozenset()
