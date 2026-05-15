"""Pure-logic tests for the ``/agents`` picker.

The interactive driver needs a TTY; these cover the headless slice:
catalog/live entry construction, sort modes, filter matching, and
the detail-rendering helpers in ``session.py`` that the picker hands
off to.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from lyra_cli.interactive.dialog_agents import (
    _CatalogEntry,
    _LiveEntry,
    _matches_catalog,
    _matches_live,
    _sort_catalog,
    _sort_live,
    build_catalog_entries,
    build_live_entries,
)


# ── catalog entries ──────────────────────────────────────────────


def _entry(
    name: str,
    *,
    model: str = "haiku",
    role: str = "leaf",
    source: str = "builtin",
    tools: tuple[str, ...] = (),
) -> _CatalogEntry:
    return _CatalogEntry(
        name=name,
        description=f"{name} desc",
        model=model,
        role=role,
        tools=tools,
        source=source,
    )


def test_build_catalog_includes_builtins(tmp_path: Path) -> None:
    """With an empty user_dir we still see explore/general/plan."""
    out = build_catalog_entries(user_dir=tmp_path / "missing")
    names = sorted(e.name for e in out)
    assert names == ["explore", "general", "plan"]
    # Built-in models pinned by presets._BUILTINS
    by_name = {e.name: e for e in out}
    assert by_name["explore"].model == "haiku"
    assert by_name["general"].model == "sonnet"
    assert by_name["plan"].model == "opus"
    assert all(e.source == "builtin" for e in out)


def test_build_catalog_picks_up_user_yaml(tmp_path: Path) -> None:
    user_dir = tmp_path / "agents"
    user_dir.mkdir()
    (user_dir / "test_runner.yaml").write_text(
        "name: test-runner\n"
        "description: runs the test suite\n"
        "model: sonnet\n"
        "role: leaf\n"
        "tools: [Read, Shell]\n",
        encoding="utf-8",
    )

    out = {e.name: e for e in build_catalog_entries(user_dir=user_dir)}
    assert "test-runner" in out
    assert out["test-runner"].source == "user"
    assert out["test-runner"].tools == ("Read", "Shell")


def test_build_catalog_marks_user_overrides_builtin(tmp_path: Path) -> None:
    user_dir = tmp_path / "agents"
    user_dir.mkdir()
    (user_dir / "explore.yaml").write_text(
        "name: explore\ndescription: my override\nmodel: opus\nrole: leaf\n",
        encoding="utf-8",
    )

    out = {e.name: e for e in build_catalog_entries(user_dir=user_dir)}
    assert out["explore"].source == "user-overrides-builtin"
    assert out["explore"].model == "opus"


# ── catalog sort ────────────────────────────────────────────────


def test_sort_catalog_by_name() -> None:
    rows = [_entry("zeta"), _entry("alpha"), _entry("mu")]
    out = _sort_catalog(rows, "name")
    assert [e.name for e in out] == ["alpha", "mu", "zeta"]


def test_sort_catalog_by_model() -> None:
    rows = [
        _entry("a", model="opus"),
        _entry("b", model="haiku"),
        _entry("c", model="sonnet"),
    ]
    out = _sort_catalog(rows, "model")
    assert [e.model for e in out] == ["haiku", "opus", "sonnet"]


def test_sort_catalog_by_source_then_name() -> None:
    rows = [
        _entry("a", source="user"),
        _entry("b", source="builtin"),
        _entry("c", source="builtin"),
    ]
    out = _sort_catalog(rows, "source")
    assert [e.name for e in out] == ["b", "c", "a"]


def test_sort_catalog_by_role() -> None:
    rows = [
        _entry("a", role="orchestrator"),
        _entry("b", role="leaf"),
    ]
    out = _sort_catalog(rows, "role")
    assert [e.role for e in out] == ["leaf", "orchestrator"]


def test_sort_catalog_unknown_mode_falls_back_to_name() -> None:
    rows = [_entry("zeta"), _entry("alpha")]
    out = _sort_catalog(rows, "totally-not-a-mode")
    assert [e.name for e in out] == ["alpha", "zeta"]


# ── catalog matches ─────────────────────────────────────────────


def test_matches_catalog_query_against_all_visible_columns() -> None:
    e = _CatalogEntry(
        name="explore",
        description="fast read-only search",
        model="haiku",
        role="leaf",
        tools=("Read", "Glob", "Grep"),
        source="builtin",
    )
    assert _matches_catalog(e, "")
    assert _matches_catalog(e, "explore")
    assert _matches_catalog(e, "READ-ONLY")
    assert _matches_catalog(e, "haiku")
    assert _matches_catalog(e, "leaf")
    assert _matches_catalog(e, "builtin")
    assert _matches_catalog(e, "Glob")
    assert not _matches_catalog(e, "kafka")


# ── live view ───────────────────────────────────────────────────


class _StubRecord:
    def __init__(self, rid: str, state: str, description: str = "", subagent_type: str = "") -> None:
        self.id = rid
        self.state = state
        self.description = description
        self.subagent_type = subagent_type


class _StubRegistry:
    def __init__(self, records: list[_StubRecord]) -> None:
        self._records = records

    def list_all(self) -> list[_StubRecord]:
        return list(self._records)


def test_build_live_entries_empty_when_no_registry() -> None:
    assert build_live_entries(None) == []


def test_build_live_entries_snapshots_records() -> None:
    reg = _StubRegistry(
        [
            _StubRecord("a-1", "running", "search", "explore"),
            _StubRecord("a-2", "done", "wrote module", "general"),
        ]
    )
    out = build_live_entries(reg)
    assert [e.record_id for e in out] == ["a-1", "a-2"]
    assert out[0].state == "running"
    assert out[1].subagent_type == "general"


def test_build_live_entries_swallows_registry_errors() -> None:
    class _Boom:
        def list_all(self) -> list[Any]:
            raise RuntimeError("bus on fire")

    assert build_live_entries(_Boom()) == []


def test_sort_live_by_state() -> None:
    rows = [
        _LiveEntry(record_id="a", state="running", description=""),
        _LiveEntry(record_id="b", state="done", description=""),
        _LiveEntry(record_id="c", state="pending", description=""),
    ]
    out = _sort_live(rows, "state")
    assert [e.state for e in out] == ["done", "pending", "running"]


def test_matches_live_searches_id_state_description_type() -> None:
    e = _LiveEntry(
        record_id="a-001", state="running", description="grep stuff", subagent_type="explore"
    )
    assert _matches_live(e, "001")
    assert _matches_live(e, "RUN")
    assert _matches_live(e, "grep")
    assert _matches_live(e, "explore")
    assert not _matches_live(e, "nope")


# ── session detail-render helpers ───────────────────────────────


def test_render_preset_detail_includes_spawn_hint() -> None:
    from lyra_cli.interactive.session import _render_preset_detail

    e = _CatalogEntry(
        name="explore",
        description="fast read-only",
        model="haiku",
        role="leaf",
        tools=("Read", "Grep"),
        source="builtin",
        aliases=("e",),
    )
    out = _render_preset_detail(e).output
    assert "explore" in out
    assert "haiku" in out
    assert "Read, Grep" in out
    assert "aliases" in out
    assert "/spawn --type explore" in out


def test_render_live_detail_includes_kill_hint() -> None:
    from lyra_cli.interactive.session import _render_live_detail

    e = _LiveEntry(
        record_id="agent-7",
        state="running",
        description="searching for the bug",
        subagent_type="explore",
    )
    out = _render_live_detail(e).output
    assert "agent-7" in out
    assert "running" in out
    assert "searching for the bug" in out
    assert "/agents kill agent-7" in out
