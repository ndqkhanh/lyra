"""Session manifest tests (v3.7 L37-3)."""
from __future__ import annotations

import pytest

from lyra_core.sessions.manifest import (
    GroupBy,
    SessionDirectory,
    SessionEntry,
    SessionFilter,
    SplitLayout,
    ViewKind,
)


def _e(sid: str, *, project: str = "p", branch: str = "main",
       status: str = "idle", title: str = "", agent: str = "") -> SessionEntry:
    return SessionEntry(
        session_id=sid, title=title or sid,
        project=project, branch=branch, status=status, agent=agent,
    )


# --- SessionDirectory + add/remove -----------------------------------------


def test_add_then_filter_returns_only_matching() -> None:
    d = SessionDirectory()
    d.add(_e("s1", project="alpha"))
    d.add(_e("s2", project="beta"))
    matches = d.filter(SessionFilter(project="alpha"))
    assert {e.session_id for e in matches} == {"s1"}


def test_add_duplicate_raises() -> None:
    d = SessionDirectory()
    d.add(_e("s1"))
    with pytest.raises(ValueError):
        d.add(_e("s1"))


def test_remove_drops_entry_and_view() -> None:
    d = SessionDirectory()
    d.add(_e("s1"))
    d.set_view("s1", ViewKind.PLAN)
    d.remove("s1")
    assert d.entries == []
    assert d.get_view("s1") is None


# --- Grouping --------------------------------------------------------------


def test_group_by_project_buckets_correctly() -> None:
    d = SessionDirectory()
    d.add(_e("s1", project="alpha"))
    d.add(_e("s2", project="alpha"))
    d.add(_e("s3", project="beta"))
    groups = d.group_by(GroupBy.PROJECT)
    labels = {g.label for g in groups}
    assert labels == {"alpha", "beta"}
    alpha = next(g for g in groups if g.label == "alpha")
    assert {e.session_id for e in alpha.entries} == {"s1", "s2"}


def test_group_by_with_filter_intersects() -> None:
    d = SessionDirectory()
    d.add(_e("s1", project="alpha", status="running"))
    d.add(_e("s2", project="alpha", status="idle"))
    d.add(_e("s3", project="beta", status="running"))
    groups = d.group_by(
        GroupBy.PROJECT,
        filter_spec=SessionFilter(status="running"),
    )
    assert {g.label for g in groups} == {"alpha", "beta"}
    alpha = next(g for g in groups if g.label == "alpha")
    assert {e.session_id for e in alpha.entries} == {"s1"}


def test_group_by_none_returns_single_all_group() -> None:
    d = SessionDirectory()
    d.add(_e("s1"))
    d.add(_e("s2"))
    groups = d.group_by(GroupBy.NONE)
    assert len(groups) == 1
    assert groups[0].label == "all"


# --- SessionFilter ---------------------------------------------------------


def test_filter_text_substring_match() -> None:
    d = SessionDirectory()
    d.add(_e("s1", title="Refactor the auth module"))
    d.add(_e("s2", title="Bump pytest"))
    matches = d.filter(SessionFilter(text="auth"))
    assert {e.session_id for e in matches} == {"s1"}


def test_filter_branch() -> None:
    d = SessionDirectory()
    d.add(_e("s1", branch="main"))
    d.add(_e("s2", branch="feature/x"))
    matches = d.filter(SessionFilter(branch="feature/x"))
    assert {e.session_id for e in matches} == {"s2"}


# --- ViewManifest ----------------------------------------------------------


def test_set_view_for_unknown_session_raises() -> None:
    d = SessionDirectory()
    with pytest.raises(KeyError):
        d.set_view("missing", ViewKind.DIFF)


def test_set_view_kinds_round_trip() -> None:
    d = SessionDirectory()
    d.add(_e("s1"))
    for kind in (ViewKind.PLAN, ViewKind.DIFF, ViewKind.FILES):
        manifest = d.set_view("s1", kind, payload={"k": kind.value})
        assert manifest.kind is kind
        assert d.get_view("s1").payload == {"k": kind.value}


# --- SplitLayout -----------------------------------------------------------


def test_split_layout_rejects_duplicate_panes() -> None:
    with pytest.raises(ValueError):
        SplitLayout(panes=("s1", "s1"))


def test_split_layout_rejects_unknown_orientation() -> None:
    with pytest.raises(ValueError):
        SplitLayout(panes=("s1",), orientation="diagonal")


def test_set_split_layout_validates_panes_in_directory() -> None:
    d = SessionDirectory()
    d.add(_e("s1"))
    d.set_split_layout(SplitLayout(panes=("s1",), orientation="horizontal"))
    with pytest.raises(KeyError):
        d.set_split_layout(SplitLayout(panes=("nope",)))
