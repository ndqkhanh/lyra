"""Contract tests for Phase 4 sidebar tabs.

Two layers:

  * Pure data helpers (:mod:`lyra_cli.tui_v2.sidebar.data`) — exercised
    against ``tmp_path`` fixtures with real filesystem state.
  * Widget contract — each tab subclasses Static and exposes
    ``refresh_content()``; we instantiate without mounting and assert
    the rendered body matches expectations.

We do NOT mount a real Textual app; widgets are constructed
standalone and their ``refresh_content`` is called directly. That
gives full coverage of the rendering layer without driver overhead.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

from lyra_cli.tui_v2.sidebar import build_lyra_sidebar_tabs, data
from lyra_cli.tui_v2.sidebar.tabs import (
    McpTab,
    MemoryTab,
    PlansTab,
    SkillsTab,
)


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------


def _rendered(widget) -> str:
    """Run refresh_content and return the rendered string."""
    widget.refresh_content()
    return str(widget.renderable)


def _touch(path: Path, *, content: str = "", age_seconds: float = 0) -> Path:
    """Create ``path`` with ``content``; backdate mtime by ``age_seconds``."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    if age_seconds > 0:
        now = time.time()
        os.utime(path, (now - age_seconds, now - age_seconds))
    return path


# ---------------------------------------------------------------------
# Data: list_plans
# ---------------------------------------------------------------------


def test_list_plans_empty_when_no_dir(tmp_path: Path) -> None:
    assert data.list_plans(tmp_path) == []


def test_list_plans_finds_markdown_and_json(tmp_path: Path) -> None:
    _touch(tmp_path / ".lyra" / "plans" / "alpha.md", content="# alpha")
    _touch(tmp_path / ".lyra" / "plans" / "beta.json", content="{}")
    _touch(tmp_path / ".lyra" / "plans" / "ignore.txt", content="skip")
    entries = data.list_plans(tmp_path)
    names = {e["name"] for e in entries}
    assert names == {"alpha.md", "beta.json"}


def test_list_plans_sorts_newest_first(tmp_path: Path) -> None:
    _touch(tmp_path / ".lyra" / "plans" / "old.md", age_seconds=10_000)
    _touch(tmp_path / ".lyra" / "plans" / "new.md", age_seconds=10)
    entries = data.list_plans(tmp_path)
    assert [e["name"] for e in entries] == ["new.md", "old.md"]


def test_list_plans_dedupes_when_both_dirs_present(tmp_path: Path) -> None:
    """``.lyra/plans/`` and ``.lyra/plan/`` (singular) — same file name
    in each must not appear twice."""
    _touch(tmp_path / ".lyra" / "plans" / "spec.md")
    _touch(tmp_path / ".lyra" / "plan" / "other.md")
    names = [e["name"] for e in data.list_plans(tmp_path)]
    assert sorted(names) == ["other.md", "spec.md"]


# ---------------------------------------------------------------------
# Data: list_memory_files
# ---------------------------------------------------------------------


def test_list_memory_files_project_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_home = tmp_path / "home"
    monkeypatch.setattr("pathlib.Path.home", lambda: fake_home)
    # Reload sidebar.data so the module-level _GLOBAL_MEMORY picks up
    # the patched home. Easier: write _GLOBAL_MEMORY directly.
    monkeypatch.setattr(data, "_GLOBAL_MEMORY", fake_home / ".claude" / "memory")

    _touch(tmp_path / ".lyra" / "memory" / "note-a.md", content="a")
    _touch(tmp_path / ".lyra" / "memory" / "note-b.md", content="b")
    entries = data.list_memory_files(tmp_path)
    names = [e["name"] for e in entries]
    sources = {e["source"] for e in entries}
    assert sorted(names) == ["note-a", "note-b"]
    assert sources == {"project"}


def test_list_memory_files_skips_memory_index(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``MEMORY.md`` is the index file; it doesn't appear in the tab."""
    monkeypatch.setattr(data, "_GLOBAL_MEMORY", tmp_path / "no-such-dir")
    _touch(tmp_path / ".lyra" / "memory" / "MEMORY.md", content="index")
    _touch(tmp_path / ".lyra" / "memory" / "real-note.md", content="content")
    entries = data.list_memory_files(tmp_path)
    names = [e["name"] for e in entries]
    assert names == ["real-note"]


def test_list_memory_files_global_and_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    global_root = tmp_path / "home" / ".claude" / "memory"
    monkeypatch.setattr(data, "_GLOBAL_MEMORY", global_root)
    _touch(tmp_path / ".lyra" / "memory" / "local.md")
    _touch(global_root / "user_prefs.md")
    entries = data.list_memory_files(tmp_path)
    by_name = {e["name"]: e["source"] for e in entries}
    assert by_name == {"local": "project", "user_prefs": "global"}


# ---------------------------------------------------------------------
# Data: list_sidebar_skills + list_mcp_servers (adapters)
# ---------------------------------------------------------------------


def test_list_sidebar_skills_adapts_to_dict_shape(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Hide the user's real ~/.claude/skills directory so the test stays
    # hermetic. The slash-command helper reads _SKILLS_GLOBAL, not Path.home().
    from lyra_cli.tui_v2.commands import skills_mcp

    monkeypatch.setattr(skills_mcp, "_SKILLS_GLOBAL", tmp_path / "no-such-global")
    _touch(
        tmp_path / ".claude" / "skills" / "compose-haiku" / "SKILL.md",
        content="---\nname: compose-haiku\ndescription: 5-7-5 syllables.\n---\nbody",
    )
    entries = data.list_sidebar_skills(tmp_path)
    assert len(entries) == 1
    assert entries[0]["name"] == "compose-haiku"
    assert entries[0]["source"] == "project"
    assert "syllables" in entries[0]["description"]


def test_list_mcp_servers_adapts_to_dict_shape(tmp_path: Path) -> None:
    _touch(
        tmp_path / ".lyra" / "mcp.json",
        content=json.dumps({"mcpServers": {"db": {"command": "psql-mcp"}}}),
    )
    entries = data.list_mcp_servers(tmp_path)
    assert len(entries) == 1
    assert entries[0]["name"] == "db"
    assert "stdio" in entries[0]["transport"]


# ---------------------------------------------------------------------
# _relative_age formatting
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "delta_s,expected_prefix",
    [
        (5, "s"),
        (90, "m"),
        (3 * 3600, "h"),
        (3 * 86400, "d"),
    ],
)
def test_relative_age_buckets(delta_s: float, expected_prefix: str) -> None:
    now = 1_700_000_000.0
    age = data._relative_age(now - delta_s, now=now)
    assert age.endswith(expected_prefix), age


def test_relative_age_old_files_show_date() -> None:
    now = 1_700_000_000.0
    age = data._relative_age(now - 365 * 86400, now=now)
    # YYYY-MM-DD shape
    assert len(age) == 10 and age.count("-") == 2


# ---------------------------------------------------------------------
# Widgets — render contract
# ---------------------------------------------------------------------


def test_plans_tab_empty_state(tmp_path: Path) -> None:
    widget = PlansTab(tmp_path)
    body = _rendered(widget)
    assert "plans" in body.lower()
    assert "(0)" in body
    assert "no plans yet" in body.lower()


def test_plans_tab_with_entries(tmp_path: Path) -> None:
    _touch(tmp_path / ".lyra" / "plans" / "alpha.md", age_seconds=120)
    widget = PlansTab(tmp_path)
    body = _rendered(widget)
    assert "(1)" in body
    assert "alpha.md" in body


def test_skills_tab_renders_count_and_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from lyra_cli.tui_v2.commands import skills_mcp

    monkeypatch.setattr(skills_mcp, "_SKILLS_GLOBAL", tmp_path / "no-such-global")
    _touch(
        tmp_path / ".claude" / "skills" / "make-coffee" / "SKILL.md",
        content="---\nname: make-coffee\ndescription: Brew espresso.\n---\nBody.",
    )
    widget = SkillsTab(tmp_path)
    body = _rendered(widget)
    assert "(1)" in body
    assert "make-coffee" in body
    assert "project" in body


def test_mcp_tab_renders_servers(tmp_path: Path) -> None:
    _touch(
        tmp_path / ".lyra" / "mcp.json",
        content=json.dumps({"mcpServers": {"fs": {"command": "mcp-fs"}}}),
    )
    widget = McpTab(tmp_path)
    body = _rendered(widget)
    assert "(1)" in body
    assert "fs" in body
    assert "stdio" in body


def test_mcp_tab_empty_state(tmp_path: Path) -> None:
    widget = McpTab(tmp_path)
    body = _rendered(widget)
    assert "no MCP servers" in body


def test_memory_tab_renders_entries(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(data, "_GLOBAL_MEMORY", tmp_path / "no-such")
    _touch(tmp_path / ".lyra" / "memory" / "my-note.md", content="content")
    widget = MemoryTab(tmp_path)
    body = _rendered(widget)
    assert "(1)" in body
    assert "my-note" in body


# ---------------------------------------------------------------------
# Tab registry surface
# ---------------------------------------------------------------------


def test_build_lyra_sidebar_tabs_returns_four_pairs(tmp_path: Path) -> None:
    tabs = build_lyra_sidebar_tabs(tmp_path)
    labels = [label for label, _ in tabs]
    assert labels == ["Plans", "Skills", "MCP", "Memory", "Agents"]
    # Each widget instance is unique and a Textual widget.
    from textual.widget import Widget
    for _, widget in tabs:
        assert isinstance(widget, Widget)


def test_build_lyra_sidebar_tabs_handles_string_path(tmp_path: Path) -> None:
    """ProjectConfig.working_dir is a str; the builder must accept that."""
    tabs = build_lyra_sidebar_tabs(str(tmp_path))
    assert len(tabs) == 5
